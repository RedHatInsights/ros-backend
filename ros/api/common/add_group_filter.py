from sqlalchemy import or_

from ros.lib.models import System
from flask import request
from ros.lib.config import get_logger

logger = get_logger(__name__)


def group_filtered_query(query):
    if able_to_access_all_systems():
        return query

    total_groups_from_request = get_host_groups()
    len_of_total_groups = len(total_groups_from_request)
    no_none_groups = [grp for grp in total_groups_from_request if grp is not None]
    len_of_no_none_groups = len(no_none_groups)
    is_none_present = (len_of_total_groups - len_of_no_none_groups) > 0
    filters = []
    if len_of_total_groups:
        if len_of_no_none_groups:
            filters.append(System.groups[0]['id'].astext.in_(no_none_groups))
        if is_none_present:
            filters.append(System.groups == '[]')
        if len(filters) > 0:
            query = query.filter(or_(*filters))
    return query


def get_host_groups():
    host_groups = []
    try:
        host_groups = [gid for gid in request.host_groups]
    except AttributeError as e:
        logger.debug(f"Can't parse the host_groups, setting host_groups attr to default empty array([])!: {e}")
    return host_groups


def able_to_access_all_systems():
    access_all_systems = False
    try:
        access_all_systems = request.able_to_access_all_systems
    except AttributeError as e:
        logger.debug("Can't parse the able_to_access_all_systems,"
                     f"setting able_to_access_all_systems attr to default False value!: {e}")
    return access_all_systems
