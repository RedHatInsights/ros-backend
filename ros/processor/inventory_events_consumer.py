# import threading
import json
import logging
from confluent_kafka import Consumer, KafkaException
from ros.lib.config import INSIGHTS_KAFKA_ADDRESS, INVENTORY_EGRESS_TOPIC, GROUP_ID
from ros.lib.app import app, db
from ros.lib.models import PerformanceProfile

logging.basicConfig(
    level='INFO',
    format='%(asctime)s - %(levelname)s  - %(funcName)s - %(message)s'
)
LOG = logging.getLogger(__name__)


class InventoryEventsConsumer:
    """Inventory events consumer."""

    def __init__(self):
        """Create a Inventory Events Consumer."""
        self.running = True
        self.consumer = Consumer({
            'bootstrap.servers': INSIGHTS_KAFKA_ADDRESS,
            'group.id': GROUP_ID,
            'enable.auto.commit': False
        })

        # Subscribe to topic
        self.consumer.subscribe([INVENTORY_EGRESS_TOPIC])
        self.event_type_map = {
            'delete': self.host_delete_event,
        }
        self.prefix = 'PROCESSING INVENTORY EVENTS'

    def run(self):
        """Initialize Consumer."""
        while self.running:
            msg = self.consumer.poll(1.0)
            if msg is None:
                continue
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
            rows_deleted = db.session.query(PerformanceProfile).filter(
                PerformanceProfile.inventory_id == host_id
            ).delete()
            if rows_deleted > 0:
                LOG.info(
                    'Deleted %d performance profile record(s) - %s',
                    rows_deleted,
                    self.prefix
                )
            db.session.commit()
