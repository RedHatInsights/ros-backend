import os

DB_USER = os.getenv("ROS_DB_USER", "postgres")
DB_PASSWORD = os.getenv("ROS_DB_PASS", "postgres")
DB_HOST = os.getenv("ROS_DB_HOST", "localhost")
DB_PORT = os.getenv("ROS_DB_PORT", "15432")
DB_NAME = os.getenv("ROS_DB_NAME", "postgres")
DB_URI = f"postgresql://{DB_USER}:{DB_PASSWORD}"\
                f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"

GROUP_ID = os.getenv('GROUP_ID', 'resource-optimization')

INVENTORY_HOST = os.getenv("INVENTORY_HOST", "localhost")
INVENTORY_PORT = os.getenv("INVENTORY_PORT", "8081")
INVENTORY_URL = f"http://{INVENTORY_HOST}:{INVENTORY_PORT}"
INVENTORY_EGRESS_TOPIC = os.getenv(
    "INVENTORY_EGRESS_TOPIC", "platform.inventory.events")


INSIGHTS_KAFKA_HOST = os.getenv("INSIGHTS_KAFKA_HOST", "localhost")
INSIGHTS_KAFKA_PORT = os.getenv("INSIGHTS_KAFKA_PORT", "29092")
INSIGHTS_KAFKA_ADDRESS = f"{INSIGHTS_KAFKA_HOST}:{INSIGHTS_KAFKA_PORT}"
