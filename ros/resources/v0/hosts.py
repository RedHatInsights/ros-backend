from flask import jsonify, make_response
from flask import request
from flask_restful import Resource, abort, fields, marshal_with

from ros.models import PerformanceProfile
from ros.utils import is_valid_uuid
from ros.app import db
from ros.lib.host_inventory_interface import fetch_all_hosts_from_inventory
from ros.api.common.pagination import build_paginated_system_list_response

from sqlalchemy import func

DEFAULT_HOSTS_PER_REP = 10
DEFAULT_OFFSET = 0


class HostsApi(Resource):

    facts_fields = {
        'cloud_provider': fields.String,
        'instance_type': fields.String,
        'idling_time': fields.String,
        'io_wait': fields.String
    }
    display_performance_score_fields = {
        'cpu_score': fields.Integer,
        'memory_score': fields.Integer,
        'io_score': fields.Integer
    }
    hosts_fields = {
        'fqdn': fields.String,
        'display_name': fields.String,
        'id': fields.Integer,
        'account': fields.String,
        'recommendation_count': fields.Integer,
        'state': fields.String,
        'display_performance_score': fields.Nested(display_performance_score_fields),
        'facts': fields.Nested(facts_fields)
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
    output_fields = {
        'meta': fields.Nested(meta_fields),
        'links': fields.Nested(links_fields),
        'data': fields.List(fields.Nested(hosts_fields))
    }

    @marshal_with(output_fields)
    def get(self):
        limit = int(request.args.get('limit') or DEFAULT_HOSTS_PER_REP)
        offset = int(request.args.get('offset') or DEFAULT_OFFSET)

        auth_key = request.headers.get('X-RH-IDENTITY')
        if not auth_key:
            response = make_response(
                jsonify({"Error": "Authentication token not provided"}), 401)
            abort(response)

        inv_hosts = fetch_all_hosts_from_inventory(auth_key)
        inv_host_ids = [host['id'] for host in inv_hosts['results']]

        last_reported = (
            db.session.query(PerformanceProfile.inventory_id, func.max(PerformanceProfile.report_date).label('max_date')
                             )
            .filter(PerformanceProfile.inventory_id.in_(inv_host_ids))
            .group_by(PerformanceProfile.inventory_id)
            .subquery()
        )

        # Note that When using LIMIT, it is important to use an ORDER BY clause
        # that constrains the result rows into a unique order.
        # Otherwise you will get an unpredictable subset of the query's rows.
        # Refer - https://www.postgresql.org/docs/13/queries-limit.html

        query = (
            db.session.query(PerformanceProfile)
            .join(last_reported, (last_reported.c.max_date == PerformanceProfile.report_date) &
                  (PerformanceProfile.inventory_id == last_reported.c.inventory_id))
            .order_by(PerformanceProfile.id.asc())
        )

        count = query.count()
        query = query.limit(limit).offset(offset)
        query_results = query.all()

        hosts = []
        for profile in query_results:
            host = list(filter(lambda host: host['id'] == str(profile.inventory_id), inv_hosts['results']))[0]
            host['id'] = profile.__dict__['id']
            host['recommendation_count'] = 5
            host['state'] = 'Undersized'
            host['display_performance_score'] = profile.display_performance_score
            hosts.append(host)

        return build_paginated_system_list_response(
            limit, offset, hosts, count
        )


class HostDetailsApi(Resource):
    profile_fields = {
        'host_id': fields.String(attribute='inventory_id'),
        'performance_record': fields.String,
        'display_performance_score': fields.String
    }

    @marshal_with(profile_fields)
    def get(self, host_id):
        if not is_valid_uuid(host_id):
            abort(404, message='Invalid host_id,'
                               ' Id should be in form of UUID4')

        profile = PerformanceProfile.query.filter_by(
                  inventory_id=host_id).first()
        if profile:
            record = {}
            record['display_performance_score'] = profile.display_performance_score
        else:
            abort(404, message="Performance Profile {} doesn't exist"
                  .format(host_id))

        return profile
