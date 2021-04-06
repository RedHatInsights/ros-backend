from sqlalchemy import func, asc, desc
from sqlalchemy.types import Integer
from flask import request
from flask_restful import Resource, abort, fields, marshal_with

from ros.lib.models import (
    PerformanceProfile, RhAccount, System,
    db, RecommendationRating)
from ros.lib.utils import is_valid_uuid, identity, user_data_from_identity
from ros.api.common.pagination import build_paginated_system_list_response


DEFAULT_HOSTS_PER_REP = 10
DEFAULT_OFFSET = 0


class HostsApi(Resource):
    display_performance_score_fields = {
        'cpu_score': fields.Integer,
        'memory_score': fields.Integer,
        'io_score': fields.Integer
    }
    link_key_fields = {
        'kcs': fields.List,
        'jira': fields.List
    }
    details_fields = {
        'rhel': fields.String,
        'type': fields.String,
        'error_key': fields.String
        # Are instance_type and cloud_provider needed here too?
        # We have them below already.
    }
    rule_hit_details_fields = {
        'key': fields.String,
        'tags': fields.List,
        'type': fields.String,
        'links': fields.Nested(link_key_fields),
        'details': fields.Nested(details_fields),
        'rule_id': fields.String,
        'component': fields.String,
        'system_id': fields.String
    }
    hosts_fields = {
        'fqdn': fields.String,
        'display_name': fields.String,
        'inventory_id': fields.String,
        'account': fields.String,
        'number_of_recommendations': fields.Integer,
        'state': fields.String,
        'display_performance_score': fields.Nested(display_performance_score_fields),
        'cloud_provider': fields.String,
        'instance_type': fields.String,
        'idling_time': fields.String,
        'io_wait': fields.String,
        'rule_hit_details': fields.List(fields.Nested(rule_hit_details_fields))
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
        order_by = (
            request.args.get('order_by') or 'display_name'
        ).strip().lower()
        order_how = (request.args.get('order_how') or 'asc').strip().lower()
        filter_display_name = request.args.get('display_name')

        ident = identity(request)['identity']
        # Note that When using LIMIT, it is important to use an ORDER BY clause
        # that constrains the result rows into a unique order.
        # Otherwise you will get an unpredictable subset of the query's rows.
        # Refer - https://www.postgresql.org/docs/13/queries-limit.html

        account_query = db.session.query(RhAccount.id).filter(RhAccount.account == ident['account_number']).subquery()
        if filter_display_name:
            system_query = db.session.query(System.id)\
                .filter(System.display_name.ilike(f'%{filter_display_name}%'))\
                .filter(System.account_id.in_(account_query))
        else:
            system_query = db.session.query(System.id)\
                .filter(System.account_id.in_(account_query))

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
        system_columns = [
            'inventory_id', 'fqdn', 'display_name',
            'instance_type', 'cloud_provider', 'rule_hit_details']
        for row in query_results:
            system_dict = row.System.__dict__
            host = {skey: system_dict[skey] for skey in system_columns}
            if host['rule_hit_details']:
                # FIXME after Ticket-86 is resolved
                host['number_of_recommendations'] = len(host['rule_hit_details'])
                host['state'] = host['rule_hit_details'][0].get('key')
            else:
                continue
            host['account'] = row.RhAccount.account
            host['display_performance_score'] = row.PerformanceProfile.display_performance_score
            host['idling_time'] = row.PerformanceProfile.idling_time
            host['io_wait'] = row.PerformanceProfile.io_wait
            hosts.append(host)

        return build_paginated_system_list_response(
            limit, offset, hosts, count
        )

    @staticmethod
    def sorting_order(order_how):
        """Sorting order method."""
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

        score_methods = ['cpu_score', 'memory_score', 'io_score']
        if order_method in score_methods:
            return (
                sort_order(PerformanceProfile.performance_score[
                    order_method].astext.cast(Integer)),
                asc(PerformanceProfile.system_id),)
        # FIXME: no ordering as of now for columns:
        # state, number_of_recommendations
        abort(403, message="Unexpected sort method {}".format(order_method))
        return None


class HostDetailsApi(Resource):
    display_performance_score_fields = {
        'cpu_score': fields.Integer,
        'memory_score': fields.Integer,
        'io_score': fields.Integer
    }
    link_key_fields = {
        'kcs': fields.List,
        'jira': fields.List
    }
    details_fields = {
        'rhel': fields.String,
        'type': fields.String,
        'error_key': fields.String
        # Are instance_type and cloud_provider needed here too?
        # We have them below already.
    }
    rule_hit_details_fields = {
        'key': fields.String,
        'tags': fields.List,
        'type': fields.String,
        'links': fields.Nested(link_key_fields),
        'details': fields.Nested(details_fields),
        'rule_id': fields.String,
        'component': fields.String,
        'system_id': fields.String
    }
    profile_fields = {
        'inventory_id': fields.String,
        'display_performance_score': fields.Nested(display_performance_score_fields),
        'rating': fields.Integer,
        'number_of_recommendations': fields.Integer,
        'state': fields.String,
        'report_date': fields.String,
        'instance_type': fields.String,
        'cloud_provider': fields.String,
        'idling_time': fields.String,
        'io_wait': fields.String,
        'rule_hit_details': fields.List(fields.Nested(rule_hit_details_fields))
    }

    @marshal_with(profile_fields)
    def get(self, host_id):
        if not is_valid_uuid(host_id):
            abort(404, message='Invalid host_id, Id should be in form of UUID4')

        ident = identity(request)['identity']
        user = user_data_from_identity(ident)
        username = user['username'] if 'username' in user else None

        account_query = db.session.query(RhAccount.id).filter(RhAccount.account == ident['account_number']).subquery()
        system_query = db.session.query(System.id) \
            .filter(System.account_id.in_(account_query)).filter(System.inventory_id == host_id).subquery()

        profile = PerformanceProfile.query.filter(
            PerformanceProfile.system_id.in_(system_query)
        ).order_by(PerformanceProfile.report_date.desc()).first()

        rating_record = RecommendationRating.query.filter(
            RecommendationRating.system_id.in_(system_query),
            RecommendationRating.rated_by == username
        ).first()

        system = db.session.query(System).filter(System.inventory_id == host_id).first()

        if profile:
            record = {'inventory_id': host_id}
            record['display_performance_score'] = profile.display_performance_score
            record['rating'] = rating_record.rating if rating_record else None
            record['report_date'] = profile.report_date
            record['cloud_provider'] = system.cloud_provider
            record['instance_type'] = system.instance_type
            record['idling_time'] = profile.idling_time
            record['io_wait'] = profile.io_wait
            record['rule_hit_details'] = system.rule_hit_details
            # FIXME
            # record['number_of_recommendations'] = fetch value from db itself
            # record['state] = fetch value from db itself
            # TODO
            # after Ticket-86 is resolved

        else:
            abort(404, message="System {} doesn't exist"
                  .format(host_id))

        return record
