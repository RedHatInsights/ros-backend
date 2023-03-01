import json
from ros.lib import consume, produce
from ros.lib.app import app, db
from datetime import datetime, timezone
from confluent_kafka import KafkaException
from ros.lib.models import RhAccount, System
from ros.lib.config import ENGINE_RESULT_TOPIC, get_logger
from ros.processor.process_archive import get_performance_profile
from ros.processor.event_producer import new_suggestion_event
from ros.lib.utils import (
    get_or_create,
    cast_iops_as_float,
    insert_performance_profiles,
    validate_type
)
from ros.processor.metrics import (processor_requests_success,
                                   processor_requests_failures,
                                   kafka_failures)

SYSTEM_STATES = {
    "INSTANCE_OVERSIZED": "Oversized",
    "INSTANCE_UNDERSIZED": "Undersized",
    "INSTANCE_IDLE": "Idling",
    "INSTANCE_OPTIMIZED_UNDER_PRESSURE": "Under pressure",
    "STORAGE_RIGHTSIZING": "Storage rightsizing",
    "OPTIMIZED": "Optimized",
    "NO_PCP_DATA": "Waiting for data"
}
OPTIMIZED_SYSTEM_KEY = "OPTIMIZED"
LOG = get_logger(__name__)

producer = None


class InsightsEngineResultConsumer:
    def __init__(self):
        """Create Engine Consumer."""
        self.consumer = consume.init_consumer(ENGINE_RESULT_TOPIC)

        self.prefix = 'PROCESSING ENGINE RESULTS'
        self.reporter = 'INSIGHTS ENGINE'

    def __iter__(self):
        return self

    def __next__(self):
        msg = self.consumer.poll()
        if msg is None:
            raise StopIteration
        return msg

    def run(self):
        LOG.info("%s - Processor is running. Awaiting msgs.", self.prefix)

        # initialize producer
        global producer
        producer = produce.init_producer()

        for msg in iter(self):
            if msg.error():
                LOG.error("%s - Consumer error: %s", self.prefix, msg.error())
                kafka_failures.labels(reporter=self.reporter).inc()
                raise KafkaException(msg.error())
            try:
                msg = json.loads(msg.value().decode("utf-8"))
                self.handle_msg(msg)
            except json.decoder.JSONDecodeError:
                kafka_failures.labels(reporter=self.reporter).inc()
                LOG.error(
                    '%s - Unable to decode kafka message: %s',
                    self.prefix, msg.value()
                )
            except Exception as err:
                processor_requests_failures.labels(
                    reporter=self.reporter,
                    org_id=msg["input"]["platform_metadata"].get('org_id')
                ).inc()
                LOG.error(
                    "%s - An error occurred during message processing: %s",
                    self.prefix,
                    repr(err)
                )
            finally:
                self.consumer.commit()

    def handle_msg(self, msg):
        is_ros_flag = validate_type(msg["input"]["platform_metadata"]["is_ros"], bool)
        if is_ros_flag is True:
            host = msg["input"]["host"]
            platform_metadata = msg["input"]["platform_metadata"]
            system_metadata = msg["results"]["system"]["metadata"]
            performance_record = get_performance_profile(
                platform_metadata['url'],
                platform_metadata.get('org_id'),
                custom_prefix=self.prefix
            )
            reports = msg["results"]["reports"]  \
                if msg["results"]["reports"] \
                and type(msg["results"]["reports"]) == list \
                else []
            ros_reports = [
                report for report in reports
                if 'ros_instance_evaluation' in report["rule_id"]
            ]
            self.process_report(host, platform_metadata, ros_reports, system_metadata, performance_record)

    def process_report(self, host, platform_metadata, reports, system_metadata, performance_record):
        """create/update system and performance_profile based on reports data."""
        with app.app_context():
            try:
                account = get_or_create(
                    db.session, RhAccount, 'account',
                    account=host['account'],
                    org_id=platform_metadata.get('org_id')
                )
                if len(reports) == 0:
                    rec_count = len(reports)
                    state_key = OPTIMIZED_SYSTEM_KEY
                    LOG.info(
                        "%s - No ROS rule hits found for system with inventory id: %s. Hence, marking the state as %s.",
                        self.prefix, host['id'], SYSTEM_STATES[state_key])
                else:
                    state_key = reports[0].get('key')
                    rec_count = 0 if state_key == 'NO_PCP_DATA' else len(reports)
                    LOG.info(
                        "%s - Marking the state of system with inventory id: %s as %s.",
                        self.prefix, host['id'], SYSTEM_STATES[state_key])

                # get previous state of the system
                system_previous_state = db.session.query(System.state) \
                    .filter(System.inventory_id == host['id']).first()

                system_attrs = {
                    'tenant_id': account.id,
                    'inventory_id': host['id'],
                    'display_name': host['display_name'],
                    'fqdn': host['fqdn'],
                    'state': SYSTEM_STATES[state_key],
                    'instance_type': performance_record.get('instance_type'),
                    'region': performance_record.get('region'),
                    'cloud_provider': system_metadata.get('cloud_provider')
                }

                # get current state of the system
                system_current_state = system_attrs['state']

                if reports and 'states' in reports[0]['details'].keys():
                    substates = reports[0]['details']['states']
                else:
                    substates = {}

                system_attrs.update({
                    'cpu_states': substates.get('cpu'),
                    'io_states': substates.get('io'),
                    'memory_states': substates.get('memory')
                })

                system = get_or_create(
                    db.session, System, 'inventory_id', **system_attrs)
                LOG.info(
                    "%s - System created/updated successfully: %s", self.prefix, host['id']
                )

                set_default_utilization = False
                # For Optimized state, reports would be empty, but system_metadata would be present
                if reports and reports[0].get('key') == 'NO_PCP_DATA':
                    set_default_utilization = True

                if set_default_utilization is False:
                    performance_utilization = {
                        'memory': int(system_metadata['mem_utilization']),
                        'cpu': int(system_metadata['cpu_utilization']),
                        'io': cast_iops_as_float(system_metadata['io_utilization'])
                    }
                    # max_io will be used to sort systems endpoint response instead of io
                    performance_utilization.update(
                       {'max_io': max(performance_utilization['io'].values())}
                    )
                else:
                    LOG.debug("%s - Setting default utilization for performance profile", self.prefix)
                    performance_utilization = {
                        'memory': -1,
                        'cpu': -1,
                        'max_io': -1.0,
                        'io': {}
                    }
                # Following are saved on respective system record
                del performance_record['instance_type']
                del performance_record['region']

                pprofile_fields = {
                    "system_id": system.id,
                    "performance_record": performance_record,
                    "performance_utilization": performance_utilization,
                    "report_date": datetime.now(timezone.utc),
                    "rule_hit_details": reports,
                    "number_of_recommendations": -1 if state_key == 'NO_PCP_DATA' else rec_count,
                    "state": SYSTEM_STATES[state_key],
                    "operating_system": system.operating_system,
                    'psi_enabled': system_metadata.get('psi_enabled'),
                }
                insert_performance_profiles(
                    db.session, system.id, pprofile_fields)
                LOG.info(
                    "%s - Performance profile created/updated successfully for the system: %s", self.prefix, host['id']
                )
                db.session.commit()

                # Trigger event for notification
                self.trigger_notification(
                    system.inventory_id, account, host, platform_metadata, system_previous_state, system_current_state
                )

                processor_requests_success.labels(
                    reporter=self.reporter, org_id=account.org_id
                ).inc()
                LOG.info("%s - Refreshed system %s (%s) belonging to account: %s (%s) and org_id: %s.",
                         self.prefix, system.inventory_id, system.id, account.account, account.id, account.org_id)
            except Exception as err:
                processor_requests_failures.labels(
                    reporter=self.reporter, org_id=account.org_id
                ).inc()
                LOG.error("%s - Unable to add system %s to DB belonging to account: %s and org_id: %s - %s",
                          self.prefix, host['id'], account.account, account.org_id, err)

    def trigger_notification(
        self, inventory_id, account, host, platform_metadata, system_previous_state, system_current_state
    ):
        if system_previous_state[0] is not None:
            if system_current_state not in (SYSTEM_STATES['OPTIMIZED'], system_previous_state[0]):
                LOG.info(
                    "%s - Triggering a new suggestion event for the system: %s belonging" +
                    "to account: %s (%s) and org_id: %s",
                    self.prefix, inventory_id, account.account, account.id, account.org_id
                )
                new_suggestion_event(host, platform_metadata, system_previous_state, system_current_state, producer)
