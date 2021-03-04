import os
import logging

LOG = logging.getLogger(__name__)

CLOWDER_ENABLED = True if os.getenv("CLOWDER_ENABLED", default="False").lower() in ["true", "t", "yes", "y"] else False

if CLOWDER_ENABLED:
    LOG.info("Using Clowder Operator...")
    from app_common_python import LoadedConfig, KafkaTopics
    INSIGHTS_KAFKA_ADDRESS = LoadedConfig.kafka.brokers[0].hostname + ":" + str(LoadedConfig.kafka.brokers[0].port)
    INVENTORY_EVENTS_TOPIC = KafkaTopics["platform.inventory.events"].name
    DB_USER = LoadedConfig.database.username
    DB_PASSWORD = LoadedConfig.database.password
    DB_HOST = LoadedConfig.database.hostname
    DB_PORT = LoadedConfig.database.port
    DB_NAME = LoadedConfig.database.name

else:
    INSIGHTS_KAFKA_HOST = os.getenv("INSIGHTS_KAFKA_HOST", "localhost")
    INSIGHTS_KAFKA_PORT = os.getenv("INSIGHTS_KAFKA_PORT", "9092")
    INSIGHTS_KAFKA_ADDRESS = f"{INSIGHTS_KAFKA_HOST}:{INSIGHTS_KAFKA_PORT}"
    INVENTORY_EVENTS_TOPIC = os.getenv("INVENTORY_EVENTS_TOPIC", "platform.inventory.events")
    DB_USER = os.getenv("ROS_DB_USER", "postgres")
    DB_PASSWORD = os.getenv("ROS_DB_PASS", "postgres")
    DB_HOST = os.getenv("ROS_DB_HOST", "localhost")
    DB_PORT = os.getenv("ROS_DB_PORT", "15432")
    DB_NAME = os.getenv("ROS_DB_NAME", "postgres")


DB_URI = f"postgresql://{DB_USER}:{DB_PASSWORD}"\
                    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"

PATH_PREFIX = os.getenv("PATH_PREFIX", "/api/")
APP_NAME = os.getenv("APP_NAME", "ros")
GROUP_ID = os.getenv('GROUP_ID', 'resource-optimization')

# Below inventory configs are deprecated.
INVENTORY_HOST = os.getenv("INVENTORY_HOST", "localhost")
INVENTORY_PORT = os.getenv("INVENTORY_PORT", "8081")
INVENTORY_URL = f"http://{INVENTORY_HOST}:{INVENTORY_PORT}"
