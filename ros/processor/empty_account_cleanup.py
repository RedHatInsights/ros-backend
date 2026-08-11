"""
One-time cleanup of rh_accounts that have no associated systems.

No systems implies no recommendations (profiles/history cascade from systems).

Controlled from app-interface like KESSEL_ENABLED:
  EMPTY_ACCOUNT_CLEANUP_DRY_RUN (default True)

Usage:
  # Dry-run (default): count + log candidate org_ids
  EMPTY_ACCOUNT_CLEANUP_DRY_RUN=true python -m ros.processor.empty_account_cleanup

  # Execute delete
  EMPTY_ACCOUNT_CLEANUP_DRY_RUN=false python -m ros.processor.empty_account_cleanup
"""
import os
import sys
import time

from prometheus_client import start_http_server
from sqlalchemy import select, exists, func

from ros.lib.app import app
from ros.extensions import db
from ros.lib.models import RhAccount, System
from ros.lib.config import METRICS_PORT, get_logger, str_to_bool
from ros.lib.cw_logging import commence_cw_log_streaming

LOG = get_logger(__name__)
PREFIX = 'EMPTY ACCOUNT CLEANUP'
# Default True so a misconfigured deploy does not purge until explicitly enabled.
DRY_RUN = str_to_bool(os.getenv('EMPTY_ACCOUNT_CLEANUP_DRY_RUN', 'True'))
DRY_RUN_ORG_ID_LOG_LIMIT = int(os.getenv('EMPTY_ACCOUNT_CLEANUP_ORG_ID_LOG_LIMIT', '100'))


def _empty_accounts_filter():
    has_systems = exists(
        select(System.id).where(System.tenant_id == RhAccount.id)
    )
    return ~has_systems


def count_empty_accounts():
    return db.session.scalar(
        select(func.count()).select_from(RhAccount).where(_empty_accounts_filter())
    )


def list_empty_account_org_ids(limit=None):
    stmt = (
        select(RhAccount.org_id)
        .where(_empty_accounts_filter())
        .order_by(RhAccount.id)
    )
    if limit is not None:
        stmt = stmt.limit(limit)
    return list(db.session.scalars(stmt).all())


def delete_empty_accounts():
    deleted = db.session.execute(
        db.delete(RhAccount).where(_empty_accounts_filter())
    )
    db.session.commit()
    return deleted.rowcount


def run():
    with app.app_context():
        candidate_count = count_empty_accounts()
        LOG.info(
            f"{PREFIX} - Found {candidate_count} account(s) with no associated systems"
        )

        if DRY_RUN:
            org_ids = list_empty_account_org_ids(limit=DRY_RUN_ORG_ID_LOG_LIMIT)
            if candidate_count > DRY_RUN_ORG_ID_LOG_LIMIT:
                LOG.info(
                    f"{PREFIX} - Dry-run candidate org_ids "
                    f"(first {DRY_RUN_ORG_ID_LOG_LIMIT} of {candidate_count}): {org_ids}"
                )
            else:
                LOG.info(f"{PREFIX} - Dry-run candidate org_ids: {org_ids}")
            LOG.info(
                f"{PREFIX} - Dry-run enabled; no accounts deleted "
                f"(set EMPTY_ACCOUNT_CLEANUP_DRY_RUN=false in app-interface to purge)"
            )
            return candidate_count, 0

        purged = delete_empty_accounts()
        if purged > 0:
            LOG.info(
                f"{PREFIX} - Purged {purged} account(s) with no associated systems"
            )
        return candidate_count, purged


if __name__ == "__main__":
    start_http_server(int(METRICS_PORT))
    commence_cw_log_streaming('ros-empty-account-cleanup')
    try:
        run()
        # Keep the pod alive so the Deployment does not restart and re-run cleanup.
        LOG.info(f"{PREFIX} - Complete; idling until scale-down or restart")
        while True:
            time.sleep(3600)
    except Exception as error:  # pylint: disable=broad-except
        LOG.error(f"{PREFIX} - Failed: {error}")
        sys.exit(1)
