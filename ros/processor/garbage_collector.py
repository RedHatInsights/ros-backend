from ros.lib.app import app, db
from ros.lib.models import PerformanceProfile
from datetime import datetime, timedelta
from ros.lib.config import GARBAGE_COLLECTION_INTERVAL
import time
import logging

logging.basicConfig(
    level='INFO',
    format='%(asctime)s - %(levelname)s  - %(funcName)s - %(message)s'
)
LOG = logging.getLogger(__name__)


class GarbageCollector():
    def run(self):
        while True:
            self.remove_outdated_data()

    def remove_outdated_data(self):
        with app.app_context():
            results = db.session.query(PerformanceProfile).filter(
                      PerformanceProfile.report_date < datetime.today() - timedelta(days=10)).delete()
            db.session.commit()
            if results:
                LOG.info("Deleted %s outdated performance profiles", results)

            time.sleep(GARBAGE_COLLECTION_INTERVAL)


if __name__ == "__main__":
    collector = GarbageCollector()
    collector.run()
