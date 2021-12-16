from flask import Flask
from .models import db
from .config import DB_URI
from flask import request
from .rbac_interface import ensure_has_permission
from .config import get_logger
from prometheus_flask_exporter import RESTfulPrometheusMetrics

# Since we're using flask_sqlalchemy, we must create the flask app in both processor and web api
app = Flask(__name__)
# Initalize database connection
app.config['SQLALCHEMY_DATABASE_URI'] = DB_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
metrics = RESTfulPrometheusMetrics.for_app_factory(defaults_prefix='ros')
db.init_app(app)


@app.before_request
def ensure_rbac():
    if request.endpoint not in ['status', 'prometheus_metrics']:
        ensure_has_permission(
            permissions=["ros:*:*", "ros:*:read"],
            application="ros",
            app_name="ros",
            request=request,
            logger=get_logger(__name__)
        )
