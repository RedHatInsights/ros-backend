import pytest
from datetime import datetime
from datetime import timedelta
from ros.lib.models import db, PerformanceProfile, PerformanceProfileHistory, RhAccount, System
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


def test_remove_obsolete_accounts_deletes_stale_empty_account(
        garbage_collector, db_setup, caplog):
    stale_account = RhAccount(
        id=10,
        account='stale-acct',
        org_id='stale-org',
        created_at=datetime.utcnow() - timedelta(days=91),
    )
    db.session.add(stale_account)
    db.session.commit()

    garbage_collector.remove_obsolete_accounts()

    assert db.session.get(RhAccount, 10) is None
    assert "Purged 1 obsolete account(s)" in caplog.text


def test_remove_obsolete_accounts_keeps_recent_empty_account(
        garbage_collector, db_setup):
    recent_account = RhAccount(
        id=11,
        account='recent-acct',
        org_id='recent-org',
        created_at=datetime.utcnow() - timedelta(days=30),
    )
    db.session.add(recent_account)
    db.session.commit()

    garbage_collector.remove_obsolete_accounts()

    assert db.session.get(RhAccount, 11) is not None


def test_remove_obsolete_accounts_keeps_null_created_at(
        garbage_collector, db_setup):
    null_created = RhAccount(
        id=12,
        account='null-created',
        org_id='null-org',
        created_at=None,
    )
    db.session.add(null_created)
    db.session.commit()

    garbage_collector.remove_obsolete_accounts()

    assert db.session.get(RhAccount, 12) is not None


def test_remove_obsolete_accounts_keeps_account_with_systems(
        garbage_collector, db_setup):
    account = RhAccount(
        id=13,
        account='with-systems',
        org_id='with-systems-org',
        created_at=datetime.utcnow() - timedelta(days=120),
    )
    system = System(
        id=13,
        tenant_id=13,
        inventory_id='aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',
        display_name='host-with-account',
        cloud_provider='aws',
    )
    db.session.add(account)
    db.session.add(system)
    db.session.commit()

    garbage_collector.remove_obsolete_accounts()

    assert db.session.get(RhAccount, 13) is not None
    assert db.session.get(System, 13) is not None
