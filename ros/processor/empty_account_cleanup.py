"""
One-time cleanup of rh_accounts that have no associated systems.

No systems implies no recommendations (profiles/history cascade from systems).
Run once (e.g. oc/job), then remove or leave idle — not a continuous loop.

Usage:
  # Dry-run: count only
  EMPTY_ACCOUNT_CLEANUP_DRY_RUN=true python -m ros.processor.empty_account_cleanup

  # Execute delete
  python -m ros.processor.empty_account_cleanup
"""
import os
import sys

from prometheus_client import start_http_server
from sqlalchemy import select, exists, func

from ros.lib.app import app
from ros.extensions import db
from ros.lib.models import RhAccount, System
from ros.lib.config import METRICS_PORT, get_logger, str_to_bool
from ros.lib.cw_logging import commence_cw_log_streaming

LOG = get_logger(__name__)
PREFIX = 'EMPTY ACCOUNT CLEANUP'
DRY_RUN = str_to_bool(os.getenv('EMPTY_ACCOUNT_CLEANUP_DRY_RUN', 'False'))


def _empty_accounts_filter():
    has_systems = exists(
        select(System.id).where(System.tenant_id == RhAccount.id)
    )
    return ~has_systems


def count_empty_accounts():
    return db.session.scalar(
        select(func.count()).select_from(RhAccount).where(_empty_accounts_filter())
    )


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
            LOG.info(
                f"{PREFIX} - Dry-run enabled; no accounts deleted "
                f"(set EMPTY_ACCOUNT_CLEANUP_DRY_RUN=false to purge)"
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
    except Exception as error:  # pylint: disable=broad-except
        LOG.error(f"{PREFIX} - Failed: {error}")
        sys.exit(1)
