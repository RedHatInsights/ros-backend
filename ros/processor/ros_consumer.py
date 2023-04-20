import json
from ros.lib import consume
from ros.processor.metrics import kafka_failures
from confluent_kafka import KafkaException
from ros.lib.config import get_logger
from ros.processor.metrics import processor_requests_failures


class RosConsumer:
    LOG = get_logger(__name__)

    def __init__(self, consumer_topic, prefix, reporter):
        """Create Inventory Events Consumer."""
        self.consumer = consume.init_consumer(consumer_topic)
        self.prefix = prefix
        self.reporter = reporter

    def __iter__(self):
        return self

    def __next__(self):
        msg = self.consumer.poll()
        if msg is None:
            raise StopIteration
        return msg

    def check_msg_for_err(self, msg, prefix, reporter):
        if msg.error():
            self.LOG.error(f"{prefix} - Consumer error: {msg.error()}")
            kafka_failures.labels(reporter=reporter).inc()
            raise KafkaException(msg.error())

    def decode_and_load_json(self, msg):
        try:
            msg_decoded = json.loads(msg.value().decode("utf-8"))
            return msg_decoded
        except json.decoder.JSONDecodeError:
            kafka_failures.labels(reporter=self.reporter).inc()
            self.LOG.error(
                f"{self.prefix} - Unable to decode kafka message: {msg.value()}"
            )

    def try_to_handle_msg(self, handler_function, org_id, processing_err=""):
        try:
            handler_function
        except Exception as err:
            processor_requests_failures.labels(
                reporter=self.reporter,
                org_id=org_id
            ).inc()
            self.LOG.error(
                f"{self.prefix} - An error occurred during message processing: {repr(err)}"
                f"{processing_err}"
            )
        finally:
            self.consumer.commit()
