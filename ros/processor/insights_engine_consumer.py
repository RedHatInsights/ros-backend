import json
from ros.lib import consume, produce
from ros.lib.app import app
from ros.extensions import db, cache
from datetime import datetime, timezone
from confluent_kafka import KafkaException
from ros.lib.models import RhAccount, System
from ros.lib.config import (
    ENGINE_RESULT_TOPIC,
    METRICS_PORT,
    get_logger,
    CACHE_KEYWORD_FOR_DELETED_SYSTEM
)
from ros.processor.process_archive import get_performance_profile
from ros.processor.event_producer import new_suggestion_event
from ros.lib.cw_logging import commence_cw_log_streaming, threadctx
from prometheus_client import start_http_server
from ros.lib.constants import SystemStatesWithKeys
from ros.lib.utils import (
    get_or_create,
    cast_iops_as_float,
    insert_performance_profiles,
    system_allowed_in_ros,
)
from ros.processor.metrics import (processor_requests_success,
                                   processor_requests_failures,
                                   kafka_failures)

LOG = get_logger(__name__)

producer = None


def topmost_candidate_from_rule_hit(reports, state_key):
    if state_key in ["OPTIMIZED", "NO_PCP_DATA"]:
        return [None, None]
    all_instances = reports[0]['details']['candidates']
    return all_instances[0]


class InsightsEngineConsumer:
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
        LOG.info(f"{self.prefix} - Processor is running. Awaiting msgs.")

        # initialize producer
        global producer
        producer = produce.init_producer()

        for msg in iter(self):
            if msg.error():
                LOG.error(f"{self.prefix} - Consumer error: {msg.error()}")
                kafka_failures.labels(reporter=self.reporter).inc()
                raise KafkaException(msg.error())
            try:
                msg = json.loads(msg.value().decode("utf-8"))
                self.handle_msg(msg)
            except json.decoder.JSONDecodeError:
                kafka_failures.labels(reporter=self.reporter).inc()
                LOG.error(
                    f"{self.prefix} - Unable to decode kafka message: {msg.value()}"
                )
            except Exception as err:
                processor_requests_failures.labels(
                    reporter=self.reporter,
                    org_id=msg["input"]["platform_metadata"].get('org_id')
                ).inc()
                LOG.error(
                    f"{self.prefix} - An error occurred during message processing: {repr(err)}"
                )
            finally:
                self.consumer.commit()

    def handle_msg(self, msg):
        with app.app_context():
            if system_allowed_in_ros(msg, self.reporter):
                host = msg["input"]["host"]
                platform_metadata = msg["input"]["platform_metadata"]
                system_metadata = msg["results"]["system"]["metadata"]

                threadctx.request_id = platform_metadata.get('request_id')
                threadctx.account = platform_metadata.get('account')
                threadctx.org_id = platform_metadata.get('org_id')

                cache_key = (f"{platform_metadata.get('org_id')}"
                             f"{CACHE_KEYWORD_FOR_DELETED_SYSTEM}{host['id']}")
                if cache.get(cache_key):
                    LOG.info(
                        f"{self.prefix} - Received a msg for deleted system "
                        f" with inventory id: {host['id']}.Hence, rejecting a msg."
                    )
                    return
                performance_record = get_performance_profile(
                    platform_metadata['url'],
                    platform_metadata.get('org_id'),
                    host['id'],
                    custom_prefix=self.prefix
                )

                reports = []
                if msg["results"]["reports"] \
                        and isinstance(msg["results"]["reports"], list):
                    reports = msg["results"]["reports"]
                ros_reports = [
                    report for report in reports
                    if 'ros_instance_evaluation' in report["rule_id"]
                ]
                self.process_report(host, platform_metadata, ros_reports,
                                    system_metadata, performance_record)

    def process_report(self, host, platform_metadata, reports, system_metadata, performance_record):
        """create/update system and performance_profile based on reports data."""
        with app.app_context():
            try:
                account = get_or_create(
                    db.session, RhAccount, 'org_id',
                    account=host['account'],
                    org_id=platform_metadata.get('org_id')
                )
                if len(reports) == 0:
                    rec_count = len(reports)
                    state_key = "OPTIMIZED"
                    LOG.info(
                        f"{self.prefix} - No ROS rule hits found for system with inventory id: {host['id']}. "
                        f"Hence, marking the state as {SystemStatesWithKeys[state_key].value}."
                    )
                else:
                    state_key = reports[0].get('key')
                    rec_count = 0 if state_key == 'NO_PCP_DATA' else len(reports)
                    LOG.info(
                        f"{self.prefix} - Marking the state of system with "
                        f"inventory id: {host['id']} as {SystemStatesWithKeys[state_key].value}"
                    )

                # get previous state of the system
                system_previous_state = db.session.scalar(db.select(System.state)
                                                          .filter(System.inventory_id == host['id']))

                system_attrs = {
                    'tenant_id': account.id,
                    'inventory_id': host['id'],
                    'display_name': host['display_name'],
                    'fqdn': host['fqdn'],
                    'state': SystemStatesWithKeys[state_key].value,
                    'instance_type': performance_record.get('instance_type'),
                    'region': performance_record.get('region'),
                    'cloud_provider': system_metadata.get('cloud_provider'),
                    'groups': host.get('groups', [])
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
                    f"{self.prefix} - System {host['id']} created/updated successfully."
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
                    LOG.debug(f"{self.prefix} - Setting default utilization for performance profile")
                    performance_utilization = {
                        'memory': -1,
                        'cpu': -1,
                        'max_io': -1.0,
                        'io': {}
                    }
                # Following are saved on respective system record
                del performance_record['instance_type']
                del performance_record['region']

                top_candidate, top_candidate_price = topmost_candidate_from_rule_hit(reports, state_key)
                pprofile_fields = {
                    "system_id": system.id,
                    "performance_record": performance_record,
                    "performance_utilization": performance_utilization,
                    "report_date": datetime.now(timezone.utc),
                    "rule_hit_details": reports,
                    "number_of_recommendations": -1 if state_key == 'NO_PCP_DATA' else rec_count,
                    "state": SystemStatesWithKeys[state_key].value,
                    "operating_system": system.operating_system,
                    'psi_enabled': system_metadata.get('psi_enabled'),
                    'top_candidate': top_candidate,
                    'top_candidate_price': top_candidate_price,
                }

                insert_performance_profiles(
                    db.session, system.id, pprofile_fields)
                LOG.info(
                    f"{self.prefix} - Performance profile created/updated successfully for the system: {host['id']}"
                )
                db.session.commit()

                # Trigger event for notification
                self.trigger_notification(
                    system.inventory_id, account, host, platform_metadata, system_previous_state, system_current_state
                )

                processor_requests_success.labels(
                    reporter=self.reporter, org_id=account.org_id
                ).inc()
                LOG.info(
                    f"{self.prefix} - Refreshed system {system.inventory_id} ({system.id}) "
                    f"belonging to account: {account.account} ({account.id}) and org_id: {account.org_id}"
                )
            except Exception as err:
                processor_requests_failures.labels(
                    reporter=self.reporter, org_id=account.org_id
                ).inc()
                LOG.error(
                    f"{self.prefix} - Unable to add system {host['id']} to DB "
                    f"belonging to account: {account.account} "
                    f"and org_id: {account.org_id} - {repr(err)}"
                )

    def trigger_notification(
            self, inventory_id, account, host, platform_metadata, system_previous_state, system_current_state
    ):
        if system_previous_state is not None:
            if system_current_state not in (
                SystemStatesWithKeys.OPTIMIZED.value,
                system_previous_state
            ):
                LOG.info(
                    f"{self.prefix} - Triggering a new suggestion event for the system: {inventory_id} belonging"
                    f" to account: {account.account} ({account.id}) and org_id: {account.org_id}"
                )
                new_suggestion_event(host, platform_metadata, system_previous_state, system_current_state, producer)


if __name__ == "__main__":
    start_http_server(int(METRICS_PORT))
    cache.init_app(app)
    commence_cw_log_streaming('ros-processor')
    processor = InsightsEngineConsumer()
    processor.run()
