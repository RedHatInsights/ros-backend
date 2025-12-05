import pytest
from datetime import datetime, timezone
from ros.lib.app import app
from ros.processor.report_processor_consumer import ReportProcessorConsumer
from ros.lib.models import RhAccount, PerformanceProfile, PerformanceProfileHistory
from ros.extensions import db
from tests.helpers.db_helper import db_get_host


@pytest.fixture(scope="function")
def report_processor_consumer():
    return ReportProcessorConsumer()


@pytest.fixture(scope="function")
def report_event_without_perf_data():
    return {
        "type": "created",
        "org_id": "000001",
        "platform_metadata": {
            "request_id": "test-request-id",
            "org_id": "000001"
        },
        "id": "ee0b9978-fe1b-4191-8408-cbadbd47f7a2",
        "display_name": "test-system.example.com",
        "fqdn": "test-system.example.com",
        "stale_timestamp": "2024-12-31T23:59:59.000Z",
        "groups": ["test-group-1"],
        "operating_system": {
            "name": "RHEL",
            "major": 8,
            "minor": 5
        },
        "cloud_provider": "aws"
    }


@pytest.fixture(scope="function")
def report_event_with_perf_data():
    return {
        "type": "created",
        "org_id": "000001",
        "platform_metadata": {
            "request_id": "test-request-id",
            "org_id": "000001"
        },
        "id": "ee0b9978-fe1b-4191-8408-cbadbd47f7a3",
        "display_name": "test-system-perf.example.com",
        "fqdn": "test-system-perf.example.com",
        "stale_timestamp": "2024-12-31T23:59:59.000Z",
        "groups": ["test-group-1"],
        "operating_system": {
            "name": "RHEL",
            "major": 8,
            "minor": 5
        },
        "cloud_provider": "aws",
        "cpu_states": ["CPU_IDLE"],
        "io_states": ["IO_IDLE"],
        "memory_states": ["MEMORY_IDLE"],
        "state": "Idling",
        "instance_type": "t2.micro",
        "region": "us-east-1",
        "performance_record": {
            "total_cpus": 1,
            "mem.physmem": 825152.0,
            "kernel.all.cpu.idle": 0.994
        },
        "performance_utilization": {
            "memory": 80,
            "cpu": 5,
            "io": {"sda": 10.0, "sdb": 5.0},
            "max_io": 10.0
        },
        "report_date": datetime.now(timezone.utc).isoformat(),
        "rule_hit_details": [
            {
                "key": "IDLE",
                "rule_id": "ros_instance_evaluation|IDLE"
            }
        ],
        "number_of_recommendations": 3,
        "psi_enabled": False,
        "top_candidate": "t2.nano",
        "top_candidate_price": 0.0058
    }


@pytest.fixture(scope="function")
def update_event_without_perf_data():
    return {
        "type": "updated",
        "org_id": "000001",
        "platform_metadata": {
            "request_id": "test-request-id-update",
            "org_id": "000001"
        },
        "id": "ee0b9978-fe1b-4191-8408-cbadbd47f7a2",
        "display_name": "updated-test-system.example.com",
        "fqdn": "updated-test-system.example.com",
        "stale_timestamp": "2024-12-31T23:59:59.000Z",
        "groups": ["test-group-1", "test-group-2"],
        "operating_system": {
            "name": "RHEL",
            "major": 8,
            "minor": 6
        },
        "cloud_provider": "aws"
    }


def test_has_performance_data(report_processor_consumer, report_event_with_perf_data, report_event_without_perf_data):
    assert report_processor_consumer._has_performance_data(report_event_with_perf_data) is True
    assert report_processor_consumer._has_performance_data(report_event_without_perf_data) is False


def test_process_without_performance_data_create(
    report_processor_consumer, report_event_without_perf_data, db_setup
):
    with app.app_context():
        report_processor_consumer._process_without_performance_data(report_event_without_perf_data)

        account = db.session.scalar(
            db.select(RhAccount).filter_by(org_id=report_event_without_perf_data['org_id'])
        )
        assert account is not None
        assert account.org_id == report_event_without_perf_data['org_id']

        system = db_get_host(report_event_without_perf_data['id'])
        assert system is not None
        assert str(system.inventory_id) == report_event_without_perf_data['id']
        assert system.display_name == report_event_without_perf_data['display_name']
        assert system.fqdn == report_event_without_perf_data['fqdn']
        assert system.cloud_provider == report_event_without_perf_data['cloud_provider']
        assert system.groups == report_event_without_perf_data['groups']
        assert system.operating_system == report_event_without_perf_data['operating_system']


def test_process_without_performance_data_update(
    report_processor_consumer, report_event_without_perf_data, update_event_without_perf_data, db_setup
):
    with app.app_context():
        # First create the record
        report_processor_consumer._process_without_performance_data(report_event_without_perf_data)

        # Then update it
        report_processor_consumer._process_without_performance_data(update_event_without_perf_data)

        system = db_get_host(update_event_without_perf_data['id'])
        assert system is not None
        assert system.display_name == update_event_without_perf_data['display_name']
        assert system.fqdn == update_event_without_perf_data['fqdn']
        assert system.groups == update_event_without_perf_data['groups']


def test_process_with_performance_data(
    report_processor_consumer, report_event_with_perf_data, db_setup
):
    with app.app_context():
        report_processor_consumer._process_with_performance_data(report_event_with_perf_data)

        account = db.session.scalar(
            db.select(RhAccount).filter_by(org_id=report_event_with_perf_data['org_id'])
        )
        assert account is not None

        system = db_get_host(report_event_with_perf_data['id'])
        assert system is not None
        assert str(system.inventory_id) == report_event_with_perf_data['id']
        assert system.display_name == report_event_with_perf_data['display_name']
        assert system.cloud_provider == report_event_with_perf_data['cloud_provider']
        assert system.state == report_event_with_perf_data['state']
        assert system.instance_type == report_event_with_perf_data['instance_type']
        assert system.region == report_event_with_perf_data['region']
        assert system.cpu_states == report_event_with_perf_data['cpu_states']
        assert system.io_states == report_event_with_perf_data['io_states']
        assert system.memory_states == report_event_with_perf_data['memory_states']

        # Verify PerformanceProfile record
        perf_profile = db.session.scalar(
            db.select(PerformanceProfile).filter_by(system_id=system.id)
        )
        assert perf_profile is not None
        assert perf_profile.performance_record == report_event_with_perf_data['performance_record']
        assert perf_profile.performance_utilization == report_event_with_perf_data['performance_utilization']
        assert perf_profile.state == report_event_with_perf_data['state']
        assert perf_profile.number_of_recommendations == report_event_with_perf_data['number_of_recommendations']
        assert perf_profile.psi_enabled == report_event_with_perf_data['psi_enabled']
        assert perf_profile.top_candidate == report_event_with_perf_data['top_candidate']
        assert perf_profile.top_candidate_price == report_event_with_perf_data['top_candidate_price']

        # Verify PerformanceProfileHistory record
        perf_history = db.session.scalar(
            db.select(PerformanceProfileHistory).filter_by(system_id=system.id)
        )
        assert perf_history is not None
        assert perf_history.performance_record == report_event_with_perf_data['performance_record']
        assert perf_history.performance_utilization == report_event_with_perf_data['performance_utilization']
        assert perf_history.state == report_event_with_perf_data['state']
