from flask import Flask
from .models import db
from .config import DB_URI, DB_POOL_SIZE, DB_MAX_OVERFLOW
from flask import request
from .rbac_interface import ensure_has_permission
from .config import get_logger, REDIS_URL
from prometheus_flask_exporter import RESTfulPrometheusMetrics
from flask_caching import Cache

# Since we're using flask_sqlalchemy, we must create the flask app in both processor and web api
app = Flask(__name__)
# Initalize database connection
app.config['SQLALCHEMY_DATABASE_URI'] = DB_URI
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_size': DB_POOL_SIZE,
    'max_overflow': DB_MAX_OVERFLOW
}
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
metrics = RESTfulPrometheusMetrics.for_app_factory(defaults_prefix='ros', group_by='url_rule')
cache = Cache(config={'CACHE_TYPE': 'RedisCache', 'CACHE_REDIS_URL': REDIS_URL, 'CACHE_DEFAULT_TIMEOUT': 300})
db.init_app(app)


@app.before_request
def ensure_rbac():
    if request.endpoint not in ['status', 'prometheus_metrics', 'openapispec']:
        ensure_has_permission(
            permissions=["ros:*:*", "ros:*:read"],
            application="ros",
            app_name="ros",
            request=request,
            logger=get_logger(__name__)
        )
