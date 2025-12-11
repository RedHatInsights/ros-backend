from ros.extensions import cache
from ros.lib.config import (
    CACHE_KEYWORD_FOR_DELETED_SYSTEM,
    CACHE_TIMEOUT_FOR_DELETED_SYSTEM,
    get_logger
)

logging = get_logger(__name__)


def set_deleted_system_cache(org_id, host_id, event_timestamp=None):
    cache_key = f"{org_id}{CACHE_KEYWORD_FOR_DELETED_SYSTEM}{host_id}"

    try:
        cache.set(cache_key, event_timestamp, timeout=CACHE_TIMEOUT_FOR_DELETED_SYSTEM)
        logging.debug(f"Set deletion cache for system {host_id} (org: {org_id}, timestamp: {event_timestamp})")
    except Exception as e:
        logging.error(f"Failed to set deletion cache for system {host_id}: {e}")


def is_system_deleted(org_id, host_id, event_timestamp=None):
    cache_key = f"{org_id}{CACHE_KEYWORD_FOR_DELETED_SYSTEM}{host_id}"

    try:
        cached_timestamp = cache.get(cache_key)
        if not cached_timestamp:
            return False

        if not event_timestamp:
            logging.debug(f"System {host_id} was deleted (no event timestamp to compare)")
            return True

        if event_timestamp <= cached_timestamp:
            return True
        else:
            logging.debug(
                f"Accepting event for system {host_id} - "
                f"event ({event_timestamp}) > deletion ({cached_timestamp}). Clearing cache."
            )
            clear_deleted_system_cache(org_id, host_id)
            return False

    except Exception as e:
        logging.error(f"Error checking deletion cache for system {host_id}: {e}")
        return False


def clear_deleted_system_cache(org_id, host_id):
    cache_key = f"{org_id}{CACHE_KEYWORD_FOR_DELETED_SYSTEM}{host_id}"

    try:
        cache.delete(cache_key)
        logging.debug(f"Cleared deletion cache for system {host_id} (org: {org_id})")
    except Exception as e:
        logging.error(f"Failed to clear deletion cache for system {host_id}: {e}")
