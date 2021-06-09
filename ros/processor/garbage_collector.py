from ros.lib.app import app, db
from ros.lib.models import PerformanceProfile
from datetime import datetime, timedelta
from ros.lib.config import GARBAGE_COLLECTION_INTERVAL, DAYS_UNTIL_STALE, get_logger
import time

LOG = get_logger(__name__)


class GarbageCollector():
    def run(self):
        while True:
            self.remove_outdated_data()

    def remove_outdated_data(self):
        with app.app_context():
            results = db.session.query(PerformanceProfile).filter(
                      PerformanceProfile.report_date < datetime.today() - timedelta(days=DAYS_UNTIL_STALE)).delete()
            db.session.commit()
            if results:
                LOG.info("Deleted %s performance profiles older than %d days", results, DAYS_UNTIL_STALE)

            time.sleep(GARBAGE_COLLECTION_INTERVAL)


if __name__ == "__main__":
    collector = GarbageCollector()
    collector.run()
