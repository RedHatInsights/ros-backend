from flask import send_file
from flask_restful import Resource


class OpenAPISpec(Resource):
    def get(self):
        return send_file("../openapi/openapi.json")
