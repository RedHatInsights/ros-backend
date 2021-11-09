from ros.lib.app import app, db
from ros.lib.models import PerformanceProfile
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

    def remove_outdated_data(self):
        with app.app_context():
            results = db.session.query(PerformanceProfile).filter(
                PerformanceProfile.report_date < (
                    datetime.now(timezone.utc) - timedelta(
                        days=DAYS_UNTIL_STALE)
                )).delete()
            db.session.commit()
            if results:
                LOG.info("%s - Deleted %s performance profiles older than %d days",
                         self.prefix, results, DAYS_UNTIL_STALE)

            time.sleep(GARBAGE_COLLECTION_INTERVAL)
