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
