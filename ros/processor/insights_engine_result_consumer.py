import json
import logging
from ros.lib.app import app, db
from ros.lib.utils import get_or_create, delete_record
from ros.lib.models import RhAccount, System
from confluent_kafka import Consumer, KafkaException
from ros.lib.config import INSIGHTS_KAFKA_ADDRESS, GROUP_ID, ENGINE_RESULT_TOPIC

logging.basicConfig(
    level='INFO',
    format='%(asctime)s - %(levelname)s  - %(funcName)s - %(message)s'
)
LOG = logging.getLogger(__name__)


class InsightsEngineResultConsumer:
    def __init__(self):
        self.consumer = Consumer({
            'bootstrap.servers': INSIGHTS_KAFKA_ADDRESS,
            'group.id': GROUP_ID,
            'enable.auto.commit': False
        })

        # Subscribe to topic
        self.consumer.subscribe([ENGINE_RESULT_TOPIC])

        self.prefix = 'PROCESSING ENGINE RESULTS'

    def __iter__(self):
        return self

    def __next__(self):
        msg = self.consumer.poll()
        if msg is None:
            raise StopIteration
        return msg

    def run(self):
        for msg in iter(self):
            if msg.error():
                print(msg.error())
                raise KafkaException(msg.error())
            try:
                msg = json.loads(msg.value().decode("utf-8"))
                self.handle_msg(msg)
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

    def handle_msg(self, msg):
        if msg["input"]["platform_metadata"]["is_ros"]:
            host = msg["input"]["host"]
            reports = msg["results"]["reports"]
            if reports:
                ros_reports = []
                for report in reports:
                    if 'cloud_instance_ros_evaluation' in report["rule_id"]:
                        ros_reports.append(report)
                if len(ros_reports) == 0:
                    with app.app_context():
                        system = delete_record(db.session, System, inventory_id=host['id'])
                        if system:
                            LOG.info("Deleted system with inventory_id: %s via engine-result.", system.inventory_id)
                        else:
                            LOG.info(
                                "Cannot upload system with inventory id: %s and no ROS rules.", host['id'])
                else:
                    self.process_report(host, ros_reports)

    def process_report(self, host, reports):
        with app.app_context():
            account = get_or_create(
                    db.session, RhAccount, 'account',
                    account=host['account']
                )

            SYSTEM_STATES = {"INSTANCE_OVERSIZED": "Oversized", "INSTANCE_UNDERSIZED": "Undersized",
                             "CONSUMPTION_MODEL": "Idling", "STORAGE_RIGHTSIZING": "Storage rightsizing"}

            system = get_or_create(
                    db.session, System, 'inventory_id',
                    account_id=account.id,
                    inventory_id=host['id'],
                    display_name=host['display_name'],
                    fqdn=host['fqdn'],
                    rule_hit_details=reports,
                    number_of_recommendations=len(reports),
                    state=SYSTEM_STATES[reports[0].get('key')]
                )

            db.session.commit()
            LOG.info("Refreshed system %s (%s) belonging to account: %s (%s) via engine-result",
                     system.inventory_id, system.id, account.account, account.id)
