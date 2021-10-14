import requests
import logging
import pydash as _
from http import HTTPStatus
from contextlib import contextmanager
from tempfile import NamedTemporaryFile
from insights import extract, rule, run, make_metadata
from insights.parsers.pmlog_summary import PmLogSummary
from insights.parsers.lscpu import LsCPU
from insights.parsers.aws_instance_id import AWSInstanceIdDoc
from insights.parsers.azure_instance_type import AzureInstanceType
from insights.core import dr
from ros.lib.config import INSIGHTS_EXTRACT_LOGLEVEL
from ros.processor.metrics import (archive_downloaded_success,
                                   archive_failed_to_download,
                                   processor_requests_failures)


LOG = logging.getLogger(__name__)
dr.log.setLevel(INSIGHTS_EXTRACT_LOGLEVEL)
prefix = "ARCHIVE PROCESSOR"


@rule(PmLogSummary, LsCPU, [AWSInstanceIdDoc, AzureInstanceType])
def performance_profile(pmlog_summary, lscpu, aws_instance_id, azure_instance_type):
    profile = {}
    performance_metrics = [
        'mem.physmem',
        'mem.util.used',
        'kernel.all.cpu.user',
        'kernel.all.cpu.sys',
        'kernel.all.cpu.nice',
        'kernel.all.cpu.steal',
        'kernel.all.cpu.idle',
        'kernel.all.cpu.wait.total',
        'disk.all.total',
        'mem.util.cached',
        'mem.util.bufmem',
        'mem.util.free'
        ]
    profile["total_cpus"] = int(lscpu.info.get('CPUs'))
    if aws_instance_id:
        profile["instance_type"] = aws_instance_id.get('instanceType')
    elif azure_instance_type:
        profile["instance_type"] = azure_instance_type.raw
    else:
        profile["instance_type"] = None
    for i in performance_metrics:
        profile[i] = _.get(pmlog_summary, f'{i}.val')

    metadata_response = make_metadata()
    metadata_response.update(profile)
    return metadata_response


def get_performance_profile(report_url, account_number):
    with _download_and_extract_report(report_url, account_number) as archive:
        try:
            LOG.info(
                "%s - Starting to extract performance profile from the report present at %s.\n",
                prefix, report_url)
            broker = run(performance_profile, root=archive.tmp_dir)
            result = broker[performance_profile]
            del result["type"]
            LOG.info(
                "%s - Extracted performance profile from the report successfully present at %s.\n",
                prefix, report_url)
            return result
        except Exception as e:
            processor_requests_failures.labels(
                reporter='INVENTORY EVENTS', account_number=account_number
            ).inc()
            LOG.error("%s - Failed to extract performance_profile from the report present at %s. ERROR - %s\n",
                      prefix, report_url, e)


@contextmanager
def _download_and_extract_report(report_url, account_number):
    download_response = requests.get(report_url)
    LOG.info("%s - Starting to download the report from %s.\n", prefix, report_url)

    if download_response.status_code != HTTPStatus.OK:
        archive_failed_to_download.labels(account_number=account_number).inc()
        LOG.error("%s - Unable to download the report from %s. ERROR - %s\n",
                  prefix, report_url, download_response.reason)
    else:
        archive_downloaded_success.labels(account_number=account_number).inc()
        with NamedTemporaryFile() as tf:
            tf.write(download_response.content)
            LOG.info("%s - Downloaded the report successfully from %s.\n", prefix, report_url)
            tf.flush()
            with extract(tf.name) as ex:
                yield ex
