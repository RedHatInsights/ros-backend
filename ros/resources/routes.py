from .v0.hosts import HostsApi, HostDetailsApi
from .v0.status import Status


# Initialize Routes
def initialize_routes(api):
    api.add_resource(Status, '/api/ros/v0/status')
    api.add_resource(HostsApi, '/api/ros/v0/systems')
    api.add_resource(HostDetailsApi, '/api/ros/v0/systems/<host_id>')
