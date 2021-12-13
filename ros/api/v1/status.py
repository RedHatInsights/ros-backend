from flask_restful import Resource
from ros.lib.app import metrics


class Status(Resource):
    @metrics.do_not_track()
    def get(self):
        return {'status': 'Application is running!'}
