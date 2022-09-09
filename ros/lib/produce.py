from confluent_kafka import Producer
from ros.lib.config import INSIGHTS_KAFKA_ADDRESS, GROUP_ID, kafka_auth_config


def init_producer():
    connection_object = {
            'group.id': GROUP_ID,
            'bootstrap.servers': INSIGHTS_KAFKA_ADDRESS,
            'enable.auto.commit': False
    }
    producer = Producer(kafka_auth_config(connection_object))

    return producer
