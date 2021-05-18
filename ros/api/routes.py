from .v0.hosts import HostsApi, HostDetailsApi, HostHistoryApi
from .v0.recommendation_ratings import RecommendationRatingsApi
from .v0.recommendations import RecommendationsApi
from .v0.openapi_spec import OpenAPISpec
from .v0.status import Status


# Initialize Routes
def initialize_routes(api):
    api.add_resource(Status, '/api/ros/v0/status')
    api.add_resource(HostsApi, '/api/ros/v0/systems')
    api.add_resource(HostHistoryApi, '/api/ros/v0/systems/<host_id>/history')
    api.add_resource(RecommendationsApi, '/api/ros/v0/systems/<host_id>/recommendations')
    api.add_resource(HostDetailsApi, '/api/ros/v0/systems/<host_id>')
    api.add_resource(RecommendationRatingsApi, '/api/ros/v0/rating')
    api.add_resource(OpenAPISpec, '/api/ros/v0/openapi.json')
