import logging
from flask import request
from sqlalchemy.types import Float
from ros.lib.constants import SubStates

from datetime import datetime, timedelta, timezone
from sqlalchemy import asc, desc, nullslast, nullsfirst
from flask_restful import Resource, abort, fields, marshal_with

from ros.lib.models import (
    db,
    System,
    RhAccount,
    PerformanceProfile,
    RecommendationRating,
    PerformanceProfileHistory,
)
from ros.lib.utils import (
    is_valid_uuid,
    identity,
    user_data_from_identity,
    systems_ids_for_existing_profiles,
    sort_io_dict,
    system_ids_by_org_id,
    count_per_state,
    calculate_percentage,
    org_id_from_identity_header,
    highlights_instance_types, get_psi_count,
)
from ros.api.common.pagination import (
    limit_value,
    offset_value,
    build_paginated_system_list_response
)


LOG = logging.getLogger(__name__)
SYSTEM_STATES_EXCEPT_EMPTY = [
    "Oversized", "Undersized", "Idling", "Under pressure", "Storage rightsizing", "Optimized", "Waiting for data"
]

SYSTEM_COLUMNS = [
    'inventory_id',
    'display_name',
    'instance_type',
    'cloud_provider',
    'state',
    'fqdn',
    'operating_system',
]


class IsROSConfiguredApi(Resource):
    def get(self):
        org_id = org_id_from_identity_header(request)
        query = systems_ids_for_existing_profiles(org_id)
        system_count = query.count()
        systems_with_suggestions = query.filter(PerformanceProfile.number_of_recommendations > 0).count()
        systems_waiting_for_data = query.filter(PerformanceProfile.state == 'Waiting for data').count()

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
        'max_io': fields.Float,
        'io_all': fields.Raw
    }
    hosts_fields = {
        'fqdn': fields.String,
        'display_name': fields.String,
        'inventory_id': fields.String,
        'org_id': fields.String,
        'number_of_suggestions': fields.Integer(attribute='number_of_recommendations'),
        'state': fields.String,
        'performance_utilization': fields.Nested(performance_utilization_fields),
        'cloud_provider': fields.String,
        'instance_type': fields.String,
        'idling_time': fields.String,
        'os': fields.String,
        'report_date': fields.String
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
            request.args.get('order_by') or 'report_date'
        ).strip().lower()
        order_how = (request.args.get('order_how') or 'desc').strip().lower()

        org_id = org_id_from_identity_header(request)
        # Note that When using LIMIT, it is important to use an ORDER BY clause
        # that constrains the result rows into a unique order.
        # Otherwise you will get an unpredictable subset of the query's rows.
        # Refer - https://www.postgresql.org/docs/13/queries-limit.html

        system_query = system_ids_by_org_id(org_id).filter(*self.build_system_filters())
        sort_expression = self.build_sort_expression(order_how, order_by)

        query = (
            db.session.query(PerformanceProfile, System, RhAccount)
            .join(System, System.id == PerformanceProfile.system_id)
            .join(RhAccount, RhAccount.id == System.tenant_id)
            .filter(PerformanceProfile.system_id.in_(system_query.subquery()))
            .order_by(*sort_expression)
        )
        count = query.count()
        # NOTE: Override limit value to get all the systems when it is -1
        if limit == -1:
            limit = count
        query = query.limit(limit).offset(offset)
        query_results = query.all()
        hosts = []
        for row in query_results:
            try:
                system_dict = row.System.__dict__
                host = {skey: system_dict[skey] for skey in SYSTEM_COLUMNS}
                host['org_id'] = row.RhAccount.org_id
                host['performance_utilization'] = sort_io_dict(
                    row.PerformanceProfile.performance_utilization
                )
                host['idling_time'] = row.PerformanceProfile.idling_time
                host['os'] = row.System.deserialize_host_os_data
                host['report_date'] = row.PerformanceProfile.report_date
                host['number_of_recommendations'] = row.PerformanceProfile.number_of_recommendations
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
                if state not in SYSTEM_STATES_EXCEPT_EMPTY:
                    abort(400, message='values are not matching')
                modified_states.append(state)
            filters.append(System.state.in_(modified_states))
        else:
            filters.append(System.state.in_(SYSTEM_STATES_EXCEPT_EMPTY))
        if operating_systems := request.args.getlist('os'):
            modified_operating_systems = []
            for os in operating_systems:
                if os.replace('.', '', 1).isdigit():
                    os_object = {"name": "RHEL"}
                    if len(os) == 1:
                        os += ".0"
                    os_object["major"] = int(os.split(".")[0])
                    os_object["minor"] = int(os.split(".")[1])
                    modified_operating_systems.append(os_object)
                else:
                    abort(400, message='Not a valid RHEL version')
            filters.append(System.operating_system.in_(modified_operating_systems))
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
                    order_method].astext.cast(Float)),
                asc(PerformanceProfile.system_id),)

        if order_method == 'number_of_suggestions':
            return (sort_order(PerformanceProfile.number_of_recommendations),
                    asc(PerformanceProfile.system_id),)

        if order_method == 'state':
            return (sort_order(System.state),
                    asc(PerformanceProfile.system_id),)

        if order_method == 'os':
            nulls_method = nullsfirst if order_how == 'asc' else nullslast
            return (
                nulls_method(sort_order(System.operating_system['name'])),
                sort_order(System.operating_system['major']),
                sort_order(System.operating_system['minor'])
            )
        if order_method == 'report_date':
            return (sort_order(PerformanceProfile.report_date),
                    asc(PerformanceProfile.system_id))

        abort(403, message="Unexpected sort method {}".format(order_method))
        return None


class HostDetailsApi(Resource):
    performance_utilization_fields = {
        'cpu': fields.Integer,
        'memory': fields.Integer,
        'max_io': fields.Float,
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
        'os': fields.String,
    }

    @marshal_with(profile_fields)
    def get(self, host_id):
        if not is_valid_uuid(host_id):
            abort(404, message='Invalid host_id, Id should be in form of UUID4')

        ident = identity(request)['identity']
        user = user_data_from_identity(ident)
        username = user['username'] if 'username' in user else None
        org_id = org_id_from_identity_header(request)

        system_query = system_ids_by_org_id(org_id).filter(System.inventory_id == host_id).subquery()

        profile = PerformanceProfile.query.filter(
            PerformanceProfile.system_id.in_(system_query)).first()

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
            record['os'] = system.deserialize_host_os_data
            record['number_of_recommendations'] = profile.number_of_recommendations
        else:
            abort(404, message="System {} doesn't exist"
                  .format(host_id))

        return record


class HostHistoryApi(Resource):
    performance_utilization_fields = {
        'cpu': fields.Integer,
        'memory': fields.Integer,
        'io_all': fields.Raw,
        'max_io': fields.Float,
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

        org_id = org_id_from_identity_header(request)

        system_query = system_ids_by_org_id(org_id).filter(System.inventory_id == host_id).subquery()

        query = PerformanceProfileHistory.query.filter(
            PerformanceProfileHistory.system_id.in_(system_query)
        ).order_by(PerformanceProfileHistory.report_date.desc())

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


class ExecutiveReportAPI(Resource):

    count_and_percentage = {
        "count": fields.Integer,
        "percentage": fields.Float
    }
    systems_per_state = {
        "optimized": fields.Nested(count_and_percentage),
        "under_pressure": fields.Nested(count_and_percentage),
        "undersized": fields.Nested(count_and_percentage),
        "oversized": fields.Nested(count_and_percentage),
        "idling": fields.Nested(count_and_percentage),
        "waiting_for_data": fields.Nested(count_and_percentage)
    }
    conditions = {
        "io": fields.Raw,
        "memory": fields.Raw,
        "cpu": fields.Raw
    }
    instance_types_highlights = {
        "current": fields.Raw,
        "suggested": fields.Raw,
        "historical": fields.Raw,
    }
    meta = {
        "total_count": fields.Integer,
        "non_optimized_count": fields.Integer,
        "conditions_count": fields.Integer,
        "stale_count": fields.Integer,
        "non_psi_count": fields.Integer,
        "psi_enabled_count": fields.Integer,
    }
    report_fields = {
        "systems_per_state": fields.Nested(systems_per_state),
        "conditions": fields.Nested(conditions),
        "instance_types_highlights": fields.Nested(instance_types_highlights),
        "meta": fields.Nested(meta)
    }

    @marshal_with(report_fields)
    def get(self):
        org_id = org_id_from_identity_header(request)
        systems_with_performance_record_queryset = db.session.query(
            System.id,
            System.state,
            System.instance_type,
            System.cpu_states,
            System.io_states,
            System.memory_states,
            PerformanceProfile.system_id,
            PerformanceProfile.report_date,
            PerformanceProfile.rule_hit_details,
            PerformanceProfile.psi_enabled,
            PerformanceProfile.operating_system
        ).select_from(System).join(PerformanceProfile).filter(
            System.id == PerformanceProfile.system_id,
            System.id.in_(system_ids_by_org_id(org_id))
        )

        systems_with_performance_record_subquery = systems_with_performance_record_queryset.subquery()

        # System counts
        total_systems = systems_with_performance_record_queryset.count()
        optimized_systems = count_per_state(systems_with_performance_record_queryset, {'state': "Optimized"})
        under_pressure_systems = count_per_state(systems_with_performance_record_queryset, {'state': "Under pressure"})
        undersized_systems = count_per_state(systems_with_performance_record_queryset, {'state': "Undersized"})
        oversized_systems = count_per_state(systems_with_performance_record_queryset, {'state': "Oversized"})
        waiting_for_data_systems = count_per_state(
            systems_with_performance_record_queryset,
            {'state': "Waiting for data"}
        )
        idling_systems = count_per_state(systems_with_performance_record_queryset, {'state': "Idling"})

        non_optimized_queryset = systems_with_performance_record_queryset.filter(
            System.state.in_(
                ['Oversized', 'Undersized', 'Idling', 'Under pressure']
            )
        )
        non_optimized_count = 0
        total_keys = ['cpu', 'memory', 'io']
        state_keys = ['undersized', 'under_pressure', 'oversized']
        totals = dict.fromkeys(total_keys, 0)
        cpu_states_dict = dict.fromkeys(state_keys, 0)
        memory_states_dict = dict.fromkeys(state_keys, 0)
        io_states_dict = dict.fromkeys(state_keys, 0)

        for record in non_optimized_queryset:
            non_optimized_count += 1
            if record.cpu_states:
                totals['cpu'] = totals['cpu'] + len(record.cpu_states)
                if SubStates.CPU_UNDERSIZED.value in record.cpu_states:
                    cpu_states_dict['undersized'] += 1
                if SubStates.CPU_UNDER_PRESSURE.value in record.cpu_states:
                    cpu_states_dict['under_pressure'] += 1
                if SubStates.CPU_OVERSIZED.value in record.cpu_states:
                    cpu_states_dict['oversized'] += 1
            if record.memory_states:
                totals['memory'] = totals['memory'] + len(record.memory_states)
                if SubStates.MEMORY_UNDERSIZED.value in record.memory_states:
                    memory_states_dict['undersized'] += 1
                if SubStates.MEMORY_UNDER_PRESSURE.value in record.memory_states:
                    memory_states_dict['under_pressure'] += 1
                if SubStates.MEMORY_OVERSIZED.value in record.memory_states:
                    memory_states_dict['oversized'] += 1
            if record.io_states:
                totals['io'] = totals['io'] + len(record.io_states)
                if SubStates.IO_UNDER_PRESSURE.value in record.io_states:
                    io_states_dict['under_pressure'] += 1
                # FIXME - enable this logic after getting IO states from advisor engine
                # if SubStates.IO_UNDERSIZED.value in system.io_states:
                #     io_states_dict['undersized'] += 1
                # if SubStates.IO_OVERSIZED.value in system.io_states:
                #     io_states_dict['oversized'] += 1

        io_states_dict['oversized'] = -1
        io_states_dict['undersized'] = -1
        total_conditions = totals['cpu'] + totals['memory'] + totals['io']

        current_utc_datetime = datetime.now(timezone.utc)
        stale_date = (current_utc_datetime - timedelta(days=7)).date()

        current_performance_profiles = [
            record
            for record in systems_with_performance_record_queryset
            if current_utc_datetime.date() >= record.report_date.date() > stale_date
        ]

        historical_performance_profiles = db.session.query(
            PerformanceProfileHistory.system_id,
            PerformanceProfileHistory.rule_hit_details
        ).join(
            systems_with_performance_record_subquery,
            systems_with_performance_record_subquery.c.system_id == PerformanceProfileHistory.system_id
        )  # Systems older than 7 days/stale systems are considered here

        stale_count = systems_with_performance_record_queryset.filter(
            PerformanceProfile.report_date <= stale_date
        ).count()

        non_psi_count = get_psi_count(systems_with_performance_record_queryset, False)
        psi_enabled_count = get_psi_count(systems_with_performance_record_queryset, True)

        response = {
            "systems_per_state": {
                "optimized": {
                    "count": optimized_systems,
                    "percentage": calculate_percentage(optimized_systems, total_systems)
                },
                "under_pressure": {
                    "count": under_pressure_systems,
                    "percentage": calculate_percentage(under_pressure_systems, total_systems)
                },
                "undersized": {
                    "count": undersized_systems,
                    "percentage": calculate_percentage(undersized_systems, total_systems)
                },
                "oversized": {
                    "count": oversized_systems,
                    "percentage": calculate_percentage(oversized_systems, total_systems)
                },
                "idling": {
                    "count": idling_systems,
                    "percentage": calculate_percentage(idling_systems, total_systems)
                },
                "waiting_for_data": {
                    "count": waiting_for_data_systems,
                    "percentage": calculate_percentage(waiting_for_data_systems, total_systems)
                }
            },
            "conditions": {
                "io": {
                    "count": totals['io'],
                    "percentage": calculate_percentage(totals['io'], total_conditions),
                    "undersized": io_states_dict['undersized'],
                    "oversized": io_states_dict['oversized'],
                    "under_pressure": io_states_dict['under_pressure']
                },
                "memory": {
                    "count": totals['memory'],
                    "percentage": calculate_percentage(totals['memory'], total_conditions),
                    "undersized": memory_states_dict['undersized'],
                    "oversized": memory_states_dict['oversized'],
                    "under_pressure": memory_states_dict['under_pressure']
                },
                "cpu": {
                    "count": totals['cpu'],
                    "percentage": calculate_percentage(totals['cpu'], total_conditions),
                    "undersized": cpu_states_dict['undersized'],
                    "oversized": cpu_states_dict['oversized'],
                    "under_pressure": cpu_states_dict['under_pressure']
                }
            },
            "instance_types_highlights": {
                "current": highlights_instance_types(current_performance_profiles, 'current'),
                "suggested": highlights_instance_types(current_performance_profiles, 'suggested'),
                "historical": highlights_instance_types(historical_performance_profiles, 'historical')
            },
            "meta": {
                "total_count": total_systems,
                "non_optimized_count": non_optimized_count,
                "conditions_count": total_conditions,
                "stale_count": stale_count,
                "non_psi_count": non_psi_count,
                "psi_enabled_count": psi_enabled_count
            }
        }

        return response
