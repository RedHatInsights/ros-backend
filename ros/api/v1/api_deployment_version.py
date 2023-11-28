from flask import jsonify
from flask_restful import Resource
from k8s_deployment_status import DeploymentStatus
from ros.extensions import metrics
from ros.lib.config import API_VERSION


class ApiDeploymentVersion(Resource):
    @metrics.do_not_track()
    def get(self):
        deployment_status_data = DeploymentStatus().get()
        if "status_code" not in deployment_status_data.keys():
            deployment_status_data['api_version'] = API_VERSION
        return jsonify(deployment_status_data)
