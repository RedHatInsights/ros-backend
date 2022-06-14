import json
from confluent_kafka import Consumer, KafkaException
from ros.sources.tasks import sources
from ros.lib.config import INSIGHTS_KAFKA_ADDRESS, GROUP_ID, SOURCES_EVENTS_TOPIC, get_logger


LOG = get_logger(__name__)


def start_listener():
    consumer = Consumer({
                'bootstrap.servers': INSIGHTS_KAFKA_ADDRESS,
                'group.id': GROUP_ID,
                'enable.auto.commit': False
            })
    consumer.subscribe([SOURCES_EVENTS_TOPIC])

    while True:
        msg = consumer.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            LOG.error(f"Kafka error occured : {msg.error()}.")
            raise KafkaException(msg.error())
        try:
            process_message(msg)
        except json.decoder.JSONDecodeError:
            consumer.commit()
            LOG.error(f"Unable to decode kafka message: {msg.value()}")
        except Exception as err:
            consumer.commit()
            LOG.error(f"An error occurred during message processing: {repr(err)}")
        finally:
            consumer.commit()


def process_message(message):
    """
    Process a single Kafka message object.

    Args:
        message(confluent_kafka.Message): message object from the Kafka listener
    """
    try:
        event_type, headers, value = extract_raw_sources_kafka_message(message)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        LOG.exception(e)
        LOG.warning(f"Malformed sources kafka message's raw value: {message.value()}")
        LOG.warning(f"Malformed sources kafka message's raw headers: {message.headers()}")
        return

    if event_type == "ApplicationAuthentication.create":
        LOG.info(f"Processing {event_type} Message: {value}. Headers: {headers}")
        LOG.info(
            "An ApplicationAuthentication object was created."
            f"Message: {value}. Headers: {headers}."
        )
        sources.create_from_sources_kafka_message(value, headers)
    # elif event_type == "ApplicationAuthentication.destroy":
    #     process_sources_destroy_event(value, headers)
    # elif event_type == "Authentication.update":
    #     process_sources_update_event(value, headers)
    # elif event_type == "Application.pause":
    #     process_sources_pause_event(value, headers)
    # elif event_type == "Application.unpause":
    #     process_sources_unpause_event(value, headers)


def extract_raw_sources_kafka_message(message):
    """
    Extract the useful bits from a Kafka message originating from sources-api.

    Args:
        message(confluent_kafka.Message): message object from the Kafka listener

    Returns:
        tuple(string, list, dict) of the event_type, headers, and value.
    """
    event_type = None
    message_headers = [
        (
            key,
            value.decode("utf-8"),
        )
        for key, value in message.headers()
    ]
    for header in message_headers:
        if header[0] == "event_type":
            event_type = header[1]
            break

    message_value = json.loads(message.value().decode("utf-8"))

    return event_type, message_headers, message_value


if __name__ == "__main__":
    start_listener()
