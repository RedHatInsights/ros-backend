from flask import Flask
from .models import db
from .config import DB_URI

# Since we're using flask_sqlalchemy, we must create the flask app in both processor and web api
app = Flask(__name__)
# Initalize database connection
app.config['SQLALCHEMY_DATABASE_URI'] = DB_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
