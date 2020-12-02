from flask import Flask
from flask_restful import Api
from flask_cors import CORS
from ros.models import db
from ros.resources.hosts import Hosts, HostDetails
from ros.resources.status import Status
from ros.config import Config

app = Flask(__name__)
CORS(app)
api = Api(app)
config = Config()

# Initalize database connection
app.config['SQLALCHEMY_DATABASE_URI'] = config.db_uri
db.init_app(app)

# Routes
api.add_resource(Status, '/api/status')
api.add_resource(Hosts, '/api/hosts')
api.add_resource(HostDetails, '/api/host/<host_id>')

if __name__ == "__main__":
    app.run(debug=True)
