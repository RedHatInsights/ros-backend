from ros.processor.report_processor import ReportProcessor
from ros.processor.inventory_events_consumer import InventoryEventsConsumer
import threading


def report_processor():
    processor = ReportProcessor()
    processor.init_consumer()


def events_processor():
    processor = InventoryEventsConsumer()
    processor.run()


if __name__ == "__main__":
    # Start processing in 2 different threads
    reports = threading.Thread(name='report-processor', target=report_processor)
    events = threading.Thread(name='events-processor', target=events_processor)
    reports.start()
    events.start()
    # Wait for threads to finish
    reports.join()
    events.join()
