import json
import logging
from confluent_kafka import Consumer, KafkaException
from ros.lib.config import INSIGHTS_KAFKA_ADDRESS, INVENTORY_EVENTS_TOPIC, GROUP_ID
from ros.lib.app import app, db
from ros.lib.models import PerformanceProfile, RhAccount, System
from ros.lib.utils import get_or_create

logging.basicConfig(
    level='INFO',
    format='%(asctime)s - %(levelname)s  - %(funcName)s - %(message)s'
)
LOG = logging.getLogger(__name__)


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
        self.prefix = 'PROCESSING INVENTORY EVENTS'

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
                print(msg.error())
                raise KafkaException(msg.error())
            try:
                msg = json.loads(msg.value().decode("utf-8"))
                event_type = msg['type']
                if event_type in self.event_type_map.keys():
                    handler = self.event_type_map[event_type]
                    handler(msg)
                else:
                    LOG.info(
                        'Event Handling is not found for event %s - %s',
                        event_type, self.prefix
                    )
            except json.decoder.JSONDecodeError:
                LOG.error(
                    'Unable to decode kafka message: %s - %s',
                    msg.value(), self.prefix
                )
            except Exception as err:
                LOG.error(
                    'An error occurred during message processing: %s - %s',
                    repr(err),
                    self.prefix
                )
            finally:
                self.consumer.commit()
        LOG.warning("Stopping inventory consumer")
        self.consumer.close()

    def host_delete_event(self, msg):
        """Process delete message."""
        self.prefix = "PROCESSING DELETE EVENT"
        host_id = msg['id']
        insights_id = msg['insights_id']
        with app.app_context():
            LOG.info(
                'Deleting performance profile records with insights_id %s - %s',
                insights_id,
                self.prefix
            )
            system_id_query = db.session.query(System.id).filter(System.inventory_id == host_id).subquery()
            rows_deleted = db.session.query(PerformanceProfile) \
                .filter(PerformanceProfile.system_id.in_(system_id_query)) \
                .delete()

            if rows_deleted > 0:
                LOG.info(
                    'Deleted %d performance profile record(s) - %s',
                    rows_deleted,
                    self.prefix
                )
            db.session.commit()

    def host_create_update_events(self, msg):
        """ Process created/updated message ( create system record, store new report )"""
        self.prefix = "PROCESSING Create/Update EVENT"
        with app.app_context():
            print(msg)
            self.process_system_details(msg)

    def process_system_details(self, msg):
        """ Store new system information (stale, stale_warning timestamp) and return internal DB id"""
        host = msg['host']

        account = get_or_create(
            db.session, RhAccount, 'account',
            account=host['account']
        )

        system = get_or_create(
            db.session, System, 'inventory_id',
            account_id=account.id,
            inventory_id=host['id']
        )
        # Commit changes
        db.session.commit()
        LOG.warning("Refreshed system %s (%s) belonging to account: %s (%s)",
                    system.inventory_id, system.id, account.account, account.id)
