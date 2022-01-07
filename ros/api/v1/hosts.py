from sqlalchemy import func, asc, desc
from sqlalchemy.types import Integer
from flask import request
from flask_restful import Resource, abort, fields, marshal_with

from ros.lib.models import (
    PerformanceProfile, RhAccount, System,
    db, RecommendationRating)
from ros.lib.utils import (
    is_valid_uuid, identity,
    user_data_from_identity,
    sort_io_dict, default_queries)
from ros.api.common.pagination import (
    build_paginated_system_list_response,
    limit_value,
    offset_value)
import logging


LOG = logging.getLogger(__name__)
SYSTEM_STATES_EXCEPT_EMPTY = [
    "Oversized", "Undersized", "Idling", "Under pressure", "Storage rightsizing", "Optimized", "Waiting for data"
]
SYSTEM_COLUMNS = [
            'inventory_id', 'display_name',
            'instance_type', 'cloud_provider',
            'rule_hit_details', 'state', 'number_of_recommendations', 'fqdn'
]


class IsROSConfiguredApi(Resource):
    def get(self):
        account_number = identity(request)['identity']['account_number']
        system_query = default_queries(account_number)
        query = (
            db.session.query(System.id)
            .filter(PerformanceProfile.system_id.in_(system_query.subquery()))
            .distinct()
        )
        system_count = query.count()
        systems_with_suggestions = query.filter(System.number_of_recommendations > 0).count()
        systems_waiting_for_data = query.filter(System.state == 'Waiting for data').count()

        if system_count <= 0:
            status, code = False, 'NO_SYSTEMS'
        else:
            status, code = True, 'SYSTEMSEXIST'
        return {
            'success': status,
            'code': code,
            'count': system_count,
            'systems_stats': {
                'waiting_for_data': systems_waiting_for_data,
                'with_suggestions': systems_with_suggestions
            }
        }


class HostsApi(Resource):
    performance_utilization_fields = {
        'cpu': fields.Integer,
        'memory': fields.Integer,
        'max_io': fields.Integer,
        'io_all': fields.Raw
    }
    hosts_fields = {
        'fqdn': fields.String,
        'display_name': fields.String,
        'inventory_id': fields.String,
        'account': fields.String,
        'number_of_suggestions': fields.Integer(attribute='number_of_recommendations'),
        'state': fields.String,
        'performance_utilization': fields.Nested(performance_utilization_fields),
        'cloud_provider': fields.String,
        'instance_type': fields.String,
        'idling_time': fields.String,
        'io_wait': fields.String,
    }
    meta_fields = {
        'count': fields.Integer,
        'limit': fields.Integer,
        'offset': fields.Integer,
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
        limit = limit_value()
        offset = offset_value()
        order_by = (
            request.args.get('order_by') or 'display_name'
        ).strip().lower()
        order_how = (request.args.get('order_how') or 'asc').strip().lower()

        account_number = identity(request)['identity']['account_number']
        # Note that When using LIMIT, it is important to use an ORDER BY clause
        # that constrains the result rows into a unique order.
        # Otherwise you will get an unpredictable subset of the query's rows.
        # Refer - https://www.postgresql.org/docs/13/queries-limit.html

        system_query = default_queries(account_number).filter(*self.build_system_filters())

        last_reported = (
            db.session.query(PerformanceProfile.system_id, func.max(PerformanceProfile.report_date).label('max_date')
                             )
            .filter(PerformanceProfile.system_id.in_(system_query.subquery()))
            .group_by(PerformanceProfile.system_id)
            .subquery()
        )

        sort_expression = self.build_sort_expression(order_how, order_by)

        query = (
            db.session.query(PerformanceProfile, System, RhAccount)
            .join(last_reported, (last_reported.c.max_date == PerformanceProfile.report_date) &
                  (PerformanceProfile.system_id == last_reported.c.system_id))
            .join(System, System.id == last_reported.c.system_id)
            .join(RhAccount, RhAccount.id == System.account_id)
            .order_by(*sort_expression)
        )
        count = query.count()
        query = query.limit(limit).offset(offset)
        query_results = query.all()
        hosts = []
        for row in query_results:
            try:
                system_dict = row.System.__dict__
                host = {skey: system_dict[skey] for skey in SYSTEM_COLUMNS}
                host['account'] = row.RhAccount.account
                host['performance_utilization'] = sort_io_dict(
                    row.PerformanceProfile.performance_utilization
                )
                host['idling_time'] = row.PerformanceProfile.idling_time
                host['io_wait'] = row.PerformanceProfile.io_wait
                hosts.append(host)
            except Exception as err:
                LOG.error(
                    'An error occured while fetching the host. %s',
                    repr(err)
                )
                count -= 1

        return build_paginated_system_list_response(
            limit, offset, hosts, count
        )

    @staticmethod
    def build_system_filters():
        """Build system filters."""
        filters = []
        if filter_display_name := request.args.get('display_name'):
            filters.append(System.display_name.ilike(f'%{filter_display_name}%'))
        if states := request.args.getlist('state'):
            modified_states = []
            for state in states:
                state = state.capitalize()
                modified_states.append(state)
                if state not in SYSTEM_STATES_EXCEPT_EMPTY:
                    abort(400, message='values are not matching')
            filters.append(System.state.in_(modified_states))
        else:
            filters.append(System.state.in_(SYSTEM_STATES_EXCEPT_EMPTY))
        return filters

    @staticmethod
    def sorting_order(order_how):
        """Sorting order method."""
        method_name = None
        if order_how == 'asc':
            method_name = asc
        elif order_how == 'desc':
            method_name = desc
        else:
            abort(
                403,
                message="Incorrect sorting order. Possible values - ASC/DESC"
            )
        return method_name

    def build_sort_expression(self, order_how, order_method):
        """Build sort expression."""
        sort_order = self.sorting_order(order_how)

        if order_method == 'display_name':
            return (sort_order(System.display_name),
                    asc(PerformanceProfile.system_id),)

        score_methods = ['cpu', 'memory', 'max_io']
        if order_method in score_methods:
            return (
                sort_order(PerformanceProfile.performance_utilization[
                    order_method].astext.cast(Integer)),
                asc(PerformanceProfile.system_id),)

        if order_method == 'number_of_suggestions':
            return (sort_order(System.number_of_recommendations),
                    asc(PerformanceProfile.system_id),)

        if order_method == 'state':
            return (sort_order(System.state),
                    asc(PerformanceProfile.system_id),)

        abort(403, message="Unexpected sort method {}".format(order_method))
        return None


class HostDetailsApi(Resource):
    performance_utilization_fields = {
        'cpu': fields.Integer,
        'memory': fields.Integer,
        'max_io': fields.Integer,
        'io_all': fields.Raw
    }
    profile_fields = {
        'fqdn': fields.String,
        'inventory_id': fields.String,
        'display_name': fields.String,
        'performance_utilization': fields.Nested(performance_utilization_fields),
        'rating': fields.Integer,
        'number_of_suggestions': fields.Integer(attribute='number_of_recommendations'),
        'state': fields.String,
        'report_date': fields.String,
        'instance_type': fields.String,
        'cloud_provider': fields.String,
        'idling_time': fields.String,
        'io_wait': fields.String
    }

    @marshal_with(profile_fields)
    def get(self, host_id):
        if not is_valid_uuid(host_id):
            abort(404, message='Invalid host_id, Id should be in form of UUID4')

        ident = identity(request)['identity']
        user = user_data_from_identity(ident)
        username = user['username'] if 'username' in user else None
        account_number = identity(request)['identity']['account_number']

        system_query = default_queries(account_number).filter(System.inventory_id == host_id).subquery()

        profile = PerformanceProfile.query.filter(
            PerformanceProfile.system_id.in_(system_query)
        ).order_by(PerformanceProfile.report_date.desc()).first()

        rating_record = RecommendationRating.query.filter(
            RecommendationRating.system_id.in_(system_query),
            RecommendationRating.rated_by == username
        ).first()

        system = db.session.query(System).filter(System.inventory_id == host_id).first()

        record = None
        if profile:
            record = {key: system.__dict__[key] for key in SYSTEM_COLUMNS}
            record['performance_utilization'] = sort_io_dict(profile.performance_utilization)
            record['rating'] = rating_record.rating if rating_record else None
            record['report_date'] = profile.report_date
            record['idling_time'] = profile.idling_time
            record['io_wait'] = profile.io_wait
        else:
            abort(404, message="System {} doesn't exist"
                  .format(host_id))

        return record


class HostHistoryApi(Resource):
    performance_utilization_fields = {
        'cpu': fields.Integer,
        'memory': fields.Integer,
        'io_all': fields.Raw,
        'max_io': fields.Integer,
        'report_date': fields.String
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
    history_fields = {
        'meta': fields.Nested(meta_fields),
        'links': fields.Nested(links_fields),
        'inventory_id': fields.String,
        'data': fields.List(fields.Nested(performance_utilization_fields))
    }

    @marshal_with(history_fields)
    def get(self, host_id):
        limit = limit_value()
        offset = offset_value()
        if not is_valid_uuid(host_id):
            abort(404, message='Invalid host_id, Id should be in form of UUID4')

        account_number = identity(request)['identity']['account_number']

        system_query = default_queries(account_number).filter(System.inventory_id == host_id).subquery()

        query = PerformanceProfile.query.filter(
            PerformanceProfile.system_id.in_(system_query)
        ).order_by(PerformanceProfile.report_date.desc())

        count = query.count()
        query = query.limit(limit).offset(offset)
        query_results = query.all()

        if not query_results:
            abort(404, message="System {} doesn't exist"
                  .format(host_id))

        performance_history = []
        for profile in query_results:
            performance_record = sort_io_dict(profile.performance_utilization)
            performance_record['report_date'] = profile.report_date
            performance_history.append(performance_record)

        paginated_response = build_paginated_system_list_response(
            limit, offset, performance_history, count
        )
        paginated_response['inventory_id'] = host_id
        return paginated_response
