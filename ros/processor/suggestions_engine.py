import json
import requests
from http import HTTPStatus
from ros.lib import consume
from insights import extract
from ros.lib.config import get_logger
from tempfile import NamedTemporaryFile
from prometheus_client import start_http_server
from ros.lib.config import (
    INVENTORY_EVENTS_TOPIC,
    METRICS_PORT,
    GROUP_ID_SUGGESTIONS_ENGINE
)


logging = get_logger(__name__)


class SuggestionsEngine:
    def __init__(self):
        self.consumer = consume.init_consumer(INVENTORY_EVENTS_TOPIC, GROUP_ID_SUGGESTIONS_ENGINE)
        self.service = 'SUGGESTIONS_ENGINE'
        self.event = None

    def handle_create_update(self, payload):
        self.event = "Update event" if payload.get('type') == 'updated' else "Create event"

        platform_metadata = payload.get('platform_metadata')
        host = payload.get('host')

        if platform_metadata is None or host is None:
            logging.info(f"{self.service} - {self.event} - Missing host or/and platform_metadata field(s).")
            return

        if not is_pcp_collected(platform_metadata):
            return

        archive_URL = platform_metadata.get('url')
        download_and_extract(self.service, self.event, archive_URL, host, org_id=host.get('org_id'))

    def run(self):
        logging.info(f"{self.service} - Engine is running. Awaiting msgs.")
        try:
            while True:
                message = self.consumer.poll(timeout=1.0)
                if message is None:
                    continue

                try:
                    payload = json.loads(message.value().decode('utf-8'))
                    event_type = payload['type']

                    if 'created' == event_type or 'updated' == event_type:
                        self.handle_create_update(payload)
                        self.consumer.commit()

                except json.JSONDecodeError as error:
                    logging.error(f"{self.service} - {self.event} - Failed to decode message: {error}")
                except Exception as error:
                    logging.error(f"{self.service} - {self.event} - Error processing message: {error}")
        except Exception as error:
            logging.error(f"{self.service} - {self.event} - error: {error}")
        finally:
            self.consumer.close()


def download_and_extract(service, event, archive_URL, host, org_id):
    logging.info(f"{service} - {event} - Downloading the report for system {host.get('id')}.")

    response = requests.get(archive_URL, timeout=10)

    if response.status_code != HTTPStatus.OK:
        logging.error(
            f"{service} - {event} - Unable to download the report for system {host.get('id')}. "
            f"ERROR - {response.reason}"
        )
    else:
        with NamedTemporaryFile(delete=True) as tempfile:
            tempfile.write(response.content)
            logging.info(
                f"{service} - {event} - Downloaded the report successfully for system {host.get('id')}"
            )
            tempfile.flush()
            with extract(tempfile.name) as extract_dir:
                return extract_dir.tmp_dir


def is_pcp_collected(platform_metadata):
    return (
        platform_metadata.get('is_ros_v2') and
        platform_metadata.get('is_pcp_raw_data_collected')
    )


if __name__ == "__main__":
    start_http_server(int(METRICS_PORT))
    processor = SuggestionsEngine()
    processor.run()
