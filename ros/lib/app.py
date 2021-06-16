from flask import Flask
from .models import db
from .config import DB_URI
from flask import request
from .rbac_interface import ensure_has_permission

# Since we're using flask_sqlalchemy, we must create the flask app in both processor and web api
app = Flask(__name__)
# Initalize database connection
app.config['SQLALCHEMY_DATABASE_URI'] = DB_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)


@app.before_request
def ensure_rbac():
    ensure_has_permission(
        permissions=["ros:*:*", "ros:read"],
        application="ros",
        app_name="ros",
        request=request,
        logger=app.logger,
    )
