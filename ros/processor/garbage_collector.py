from ros.lib.app import app
from ros.extensions import db
from ros.lib.models import PerformanceProfile, PerformanceProfileHistory, RhAccount, System
from datetime import datetime, timedelta, timezone
from ros.lib.config import (
    GARBAGE_COLLECTION_INTERVAL,
    DAYS_UNTIL_STALE,
    DAYS_UNTIL_ACCOUNT_STALE,
    METRICS_PORT,
    get_logger,
)
from ros.lib.cw_logging import commence_cw_log_streaming
from prometheus_client import start_http_server
from sqlalchemy import select, exists
import time

LOG = get_logger(__name__)


class GarbageCollector():
    def __init__(self):
        self.prefix = 'GARBAGE COLLECTOR'

    def run(self):
        while True:
            self.remove_outdated_data()
            self.remove_obsolete_accounts()
            time.sleep(GARBAGE_COLLECTION_INTERVAL)

    def remove_outdated_data(self):
        try:
            time_value = datetime.now(timezone.utc) - timedelta(
                        days=DAYS_UNTIL_STALE)
            with app.app_context():
                deleted_history = db.session.execute(
                    db.delete(PerformanceProfileHistory).filter(
                        PerformanceProfileHistory.report_date < time_value
                    )
                )

                if deleted_history.rowcount > 0:
                    LOG.info(
                        f"{self.prefix} - Deleted {deleted_history.rowcount} outdated history record(s) "
                        f"older than {DAYS_UNTIL_STALE} days"
                    )

                deleted_profiles = db.session.execute(
                    db.delete(PerformanceProfile).filter(PerformanceProfile.report_date < time_value)
                )

                if deleted_profiles.rowcount > 0:
                    LOG.info(
                        f"{self.prefix} - Deleted {deleted_profiles.rowcount} outdated performance profile(s) "
                        f"older than {DAYS_UNTIL_STALE} days"
                    )
                db.session.commit()
        except Exception as error:  # pylint: disable=broad-except
            LOG.error(
                f"{self.prefix} - Could not remove outdated records "
                f"due to the following error {str(error)}."
            )

    def remove_obsolete_accounts(self):
        """
        Purge rh_accounts that have no associated systems and whose created_at
        is older than DAYS_UNTIL_ACCOUNT_STALE. Accounts with NULL created_at
        are skipped (cannot evaluate staleness).
        """
        if DAYS_UNTIL_ACCOUNT_STALE < 1:
            LOG.error(
                f"{self.prefix} - Skipping obsolete account purge: "
                f"DAYS_UNTIL_ACCOUNT_STALE must be >= 1 "
                f"(got {DAYS_UNTIL_ACCOUNT_STALE})"
            )
            return

        # created_at is naive UTC; use utcnow() to match.
        cutoff = datetime.utcnow() - timedelta(days=DAYS_UNTIL_ACCOUNT_STALE)
        has_systems = exists(
            select(System.id).where(System.tenant_id == RhAccount.id)
        )

        with app.app_context():
            try:
                deleted_accounts = db.session.execute(
                    db.delete(RhAccount).where(
                        RhAccount.created_at.is_not(None),
                        RhAccount.created_at <= cutoff,
                        ~has_systems,
                    )
                )
                db.session.commit()
                LOG.info(
                    f"{self.prefix} - Purged {deleted_accounts.rowcount} obsolete account(s) "
                    f"with no systems and created_at older than {DAYS_UNTIL_ACCOUNT_STALE} days"
                )
            except Exception as error:  # pylint: disable=broad-except
                LOG.error(
                    f"{self.prefix} - Could not remove obsolete accounts "
                    f"due to the following error {error}."
                )


if __name__ == "__main__":
    start_http_server(int(METRICS_PORT))
    commence_cw_log_streaming('ros-garbage-collector')
    processor = GarbageCollector()
    processor.run()
