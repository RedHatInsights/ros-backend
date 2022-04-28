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
            time.sleep(int(GARBAGE_COLLECTION_INTERVAL))

    def remove_outdated_data(self):
        try:
            time_value = datetime.now(timezone.utc) - timedelta(
                        days=int(DAYS_UNTIL_STALE))
            with app.app_context():
                deleted_history = db.session.query(
                    PerformanceProfileHistory).filter(
                        PerformanceProfileHistory.report_date < time_value
                    ).delete()

                if deleted_history:
                    LOG.info(
                        "%s - Deleted %s outdated history record(s) "
                        "older than %d days",
                        self.prefix, deleted_history, DAYS_UNTIL_STALE
                    )

                deleted_profiles = db.session.query(
                    PerformanceProfile
                ).filter(PerformanceProfile.report_date < time_value).delete()

                if deleted_profiles:
                    LOG.info(
                        "%s - Deleted %s outdated performance profile(s) "
                        "older than %d days",
                        self.prefix, deleted_profiles, DAYS_UNTIL_STALE
                    )
                db.session.commit()
        except Exception as error:  # pylint: disable=broad-except
            LOG.error(
                "%s - Could not remove outdated records "
                "due to the following error %s.",
                self.prefix, str(error)
            )
