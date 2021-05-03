import json
import logging
import datetime
from confluent_kafka import Consumer, KafkaException
from ros.lib.config import INSIGHTS_KAFKA_ADDRESS, INVENTORY_EVENTS_TOPIC, GROUP_ID
from ros.lib.app import app, db
from ros.lib.models import PerformanceProfile, RhAccount, System
from ros.lib.utils import get_or_create
from ros.processor.process_archive import get_performance_profile
from ros.processor.metrics import add_host_success, add_host_failure

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
            rows_deleted = db.session.query(System.id).filter(System.inventory_id == host_id).delete()
            if rows_deleted > 0:
                LOG.info(
                    'Deleted host from inventory with id: %s - %s',
                    host_id,
                    self.prefix
                )
            db.session.commit()

    def host_create_update_events(self, msg):
        """ Process created/updated message ( create system record, store new report )"""
        self.prefix = "PROCESSING Create/Update EVENT"
        if 'is_ros' in msg['platform_metadata']:
            self.process_system_details(msg)

    def process_system_details(self, msg):
        """ Store new system information (stale, stale_warning timestamp) and return internal DB id"""
        host = msg['host']
        performance_record = get_performance_profile(msg['platform_metadata']['url'])
        if performance_record:
            performance_score = self._calculate_performance_score(performance_record, host)
            with app.app_context():
                try:
                    account = get_or_create(
                        db.session, RhAccount, 'account',
                        account=host['account']
                    )

                    system = get_or_create(
                        db.session, System, 'inventory_id',
                        account_id=account.id,
                        inventory_id=host['id'],
                        display_name=host['display_name'],
                        fqdn=host['fqdn'],
                        cloud_provider=host['system_profile']['cloud_provider'],
                        instance_type=performance_record.get('instance_type')
                    )

                    get_or_create(
                        db.session, PerformanceProfile, ['system_id', 'report_date'],
                        system_id=system.id,
                        performance_record=performance_record,
                        performance_score=performance_score,
                        report_date=datetime.datetime.utcnow().date()
                    )

                    # Commit changes
                    db.session.commit()
                    add_host_success.labels('inventory-report-processor').inc()
                    LOG.info("Refreshed system %s (%s) belonging to account: %s (%s) via report-processor",
                             system.inventory_id, system.id, account.account, account.id)
                except Exception as err:
                    add_host_failure.labels('inventory-report-processor').inc()
                    LOG.error("Unable to add host %s to DB belonging to account: %s via report-processor - %s",
                              host['fqdn'], host['account'], err)

    def _calculate_performance_score(self, performance_record, host):
        MAX_IOPS_CAPACITY = 16000
        memory_score = (float(performance_record['mem.util.used']) / float(performance_record['mem.physmem'])) * 100
        cpu_score = self._calculate_cpu_score(performance_record)
        cloud_provider = host['system_profile']['cloud_provider']
        if cloud_provider == 'aws':
            MAX_IOPS_CAPACITY = 16000
        if cloud_provider == 'azure':
            MAX_IOPS_CAPACITY = 20000
        io_score = (float(performance_record['disk.all.total']) / float(MAX_IOPS_CAPACITY)) * 100
        performance_score = {
            'memory_score': int(memory_score),
            'cpu_score': int(cpu_score),
            'io_score': int(io_score)
            }
        return performance_score

    def _calculate_cpu_score(self, performance_record):
        idle_cpu_percent = ((float(performance_record['kernel.all.cpu.idle']) * 100)
                            / int(performance_record['total_cpus']))
        cpu_utilized_percent = 100 - idle_cpu_percent
        return cpu_utilized_percent
