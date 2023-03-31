import json
from ros.lib import consume
from ros.lib.app import app, db
from ros.lib.utils import get_or_create, validate_system
from confluent_kafka import KafkaException
from ros.lib.models import RhAccount, System
from ros.lib.config import INVENTORY_EVENTS_TOPIC, METRICS_PORT, get_logger
from ros.lib.cw_logging import commence_cw_log_streaming
from prometheus_client import start_http_server
from ros.processor.metrics import (processor_requests_success,
                                   processor_requests_failures,
                                   kafka_failures)

LOG = get_logger(__name__)


class InventoryEventsConsumer:
    """Inventory events consumer."""

    def __init__(self):
        """Create Inventory Events Consumer."""
        self.consumer = consume.init_consumer(INVENTORY_EVENTS_TOPIC)

        self.event_type_map = {
            'delete': self.host_delete_event,
            'created': self.host_create_update_events,
            'updated': self.host_create_update_events
        }
        self.prefix = 'INVENTORY EVENTS'
        self.reporter = 'INVENTORY EVENTS'

    def __iter__(self):
        return self

    def __next__(self):
        msg = self.consumer.poll()
        if msg is None:
            raise StopIteration
        return msg

    def run(self):
        """Initialize Consumer."""
        LOG.info(f"{self.prefix} - Processor is running. Awaiting msgs.")
        for msg in iter(self):
            if msg.error():
                LOG.error(f"{self.prefix} - Consumer error: {msg.error()}")
                kafka_failures.labels(reporter=self.reporter).inc()
                raise KafkaException(msg.error())

            account = None
            host_id = None
            org_id = None
            try:
                msg = json.loads(msg.value().decode("utf-8"))
                event_type = msg['type']
                if event_type == 'delete':
                    account = msg['account']
                    host_id = msg['id']
                    org_id = msg['org_id']
                else:
                    account = msg['host']['account']
                    host_id = msg['host']['id']
                    org_id = msg['host'].get('org_id')

                if event_type in self.event_type_map.keys():
                    handler = self.event_type_map[event_type]
                    handler(msg)
                else:
                    LOG.info(
                        f"{self.prefix} - Event Handling is not found for event {event_type}"
                    )
            except json.decoder.JSONDecodeError:
                kafka_failures.labels(reporter=self.reporter).inc()
                LOG.error(
                    f"{self.prefix} - Unable to decode kafka message: {msg.value()}"
                )
            except Exception as err:
                processor_requests_failures.labels(
                    reporter=self.reporter, org_id=org_id
                ).inc()
                LOG.error(
                    f"{self.prefix} - An error occurred during message processing: {repr(err)} "
                    f"in the system {host_id} created from account: {account} and org_id: {org_id}"
                )
            finally:
                self.consumer.commit()
        LOG.warning("Stopping inventory consumer")
        self.consumer.close()

    def host_delete_event(self, msg):
        """Process delete message."""
        self.prefix = "INVENTORY DELETE EVENT"
        host_id = msg['id']
        with app.app_context():
            LOG.debug(
                f"{self.prefix} - Received a message for system with inventory_id {host_id}"
            )
            rows_deleted = db.session.query(System.id).filter(System.inventory_id == host_id).delete()
            db.session.commit()
            if rows_deleted == 1:
                processor_requests_success.labels(
                    reporter=self.reporter, org_id=msg['org_id']
                ).inc()
                LOG.info(
                    f"{self.prefix} - Deleted system with inventory id: {host_id}"
                )

    def host_create_update_events(self, msg):
        """ Process created/updated message ( create system record, store new report )"""
        self.prefix = "INVENTORY Update EVENT" if msg['type'] == 'updated' else "INVENTORY CREATE EVENT"
        is_valid = validate_system(self.reporter, msg)
        if is_valid:
            LOG.info(
                f"{self.prefix} - Processing a message for system({msg['host']['id']}) "
                f"belonging to account: {msg['host']['account']} and org_id: {msg['host'].get('org_id')}"
            )
            self.process_system_details(msg)

    def process_system_details(self, msg):
        """ Store new system information (stale, stale_warning timestamp) and return internal DB id"""
        host = msg['host']
        with app.app_context():
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
                }
                system = get_or_create(db.session, System, 'inventory_id', **system_fields)

                # Commit changes
                db.session.commit()
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
                    f"belonging to account: {account.account} and org_id: {account.org_id} - {err}"
                )


if __name__ == "__main__":
    start_http_server(int(METRICS_PORT))
    commence_cw_log_streaming('ros-processor')
    processor = InventoryEventsConsumer()
    processor.run()
