from ros.processor.inventory_events_consumer import InventoryEventsConsumer
from ros.processor.insights_engine_result_consumer import InsightsEngineResultConsumer
from ros.processor.garbage_collector import GarbageCollector
from prometheus_client import start_http_server
import threading


def process_engine_results():
    processor = InsightsEngineResultConsumer()
    processor.run()


def events_processor():
    processor = InventoryEventsConsumer()
    processor.run()


def garbage_collector():
    collector = GarbageCollector()
    collector.run()


if __name__ == "__main__":
    # Start processing in 2 different threads
    engine_results = threading.Thread(name='process-engine-results', target=process_engine_results)
    events = threading.Thread(name='events-processor', target=events_processor)
    collector = threading.Thread(name='garbage-collector', target=garbage_collector)
    events.start()
    engine_results.start()
    collector.start()
    start_http_server(5005)
    # Wait for threads to finish
    events.join()
    engine_results.join()
    collector.join()
