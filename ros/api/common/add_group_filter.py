from ros.lib.models import System
from flask_restful import request


def group_filtered_query(query):
    if hasattr(request, "host_groups"):
        host_groups = [gid for gid in request.host_groups if gid is not None]
        if len(host_groups) > 1:
            query = query.filter(System.groups[0]['id'].astext.in_(host_groups) | (System.groups == '[]'))
        else:
            query = query.filter((System.groups == '[]'))
    return query
