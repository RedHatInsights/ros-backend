from confluent_kafka import Producer
from ros.lib.config import kafka_auth_config, get_logger
from confluent_kafka import KafkaError


logger = get_logger(__name__)


def init_producer():
    producer = Producer(kafka_auth_config())
    return producer


def delivery_report(err, msg, host_id, request_id, kafka_topic):
    try:
        if not err:
            logger.info(
                f"Message delivered to {msg.topic()} topic for request_id {request_id} and system {host_id}"
            )
            return

        logger.error(
                f"Message delivery for topic {msg.topic()} topic failed for request_id [{err}]: {request_id}"
        )
    except KafkaError:
        logger.exception(
            f"Failed to produce message to [{kafka_topic}] topic: {request_id}"
        )
