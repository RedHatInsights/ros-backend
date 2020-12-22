from flask import jsonify
from flask_restful import Resource, abort, fields, marshal_with
from ros.models import PerformanceProfile
from ros.utils import is_valid_uuid


class Hosts(Resource):
    def get(self):
        dummy_systems = {
            'results': [
                {
                    'fqdn': 'machine1.local.company.com',
                    'display_name': 'machine1-rhel_test123',
                    'id': '12345-57575757',
                    'account': '12345',
                    'vm_uuid': '12345a1',
                    'state': 'Crashloop',
                    'recommendation_count': 5,
                    'organization_id': 1,
                    'performance_score': {
                        'cpu_score': 20,
                        'memory_score': 20,
                        'io_score': 20
                    },
                    'facts': {
                        'cloud_provider': 'AWS',
                        'instance_type': 'm4large',
                        'idling_time': '20',
                        'io_wait': '180'
                    }
                },
                {
                    'fqdn': 'machine2.local.company.com',
                    'display_name': 'machine2-rhel_test456',
                    'id': '12345-58585858',
                    'account': '12345',
                    'vm_uuid': '12345a2',
                    'state': 'Undersized',
                    'recommendation_count': 3,
                    'organization_id': 1,
                    'performance_score': {
                        'cpu_score': 30,
                        'memory_score': 50,
                        'io_score': 60
                    },
                    'facts': {
                        'cloud_provider': 'AWS',
                        'instance_type': 'm1small',
                        'idling_time': '38',
                        'io_wait': '180'
                    }
                },
                {
                    'fqdn': 'machine3.local.company.com',
                    'display_name': 'machine3-rhel_test789',
                    'id': '12345-59595959',
                    'account': '12345',
                    'vm_uuid': '12345a3',
                    'state': 'Optimized',
                    'recommendation_count': 1,
                    'organization_id': 1,
                    'performance_score': {
                        'cpu_score': 80,
                        'memory_score': 90,
                        'io_score': 90
                    },
                    'facts': {
                        'cloud_provider': 'AWS',
                        'instance_type': 'm1small',
                        'idling_time': '38',
                        'io_wait': '180'
                    }
                },
                {
                    'fqdn': 'machine4.local.company.com',
                    'display_name': 'machine4-rhel_test101',
                    'id': '12345-60606060',
                    'account': '12345',
                    'vm_uuid': '12345a4',
                    'state': 'Optimized',
                    'recommendation_count': 0,
                    'organization_id': 1,
                    'performance_score': {
                        'cpu_score': 90,
                        'memory_score': 90,
                        'io_score': 90
                    },
                    'facts': {
                        'cloud_provider': 'AWS',
                        'instance_type': 'm1large',
                        'idling_time': '38',
                        'io_wait': '180'
                    }
                }
            ]
        }

        return jsonify(dummy_systems)


class HostDetails(Resource):
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
