from confluent_kafka import Consumer
from ros.lib.config import INSIGHTS_KAFKA_ADDRESS, GROUP_ID, kafka_auth_config


def init_consumer(kafka_topic):
    connection_object = {
            'group.id': GROUP_ID,
            'bootstrap.servers': INSIGHTS_KAFKA_ADDRESS,
            'enable.auto.commit': False
    }
    consumer = Consumer(kafka_auth_config(connection_object))
    # Subscribe to topic
    consumer.subscribe([kafka_topic])

    return consumer
