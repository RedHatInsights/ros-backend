import json
import signal

from prometheus_client import start_http_server

from ros.lib.config import (
    get_logger,
    METRICS_PORT,
    INVENTORY_EVENTS_TOPIC,
    GROUP_ID_SUGGESTIONS_ENGINE,
    POLL_TIMEOUT_SECS
)
from ros.lib import consume


logging = get_logger(__name__)


class SystemEraser:
    def __init__(self):
        self.consumer = consume.init_consumer(INVENTORY_EVENTS_TOPIC, GROUP_ID_SUGGESTIONS_ENGINE)
        self.service = 'SYSTEM_ERASER'
        self.event = 'Delete event'
        self.running = True
        signal.signal(signal.SIGTERM, self._shutdown)
        signal.signal(signal.SIGINT, self._shutdown)

    def _shutdown(self, signum, frame):
        logging.info(f"{self.service} - Shutdown signal received: {signum}")
        self.running = False

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

                    if event_type != 'delete':
                        continue

                    host = payload.get('host')
                    host_id = host.get('id')

                    logging.debug(
                        f"{self.service} - Received a message for system with inventory_id {host_id}"
                    )

                except json.JSONDecodeError as error:
                    logging.error(f"{self.service} - {self.event} - Failed to decode message: {error}")
                except Exception as error:
                    logging.error(f"{self.service} - {self.event} - Error processing message: {error}")

        except Exception as error:
            logging.error(f"{self.service} - {self.event} - error: {error}")
        finally:
            logging.info(f"{self.service} - Shutting down gracefully")
            self.consumer.close()


if __name__ == "__main__":
    start_http_server(int(METRICS_PORT))
    processor = SystemEraser()
    processor.run()
