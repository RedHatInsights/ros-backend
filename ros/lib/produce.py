from confluent_kafka import Producer
from ros.lib.config import kafka_auth_config


def init_producer():
    producer = Producer(kafka_auth_config())
    return producer
