from flask import request
from flask_restful import Resource, abort, fields, marshal_with

from ros.lib.models import PerformanceProfile, RhAccount, System, db
from ros.lib.utils import is_valid_uuid, identity
from ros.api.common.pagination import build_paginated_system_list_response

from sqlalchemy import func

DEFAULT_HOSTS_PER_REP = 10
DEFAULT_OFFSET = 0


class HostsApi(Resource):

    display_performance_score_fields = {
        'cpu_score': fields.Integer,
        'memory_score': fields.Integer,
        'io_score': fields.Integer
    }
    hosts_fields = {
        'fqdn': fields.String,
        'display_name': fields.String,
        'inventory_id': fields.String,
        'account': fields.String,
        'recommendation_count': fields.Integer,
        'state': fields.String,
        'display_performance_score': fields.Nested(display_performance_score_fields),
        'cloud_provider': fields.String,
        'instance_type': fields.String
        # TODO - idling_time, io_wait
        # 'idling_time': fields.String,
        # 'io_wait': fields.String
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

        ident = identity(request)['identity']
        # Note that When using LIMIT, it is important to use an ORDER BY clause
        # that constrains the result rows into a unique order.
        # Otherwise you will get an unpredictable subset of the query's rows.
        # Refer - https://www.postgresql.org/docs/13/queries-limit.html

        account_query = db.session.query(RhAccount.id).filter(RhAccount.account == ident['account_number']).subquery()
        system_query = db.session.query(System.id)\
            .filter(System.account_id.in_(account_query)).subquery()

        last_reported = (
            db.session.query(PerformanceProfile.system_id, func.max(PerformanceProfile.report_date).label('max_date')
                             )
            .filter(PerformanceProfile.system_id.in_(system_query))
            .group_by(PerformanceProfile.system_id)
            .subquery()
        )

        query = (
            db.session.query(PerformanceProfile, System, RhAccount)
            .join(last_reported, (last_reported.c.max_date == PerformanceProfile.report_date) &
                  (PerformanceProfile.system_id == last_reported.c.system_id))
            .join(System, System.id == last_reported.c.system_id)
            .join(RhAccount, RhAccount.id == System.account_id)
            .order_by(PerformanceProfile.system_id.asc())
        )

        count = query.count()
        query = query.limit(limit).offset(offset)
        query_results = query.all()

        hosts = []
        system_columns = ['inventory_id', 'fqdn', 'display_name', 'instance_type', 'cloud_provider']
        for row in query_results:
            system_dict = row.System.__dict__
            host = {skey: system_dict[skey] for skey in system_columns}
            host['recommendation_count'] = 5
            host['state'] = 'Undersized'
            host['account'] = row.RhAccount.account
            host['display_performance_score'] = row.PerformanceProfile.display_performance_score
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
            abort(404, message='Invalid host_id, Id should be in form of UUID4')

        ident = identity(request)['identity']
        account_query = db.session.query(RhAccount.id).filter(RhAccount.account == ident['account_number']).subquery()
        system_query = db.session.query(System.id) \
            .filter(System.account_id.in_(account_query)).filter(System.inventory_id == host_id).subquery()

        profile = PerformanceProfile.query.filter(
            PerformanceProfile.system_id.in_(system_query)
        ).order_by(PerformanceProfile.report_date.desc()).first()

        if profile:
            record = {'inventory_id': host_id}
            record['display_performance_score'] = profile.display_performance_score
        else:
            abort(404, message="Performance Profile {} doesn't exist"
                  .format(host_id))

        return record
