from confluent_kafka import Consumer
from ros.lib.config import kafka_auth_config


def init_consumer(kafka_topic, GROUP_ID):
    connection_object = {
        'group.id': GROUP_ID,
        'enable.auto.commit': False
    }
    consumer = Consumer(kafka_auth_config(connection_object))
    # Subscribe to topic
    consumer.subscribe([kafka_topic])
    return consumer
