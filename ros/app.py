from flask import Flask
from flask_restful import Api
from flask_cors import CORS
from ros.models import db
from ros.resources.hosts import Hosts, HostDetails
from ros.resources.status import Status
from ros.config import DB_URI
import threading

app = Flask(__name__)
CORS(app)
api = Api(app)

# Initalize database connection
app.config['SQLALCHEMY_DATABASE_URI'] = DB_URI
db.init_app(app)

# Routes
api.add_resource(Status, '/api/ros/status')
api.add_resource(Hosts, '/api/ros/systems')
api.add_resource(HostDetails, '/api/ros/systems/<host_id>')


def initialize_report_processor():
    from ros.processors.report_processor import ReportProcessor
    processor = ReportProcessor()
    processor.init_consumer()


report_processor_thread = threading.Thread(
    target=initialize_report_processor, name='ReportProcessor', daemon=True)
report_processor_thread.start()

if __name__ == "__main__":
    app.run(debug=True)
