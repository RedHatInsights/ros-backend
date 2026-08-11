from ros.lib.models import db, RhAccount, System
from ros.processor import empty_account_cleanup


def test_count_empty_accounts(db_setup):
    empty = RhAccount(id=20, account='empty', org_id='empty-org')
    with_system = RhAccount(id=21, account='has-sys', org_id='has-sys-org')
    system = System(
        id=21,
        tenant_id=21,
        inventory_id='bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
        display_name='host',
        cloud_provider='aws',
    )
    db.session.add_all([empty, with_system, system])
    db.session.commit()

    with empty_account_cleanup.app.app_context():
        assert empty_account_cleanup.count_empty_accounts() == 1


def test_delete_empty_accounts_purges_only_empty(db_setup, caplog, monkeypatch):
    monkeypatch.setenv('EMPTY_ACCOUNT_CLEANUP_DRY_RUN', 'False')
    # Re-read flag after env change is awkward; call delete directly.
    empty = RhAccount(id=22, account='empty2', org_id='empty-org-2', created_at=None)
    with_system = RhAccount(id=23, account='has-sys-2', org_id='has-sys-org-2')
    system = System(
        id=23,
        tenant_id=23,
        inventory_id='cccccccc-cccc-cccc-cccc-cccccccccccc',
        display_name='host-2',
        cloud_provider='aws',
    )
    db.session.add_all([empty, with_system, system])
    db.session.commit()

    with empty_account_cleanup.app.app_context():
        purged = empty_account_cleanup.delete_empty_accounts()

    assert purged == 1
    assert db.session.get(RhAccount, 22) is None
    assert db.session.get(RhAccount, 23) is not None
    assert db.session.get(System, 23) is not None


def test_run_dry_run_does_not_delete(db_setup, monkeypatch, caplog):
    monkeypatch.setattr(empty_account_cleanup, 'DRY_RUN', True)
    empty = RhAccount(id=24, account='dry', org_id='dry-org')
    db.session.add(empty)
    db.session.commit()

    candidates, purged = empty_account_cleanup.run()

    assert candidates == 1
    assert purged == 0
    assert db.session.get(RhAccount, 24) is not None
    assert "Dry-run candidate org_ids: ['dry-org']" in caplog.text
    assert "Dry-run enabled; no accounts deleted" in caplog.text


def test_run_deletes_all_empty_accounts(db_setup, monkeypatch, caplog):
    monkeypatch.setattr(empty_account_cleanup, 'DRY_RUN', False)
    a1 = RhAccount(id=25, account='a1', org_id='org-a1', created_at=None)
    a2 = RhAccount(id=26, account='a2', org_id='org-a2')
    db.session.add_all([a1, a2])
    db.session.commit()

    candidates, purged = empty_account_cleanup.run()

    assert candidates == 2
    assert purged == 2
    assert db.session.get(RhAccount, 25) is None
    assert db.session.get(RhAccount, 26) is None
    assert "Purged 2 account(s) with no associated systems" in caplog.text
