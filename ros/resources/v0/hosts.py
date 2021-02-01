from flask import jsonify, make_response
from flask import request
from flask_restful import Resource, abort, fields, marshal_with

from ros.models import PerformanceProfile
from ros.utils import is_valid_uuid
from ros.lib.host_inventory_interface import fetch_all_hosts_from_inventory
from ros.api.common.pagination import build_paginated_system_list_response

class HostsApi(Resource):
    # facts_fields = {
    #     'cloud_provider': fields.String,
    #     'instance_type': fields.String,
    #     'idling_time': fields.String,
    #     'io_wait': fields.String
    # }
    # performance_score_fields = {
    #     'cpu_score': fields.Integer,
    #     'memory_score': fields.Integer,
    #     'io_score': fields.Integer
    # }
    # hosts_fields = {
    #     'fqdn': fields.String,
    #     'display_name': fields.String,
    #     'id': fields.String,
    #     'account': fields.String,
    #     'recommendation_count': fields.Integer,
    #     'state': fields.String,
    #     'performance_score': fields.Nested(performance_score_fields),
    #     'facts': fields.Nested(facts_fields)
    # }
    # output_fields = {
    #     'results': fields.List(fields.Nested(hosts_fields))
    # }

    # @marshal_with(output_fields)
    def get(self):
        max_limit = 1000
        default_offset = 0

        auth_key = request.headers.get('X-RH-IDENTITY')
        if not auth_key:
            response = make_response(
                jsonify({"Error": "Authentication token not provided"}), 401)
            abort(response)

        inv_hosts = fetch_all_hosts_from_inventory(auth_key)
        inv_host_ids = [host['id'] for host in inv_hosts['results']]

        # Note that When using LIMIT, it is important to use an ORDER BY clause
        # that constrains the result rows into a unique order.
        # Otherwise you will get an unpredictable subset of the query's rows.
        # Refer - https://www.postgresql.org/docs/13/queries-limit.html
        query = PerformanceProfile.query.filter(
            PerformanceProfile.inventory_id.in_(inv_host_ids)).order_by(
                PerformanceProfile.report_date.desc()).order_by(
                    PerformanceProfile.id.asc())

        limit = int(request.args.get('limit') or max_limit)
        offset = int(request.args.get('offset') or default_offset)
        count = query.count()
        query = query.limit(limit).offset(offset)
        query_results = query.all()

        hosts = []
        for i in query_results:
            if len(list(filter(lambda host: host['id'] == str(i.inventory_id), hosts))):
                continue
            else:
                host = list(filter(lambda host: host['id'] == str(i.inventory_id), inv_hosts['results']))[0]
                host['performance_score'] = i.__dict__['performance_score']
                host['performance_score'].update(
                    {'cpu_score': 60, 'io_score': 30}
                )
                host['id'] = i.__dict__['id']
                host['recommendation_count'] = 5
                host['state'] = 'Undersized'
                hosts.append(host)

        return build_paginated_system_list_response(
            limit, offset, hosts, count)

class HostDetailsApi(Resource):
    profile_fields = {
        'host_id': fields.String(attribute='inventory_id'),
        'performance_record': fields.String,
        'performance_score': fields.String
    }

    @marshal_with(profile_fields)
    def get(self, host_id):
        if not is_valid_uuid(host_id):
            abort(404, message='Invalid host_id,'
                               ' Id should be in form of UUID4')

        profile = PerformanceProfile.query.filter_by(
                  inventory_id=host_id).first()
        if not profile:
            abort(404, message="Performance Profile {} doesn't exist"
                  .format(host_id))

        return profile
