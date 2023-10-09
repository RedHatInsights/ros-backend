from flask import request
from sqlalchemy import func
from flask_restful import Resource, fields, marshal_with, abort
from ros.api.common.add_group_filter import group_filtered_query
from ros.lib.utils import (
    system_ids_by_org_id,
    org_id_from_identity_header,
)

from ros.lib.models import (
    db,
    PerformanceProfile,
)

from ros.api.common.pagination import (
    limit_value,
    offset_value,
    build_paginated_system_list_response
)
from ros.api.common.instance_types_helper import instance_types_desc_dict
from ros.api.common.utils import sorting_order


def non_null_suggested_instance_types():
    org_id = org_id_from_identity_header(request)
    systems_query = group_filtered_query(system_ids_by_org_id(org_id))
    return db.session.query(PerformanceProfile.top_candidate,
                            func.count(PerformanceProfile.system_id).label('system_count')).filter(
        PerformanceProfile.top_candidate.is_not(None)).filter(
        PerformanceProfile.system_id.in_(systems_query)).group_by(PerformanceProfile.top_candidate)


class SuggestedInstanceTypes(Resource):
    data = {
        'instance_type': fields.String,
        'cloud_provider': fields.String,
        'system_count': fields.Integer,
        'description': fields.String,
    }
    meta_fields = {
        'count': fields.Integer,
        'limit': fields.Integer,
        'offset': fields.Integer
    }
    links_fields = {
        'first': fields.String,
        'last': fields.String,
        'next': fields.String,
        'previous': fields.String
    }
    output = {
        'meta': fields.Nested(meta_fields),
        'links': fields.Nested(links_fields),
        'data': fields.List(fields.Nested(data))
    }

    @marshal_with(output)
    def get(self):
        limit = limit_value()
        offset = offset_value()
        order_by = (
            request.args.get('order_by') or 'system_count'
        ).strip().lower()
        order_how = (request.args.get('order_how') or 'desc').strip().lower()
        sort_expression = self.build_sort_expression(order_how, order_by)
        query = non_null_suggested_instance_types().filter(*self.build_instance_filters()).order_by(*sort_expression)
        count = query.count()
        query = query.limit(limit).offset(offset)
        query_result = query.all()
        suggested_instance_types = []
        for row in query_result:
            # FIXME: As of now we only support AWS cloud, so statically adding it to the dict. Fix this code block
            #  upon supporting multiple clouds.
            record = {'instance_type': row.top_candidate, 'cloud_provider': 'AWS', 'system_count': row.system_count,
                      'description': instance_types_desc_dict()[row.top_candidate]}
            suggested_instance_types.append(record)
        return build_paginated_system_list_response(limit, offset, suggested_instance_types, count)

    @staticmethod
    def build_instance_filters():
        filters = []
        if filter_instance_type := request.args.get('instance_type'):
            filters.append(PerformanceProfile.top_candidate.ilike(f'%{filter_instance_type}'))
        # TODO: once ROS has multi cloud support, add cloud provider filter
        return filters

    def build_sort_expression(self, order_how, order_method):
        """Build sort expression."""
        sort_order = sorting_order(order_how)

        if order_method == 'instance_type':
            return (sort_order(PerformanceProfile.top_candidate),)

        if order_method == 'system_count':
            return (sort_order(func.count(PerformanceProfile.system_id)),)

        abort(403, message="Unexpected sort method {}".format(order_method))
        return None
