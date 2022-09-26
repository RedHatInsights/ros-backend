import json
from confluent_kafka import KafkaError
from datetime import datetime, timezone
from ros.lib.models import PerformanceProfile
from ros.lib.config import NOTIFICATIONS_TOPIC, get_logger
from ros.lib.utils import systems_ids_for_existing_profiles

logger = get_logger(__name__)


def new_suggestion_event(host, platform_metadata, previous_state, current_state, producer):

    org_id = host.get("org_id")
    query = systems_ids_for_existing_profiles(org_id)
    systems_with_suggestions = query.filter(PerformanceProfile.number_of_recommendations > 0).count()
    request_id = platform_metadata.get('request_id')
    payload = {
        "bundle": "rhel",
        "application": "ros",
        "event_type": "new-suggestion",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "account_id": host.get("account_id") or "",
        "org_id": org_id,
        "context": {
            "event_name": "New suggestion",
            "systems_with_suggestions": systems_with_suggestions
        },
        "events": [
            {
                "metadata": {},
                "payload": {
                    "display_name": host.get('display_name'),
                    "inventory_id": host.get('id'),
                    "message": f"{host.get('display_name')} has a new suggestion.",
                    "previous_state": previous_state,
                    "current_state": current_state
                },
            }
        ],
    }
    upload_message_to_notification(payload, request_id, producer)


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


def upload_message_to_notification(payload, request_id, producer):
    bytes_ = json.dumps(payload).encode('utf-8')
    producer.produce(NOTIFICATIONS_TOPIC, bytes_, on_delivery=lambda err, msg: delivery_report(err, msg, request_id))
    producer.poll()
