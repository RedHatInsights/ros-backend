from flask import Flask
from ros.extensions import db
from .config import DB_URI, DB_POOL_SIZE, DB_MAX_OVERFLOW
from flask import request
from .rbac_interface import ensure_has_permission
from .config import get_logger
from flask_migrate import Migrate
# Uncomment this when we can sort out the unleash connection issues
# from ros.lib.feature_flags import init_unleash_app
# Since we're using flask_sqlalchemy, we must create the flask app in both processor and web api

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
    # Uncomment this when we can sort out the unleash connection issues
    # if not BYPASS_UNLEASH:
    #     from .config import UNLEASH_URL, UNLEASH_TOKEN, UNLEASH_CACHE_DIR
    #     if UNLEASH_TOKEN:
    #         app.config['UNLEASH_APP_NAME'] = 'ros-backend'
    #         app.config['UNLEASH_ENVIRONMENT'] = 'default'
    #         app.config['UNLEASH_URL'] = UNLEASH_URL
    #         app.config['UNLEASH_CUSTOM_HEADERS'] = {'Authorization': f"Bearer{UNLEASH_TOKEN}"}
    #         app.config['UNLEASH_CACHE_DIRECTORY'] = UNLEASH_CACHE_DIR
    #         init_unleash_app(app)
    # else:
    #     fallback_msg = (
    #         "Unleash is bypassed by config value!"
    #         if BYPASS_UNLEASH
    #         else "No API token was provided for the Unleash server connection!"
    #     )
    #     fallback_msg += " Feature flag toggles will default to their fallback values."
    #     logger.warning(fallback_msg)
    db.init_app(app)
    migrate = Migrate()
    migrate.init_app(app, db)
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
