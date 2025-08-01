import pytest
import json
import copy
from pathlib import Path
from ros.lib.app import app
from ros.lib.models import db, PerformanceProfile, PerformanceProfileHistory
from ros.processor.insights_engine_consumer import InsightsEngineConsumer
from ros.lib.constants import SystemStatesWithKeys
from tests.helpers.db_helper import db_get_host, db_get_record
from ros.processor.notification_event_producer import notification_payload


@pytest.fixture(scope="function")
def performance_record():
    PERFORMANCE_RECORD = {
        "hinv.ncpu": 8.0, "total_cpus": 1, "mem.physmem": 32617072.0,
        "instance_type": "t2.micro", "disk.dev.total": {"nvme0n1": {"val": 7.22, "units": "count / sec"}},
        "mem.util.available": 27455175.254, "kernel.all.cpu.idle": 7.55, 'region': 'ap-northeast-1',
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
    return PERFORMANCE_RECORD


@pytest.fixture(scope="session")
def engine_result_message():
    def _return_engine_msg_json(filename):
        f = open(f"{Path(__file__).parent}/data_files/{filename}")
        msg_data = json.loads(f.read())
        f.close()
        return msg_data

    return _return_engine_msg_json


@pytest.fixture
def engine_consumer():
    return InsightsEngineConsumer()


def test_handle_msg(engine_result_message, engine_consumer, mocker, performance_record, redis_client):
    engine_result_message = engine_result_message("insights-engine-result-idle.json")
    mocker.patch(
        'ros.processor.insights_engine_consumer.get_performance_profile',
        return_value=performance_record,
        autospec=True
    )
    mocker.patch.object(engine_consumer, 'process_report', return_value=True, autospec=True)
    engine_consumer.handle_msg(engine_result_message)
    engine_consumer.process_report.assert_called_once()


def test_process_report_idle(engine_result_message, engine_consumer, db_setup, performance_record):
    engine_result_message = engine_result_message("insights-engine-result-idle.json")
    host = engine_result_message["input"]["host"]
    ros_reports = [engine_result_message["results"]["reports"][7]]
    system_metadata = engine_result_message["results"]["system"]["metadata"]
    platform_metadata = engine_result_message["input"]["platform_metadata"]
    _performance_record = copy.copy(performance_record)
    engine_consumer.process_report(host, platform_metadata, ros_reports, system_metadata, performance_record)
    system_record = db_get_host(host['id'])
    assert str(system_record.inventory_id) == host['id']
    assert system_record.groups == host['groups']
    with app.app_context():
        assert system_record.instance_type == _performance_record['instance_type']
        assert system_record.region == _performance_record['region']
        assert system_record.state == SystemStatesWithKeys.INSTANCE_IDLE.value
        assert db.session.scalar(db.select(PerformanceProfile).filter_by(system_id=system_record.id))\
            .performance_record == performance_record


def test_process_report_under_pressure(engine_result_message, engine_consumer,
                                       db_setup, performance_record):
    engine_result_message = engine_result_message("insights-engine-result-under-pressure.json")
    host = engine_result_message["input"]["host"]
    ros_reports = [engine_result_message["results"]["reports"][7]]
    system_metadata = engine_result_message["results"]["system"]["metadata"]
    platform_metadata = engine_result_message["input"]["platform_metadata"]
    _performance_record = copy.copy(performance_record)
    engine_consumer.process_report(host, platform_metadata, ros_reports, system_metadata, performance_record)
    system_record = db_get_host(host['id'])
    assert str(system_record.inventory_id) == host['id']
    assert system_record.groups == host['groups']
    with app.app_context():
        assert system_record.instance_type == _performance_record['instance_type']
        assert system_record.region == _performance_record['region']
        assert system_record.state == SystemStatesWithKeys.INSTANCE_OPTIMIZED_UNDER_PRESSURE.value
        assert db.session.scalar(db.select(PerformanceProfile).filter_by(system_id=system_record.id))\
            .performance_record == performance_record


def test_process_report_no_pcp(engine_result_message, engine_consumer, db_setup, performance_record):
    engine_result_message = engine_result_message("insights-engine-result-no-pcp.json")
    host = engine_result_message["input"]["host"]
    ros_reports = [engine_result_message["results"]["reports"][7]]
    system_metadata = engine_result_message["results"]["system"]["metadata"]
    platform_metadata = engine_result_message["input"]["platform_metadata"]
    _performance_record = copy.copy(performance_record)
    engine_consumer.process_report(host, platform_metadata, ros_reports, system_metadata, performance_record)
    system_record = db_get_host(host['id'])
    performance_utilization = db.session.scalar(db.select(PerformanceProfile)
                                                .filter_by(system_id=system_record.id)).performance_utilization
    sample_performance_util_no_pcp = {'cpu': -1, 'memory': -1, 'max_io': -1.0, 'io': {}}
    assert str(system_record.inventory_id) == host['id']
    assert system_record.groups == host['groups']
    with app.app_context():
        assert system_record.instance_type == _performance_record['instance_type']
        assert system_record.region == _performance_record['region']
        assert system_record.state == SystemStatesWithKeys.NO_PCP_DATA.value
        assert performance_utilization == sample_performance_util_no_pcp


def test_process_report_undersized(engine_result_message, engine_consumer, db_setup, performance_record):
    engine_result_message = engine_result_message("insights-engine-result-undersized.json")
    host = engine_result_message["input"]["host"]
    ros_reports = [engine_result_message["results"]["reports"][7]]
    system_metadata = engine_result_message["results"]["system"]["metadata"]
    platform_metadata = engine_result_message["input"]["platform_metadata"]
    _performance_record = copy.copy(performance_record)
    engine_consumer.process_report(host, platform_metadata, ros_reports, system_metadata, performance_record)
    system_record = db_get_host(host['id'])
    assert str(system_record.inventory_id) == host['id']
    assert system_record.groups == host['groups']
    with app.app_context():
        assert system_record.instance_type == _performance_record['instance_type']
        assert system_record.region == _performance_record['region']
        assert system_record.state == SystemStatesWithKeys.INSTANCE_UNDERSIZED.value
        assert db.session.scalar(db.select(PerformanceProfile).filter_by(system_id=system_record.id))\
            .performance_record == performance_record


def test_process_report_optimized(engine_result_message, engine_consumer, db_setup, performance_record):
    engine_result_message = engine_result_message("insights-engine-result-optimized.json")
    host = engine_result_message["input"]["host"]
    ros_reports = []
    system_metadata = engine_result_message["results"]["system"]["metadata"]
    platform_metadata = engine_result_message["input"]["platform_metadata"]
    _performance_record = copy.copy(performance_record)
    engine_consumer.process_report(host, platform_metadata, ros_reports, system_metadata, performance_record)
    system_record = db_get_host(host['id'])
    profile_record = db_get_record(PerformanceProfile, system_id=system_record.id)
    assert str(system_record.inventory_id) == host['id']
    assert system_record.groups == host['groups']
    with app.app_context():
        assert profile_record.rule_hit_details == ros_reports
        assert system_record.instance_type == _performance_record['instance_type']
        assert system_record.region == _performance_record['region']
        assert system_record.state == SystemStatesWithKeys.OPTIMIZED.value
        assert db.session.scalar(db.select(PerformanceProfile).filter_by(system_id=system_record.id))\
            .performance_record == performance_record


def test_system_properties(engine_result_message, engine_consumer, db_setup, performance_record):
    engine_result_message = engine_result_message("insights-engine-result-idle.json")
    host = engine_result_message["input"]["host"]
    ros_reports = [engine_result_message["results"]["reports"][7]]
    system_metadata = engine_result_message["results"]["system"]["metadata"]
    platform_metadata = engine_result_message["input"]["platform_metadata"]
    engine_consumer.process_report(host, platform_metadata, ros_reports, system_metadata, performance_record)
    data = db_get_host(host['id'])
    assert str(data.inventory_id) == host['id']
    assert data.groups == host['groups']


def test_history_record_creation(engine_result_message, engine_consumer, db_setup, performance_record):
    engine_result_message = engine_result_message("insights-engine-result-idle.json")
    host = engine_result_message["input"]["host"]
    ros_reports = [engine_result_message["results"]["reports"][7]]
    system_metadata = engine_result_message["results"]["system"]["metadata"]
    platform_metadata = engine_result_message["input"]["platform_metadata"]
    engine_consumer.process_report(host, platform_metadata, ros_reports, system_metadata, performance_record)
    system_record = db_get_host(host['id'])
    assert str(system_record.inventory_id) == host['id']
    with app.app_context():
        history_rec_count = PerformanceProfileHistory.query.filter_by(
            system_id=system_record.id
        ).count()
        assert history_rec_count == 1


def test_substate_updates(engine_result_message, engine_consumer, db_setup, performance_record):
    engine_result_message = engine_result_message("insights-engine-result-under-pressure.json")
    host = engine_result_message["input"]["host"]
    ros_reports = [engine_result_message["results"]["reports"][7]]
    system_metadata = engine_result_message["results"]["system"]["metadata"]
    platform_metadata = engine_result_message["input"]["platform_metadata"]
    ros_reports[0]['details'].update({
        "states":
            {
                'cpu': ['CPU_UNDERSIZED', 'CPU_UNDERSIZED_BY_PRESSURE'],
                'io': ['IO_UNDERSIZED_BY_PRESSURE'],
                'memory': ['MEMORY_UNDERSIZED', 'MEMORY_UNDERSIZED_BY_PRESSURE']
            }

    })
    engine_consumer.process_report(host, platform_metadata, ros_reports, system_metadata, performance_record)
    system_record = db_get_host(host['id'])
    assert str(system_record.inventory_id) == host['id']
    with app.app_context():
        assert system_record.cpu_states == ['CPU_UNDERSIZED', 'CPU_UNDERSIZED_BY_PRESSURE']
        assert system_record.io_states == ['IO_UNDERSIZED_BY_PRESSURE']
        assert system_record.memory_states == ['MEMORY_UNDERSIZED', 'MEMORY_UNDERSIZED_BY_PRESSURE']


def test_process_report_psi_enabled(engine_result_message, engine_consumer, db_setup, performance_record):
    engine_result_message = engine_result_message("insights-engine-result-idle.json")
    host = engine_result_message["input"]["host"]
    ros_reports = [engine_result_message["results"]["reports"][7]]
    system_metadata = engine_result_message["results"]["system"]["metadata"]
    platform_metadata = engine_result_message["input"]["platform_metadata"]
    engine_consumer.process_report(host, platform_metadata, ros_reports, system_metadata, performance_record)
    system_record = db_get_host(host['id'])
    psi_enabled = db.session.scalar(db.select(PerformanceProfile).filter_by(system_id=system_record.id))\
                    .psi_enabled
    assert psi_enabled is True


def test_notification(engine_result_message, engine_consumer, db_setup, performance_record):
    engine_result_message = engine_result_message("insights-engine-result-under-pressure.json")
    host = engine_result_message["input"]["host"]
    platform_metadata = engine_result_message["input"]["platform_metadata"]
    ros_reports = [engine_result_message["results"]["reports"][7]]
    system_metadata = engine_result_message["results"]["system"]["metadata"]
    system_previous_state = "Idle"
    engine_consumer.process_report(host, platform_metadata, ros_reports, system_metadata, performance_record)
    system_record = db_get_host(host['id'])
    response = notification_payload(
        host, system_previous_state, system_record.state)

    assert response["account_id"] == host["account"]
    assert response["context"]["display_name"] == "ip-172-31-28-69.ec2.internal"
    assert response["events"][0]["payload"]["inventory_id"] == host["id"]
    assert response["events"][0]["payload"]["previous_state"] == system_previous_state
    assert response["events"][0]["payload"]["current_state"] == system_record.state
    assert response["bundle"] == "rhel"
    assert response["application"] == "resource-optimization"
    assert response["event_type"] == "new-suggestion"
