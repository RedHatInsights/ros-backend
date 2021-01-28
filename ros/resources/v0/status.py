from flask_restful import Resource


class Status(Resource):
    def get(self):
        return {'status': 'Application is running!'}
