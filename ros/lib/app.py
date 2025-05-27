from flask import Flask
from ros.extensions import db, cache
from .config import DB_URI, DB_POOL_SIZE, DB_MAX_OVERFLOW
from flask import request
from .rbac_interface import ensure_has_permission
from .config import get_logger
from flask_migrate import Migrate

logger = get_logger(__name__)


def create_app():
    app = Flask(__name__)
    # Initalize database connection
    app.config['SQLALCHEMY_DATABASE_URI'] = DB_URI
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_size': DB_POOL_SIZE,
        'max_overflow': DB_MAX_OVERFLOW
    }
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    migrate = Migrate()
    migrate.init_app(app, db)
    cache.init_app(app)
    return app


app = create_app()


@app.before_request
def ensure_rbac():
    if request.endpoint not in ['status', 'prometheus_metrics', 'openapispec']:
        ensure_has_permission(
            permissions=["ros:*:*", "ros:*:read"],
            application="ros,inventory",
            app_name="ros",
            request=request,
            logger=get_logger(__name__)
        )


@app.after_request
def add_headers(response):
    response.headers['Content-Security-Policy'] = "script-src 'self';"
    response.headers['Cache-Control'] = 'no-store'
    response.headers['Content-Type'] = 'application/json; charset=UTF-8;'
    response.headers['Referrer-Policy'] = 'no-referrer'
    return response
