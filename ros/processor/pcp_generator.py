from ros.processor import app
from ros.lib.config import get_logger
from ros.lib.config import ROS_PCP_PROCESSOR_PORT


logging = get_logger(__name__)


class PCPGenerator:
    def __init__(self):
        pass


if __name__ == "__main__":
    logging.info("Flask server running on port %s", ROS_PCP_PROCESSOR_PORT)
    app.run(host='0.0.0.0', port=ROS_PCP_PROCESSOR_PORT)
