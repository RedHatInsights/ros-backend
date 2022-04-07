import os
import logging


# small helper to convert strings to boolean
def str_to_bool(s):
    try:
        if s.lower() == "true":
            return True
        if s.lower() == "false":
            return False
    except AttributeError:
        raise ValueError("Valid string argument expected")
    raise ValueError("Unable to determine boolean value from given string argument")


def get_logger(name):
    logging.basicConfig(
        level='INFO',
        format='%(asctime)s - %(levelname)s  - %(funcName)s - %(message)s'
    )
    return logging.getLogger(name)


LOG = logging.getLogger(__name__)
CLOWDER_ENABLED = True if os.getenv("CLOWDER_ENABLED", default="False").lower() in ["true", "t", "yes", "y"] else False

if CLOWDER_ENABLED:
    LOG.info("Using Clowder Operator...")
    from app_common_python import LoadedConfig, KafkaTopics
    DB_NAME = LoadedConfig.database.name
    DB_USER = LoadedConfig.database.username
    DB_PASSWORD = LoadedConfig.database.password
    DB_HOST = LoadedConfig.database.hostname
    DB_PORT = LoadedConfig.database.port
    METRICS_PORT = LoadedConfig.metricsPort
    INSIGHTS_KAFKA_ADDRESS = LoadedConfig.kafka.brokers[0].hostname + ":" + str(LoadedConfig.kafka.brokers[0].port)
    INVENTORY_EVENTS_TOPIC = KafkaTopics["platform.inventory.events"].name
    ENGINE_RESULT_TOPIC = KafkaTopics["platform.engine.results"].name
    for endpoint in LoadedConfig.endpoints:
        if endpoint.app == "rbac":
            RBAC_SVC_URL = f"http://{endpoint.hostname}:{endpoint.port}"
            break

    CW_ENABLED = True if LoadedConfig.logging.cloudwatch else False  # CloudWatch/Kibana Logging
    if CW_ENABLED is True:
        # Available only in k8s namespace, through an app-interface automation
        AWS_ACCESS_KEY_ID = LoadedConfig.logging.cloudwatch.accessKeyId
        AWS_SECRET_ACCESS_KEY = LoadedConfig.logging.cloudwatch.secretAccessKey
        AWS_REGION_NAME = LoadedConfig.logging.cloudwatch.region
        AWS_LOG_GROUP = LoadedConfig.logging.cloudwatch.logGroup

else:
    DB_NAME = os.getenv("ROS_DB_NAME", "postgres")
    DB_USER = os.getenv("ROS_DB_USER", "postgres")
    DB_PASSWORD = os.getenv("ROS_DB_PASS", "postgres")
    DB_HOST = os.getenv("ROS_DB_HOST", "localhost")
    DB_PORT = os.getenv("ROS_DB_PORT", "15432")
    INSIGHTS_KAFKA_HOST = os.getenv("INSIGHTS_KAFKA_HOST", "localhost")
    INSIGHTS_KAFKA_PORT = os.getenv("INSIGHTS_KAFKA_PORT", "9092")
    INSIGHTS_KAFKA_ADDRESS = f"{INSIGHTS_KAFKA_HOST}:{INSIGHTS_KAFKA_PORT}"
    INVENTORY_EVENTS_TOPIC = os.getenv("INVENTORY_EVENTS_TOPIC", "platform.inventory.events")
    ENGINE_RESULT_TOPIC = os.getenv("ENGINE_RESULT_TOPIC", "platform.engine.results")
    METRICS_PORT = os.getenv("METRICS_PORT", 5005)
    RBAC_HOST = os.getenv("RBAC_HOST", "localhost")
    RBAC_PORT = os.getenv("RBAC_PORT", "8114")
    RBAC_SVC_URL = os.getenv("RBAC_SVC_URL", f"http://{RBAC_HOST}:{RBAC_PORT}/")

    CW_ENABLED = str_to_bool(os.getenv('CW_ENABLED', 'False'))  # CloudWatch/Kibana Logging
    if CW_ENABLED is True:
        AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", None)
        AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", None)
        AWS_REGION_NAME = os.getenv("AWS_REGION_NAME", None)
        AWS_LOG_GROUP = os.getenv("AWS_LOG_GROUP", None)

DB_URI = f"postgresql://{DB_USER}:{DB_PASSWORD}"\
                f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
GROUP_ID = os.getenv('GROUP_ID', 'resource-optimization')
PATH_PREFIX = os.getenv("PATH_PREFIX", "/api/")
APP_NAME = os.getenv("APP_NAME", "ros")
INSIGHTS_EXTRACT_LOGLEVEL = os.getenv("INSIGHTS_EXTRACT_LOGLEVEL", "ERROR")
ENABLE_RBAC = str_to_bool(os.getenv("ENABLE_RBAC", "False"))
# Time interval after which garbage collector is involved to check for outdated data.
GARBAGE_COLLECTION_INTERVAL = os.getenv("GARBAGE_COLLECTION_INTERVAL", 86400)
# Number of days after which data is considered to be outdated.
DAYS_UNTIL_STALE = os.getenv("DAYS_UNTIL_STALE", 45)
INSTANCE_PRICE_UNIT = 'USD/hour'
CW_LOGGING_FORMAT = '%(asctime)s - %(levelname)s  - %(funcName)s - %(message)s'
