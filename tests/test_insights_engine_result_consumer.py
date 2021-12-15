import pytest
import json

from ros.lib.app import app
from ros.lib.models import db, PerformanceProfile
from ros.processor.insights_engine_result_consumer import InsightsEngineResultConsumer, SYSTEM_STATES
from tests.helpers.db_helper import db_get_host


PERFORMANCE_RECORD = {
    "hinv.ncpu": 8.0, "total_cpus": 1, "mem.physmem": 32617072.0,
    "instance_type": "t2.micro", "disk.dev.total": {"nvme0n1": {"val": 7.22, "units": "count / sec"}},
    "mem.util.available": 27455175.254, "kernel.all.cpu.idle": 7.55,
    "kernel.all.pressure.io.full.avg": {"1 minute": {"val": 0.006, "units": "none"},
                                        "5 minute": {"val": 0.004, "units": "none"},
                                        "10 second": {"val": 0.012, "units": "none"}},
    "kernel.all.pressure.io.some.avg": {"1 minute": {"val": 0.006, "units": "none"},
                                        "5 minute": {"val": 0.004, "units": "none"},
                                        "10 second": {"val": 0.013, "units": "none"}},
    "kernel.all.pressure.cpu.some.avg": {"1 minute": {"val": 0.575, "units": "none"},
                                         "5 minute": {"val": 0.572, "units": "none"},
                                         "10 second": {"val": 0.579, "units": "none"}},
    "kernel.all.pressure.memory.full.avg": {"1 minute": {"val": 0.0, "units": "none"},
                                            "5 minute": {"val": 0.0, "units": "none"},
                                            "10 second": {"val": 0.0, "units": "none"}},
    "kernel.all.pressure.memory.some.avg": {"1 minute": {"val": 0.0, "units": "none"},
                                            "5 minute": {"val": 0.0, "units": "none"},
                                            "10 second": {"val": 0.0, "units": "none"}}
}


@pytest.fixture(scope="session")
def engine_result_message():
    def _return_engine_msg_json(filename):
        f = open(f"sample-files/{filename}")
        msg_data = json.loads(f.read())
        f.close()
        return msg_data
    return _return_engine_msg_json


@pytest.fixture
def engine_consumer():
    return InsightsEngineResultConsumer()


def test_handle_msg(engine_result_message, engine_consumer, mocker):
    engine_result_message = engine_result_message("insights-engine-result-idle-old.json")
    mocker.patch(
        'ros.processor.insights_engine_result_consumer.get_performance_profile',
        return_value=PERFORMANCE_RECORD,
        autospec=True
    )
    mocker.patch.object(engine_consumer, 'process_report', return_value=True, autospec=True)
    engine_consumer.handle_msg(engine_result_message)
    engine_consumer.process_report.assert_called_once()


def test_process_report_idle(engine_result_message, engine_consumer, db_setup):
    engine_result_message = engine_result_message("insights-engine-result-idle-old.json")
    host = engine_result_message["input"]["host"]
    ros_reports = [engine_result_message["results"]["reports"][4]]
    system_metadata = engine_result_message["results"]["system"]["metadata"]
    engine_consumer.process_report(host, ros_reports, system_metadata, PERFORMANCE_RECORD)
    data = db_get_host(host['id'])
    assert str(data.inventory_id) == host['id']
    with app.app_context():
        assert data.instance_type == PERFORMANCE_RECORD['instance_type']
        assert db.session.query(PerformanceProfile).filter_by(system_id=data.id).first().performance_record ==\
               PERFORMANCE_RECORD


def test_process_report_under_pressure(engine_result_message, engine_consumer, db_setup):
    engine_result_message = engine_result_message("insights-engine-result-under-pressure.json")
    host = engine_result_message["input"]["host"]
    ros_reports = [engine_result_message["results"]["reports"][7]]
    system_metadata = engine_result_message["results"]["system"]["metadata"]
    engine_consumer.process_report(host, ros_reports, system_metadata, PERFORMANCE_RECORD)
    data = db_get_host(host['id'])
    assert str(data.inventory_id) == host['id']
    with app.app_context():
        assert data.instance_type == PERFORMANCE_RECORD['instance_type']
        assert data.state == SYSTEM_STATES['INSTANCE_OPTIMIZED_UNDER_PRESSURE']
        assert db.session.query(PerformanceProfile).filter_by(system_id=data.id).first().performance_record ==\
               PERFORMANCE_RECORD
