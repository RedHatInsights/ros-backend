from ros.processor.inventory_events_consumer import InventoryEventsConsumer
import threading


def events_processor():
    processor = InventoryEventsConsumer()
    processor.run()


if __name__ == "__main__":
    # Start processing in 2 different threads
    events = threading.Thread(name='events-processor', target=events_processor)
    events.start()
    # Wait for threads to finish
    events.join()
