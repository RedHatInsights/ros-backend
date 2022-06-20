from sqlalchemy import asc, desc, nullslast, nullsfirst, or_
from sqlalchemy.types import Float
from flask import request
from flask_restful import Resource, abort, fields, marshal_with

from ros.lib.constants import SubStates
from ros.lib.models import (
    PerformanceProfile, RhAccount, System,
    db, RecommendationRating, PerformanceProfileHistory)
from ros.lib.utils import (
    is_valid_uuid, identity,
    user_data_from_identity,
    sort_io_dict, system_ids_by_org_id,
    count_per_state,
    calculate_percentage, org_id_from_identity_header
)
from ros.api.common.pagination import (
    build_paginated_system_list_response,
    limit_value,
    offset_value)
import logging


LOG = logging.getLogger(__name__)
SYSTEM_STATES_EXCEPT_EMPTY = [
    "Oversized", "Undersized", "Idling", "Under pressure", "Storage rightsizing", "Optimized", "Waiting for data"
]
OS_VERSIONS = {
    '7.0': {"name": "RHEL", "major": 7, "minor": 0},
    '7.1': {"name": "RHEL", "major": 7, "minor": 1},
    '7.2': {"name": "RHEL", "major": 7, "minor": 2},
    '7.3': {"name": "RHEL", "major": 7, "minor": 3},
    '7.4': {"name": "RHEL", "major": 7, "minor": 4},
    '7.5': {"name": "RHEL", "major": 7, "minor": 5},
    '7.6': {"name": "RHEL", "major": 7, "minor": 6},
    '7.7': {"name": "RHEL", "major": 7, "minor": 7},
    '7.8': {"name": "RHEL", "major": 7, "minor": 8},
    '7.9': {"name": "RHEL", "major": 7, "minor": 9},
    '8.0': {"name": "RHEL", "major": 8, "minor": 0},
    '8.1': {"name": "RHEL", "major": 8, "minor": 1},
    '8.2': {"name": "RHEL", "major": 8, "minor": 2},
    '8.3': {"name": "RHEL", "major": 8, "minor": 3},
    '8.4': {"name": "RHEL", "major": 8, "minor": 4},
    '8.5': {"name": "RHEL", "major": 8, "minor": 5}
}

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
        query = (
            db.session.query(System.id)
            .join(PerformanceProfile, PerformanceProfile.system_id == System.id)
            .join(RhAccount, RhAccount.id == System.tenant_id)
            .filter(RhAccount.org_id == org_id)
        )
        system_count = query.count()
        systems_with_suggestions = query.filter(PerformanceProfile.number_of_recommendations > 0).count()
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
        'max_io': fields.Float,
        'io_all': fields.Raw
    }
    hosts_fields = {
        'fqdn': fields.String,
        'display_name': fields.String,
        'inventory_id': fields.String,
        'account': fields.String,
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
                host['account'] = row.RhAccount.account
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
                modified_states.append(state)
                if state not in SYSTEM_STATES_EXCEPT_EMPTY:
                    abort(400, message='values are not matching')
            filters.append(System.state.in_(modified_states))
        else:
            filters.append(System.state.in_(SYSTEM_STATES_EXCEPT_EMPTY))
        if operating_systems := request.args.getlist('os'):
            modified_operating_systems = []
            for os in operating_systems:
                os = os.split(" ")[1]
                if os not in OS_VERSIONS.keys():
                    abort(400, message='Not a valid RHEL version')
                modified_operating_systems.append(OS_VERSIONS[os])
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
    condtions = {
        "io": fields.Raw,
        "memory": fields.Raw,
        "cpu": fields.Raw
    }
    meta = {
        "total_count": fields.Integer,
        "non_optimized_count": fields.Integer,
        "conditions_count": fields.Integer,
    }
    report_fields = {
        "systems_per_state": fields.Nested(systems_per_state),
        "conditions": fields.Nested(condtions),
        "meta": fields.Nested(meta)
    }

    @marshal_with(report_fields)
    def get(self):
        org_id = org_id_from_identity_header(request)
        system_queryset = system_ids_by_org_id(org_id, fetch_records=True)
        systems_with_performance_record_query = (
            db.session.query(PerformanceProfile.system_id)
            .filter(PerformanceProfile.system_id.in_(
                system_ids_by_org_id(org_id).subquery()
            ))
        )

        # System counts
        all_systems_count = systems_with_performance_record_query.count()
        optimized_systems = count_per_state(system_queryset, {'state': "Optimized"})
        under_pressure_systems = count_per_state(system_queryset, {'state': "Under pressure"})
        undersized_systems = count_per_state(system_queryset, {'state': "Undersized"})
        oversized_systems = count_per_state(system_queryset, {'state': "Oversized"})
        waiting_for_data_systems = count_per_state(system_queryset, {'state': "Waiting for data"})
        idling_systems = count_per_state(system_queryset, {'state': "Idling"})

        non_optimized = system_queryset.filter(
            or_(
                System.state == 'Oversized',
                System.state == 'Undersized',
                System.state == 'Idling',
                System.state == 'Under pressure'
            )
        )
        non_optimized_count = non_optimized.count()

        # cpu counts
        total_cpu_issues = sum([
            len(system.cpu_states) if system.cpu_states else 0
            for system in non_optimized.filter(System.cpu_states is not None)
        ])
        cpu_undersized = non_optimized.filter(System.cpu_states.any(SubStates.CPU_UNDERSIZED.value)).count()
        cpu_under_pressure = non_optimized.filter(System.cpu_states.any(
            SubStates.CPU_UNDER_PRESSURE.value)
        ).count()
        cpu_oversized = non_optimized.filter(System.cpu_states.any(SubStates.CPU_OVERSIZED.value)).count()

        # memory counts
        total_memory_issues = sum([
            len(system.memory_states) if system.memory_states else 0
            for system in non_optimized.filter(System.memory_states is not None)
        ])
        memory_undersized = non_optimized.filter(System.memory_states.any(SubStates.MEMORY_UNDERSIZED.value)).count()
        memory_pressure = non_optimized.filter(System.memory_states.any(
            SubStates.MEMORY_UNDER_PRESSURE.value)
        ).count()
        memory_oversized = non_optimized.filter(System.memory_states.any(SubStates.MEMORY_OVERSIZED.value)).count()

        # io counts
        total_io_issues = sum([
            len(system.io_states) if system.io_states else 0
            for system in non_optimized.filter(System.io_states is not None)
        ])
        io_pressure = non_optimized.filter(System.io_states.any(SubStates.IO_UNDER_PRESSURE.value)).count()

        # FIXME - enable this logic after getting IO states from advisor engine
        # io_undersized = non_optimized.filter(
        #    System.io_states.any(SubStates.IO_UNDERSIZED.value)).count()
        # io_oversized = non_optimized.filter(
        #    System.io_states.any(SubStates.IO_OVERSIZED.value)).count()
        io_undersized = -1
        io_oversized = -1

        all_conditions_count = total_cpu_issues + total_memory_issues + total_io_issues

        response = {
            "systems_per_state": {
                "optimized": {
                    "count": optimized_systems,
                    "percentage": calculate_percentage(optimized_systems, all_systems_count)
                },
                "under_pressure": {
                    "count": under_pressure_systems,
                    "percentage": calculate_percentage(under_pressure_systems, all_systems_count)
                },
                "undersized": {
                    "count": undersized_systems,
                    "percentage": calculate_percentage(undersized_systems, all_systems_count)
                },
                "oversized": {
                    "count": oversized_systems,
                    "percentage": calculate_percentage(oversized_systems, all_systems_count)
                },
                "idling": {
                    "count": idling_systems,
                    "percentage": calculate_percentage(idling_systems, all_systems_count)
                },
                "waiting_for_data": {
                    "count": waiting_for_data_systems,
                    "percentage": calculate_percentage(waiting_for_data_systems, all_systems_count)
                }
            },
            "conditions": {
                "io": {
                    "count": total_io_issues,
                    "percentage": calculate_percentage(total_io_issues, all_conditions_count),
                    "undersized": io_undersized,
                    "oversized": io_oversized,
                    "under_pressure": io_pressure
                },
                "memory": {
                    "count": total_memory_issues,
                    "percentage": calculate_percentage(total_memory_issues, all_conditions_count),
                    "undersized": memory_undersized,
                    "oversized": memory_oversized,
                    "under_pressure": memory_pressure
                },
                "cpu": {
                    "count": total_cpu_issues,
                    "percentage": calculate_percentage(total_cpu_issues, all_conditions_count),
                    "undersized": cpu_undersized,
                    "oversized": cpu_oversized,
                    "under_pressure": cpu_under_pressure
                }
            },
            "meta": {
                "total_count": all_systems_count,
                "non_optimized_count": non_optimized_count,
                "conditions_count": all_conditions_count
            }
        }

        return response
