# import threading
import json
import logging
from confluent_kafka import Consumer, KafkaException
from ros.config import INSIGHTS_KAFKA_ADDRESS, INVENTORY_EGRESS_TOPIC
from ros.app import app, db
from ros.models import PerformanceProfile

logging.basicConfig(
    level='INFO',
    format='%(asctime)s - %(levelname)s  - %(funcName)s - %(message)s'
)
LOG = logging.getLogger(__name__)


class InventoryEventsListener:
    """Inventory events listener."""

    def __init__(self):
        """Create a Inventory Events Listener."""
        self.running = True
        self.consumer = Consumer({
            'bootstrap.servers': INSIGHTS_KAFKA_ADDRESS,
            'group.id': 'inventory-event-lisener',
            'enable.auto.commit': False
        })

        # Subscribe to topic
        self.consumer.subscribe([INVENTORY_EGRESS_TOPIC])
        self.event_type_map = {
            'created': self.host_create_update_event,
            'updated': self.host_create_update_event,
            'delete': self.host_delete_event,
        }
        self.prefix = 'PROCESSING INVENTORY EVENTS'

    def run(self):
        """Initialize consumer."""
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

    def host_create_update_event(self, _msg):
        """Process create/update message."""
        self.prefix = "PROCESSING CREATE/UPDATE EVENT"
        LOG.info(
            'Not listening to created/updated events - %s',
            self.prefix
        )

    def host_delete_event(self, msg):
        """Process delete message."""
        self.prefix = "PROCESSING DELETE EVENT"
        host_id = msg['id']
        insights_id = msg['insights_id']
        with app.app_context():
            pp_record = PerformanceProfile.query.filter_by(
                inventory_id=host_id).first()
            if pp_record:
                LOG.info(
                    'Deleting performance profile of host with insights_id %s - %s',
                    insights_id,
                    self.prefix
                )
                db.session.delete(pp_record)
                db.session.commit()
            else:
                LOG.info(
                    'Not found any performance profile of host with host_id %s'
                    ' & insights_id %s - %s',
                    host_id, insights_id, self.prefix
                )


# FIXUP: app context so don't need to add it to app.py
# def inventory_target():
#     """Initalize inventory events listerner."""
#     inventory_events_processor = InventoryEventsListener()
#     inventory_events_processor.run()


# def start_inventory_events_listener_thread():
#     """Start inventory events listener thread."""
#     inventory_processor_thread = threading.Thread(
#         target=inventory_target, name='InventoryEventsListener', daemon=True)
#     inventory_processor_thread.start()
