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
                    'state': 'Oversized',
                    'recommendation_count': 4,
                    'organization_id': 1,
                    'performance_profile': {
                        'cpu_score': 70,
                        'memory_score': 20,
                        'io_score': 80
                    },
                    'facts': {
                        'provider': 'AWS',
                        'instance_type': 'm4large',
                        'idling_type': '20',
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
                    'performance_profile': {
                        'cpu_score': 30,
                        'memory_score': 50,
                        'io_score': 60
                    },
                    'facts': {
                        'provider': 'AWS',
                        'instance_type': 'm1small',
                        'idling_type': '38',
                        'io_wait': '180'
                    }
                }
            ]
        }

        return jsonify(dummy_systems)


class HostDetails(Resource):
    profile_fields = {
        'host_id': fields.String,
        'avg_memory': fields.String(attribute='avg_memory'),
        'avg_memory_used': fields.String(attribute='avg_memory_used')
    }

    @marshal_with(profile_fields)
    def get(self, host_id):
        if not is_valid_uuid(host_id):
            abort(404, message='Invalid host_id,'
                               ' Id should be in form of UUID4')
        profile = PerformanceProfile.query.filter_by(host_id=host_id).first()
        if not profile:
            abort(404, message="Performance Profile {} doesn't exist"
                  .format(host_id))

        return profile
