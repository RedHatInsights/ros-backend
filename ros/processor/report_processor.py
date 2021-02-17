import json
import requests
import tarfile
from io import BytesIO
from http import HTTPStatus
from confluent_kafka import Consumer
from ros.lib.host_inventory_interface import fetch_host_from_inventory
from ros.lib.app import app, db
from ros.lib.config import INSIGHTS_KAFKA_ADDRESS, GROUP_ID
from ros.lib.models import PerformanceProfile

running = True


consumer = Consumer({
    'bootstrap.servers': INSIGHTS_KAFKA_ADDRESS,
    'group.id': GROUP_ID,
    "enable.auto.commit": False
})


class ReportProcessor:
    def init_consumer(self):
        consumer.subscribe(['platform.upload.resource-optimization'])
        while running:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                print(msg.error())
                continue
            try:
                self.msg = json.loads(msg.value().decode("utf-8"))
                self.handle_message()
            except json.decoder.JSONDecodeError:
                print(f"Unable to decode kafka message - {msg.value()}")
            except Exception as err:
                print(f"An error occurred during message processing - {repr(err)}")
            finally:
                consumer.commit()

        consumer.close()

    def handle_message(self):
        self.report_url = self.msg.get('url', None)
        metadata = self.msg.get('metadata', None)
        if not metadata or not metadata['insights_id']:
            return None
        insights_id = metadata['insights_id']
        rh_identity = self.msg.get('b64_identity', None)
        host = fetch_host_from_inventory(insights_id, rh_identity)
        if not host.get('results', None):
            print("No record found. Make sure system is registered in insights")
            return None
        if not self.report_url:
            print("kafka message missing report url")
        host_id = host['results'][0]['id']
        report_tar = self._download_report()
        performance_record = self._extract_performance_record(report_tar)

        with app.app_context():
            if performance_record:
                performance_score = self._calculate_performance_score(performance_record)
                profile = PerformanceProfile.query.filter_by(inventory_id=host_id).first()
                if profile:
                    profile.performance_record = performance_record
                    profile.performance_score = performance_score
                else:
                    record = PerformanceProfile(inventory_id=host_id,
                                                performance_record=performance_record,
                                                performance_score=performance_score)
                    db.session.add(record)

                db.session.commit()

    def _calculate_performance_score(self, performance_record):
        memory_score = (float(performance_record['avg_memory_used']) / float(performance_record['avg_memory'])) * 100
        performance_score = {'memory_score': int(memory_score)}
        return performance_score

    def _download_report(self):
        download_response = requests.get(self.report_url)
        if download_response.status_code != HTTPStatus.OK:
            print("Unable to download the report")
        return download_response.content

    def _extract_performance_record(self, report_tar):
        tar = tarfile.open(fileobj=BytesIO(report_tar), mode='r:*')
        files = tar.getmembers()
        metrics_file = None
        for file in files:

            if '/metrics.json' in file.name or file.name == 'metrics.json':
                metrics_file = file

        if metrics_file:
            extracted_metrics_file = tar.extractfile(metrics_file)
            record_string = extracted_metrics_file.read().decode('utf-8')
            performance_record = json.loads(record_string)
            return performance_record


def check_kafka_connection():
    topics = consumer.list_topics().topics
    return ("platform.upload.resource-optimization" in topics)
