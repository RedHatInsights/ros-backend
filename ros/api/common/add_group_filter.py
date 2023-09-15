from ros.lib.models import System
from flask import request
from ros.lib.feature_flags import FLAG_INVENTORY_GROUPS, get_flag_value
from ros.lib.config import get_logger

logger = get_logger(__name__)


def group_filtered_query(query):
    if get_flag_value(FLAG_INVENTORY_GROUPS):
        if len(get_host_groups()) >= 1:
            query = query.filter(System.groups[0]['id'].astext.in_(get_host_groups()) | (System.groups == '[]'))
    return query


def get_host_groups():
    host_groups = []
    try:
        host_groups = [gid for gid in request.host_groups if gid is not None]
    except AttributeError as e:
        logger.debug(f"Can't parse the host groups, inventory groups feature is not available?: {e}")
    return host_groups
