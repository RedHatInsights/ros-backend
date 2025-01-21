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

PCP_METRICS = [
        'disk.dev.total',
        'hinv.ncpu',
        'kernel.all.cpu.idle',
        'kernel.all.pressure.cpu.some.avg',
        'kernel.all.pressure.io.full.avg',
        'kernel.all.pressure.io.some.avg',
        'kernel.all.pressure.memory.full.avg',
        'kernel.all.pressure.memory.some.avg',
        'mem.physmem',
        'mem.util.available',
]


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
        with download_and_extract(
                self.service,
                self.event,
                archive_URL,
                host,
                org_id=host.get('org_id')
        ) as ext_dir:
            extracted_dir = ext_dir.tmp_dir
            index_file_path = get_index_file_path(self.service, self.event, host, extracted_dir)
            if index_file_path is not None:
                run_pcp_commands(self.service, self.event, index_file_path, host, platform_metadata.get('request_id'))

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


def find_root_directory(directory, target_file):
    """
    Recursively search for the target file in the given directory - to get root directory of an archive.
    """
    for dirpath, dirnames, filenames in os.walk(directory):
        if target_file in filenames:
            return dirpath

    return None


def get_index_file_path(service, event, host, extracted_dir):
    extracted_dir_root = find_root_directory(extracted_dir, "insights_archive.txt")

    if not extracted_dir_root:
        logging.error(
            f"{service} - {event} - insights_archive.txt not found in the extracted dir for system {host.get('id')}."
        )
        return None

    pmlogger_dir = os.path.join(extracted_dir_root, "data/var/log/pcp/pmlogger/")

    index_files = [
        file for file in os.listdir(pmlogger_dir) if file.endswith(".index")
    ]
    index_file_path = os.path.join(pmlogger_dir, index_files[0])

    return index_file_path


def create_output_dir(request_id):
    output_dir = f"/tmp/pmlogextract-output-{request_id}/"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    return output_dir


def run_pcp_commands(service, event, host, index_file_path, request_id):
    try:
        sanitized_request_id = request_id.replace("/", "_")
        output_dir = create_output_dir(sanitized_request_id)

        pmlogextract_command = [
            "pmlogextract",
            "-c",
            "ros/lib/pcp_extract_config",
            index_file_path,
            output_dir
        ]
        try:
            subprocess.run(pmlogextract_command, check=True)
            logging.info(f"{service} - {event} - Successfully ran pmlogextract command for system {host.get('id')}.")
        except subprocess.CalledProcessError as error:
            logging.error(
                f"{service} - {event} - Error running pmlogextract command for system {host.get('id')}: {error}"
            )
            return

        pmlogsummary_command = [
            "pmlogsummary",
            "-f",
            output_dir,
            *PCP_METRICS
        ]
        try:
            subprocess.run(pmlogsummary_command, check=True)
            logging.info(f"{service} - {event} - Successfully ran pmlogsummary command for system {host.get('id')}.")
        except subprocess.CalledProcessError as error:
            logging.error(
                f"{service} - {event} - Error running pmlogsummary command for system {host.get('id')}: {error}"
            )
            return

    except Exception as error:
        logging.error(
            f"{service} - {event} - Unexpected error during PCP command execution for system {host.get('id')}: {error}"
        )
    finally:
        try:
            if os.path.exists(output_dir):
                shutil.rmtree(output_dir)
                logging.info(f"{service} - {event} - Cleaned up output directory for system {host.get('id')}.")
        except Exception as error:
            logging.error(
                f"{service} - {event} - Error cleaning up the output directory for system {host.get('id')}: {error}"
            )


@contextmanager
def download_and_extract(service, event, archive_URL, host, org_id):
    logging.info(f"{service} - {event} - Downloading the report for system {host.get('id')}.")

    try:
        response = requests.get(archive_URL, timeout=10)

        if response.status_code != HTTPStatus.OK:
            logging.error(
                f"{service} - {event} - Unable to download the report for system {host.get('id')}. "
                f"ERROR - {response.reason}"
            )
            yield None
        else:
            with NamedTemporaryFile(delete=True) as tempfile:
                tempfile.write(response.content)
                logging.info(
                    f"{service} - {event} - Downloaded the report successfully for system {host.get('id')}"
                )
                tempfile.flush()
                with extract(tempfile.name) as extract_dir:
                    yield extract_dir
    except Exception as e:
        logging.error(f"{service} - {event} - Error occurred during download and extraction: {str(e)}")


def is_pcp_collected(platform_metadata):
    return (
        platform_metadata.get('is_ros_v2') and
        platform_metadata.get('is_pcp_raw_data_collected')
    )


if __name__ == "__main__":
    start_http_server(int(METRICS_PORT))
    processor = SuggestionsEngine()
    processor.run()
