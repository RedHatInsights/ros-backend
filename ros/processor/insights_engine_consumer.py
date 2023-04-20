import json
from ros.lib import consume, produce
from ros.lib.app import app
from ros.extensions import db
from datetime import datetime, timezone
from ros.lib.models import RhAccount, System
from ros.lib.config import ENGINE_RESULT_TOPIC, METRICS_PORT
from ros.processor.process_archive import get_performance_profile
from ros.processor.event_producer import new_suggestion_event
from ros.lib.cw_logging import commence_cw_log_streaming
from prometheus_client import start_http_server
from ros.lib.utils import (
    get_or_create,
    cast_iops_as_float,
    insert_performance_profiles,
    system_allowed_in_ros,
)
from ros.processor.metrics import (processor_requests_success,
                                   processor_requests_failures,
                                   )
from ros.processor.ros_consumer import RosConsumer

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
producer = None


def org_id(decoded_msg):
    return decoded_msg["input"]["platform_metadata"].get('org_id')


class InsightsEngineConsumer(RosConsumer):
    def __init__(self, consumer_topic, prefix, reporter):
        """Create Engine Consumer."""
        super().__init__(consumer_topic, prefix, reporter)

    def run(self):
        self.LOG.info(f"{self.prefix} - Processor is running. Awaiting msgs.")

        # initialize producer
        global producer
        producer = produce.init_producer()

        for msg in iter(self):
            self.check_msg_for_err(msg, self.prefix, self.reporter)
            decoded_msg = self.decode_and_load_json(msg)
            self.try_to_handle_msg(self.handle_msg(decoded_msg),
                                   org_id(decoded_msg))

    def handle_msg(self, msg):
        if system_allowed_in_ros(msg, self.reporter):
            host = msg["input"]["host"]
            platform_metadata = msg["input"]["platform_metadata"]
            system_metadata = msg["results"]["system"]["metadata"]
            performance_record = get_performance_profile(
                platform_metadata['url'],
                platform_metadata.get('org_id'),
                host['id'],
                custom_prefix=self.prefix
            )
            reports = msg["results"]["reports"] \
                if msg["results"]["reports"] and isinstance(msg["results"]["reports"], list) else []
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
                    self.LOG.info(
                        f"{self.prefix} - No ROS rule hits found for system with inventory id: {host['id']}. "
                        f"Hence, marking the state as {SYSTEM_STATES[state_key]}."
                    )
                else:
                    state_key = reports[0].get('key')
                    rec_count = 0 if state_key == 'NO_PCP_DATA' else len(reports)
                    self.LOG.info(
                        f"{self.prefix} - Marking the state of system with "
                        f"inventory id: {host['id']} as {SYSTEM_STATES[state_key]}"
                    )

                # get previous state of the system
                system_previous_state = db.session.scalar(db.select(System.state)
                                                          .filter(System.inventory_id == host['id']))

                system_attrs = {
                    'tenant_id': account.id,
                    'inventory_id': host['id'],
                    'display_name': host['display_name'],
                    'fqdn': host['fqdn'],
                    'state': SYSTEM_STATES[state_key],
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
                self.LOG.info(
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
                    self.LOG.debug(f"{self.prefix} - Setting default utilization for performance profile")
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
                self.LOG.info(
                    f"{self.prefix} - Performance profile created/updated successfully for the system: {host['id']}"
                )
                db.session.commit()

                # Trigger event for notification
                self.trigger_notification(
                    system.inventory_id, account, host, platform_metadata, system_previous_state,
                    system_current_state
                )

                processor_requests_success.labels(
                    reporter=self.reporter, org_id=account.org_id
                ).inc()
                self.LOG.info(
                    f"{self.prefix} - Refreshed system {system.inventory_id} ({system.id}) "
                    f"belonging to account: {account.account} ({account.id}) and org_id: {account.org_id}"
                )

            except Exception as err:
                processor_requests_failures.labels(
                    reporter=self.reporter, org_id=account.org_id
                ).inc()
                self.LOG.error(
                    f"{self.prefix} - Unable to add system {host['id']} to DB "
                    f"belonging to account: {account.account} and org_id: {account.org_id} - {err}"
                )

    def trigger_notification(
            self, inventory_id, account, host, platform_metadata, system_previous_state, system_current_state
    ):
        if system_previous_state is not None:
            if system_current_state not in (SYSTEM_STATES['OPTIMIZED'], system_previous_state):
                LOG.info(
                    f"{self.prefix} - Triggering a new suggestion event for the system: {inventory_id} belonging"
                    f" to account: {account.account} ({account.id}) and org_id: {account.org_id}"
                )
                new_suggestion_event(host, platform_metadata, system_previous_state, system_current_state, producer)


if __name__ == "__main__":
    start_http_server(int(METRICS_PORT))
    commence_cw_log_streaming('ros-processor')
    processor = InsightsEngineConsumer(ENGINE_RESULT_TOPIC, 'PROCESSING ENGINE RESULTS', 'INSIGHTS ENGINE')
    processor.run()
