import json
import signal

from prometheus_client import start_http_server

from ros.lib.config import (
    get_logger,
    METRICS_PORT,
    INVENTORY_EVENTS_TOPIC,
    GROUP_ID_SYSTEM_ERASER,
    POLL_TIMEOUT_SECS,
    UNLEASH_ROS_V2_FLAG
)
from ros.lib import consume
from ros.lib.app import app
from ros.extensions import db, cache
from ros.lib.models import System
from ros.lib.unleash import is_feature_flag_enabled
from ros.lib.cache_utils import set_deleted_system_cache


logging = get_logger(__name__)


class SystemEraser:
    def __init__(self):
        self.consumer = consume.init_consumer(INVENTORY_EVENTS_TOPIC, GROUP_ID_SYSTEM_ERASER)
        self.service = 'SYSTEM_ERASER'
        self.event = 'Delete event'
        self.running = True
        signal.signal(signal.SIGTERM, self._shutdown)
        signal.signal(signal.SIGINT, self._shutdown)

    def _shutdown(self, signum, frame):
        logging.info(f"{self.service} - Shutdown signal received: {signum}")
        self.running = False

    def delete_system(self, host_id, org_id=None, event_timestamp=None):
        try:
            with app.app_context():
                rows_deleted = db.session.execute(
                    db.delete(System).filter(System.inventory_id == host_id)
                )
                db.session.commit()

                if org_id:
                    set_deleted_system_cache(org_id, host_id, event_timestamp)

                if rows_deleted.rowcount > 0:
                    logging.info(
                        f"{self.service} - Successfully deleted {rows_deleted.rowcount} system(s) "
                        f"with inventory_id: {host_id}"
                    )
                    return True
                else:
                    logging.warning(
                        f"{self.service} - No system found with inventory_id: {host_id}"
                    )
                    return False

        except Exception as error:
            logging.error(
                f"{self.service} - {self.event} - Failed to delete system with "
                f"inventory_id {host_id}: {error}"
            )
            return False

    def run(self):
        logging.info(f"{self.service} - System Eraser is running. Awaiting msgs.")
        try:
            while self.running:
                message = self.consumer.poll(timeout=POLL_TIMEOUT_SECS)
                if message is None:
                    continue

                try:
                    payload = json.loads(message.value().decode('utf-8'))
                    event_type = payload.get('type')

                    org_id = payload.get('org_id')
                    if not is_feature_flag_enabled(org_id, UNLEASH_ROS_V2_FLAG, self.service):
                        continue

                    if event_type != 'delete':
                        continue

                    host_id = payload.get('id')
                    event_timestamp = payload.get('timestamp')

                    logging.debug(
                        f"{self.service} - Received delete message for system {host_id}"
                    )

                    self.delete_system(host_id, org_id, event_timestamp)

                except json.JSONDecodeError as error:
                    logging.error(f"{self.service} - {self.event} - Failed to decode message: {error}")
                except Exception as error:
                    logging.error(f"{self.service} - {self.event} - Error processing message: {error}")
                finally:
                    self.consumer.commit()

        except Exception as error:
            logging.error(f"{self.service} - {self.event} - error: {error}")
        finally:
            logging.info(f"{self.service} - Shutting down gracefully")
            self.consumer.close()


if __name__ == "__main__":
    start_http_server(int(METRICS_PORT))
    cache.init_app(app)
    processor = SystemEraser()
    processor.run()
