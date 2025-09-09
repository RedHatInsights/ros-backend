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


def build_endpoint_url(ep):
    """check for TLS certs path."""
    protocol = 'https' if LoadedConfig.tlsCAPath else 'http'
    port = ep.tlsPort if LoadedConfig.tlsCAPath else ep.port
    return f"{protocol}://{ep.hostname}:{port}"


LOG = logging.getLogger(__name__)
CLOWDER_ENABLED = True if os.getenv("CLOWDER_ENABLED", default="False").lower() in ["true", "t", "yes", "y"] else False
DB_SSL_MODE = "verify-full"
DB_SSL_CERTPATH = None

if CLOWDER_ENABLED:
    LOG.info("Using Clowder Operator...")
    from app_common_python import LoadedConfig, KafkaTopics, KafkaServers

    TLS_CA_PATH = getattr(LoadedConfig, "tlsCAPath", None)

    DB_NAME = LoadedConfig.database.name
    DB_USER = LoadedConfig.database.username
    DB_PASSWORD = LoadedConfig.database.password
    DB_HOST = LoadedConfig.database.hostname
    DB_PORT = LoadedConfig.database.port
    if LoadedConfig.database.rdsCa:
        DB_SSL_CERTPATH = LoadedConfig.rds_ca()
    REDIS_USERNAME = LoadedConfig.inMemoryDb.username
    REDIS_PASSWORD = LoadedConfig.inMemoryDb.password
    REDIS_HOST = LoadedConfig.inMemoryDb.hostname
    REDIS_PORT = LoadedConfig.inMemoryDb.port
    METRICS_PORT = LoadedConfig.metricsPort
    KAFKA_BROKER = LoadedConfig.kafka.brokers[0]
    KAFKA_CACERT_LOCATION = None
    if KAFKA_BROKER.cacert:
        KAFKA_CACERT_LOCATION = LoadedConfig.kafka_ca()
    KAFKA_BOOTSTRAP_SERVERS = KafkaServers
    INVENTORY_EVENTS_TOPIC = KafkaTopics["platform.inventory.events"].name
    ENGINE_RESULT_TOPIC = KafkaTopics["platform.engine.results"].name
    NOTIFICATIONS_TOPIC = KafkaTopics["platform.notifications.ingress"].name
    ROS_EVENTS_TOPIC = KafkaTopics["ros.events"].name
    for endpoint in LoadedConfig.endpoints:
        if endpoint.app == "rbac":
            RBAC_SVC_URL = f"{build_endpoint_url(endpoint)}"
            break
        # Todo: Load Kessel app from clowdapp
    KESSEL_SVC_URL = os.getenv("KESSEL_URL", default="kessel-inventory-api:9000")
    # Kessel OAuth 2.0 Authentication
    KESSEL_OAUTH_CLIENT_ID = os.getenv("KESSEL_OAUTH_CLIENT_ID", "")
    KESSEL_OAUTH_CLIENT_SECRET = os.getenv("KESSEL_OAUTH_CLIENT_SECRET", "")
    KESSEL_OAUTH_OIDC_ISSUER = os.getenv("KESSEL_OAUTH_OIDC_ISSUER", "")
    KESSEL_USE_TLS = str_to_bool(os.getenv("KESSEL_USE_TLS", "True"))  # True for Clowder
    CW_ENABLED = True if LoadedConfig.logging.cloudwatch else False  # CloudWatch/Kibana Logging
    if CW_ENABLED is True:
        # Available only in k8s namespace, through an app-interface automation
        AWS_ACCESS_KEY_ID = LoadedConfig.logging.cloudwatch.accessKeyId
        AWS_SECRET_ACCESS_KEY = LoadedConfig.logging.cloudwatch.secretAccessKey
        AWS_REGION_NAME = LoadedConfig.logging.cloudwatch.region
        AWS_LOG_GROUP = LoadedConfig.logging.cloudwatch.logGroup

    # Feature flags
    unleash = LoadedConfig.featureFlags
    UNLEASH_CACHE_DIR = os.getenv("UNLEASH_CACHE_DIR", "/tmp/.unleashcache")
    UNLEASH_TOKEN = unleash.clientAccessToken if unleash else None
    UNLEASH_URL = f"{unleash.hostname}:{unleash.port}/api" if unleash else None
    if unleash and unleash.port in (80, 8080):
        UNLEASH_URL = f"http://{UNLEASH_URL}"
    elif unleash:
        UNLEASH_URL = f"https://{UNLEASH_URL}"


else:
    DB_NAME = os.getenv("ROS_DB_NAME", "postgres")
    DB_USER = os.getenv("ROS_DB_USER", "postgres")
    DB_PASSWORD = os.getenv("ROS_DB_PASS", "postgres")
    DB_HOST = os.getenv("ROS_DB_HOST", "localhost")
    DB_PORT = os.getenv("ROS_DB_PORT", "15432")
    REDIS_USERNAME = os.getenv("REDIS_USERNAME", default="")
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", default="")
    REDIS_HOST = os.getenv("REDIS_HOST", default="localhost")
    REDIS_PORT = os.getenv("REDIS_PORT", default=6379)
    INSIGHTS_KAFKA_HOST = os.getenv("INSIGHTS_KAFKA_HOST", "localhost")
    INSIGHTS_KAFKA_PORT = os.getenv("INSIGHTS_KAFKA_PORT", "9092")
    KAFKA_BOOTSTRAP_SERVERS = [f"{INSIGHTS_KAFKA_HOST}:{INSIGHTS_KAFKA_PORT}"]
    INVENTORY_EVENTS_TOPIC = os.getenv("INVENTORY_EVENTS_TOPIC", "platform.inventory.events")
    ENGINE_RESULT_TOPIC = os.getenv("ENGINE_RESULT_TOPIC", "platform.engine.results")
    METRICS_PORT = os.getenv("METRICS_PORT", 5005)
    KAFKA_BROKER = None
    KAFKA_CACERT_LOCATION = None
    RBAC_HOST = os.getenv("RBAC_HOST", "localhost")
    RBAC_PORT = os.getenv("RBAC_PORT", "8114")
    RBAC_SVC_URL = os.getenv("RBAC_SVC_URL", f"http://{RBAC_HOST}:{RBAC_PORT}/")
    KESSEL_HOST = os.getenv("KESSEL_HOST", "localhost")
    KESSEL_PORT = os.getenv("KESSEL_PORT", "9081")
    KESSEL_SVC_URL = os.getenv("KESSEL_SVC_URL", f"{KESSEL_HOST}:{KESSEL_PORT}")
    # Kessel OAuth 2.0 Authentication
    KESSEL_OAUTH_CLIENT_ID = os.getenv("KESSEL_OAUTH_CLIENT_ID", "")
    KESSEL_OAUTH_CLIENT_SECRET = os.getenv("KESSEL_OAUTH_CLIENT_SECRET", "")
    KESSEL_OAUTH_OIDC_ISSUER = os.getenv("KESSEL_OAUTH_OIDC_ISSUER", "")
    KESSEL_USE_TLS = str_to_bool(os.getenv("KESSEL_USE_TLS", "False"))  # False for local dev
    NOTIFICATIONS_TOPIC = os.getenv("NOTIFICATIONS_TOPIC", "platform.notifications.ingress")
    ROS_EVENTS_TOPIC = os.getenv("ROS_EVENTS_TOPIC", "ros.events")
    TLS_CA_PATH = os.getenv("TLS_CA_PATH", None)
    CW_ENABLED = str_to_bool(os.getenv('CW_ENABLED', 'False'))  # CloudWatch/Kibana Logging
    if CW_ENABLED is True:
        AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", None)
        AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", None)
        AWS_REGION_NAME = os.getenv("AWS_REGION_NAME", None)
        AWS_LOG_GROUP = os.getenv("AWS_LOG_GROUP", None)

DB_URI = f"postgresql://{DB_USER}:{DB_PASSWORD}"\
         f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
if DB_SSL_CERTPATH:
    DB_URI += f"?sslmode={DB_SSL_MODE}&sslrootcert={DB_SSL_CERTPATH}"

DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", '5'))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", '10'))
REDIS_AUTH = f"{REDIS_USERNAME or ''}:{REDIS_PASSWORD}@" if REDIS_PASSWORD else ""
REDIS_SCHEME = "rediss://" if REDIS_PASSWORD else "redis://"
REDIS_URL = f"{REDIS_SCHEME}{REDIS_AUTH}{REDIS_HOST}:{REDIS_PORT}"
GROUP_ID = os.getenv('GROUP_ID', 'resource-optimization')
GROUP_ID_SUGGESTIONS_ENGINE = os.getenv('GROUP_ID_SUGGESTIONS_ENGINE', 'suggestions-engine-group')
# The default value for PATH_PREFIX is same as under clowdapp file
PATH_PREFIX = os.getenv("PATH_PREFIX", "/api")
APP_NAME = os.getenv("APP_NAME", "ros")
INSIGHTS_EXTRACT_LOGLEVEL = os.getenv("INSIGHTS_EXTRACT_LOGLEVEL", "ERROR")
ENABLE_RBAC = str_to_bool(os.getenv("ENABLE_RBAC", "False"))
ENABLE_KESSEL = str_to_bool(os.getenv("ENABLE_KESSEL", "False"))
# Time interval after which garbage collector is involved to check for outdated data.
GARBAGE_COLLECTION_INTERVAL = int(
    os.getenv("GARBAGE_COLLECTION_INTERVAL", '86400')
)
# Number of days after which data is considered to be outdated.
DAYS_UNTIL_STALE = int(os.getenv("DAYS_UNTIL_STALE", '45'))
CW_LOGGING_FORMAT = '%(asctime)s - %(levelname)s  - %(funcName)s - %(message)s'
ROS_PROCESSOR_PORT = int(os.getenv("ROS_PROCESSOR_PORT", "8000"))
ROS_SUGGESTIONS_ENGINE_PORT = int(os.getenv("ROS_SUGGESTIONS_ENGINE_PORT", "8003"))
ROS_API_PORT = int(os.getenv("ROS_API_PORT", "8000"))
# Timeout in seconds to set against keys of deleted systems in a cache
CACHE_TIMEOUT_FOR_DELETED_SYSTEM = int(
    os.getenv("CACHE_TIMEOUT_FOR_DELETED_SYSTEM", "86400"))
CACHE_KEYWORD_FOR_DELETED_SYSTEM = '_del_'
POLL_TIMEOUT_SECS = 1.0


def kafka_auth_config(connection_object=None):
    if connection_object is None:
        connection_object = {}
    connection_object['bootstrap.servers'] = ",".join(KAFKA_BOOTSTRAP_SERVERS)

    if KAFKA_BROKER:
        if KAFKA_CACERT_LOCATION:
            connection_object["ssl.ca.location"] = KAFKA_CACERT_LOCATION
        if KAFKA_BROKER.sasl and KAFKA_BROKER.sasl.username:
            connection_object.update({
                "security.protocol": KAFKA_BROKER.sasl.securityProtocol,
                "sasl.mechanisms": KAFKA_BROKER.sasl.saslMechanism,
                "sasl.username": KAFKA_BROKER.sasl.username,
                "sasl.password": KAFKA_BROKER.sasl.password,
            })
    return connection_object
