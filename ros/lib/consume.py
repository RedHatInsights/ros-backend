from confluent_kafka import Consumer
from ros.lib.config import kafka_auth_config


def init_consumer(kafka_topic, GROUP_ID, max_poll_interval_ms=None):
    connection_object = {
        'group.id': GROUP_ID,
        'enable.auto.commit': False
    }
    if max_poll_interval_ms is not None:
        connection_object['max.poll.interval.ms'] = max_poll_interval_ms
    consumer = Consumer(kafka_auth_config(connection_object))
    # Subscribe to topic
    consumer.subscribe([kafka_topic])
    return consumer
