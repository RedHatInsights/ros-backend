from flask_restful import Api
from flask_cors import CORS
from ros.api.routes import initialize_routes
from ros.lib.app import app

CORS(app)
api = Api(app)
initialize_routes(api)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)
