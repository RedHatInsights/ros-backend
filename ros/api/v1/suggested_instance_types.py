import logging
from flask import request
from sqlalchemy import func
from flask_restful import Resource, fields, marshal_with, abort
from ros.api.common.add_group_filter import group_filtered_query
from ros.lib.utils import (
    system_ids_by_org_id,
    org_id_from_identity_header, sort_io_dict,
)

from ros.lib.models import (
    db,
    PerformanceProfile,
    System
)

from ros.api.common.pagination import (
    limit_value,
    offset_value,
    build_paginated_system_list_response
)
from ros.api.common.instance_types_helper import instance_types_desc_dict
from ros.api.common.utils import sorting_order
from ros.lib.config import get_logger

LOG = get_logger(__name__)

LOG = logging.getLogger(__name__)


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
            record = {'instance_type': row.top_candidate, 'cloud_provider': 'AWS', 'system_count': row.system_count}
            try:
                record['description'] = instance_types_desc_dict()[row.top_candidate]
            except KeyError:
                LOG.info(f"Unable to get the description for {row.top_candidate}! "
                         f"Looks like lib/aws_instance_types.py is stale!")
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


class SuggestedInstanceDetails(Resource):
    performance_utilization_fields = {
        'cpu': fields.Integer,
        'memory': fields.Integer,
        'max_io': fields.Float,
        'io_all': fields.Raw
    }

    data = {
        'fqdn': fields.String,
        'display_name': fields.String,
        'instance_type': fields.String,
        'os': fields.String,
        'performance_utilization': fields.Nested(performance_utilization_fields),
        'state': fields.String,
        'last_reported': fields.DateTime(dt_format='iso8601')
    }

    instance_type_detail = {
        'instance_type': fields.String,
        'cloud_provider': fields.String,
        'description': fields.String
    }

    meta_fields = {
        'count': fields.Integer,
        'limit': fields.Integer,
        'offset': fields.Integer,
        'suggested_instance_type_detail': fields.Nested(instance_type_detail)
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
    def get(self, instance_type):
        limit = limit_value()
        offset = offset_value()
        org_id = org_id_from_identity_header(request)
        system_query = group_filtered_query(system_ids_by_org_id(org_id))
        query = db.session.query(
            System.fqdn,
            System.display_name,
            func.concat(System.operating_system["name"].astext, ' ', System.operating_system['major'], '.',
                        System.operating_system['minor']).label("os"),
            PerformanceProfile.top_candidate.label('instance_type'),
            PerformanceProfile.performance_utilization,
            PerformanceProfile.state,
            PerformanceProfile.report_date.label('last_reported')).select_from(System).join(PerformanceProfile).filter(
            System.id == PerformanceProfile.system_id,
            System.id.in_(system_query),
            PerformanceProfile.top_candidate == instance_type
        )

        query = query.filter(*self.build_instance_details_filters())
        count = query.count()
        if limit == -1:
            limit = count
        query_after_request_filters = query.limit(limit).offset(offset)
        query_results = query_after_request_filters.all()
        instance_details = []
        for result in query_results:
            try:
                record = result._asdict()
                record['performance_utilization'] = sort_io_dict(result.performance_utilization)
                instance_details.append(record)
            except Exception as err:
                LOG.error(
                    f"An error occurred while fetching the host! {repr(err)}"
                )
                count -= 1

        instance_type_details = {'instance_type': instance_type, 'cloud_provider': 'AWS',
                                 'description': instance_types_desc_dict()[instance_type]}
        paginated_system_list_response = build_paginated_system_list_response(limit, offset, instance_details, count)
        paginated_system_list_response['meta']['suggested_instance_type_detail'] = instance_type_details
        return paginated_system_list_response

    @staticmethod
    def build_instance_details_filters():
        filters = []
        if filter_display_name := request.args.get('display_name'):
            filters.append(System.display_name.ilike(f'%{filter_display_name}'))
        if filter_state := request.args.get('state'):
            filters.append(System.state.ilike(f'%{filter_state}'))
        if filter_os := request.args.get('os'):
            filters.append(func.concat(System.operating_system["name"].astext, ' ',
                                       System.operating_system['major'], '.',
                                       System.operating_system['minor']).ilike(filter_os))
        return filters
