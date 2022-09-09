import json
from ros.lib import produce
from confluent_kafka import KafkaError
from datetime import datetime, timezone
from ros.lib.config import NOTIFICATIONS_TOPIC, get_logger

logger = get_logger(__name__)


# Event for new suggestion
def new_suggestion_event(host, platform_metadata):
    request_id = platform_metadata.get('request_id')
    payload = {
        "version": "v1.0.0",
        "bundle": "rhel",
        "application": "ros",
        "event_type": "new-suggestion",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "account_id": host.get("account_id") or "",
        "org_id": host.get("org_id"),
        "context": {"event_name": "New suggestion"},
        "events": [
            {
                "metadata": {},
                "payload": {
                    "display_name": host.get('display_name'),
                    "inventory_id": host.get('id'),
                    "message": f"{host.get('display_name')} has a new suggestion."
                },
            }
        ],
    }
    upload_message_to_notification(payload, request_id)


def delivery_report(err, msg, request_id):
    try:
        if not err:
            logger.info(
                "Message delivered to %s [%s] for request_id [%s]",
                msg.topic(),
                msg.partition(),
                request_id,
            )
            return

        logger.error(
                "Message delivery for topic %s failed for request_id [%s]: %s",
                msg.topic(),
                err,
                request_id,
        )
    except KafkaError:
        logger.exception(
            "Failed to produce message to [%s] topic: %s", NOTIFICATIONS_TOPIC, request_id
        )


def upload_message_to_notification(payload, request_id):
    bytes_ = json.dumps(payload).encode('utf-8')
    producer = produce.init_producer()
    producer.produce(NOTIFICATIONS_TOPIC, bytes_, on_delivery=lambda err, msg: delivery_report(err, msg, request_id))
    producer.poll()
