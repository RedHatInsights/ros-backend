from flask import Flask, jsonify
from flask_cors import CORS
app = Flask(__name__)
CORS(app)


@app.route('/ping')
def ping():
    """Ping API to check application status."""
    return 'Application is running! Ping worked!'


DUMMY_SYSTEMS = {
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


@app.route('/api/systems')
def list_systems():
    """Function returns list of systems."""
    return jsonify(DUMMY_SYSTEMS)


if __name__ == '__main__':
    app.run(debug=True)
