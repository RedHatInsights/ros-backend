import threading
from flask import Flask
from flask_restful import Api
from flask_cors import CORS
from ros.models import db
from ros.config import DB_URI
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


def inventory_target():
    """Initalize inventory events listerner."""
    from ros.processors.inventory_events_listener import InventoryEventsListener
    inventory_events_processor = InventoryEventsListener()
    inventory_events_processor.run()

inventory_processor_thread = threading.Thread(
    target=inventory_target, name='InventoryEventsListener', daemon=True)
inventory_processor_thread.start()


# TODO: remove this dead code. implement create_app - flask to use current_app
if __name__ == "__main__":
    app.run(debug=True)
