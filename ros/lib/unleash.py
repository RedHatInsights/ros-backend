from UnleashClient import UnleashClient
from .config import UNLEASH_URL, UNLEASH_TOKEN, APP_NAME, UNLEASH_CACHE_DIR, get_logger
import logging

logger = get_logger(__name__)

logging.getLogger('UnleashClient').setLevel(logging.WARNING)
logging.getLogger('apscheduler').setLevel(logging.WARNING)

unleash_client = UnleashClient(
    url=UNLEASH_URL,
    app_name=APP_NAME,
    custom_headers={"Authorization": UNLEASH_TOKEN},
    cache_directory=UNLEASH_CACHE_DIR
)

unleash_client.initialize_client()
logger.info(f"Unleash client initialized: {unleash_client.is_initialized}")


def is_feature_flag_enabled(org_id, flag_name, service_name):
    context = {"userId": str(org_id)}
    is_enabled = unleash_client.is_enabled(flag_name, context)

    logger.debug(
        f"{service_name} - Feature flag {flag_name} is {'enabled' if is_enabled else 'disabled'} "
        f"for org_id {org_id}"
    )

    return is_enabled
