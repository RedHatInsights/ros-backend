
import json
from confluent_kafka import Consumer, KafkaException
from ros.lib.config import INSIGHTS_KAFKA_ADDRESS, INVENTORY_EVENTS_TOPIC, GROUP_ID, get_logger
from ros.lib.app import app, db
from ros.lib.models import RhAccount, System
from ros.lib.utils import get_or_create
from ros.processor.metrics import (processor_requests_success,
                                   processor_requests_failures,
                                   kafka_failures)


LOG = get_logger(__name__)


class InventoryEventsConsumer:
    """Inventory events consumer."""

    def __init__(self):
        """Create a Inventory Events Consumer."""
        self.consumer = Consumer({
            'bootstrap.servers': INSIGHTS_KAFKA_ADDRESS,
            'group.id': GROUP_ID,
            'enable.auto.commit': False
        })

        # Subscribe to topic
        self.consumer.subscribe([INVENTORY_EVENTS_TOPIC])
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
        for msg in iter(self):
            if msg.error():
                LOG.error("%s - Consumer error: %s", self.prefix, msg.error())
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
                        '%s - Event Handling is not found for event %s',
                        self.prefix,
                        event_type
                    )
            except json.decoder.JSONDecodeError:
                kafka_failures.labels(reporter=self.reporter).inc()
                LOG.error(
                    '%s - Unable to decode kafka message: %s',
                    self.prefix,
                    msg.value()
                )
            except Exception as err:
                processor_requests_failures.labels(
                    reporter=self.reporter, account_number=account
                ).inc()
                LOG.error(
                    '%s - An error occurred during message processing: %s in the system %s created \
                    from account: %s and org_id: %s',
                    self.prefix,
                    repr(err),
                    host_id,
                    account,
                    org_id
                )
            finally:
                self.consumer.commit()
        LOG.warning("Stopping inventory consumer")
        self.consumer.close()

    def host_delete_event(self, msg):
        """Process delete message."""
        self.prefix = "INVENTORY DELETE EVENT"
        host_id = msg['id']
        insights_id = msg['insights_id']
        with app.app_context():
            LOG.debug(
                '%s - Received a message for system with insights_id %s',
                self.prefix,
                insights_id
            )
            rows_deleted = db.session.query(System.id).filter(System.inventory_id == host_id).delete()
            db.session.commit()
            if rows_deleted == 1:
                processor_requests_success.labels(
                    reporter=self.reporter, account_number=msg['account']
                ).inc()
                LOG.info(
                    '%s - Deleted system with inventory id: %s',
                    self.prefix,
                    host_id
                )

    def host_create_update_events(self, msg):
        """ Process created/updated message ( create system record, store new report )"""
        self.prefix = "INVENTORY Update EVENT" if msg['type'] == 'updated' else "INVENTORY CREATE EVENT"
        if (
                msg['platform_metadata'] is None
                and msg['type'] == 'updated'
        ) or 'is_ros' in msg['platform_metadata']:
            LOG.info(
                '%s - Processing a message for system(%s) belonging to account: %s and org_id: %s',
                self.prefix, msg['host']['id'], msg['host']['account'], msg['host'].get('org_id')
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
                    reporter=self.reporter, account_number=host['account']
                ).inc()
                LOG.info(
                    "%s - Refreshed system %s (%s) belonging to account: %s (%s) and org_id: %s.",
                    self.prefix, system.inventory_id, system.id, account.account, account.id, account.org_id
                )
            except Exception as err:
                processor_requests_failures.labels(
                    reporter=self.reporter, account_number=host['account']
                ).inc()
                LOG.error("%s - Unable to add system %s to DB belonging to account: %s and org_id: %s - %s",
                          self.prefix, host['fqdn'], host['account'], account.org_id, err)
