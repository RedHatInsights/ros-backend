import json
from ros.lib.app import app, db
from ros.lib.config import (INSIGHTS_KAFKA_ADDRESS, GROUP_ID,
                            ENGINE_RESULT_TOPIC, get_logger)
from ros.lib.models import RhAccount, System
from ros.lib.utils import get_or_create
from confluent_kafka import Consumer, KafkaException
from ros.processor.metrics import (processor_requests_success,
                                   processor_requests_failures,
                                   kafka_failures)

SYSTEM_STATES = {
    "INSTANCE_OVERSIZED": "Oversized",
    "INSTANCE_UNDERSIZED": "Undersized",
    "INSTANCE_IDLE": "Idling",
    "INSTANCE_UNDER_PRESSURE": "Under Pressure",
    "STORAGE_RIGHTSIZING": "Storage rightsizing",
    "OPTIMIZED": "Optimized",
    "NO_PCP_DATA": "Waiting for data"
}
OPTIMIZED_SYSTEM_KEY = "OPTIMIZED"
LOG = get_logger(__name__)


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
        self.reporter = 'INSIGHTS ENGINE'

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
                kafka_failures.labels(
                    reporter=self.reporter,
                    account_number=msg['input']['host']['account']
                ).inc()
                LOG.error(
                    'Unable to decode kafka message: %s - %s',
                    msg.value(), self.prefix
                )
            except Exception as err:
                processor_requests_failures.labels(
                    reporter=self.reporter,
                    account_number=msg['input']['host']['account']
                ).inc()
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
                self.process_report(host, ros_reports)

    def process_report(self, host, reports):
        """create/update system based on reports data."""
        with app.app_context():
            try:
                account = get_or_create(
                    db.session, RhAccount, 'account',
                    account=host['account']
                )
                if len(reports) == 0:
                    rec_count = len(reports)
                    state_key = OPTIMIZED_SYSTEM_KEY
                    LOG.info(
                        "%s - No ROS rule hits found for system with inventory id: %s. Hence, marking the state as %s.",
                        self.prefix, host['id'], SYSTEM_STATES[state_key])
                else:
                    state_key = reports[0].get('key')
                    rec_count = 0 if state_key == 'NO_PCP_DATA' else len(reports)
                    LOG.info(
                        "%s - Marking the state of system with inventory id: %s as %s.",
                        self.prefix, host['id'], SYSTEM_STATES[state_key])

                system = get_or_create(
                    db.session, System, 'inventory_id',
                    account_id=account.id,
                    inventory_id=host['id'],
                    display_name=host['display_name'],
                    fqdn=host['fqdn'],
                    rule_hit_details=reports,
                    number_of_recommendations=rec_count,
                    state=SYSTEM_STATES[state_key]
                )

                db.session.commit()
                processor_requests_success.labels(
                    reporter=self.reporter, account_number=host['account']
                ).inc()
                LOG.info("%s - Refreshed system %s (%s) belonging to account: %s (%s).",
                         self.prefix, system.inventory_id, system.id, account.account, account.id)
            except Exception as err:
                processor_requests_failures.labels(
                    reporter=self.reporter, account_number=host['account']
                ).inc()
                LOG.error("%s - Unable to add host %s to DB belonging to account: %s - %s",
                          self.prefix, host['fqdn'], host['account'], err)
