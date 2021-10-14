from ros.lib.app import app, db
from ros.lib.models import PerformanceProfile, System
from datetime import datetime, timedelta, timezone
from ros.lib.config import GARBAGE_COLLECTION_INTERVAL, DAYS_UNTIL_STALE, get_logger
from ros.lib.utils import delete_record
import time

LOG = get_logger(__name__)


class GarbageCollector():
    def run(self):
        while True:
            self.remove_outdated_data()

    def remove_outdated_data(self):
        with app.app_context():
            stale_performance_profiles = db.session.query(PerformanceProfile).filter(
                PerformanceProfile.report_date < (
                    datetime.now(timezone.utc) - timedelta(
                        days=DAYS_UNTIL_STALE)
                ))
            if stale_performance_profiles:
                for record in stale_performance_profiles:
                    selected_system = db.session.query(System).filter(System.id == record.system_id).first()

                    LOG.info("Deleting performance profile of the system: %s older than %d days",
                             selected_system.inventory_id, DAYS_UNTIL_STALE)
                delete_record(db.session, PerformanceProfile, system_id=record.system_id)

            time.sleep(GARBAGE_COLLECTION_INTERVAL)
