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
from insights.core import dr
from ros.lib.config import INSIGHTS_EXTRACT_LOGLEVEL


LOG = logging.getLogger(__name__)
dr.log.setLevel(INSIGHTS_EXTRACT_LOGLEVEL)


@rule(PmLogSummary, LsCPU, AWSInstanceIdDoc)
def performance_profile(pmlog_summary, lscpu, aws_instance_id):
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
    profile["instance_type"] = aws_instance_id.get('instanceType')
    for i in performance_metrics:
        profile[i] = _.get(pmlog_summary, f'{i}.val')

    metadata_response = make_metadata()
    metadata_response.update(profile)
    return metadata_response


def get_performance_profile(report_url):
    with _download_and_extract_report(report_url) as archive:
        try:
            broker = run(performance_profile, root=archive.tmp_dir)
            result = broker[performance_profile]
            del result["type"]
            return result
        except Exception as e:
            LOG.error("Failed to extract performance_profile: %s", e)


@contextmanager
def _download_and_extract_report(report_url):
    download_response = requests.get(report_url)
    if download_response.status_code != HTTPStatus.OK:
        LOG.error("Unable to download the report. ERROR - %s", download_response.reason)
    else:
        with NamedTemporaryFile() as tf:
            tf.write(download_response.content)
            tf.flush()
            with extract(tf.name) as ex:
                yield ex
