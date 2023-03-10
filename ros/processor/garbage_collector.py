from ros.lib.app import app, db
from ros.lib.models import PerformanceProfile, PerformanceProfileHistory
from datetime import datetime, timedelta, timezone
from ros.lib.config import GARBAGE_COLLECTION_INTERVAL, DAYS_UNTIL_STALE, get_logger
import time

LOG = get_logger(__name__)


class GarbageCollector():
    def __init__(self):
        self.prefix = 'GARBAGE COLLECTOR'

    def run(self):
        while True:
            self.remove_outdated_data()
            time.sleep(GARBAGE_COLLECTION_INTERVAL)

    def remove_outdated_data(self):
        try:
            time_value = datetime.now(timezone.utc) - timedelta(
                        days=DAYS_UNTIL_STALE)
            with app.app_context():
                deleted_history = db.session.query(
                    PerformanceProfileHistory).filter(
                        PerformanceProfileHistory.report_date < time_value
                    ).delete()

                if deleted_history:
                    LOG.info(
                        f"{self.prefix} - Deleted {deleted_history} outdated history record(s) "
                        f"older than {DAYS_UNTIL_STALE} days"
                    )

                deleted_profiles = db.session.query(
                    PerformanceProfile
                ).filter(PerformanceProfile.report_date < time_value).delete()

                if deleted_profiles:
                    LOG.info(
                        f"{self.prefix} - Deleted {deleted_profiles} outdated performance profile(s) "
                        f"older than {DAYS_UNTIL_STALE} days"
                    )
                db.session.commit()
        except Exception as error:  # pylint: disable=broad-except
            LOG.error(
                f"{self.prefix} - Could not remove outdated records "
                f"due to the following error {str(error)}."
            )
