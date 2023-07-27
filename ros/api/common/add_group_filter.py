from ros.lib.models import System
from flask_restful import request


def group_filtered_query(query):
    if hasattr(request, "host_groups"):
        if len(request.host_groups) > 1 or (len(request.host_groups) == 0 and request.host_groups[0] is not None):
            query = query.filter(System.groups[0]['id'].astext.in_(request.host_groups) | (System.groups == '[]'))
        else:
            query = query.filter((System.groups == '[]'))
    return query
