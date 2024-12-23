import time
from ros.lib.config import get_logger
from prometheus_client import start_http_server
from ros.lib.config import ROS_SUGGESTIONS_ENGINE_PORT


logging = get_logger(__name__)


class SuggestionsEngine:
    def __init__(self):
        pass

    def run(self):
        try:
            logging.info("Flask server running on port %s", ROS_SUGGESTIONS_ENGINE_PORT)
            while True:
                time.sleep(1)
        except Exception as err:
            logging.error(err)


if __name__ == "__main__":
    start_http_server(ROS_SUGGESTIONS_ENGINE_PORT)
    processor = SuggestionsEngine()
    processor.run()
