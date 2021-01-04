from flask import Flask
from flask_restful import Api
from flask_cors import CORS
from ros.models import db
from ros.config import DB_URI
import threading
from ros.resources.routes import initialize_routes

app = Flask(__name__)
CORS(app)

api = Api(app)

# Initalize database connection
app.config['SQLALCHEMY_DATABASE_URI'] = DB_URI
db.init_app(app)

initialize_routes(api)


def initialize_report_processor():
    from ros.processors.report_processor import ReportProcessor
    processor = ReportProcessor()
    processor.init_consumer()


report_processor_thread = threading.Thread(
    target=initialize_report_processor, name='ReportProcessor', daemon=True)
report_processor_thread.start()

if __name__ == "__main__":
    app.run(debug=True)
