import pytest
from datetime import datetime
from datetime import timedelta
from ros.lib.models import db, PerformanceProfile, PerformanceProfileHistory
from ros.processor.garbage_collector import GarbageCollector
from tests.helpers.db_helper import db_get_records


@pytest.fixture
def garbage_collector():
    return GarbageCollector()


def test_remove_outdated_data(
        garbage_collector,
        db_setup,
        db_create_system,
        db_create_performance_profile,
        db_create_performance_profile_history):
    system_id = 1
    date_to_set = datetime.utcnow() - timedelta(days=46)
    profile_records = db_get_records(PerformanceProfile, system_id=system_id)
    history_records = db_get_records(PerformanceProfileHistory, system_id=system_id)
    total_profile_records_before = profile_records.count()
    total_history_records_before = history_records.count()
    assert total_profile_records_before == 1
    assert total_history_records_before == 1
    history_rec = history_records.first()
    pprofile_rec = profile_records.first()
    history_rec.report_date = date_to_set
    pprofile_rec.report_date = date_to_set
    db.session.commit()
    garbage_collector.remove_outdated_data()
    profile_records = db_get_records(PerformanceProfile, system_id=system_id)
    history_records = db_get_records(PerformanceProfileHistory, system_id=system_id)
    assert profile_records.count() == (total_profile_records_before - 1)
    assert history_records.count() == (total_history_records_before - 1)


def test_gc_method_when_no_outdated_data(
        garbage_collector,
        db_setup,
        db_create_system,
        db_create_performance_profile,
        db_create_performance_profile_history):
    system_id = 1
    profile_records = db_get_records(PerformanceProfile, system_id=system_id)
    historical_profile_records = db_get_records(
        PerformanceProfileHistory, system_id=system_id)
    assert profile_records.count() == historical_profile_records.count() == 1
    garbage_collector.remove_outdated_data()
    profile_records = db_get_records(PerformanceProfile, system_id=system_id)
    historical_profile_records = db_get_records(
        PerformanceProfileHistory, system_id=system_id)
    assert profile_records.count() == historical_profile_records.count() == 1
