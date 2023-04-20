import json
from ros.lib import consume
from ros.lib.app import app
from ros.extensions import db
from ros.lib.utils import get_or_create, system_allowed_in_ros, update_system_record
from ros.lib.models import RhAccount, System
from ros.lib.config import INVENTORY_EVENTS_TOPIC, METRICS_PORT
from ros.lib.cw_logging import commence_cw_log_streaming
from prometheus_client import start_http_server
from ros.processor.metrics import (processor_requests_success,
                                   processor_requests_failures,
                                   )
from ros.processor.ros_consumer import RosConsumer


def extract_attr(msg):
    event_type = msg['type']
    if event_type == 'delete':
        account = msg['account']
        host_id = msg['id']
        org_id = msg['org_id']
    else:
        account = msg['host']['account']
        host_id = msg['host']['id']
        org_id = msg['host'].get('org_id')
    return event_type, account, host_id, org_id


class InventoryEventsConsumer(RosConsumer):
    """Inventory events consumer."""

    def __init__(self, consumer_topic, prefix, reporter):
        """Create Inventory Events Consumer."""
        super().__init__(consumer_topic, prefix, reporter)
        self.event_type_map = {
            'delete': self.host_delete_event,
            'created': self.host_create_update_events,
            'updated': self.host_create_update_events
        }

    def run(self):
        """Initialize Consumer."""
        self.LOG.info(f"{self.prefix} - Processor is running. Awaiting msgs.")
        for msg in iter(self):
            self.check_msg_for_err(msg, self.prefix, self.reporter)
            decoded_msg = self.decode_and_load_json(msg)
            event_type, account, host_id, org_id = extract_attr(decoded_msg)
            processing_err = f"\nin the system {host_id} created from account: {account} and org_id: {org_id}"
            if event_type in self.event_type_map.keys():
                handler = self.event_type_map[event_type]
                self.try_to_handle_msg(handler(decoded_msg), org_id, processing_err)
            else:
                self.LOG.info(
                    f"{self.prefix} - Event Handling is not found for event {event_type}"
                )

    def host_delete_event(self, msg):
        """Process delete message."""
        self.prefix = "INVENTORY DELETE EVENT"
        host_id = msg['id']
        with app.app_context():
            self.LOG.debug(
                f"{self.prefix} - Received a message for system with inventory_id {host_id}"
            )

            rows_deleted = db.session.execute(db.delete(System).filter(System.inventory_id == host_id))
            db.session.commit()

            if rows_deleted.rowcount == 1:
                processor_requests_success.labels(
                    reporter=self.reporter, org_id=msg['org_id']
                ).inc()
                self.LOG.info(
                    f"{self.prefix} - Deleted system with inventory id: {host_id}"
                )

    def host_create_update_events(self, msg):
        """ Process created/updated message ( create system record, store new report )"""
        self.prefix = "INVENTORY Update EVENT" if msg['type'] == 'updated' else "INVENTORY CREATE EVENT"
        if system_allowed_in_ros(msg, self.reporter):
            self.LOG.info(
                f"{self.prefix} - Processing a message for system({msg['host']['id']}) "
                f"belonging to account: {msg['host']['account']} and org_id: {msg['host'].get('org_id')}"
            )
            self.process_system_details(msg)

    def process_system_details(self, msg):
        """ Store new system information (stale, stale_warning timestamp) and return internal DB id"""
        host = msg['host']
        with app.app_context():
            # 'platform_metadata' field not included when the host is updated via the API.
            if (
                    msg.get('type') == 'updated'
                    and msg.get("platform_metadata") is None
            ):
                system_fields = {
                    "inventory_id": host['id'],
                    "display_name": host['display_name'],
                    "fqdn": host['fqdn'],
                    "cloud_provider": host['system_profile']['cloud_provider'],
                    "stale_timestamp": host['stale_timestamp'],
                    "operating_system": host['system_profile']['operating_system'],
                    "groups": host.get('groups', [])
                }
                system = update_system_record(db.session, **system_fields)
                if system is not None:
                    db.session.commit()
                    account = db.session.scalar(db.select(RhAccount).filter_by(id=system.tenant_id))
                    processor_requests_success.labels(
                        reporter=self.reporter, org_id=account.org_id
                    ).inc()
                    self.LOG.info(
                        f"{self.prefix} - Refreshed system {system.inventory_id} ({system.id}) "
                        f"belonging to account: {account.account} ({account.id}) and org_id: {account.org_id}"
                    )
                else:
                    self.LOG.info(
                        f"{self.prefix} - System {system_fields.get('inventory_id')} does not exist in the database"
                    )
            else:
                try:
                    account = get_or_create(
                        db.session, RhAccount, 'account',
                        account=host['account'],
                        org_id=host.get('org_id')
                    )

                    system_fields = {
                        "tenant_id": account.id,
                        "inventory_id": host['id'],
                        "display_name": host['display_name'],
                        "fqdn": host['fqdn'],
                        "cloud_provider": host['system_profile']['cloud_provider'],
                        "stale_timestamp": host['stale_timestamp'],
                        "operating_system": host['system_profile']['operating_system'],
                        "groups": host.get('groups', [])
                    }
                    system = get_or_create(db.session, System, 'inventory_id', **system_fields)

                    # Commit changes
                    db.session.commit()
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


if __name__ == "__main__":
    start_http_server(int(METRICS_PORT))
    commence_cw_log_streaming('ros-processor')
    processor = InventoryEventsConsumer(INVENTORY_EVENTS_TOPIC, 'INVENTORY EVENTS', 'INVENTORY EVENTS')
    processor.run()
