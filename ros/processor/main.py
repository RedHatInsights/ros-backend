from http.server import HTTPServer
from ros.lib.utils import PROCESSOR_INSTANCES, MonitoringHandler
from ros.lib.cw_logging import commence_cw_log_streaming
from ros.processor.inventory_events_consumer import InventoryEventsConsumer
from ros.processor.insights_engine_result_consumer import InsightsEngineResultConsumer
from ros.processor.garbage_collector import GarbageCollector
from prometheus_client import start_http_server
import threading
from ros.lib.config import METRICS_PORT


def process_engine_results():
    processor = InsightsEngineResultConsumer()
    processor.processor_name = 'process-engine-results'
    PROCESSOR_INSTANCES.append(processor)
    processor.run()


def events_processor():
    processor = InventoryEventsConsumer()
    processor.processor_name = 'events-processor'
    PROCESSOR_INSTANCES.append(processor)
    processor.run()


def garbage_collector():
    collector = GarbageCollector()
    collector.processor_name = 'garbage-collector'
    PROCESSOR_INSTANCES.append(collector)
    collector.run()


def thread_monitor():
    server = HTTPServer(('', 8000), MonitoringHandler)
    server.serve_forever()


if __name__ == "__main__":
    commence_cw_log_streaming('ros-processor')
    # Start processing in 2 different threads
    engine_results = threading.Thread(name='process-engine-results', target=process_engine_results)
    events = threading.Thread(name='events-processor', target=events_processor)
    collector = threading.Thread(name='garbage-collector', target=garbage_collector)
    threadmonitor = threading.Thread(name='thread-monitor', target=thread_monitor)
    events.start()
    engine_results.start()
    collector.start()
    threadmonitor.start()
    start_http_server(int(METRICS_PORT))
    # Wait for threads to finish
    events.join()
    engine_results.join()
    collector.join()
