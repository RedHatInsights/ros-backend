import os
import json
import shutil
import subprocess
from http import HTTPStatus
from contextlib import contextmanager
from tempfile import NamedTemporaryFile

import requests
from insights import extract
from prometheus_client import start_http_server

from ros.lib import consume
from ros.lib.config import (
    get_logger,
    METRICS_PORT,
    INVENTORY_EVENTS_TOPIC,
    GROUP_ID_SUGGESTIONS_ENGINE,
)


logging = get_logger(__name__)


class SuggestionsEngine:
    def __init__(self):
        self.consumer = consume.init_consumer(INVENTORY_EVENTS_TOPIC, GROUP_ID_SUGGESTIONS_ENGINE)
        self.service = 'SUGGESTIONS_ENGINE'
        self.event = None

    def run_pmlogextract(self, host, index_file_path, output_dir):
        """Run the pmlogextract command."""

        pmlogextract_command = [
            "pmlogextract",
            "-c",
            "ros/lib/pcp_extract_config",
            index_file_path,
            output_dir
        ]

        logging.debug(f"{self.service} - {self.event} - Running pmlogextract command for system {host.get('id')}.")
        try:
            subprocess.run(pmlogextract_command, check=True)
            logging.debug(
                f"{self.service} - {self.event} - Successfully ran pmlogextract command for system {host.get('id')}."
            )
        except subprocess.CalledProcessError as error:
            logging.error(
                f"{self.service} - {self.event} - Error running pmlogextract command for system {host.get('id')}:"
                f" {error.stdout}"
            )
            raise

    def run_pmlogsummary(self, host, output_dir):
        """Run the pmlogsummary command."""

        pmlogsummary_command = [
            "pmlogsummary",
            "-F",
            os.path.join(output_dir, ".index")
        ]

        logging.debug(f"{self.service} - {self.event} - Running pmlogsummary command for system {host.get('id')}.")
        try:
            subprocess.run(pmlogsummary_command, check=True, text=True, capture_output=True)
            logging.debug(
                f"{self.service} - {self.event} - Successfully ran pmlogsummary command for system {host.get('id')}."
            )
        except subprocess.CalledProcessError as error:
            logging.error(
                f"{self.service} - {self.event} - Error running pmlogsummary command for system {host.get('id')}:"
                f" {error.stdout}"
            )
            raise

    def create_output_dir(self, request_id, host):
        output_dir = f"/var/tmp/pmlogextract-output-{request_id}/"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        logging.debug(f"Successfully created output_dir for system {host.get('id')}: {output_dir}")

        return output_dir

    def run_pcp_commands(self, host, index_file_path, request_id):
        sanitized_request_id = request_id.replace("/", "_")
        output_dir = self.create_output_dir(sanitized_request_id, host)

        self.run_pmlogextract(host, index_file_path, output_dir)

        self.run_pmlogsummary(host, output_dir)

        logging.info(f"{self.service} - {self.event} - Successfully ran pcp commands for system {host.get('id')}.")

        try:
            if os.path.exists(output_dir):
                shutil.rmtree(output_dir)
                logging.debug(
                    f"{self.service} - {self.event} - Cleaned up output directory for system {host.get('id')}."
                )
        except Exception as error:
            logging.error(
                f"{self.service} - {self.event} - Error cleaning up the output directory for system {host.get('id')}:"
                f" {error}"
            )

    def find_root_directory(self, directory, target_file):
        """
        Recursively search for the target file in the given directory - to get root directory of an archive.
        """
        for dirpath, _, filenames in os.walk(directory):
            if target_file in filenames:
                return dirpath

        return None

    def get_index_file_path(self, host, extracted_dir):
        extracted_dir_root = self.find_root_directory(extracted_dir, "insights_archive.txt")

        if not extracted_dir_root:
            logging.error(
                f"{self.service} - {self.event} -"
                f" insights_archive.txt not found in the extracted dir for system {host.get('id')}"
            )
            return None

        pmlogger_dir = os.path.join(extracted_dir_root, "data/var/log/pcp/pmlogger/")

        index_files = [
            file for file in os.listdir(pmlogger_dir) if file.endswith(".index")
        ]
        index_file_path = os.path.join(pmlogger_dir, index_files[0])

        return index_file_path

    @contextmanager
    def download_and_extract(self, archive_URL, host, org_id):
        logging.debug(f"{self.service} - {self.event} - Report downloading for system {host.get('id')}.")

        try:
            response = requests.get(archive_URL, timeout=10)

            if response.status_code != HTTPStatus.OK:
                logging.error(
                    f"{self.service} - {self.event} - Unable to download the report for system {host.get('id')}. "
                    f"ERROR - {response.reason}"
                )
                yield None
            else:
                with NamedTemporaryFile(delete=True) as tempfile:
                    tempfile.write(response.content)
                    logging.info(
                        f"{self.service} - {self.event} - Report downloaded successfully for system {host.get('id')}"
                    )
                    tempfile.flush()
                    with extract(tempfile.name) as extract_dir:
                        yield extract_dir
        except Exception as error:
            logging.error(f"{self.service} - {self.event} - Error occurred during download and extraction: {error}")

    def is_pcp_collected(self, platform_metadata):
        return (
            platform_metadata.get('is_ros_v2') and
            platform_metadata.get('is_pcp_raw_data_collected')
        )

    def handle_create_update(self, payload):
        self.event = "Update event" if payload.get('type') == 'updated' else "Create event"

        platform_metadata = payload.get('platform_metadata')
        host = payload.get('host')

        if platform_metadata is None or host is None:
            logging.info(f"{self.service} - {self.event} - Missing host or/and platform_metadata field(s).")
            return

        if not self.is_pcp_collected(platform_metadata):
            return

        archive_URL = platform_metadata.get('url')
        with self.download_and_extract(
                archive_URL,
                host,
                org_id=host.get('org_id')
        ) as ext_dir:
            extracted_dir = ext_dir.tmp_dir
            index_file_path = self.get_index_file_path(host, extracted_dir)
            if index_file_path is not None:
                self.run_pcp_commands(host, index_file_path, platform_metadata.get('request_id'))

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

                except json.JSONDecodeError as error:
                    logging.error(f"{self.service} - {self.event} - Failed to decode message: {error}")
                except Exception as error:
                    logging.error(f"{self.service} - {self.event} - Error processing message: {error}")
                finally:
                    self.consumer.commit()
        except Exception as error:
            logging.error(f"{self.service} - {self.event} - error: {error}")
        finally:
            self.consumer.close()


if __name__ == "__main__":
    start_http_server(int(METRICS_PORT))
    processor = SuggestionsEngine()
    processor.run()
