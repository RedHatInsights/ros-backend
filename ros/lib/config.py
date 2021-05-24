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
INVENTORY_EVENTS_TOPIC = os.getenv("INVENTORY_EVENTS_TOPIC", "platform.inventory.events")

ENGINE_RESULT_TOPIC = os.getenv("ENGINE_RESULT_TOPIC", "platform.engine.results")

INSIGHTS_KAFKA_HOST = os.getenv("INSIGHTS_KAFKA_HOST", "localhost")
INSIGHTS_KAFKA_PORT = os.getenv("INSIGHTS_KAFKA_PORT", "9092")
INSIGHTS_KAFKA_ADDRESS = f"{INSIGHTS_KAFKA_HOST}:{INSIGHTS_KAFKA_PORT}"

PATH_PREFIX = os.getenv("PATH_PREFIX", "/api/")
APP_NAME = os.getenv("APP_NAME", "ros")

INSIGHTS_EXTRACT_LOGLEVEL = os.getenv("INSIGHTS_EXTRACT_LOGLEVEL", "ERROR")

GARBAGE_COLLECTION_INTERVAL = os.getenv("GARBAGE_COLLECTION_INTERVAL", 86400)
