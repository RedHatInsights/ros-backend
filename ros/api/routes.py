from .v1.recommendation_ratings import RecommendationRatingsApi
from .v1.recommendations import RecommendationsApi
from .v1.openapi_spec import OpenAPISpec
from .v1.status import Status
from .v1.call_to_action import CallToActionApi
from .v1.suggested_instance_types import SuggestedInstanceTypes, SuggestedInstanceDetails

from .v1.hosts import (
    HostsApi,
    HostDetailsApi,
    HostHistoryApi,
    IsROSConfiguredApi,
    ExecutiveReportAPI,
)
from .v1.api_deployment_version import ApiDeploymentVersion
from ros.lib.config import API_VERSION


# Initialize Routes
def initialize_routes(api):
    api.add_resource(Status, f'/api/ros/{API_VERSION}/status')
    api.add_resource(IsROSConfiguredApi, f'/api/ros/{API_VERSION}/is_configured')
    api.add_resource(HostsApi, f'/api/ros/{API_VERSION}/systems')
    api.add_resource(HostHistoryApi, f'/api/ros/{API_VERSION}/systems/<host_id>/history')
    api.add_resource(RecommendationsApi, f'/api/ros/{API_VERSION}/systems/<host_id>/suggestions')
    api.add_resource(HostDetailsApi, f'/api/ros/{API_VERSION}/systems/<host_id>')
    api.add_resource(RecommendationRatingsApi, f'/api/ros/{API_VERSION}/rating')
    api.add_resource(OpenAPISpec, f'/api/ros/{API_VERSION}/openapi.json')
    api.add_resource(CallToActionApi, f'/api/ros/{API_VERSION}/call_to_action')
    api.add_resource(ExecutiveReportAPI, f'/api/ros/{API_VERSION}/executive_report')
    api.add_resource(SuggestedInstanceTypes, '/api/ros/{API_VERSION}/suggested_instance_types')
    api.add_resource(SuggestedInstanceDetails, '/api/ros/{API_VERSION}/suggested_instance_types/<instance_type>')
    api.add_resource(ApiDeploymentVersion, f'/api/ros/{API_VERSION}/deployment_status')
