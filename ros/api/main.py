from flask_restful import Api
from flask_cors import CORS
from ros.api.routes import initialize_routes
from ros.lib.app import app, metrics, cache
from ros.lib.cw_logging import commence_cw_log_streaming

CORS(app)
api = Api(app)
initialize_routes(api)
cache.init_app(app)
metrics.init_app(app, api)

if __name__ == "__main__":
    commence_cw_log_streaming('ros-api')
    app.run(host='0.0.0.0', port=8000)
