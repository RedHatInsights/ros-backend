import json
from confluent_kafka import KafkaError
from datetime import datetime, timezone
from ros.lib.models import PerformanceProfile
from ros.lib.config import (
    NOTIFICATIONS_TOPIC,
    ROS_EVENTS_TOPIC,
    get_logger
)
from ros.lib.utils import systems_ids_for_existing_profiles
from ros.lib.constants import Notification

logger = get_logger(__name__)


def notification_payload(host, system_previous_state, system_current_state):

    org_id = host.get("org_id")
    query = systems_ids_for_existing_profiles(org_id)
    systems_with_suggestions = query.filter(PerformanceProfile.number_of_recommendations > 0).count()
    payload = {
        "bundle": Notification.BUNDLE.value,
        "application": Notification.APPLICATION.value,
        "event_type": Notification.EVENT_TYPE.value,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "account_id": host.get("account") or "",
        "org_id": org_id,
        "context": {
            "event_name": "New suggestion",
            "systems_with_suggestions": systems_with_suggestions,
            "display_name": host.get('display_name'),
            "inventory_id": host.get('id')
        },
        "events": [
            {
                "metadata": {},
                "payload": {
                    "display_name": host.get('display_name'),
                    "inventory_id": host.get('id'),
                    "message": f"{host.get('display_name')} has a new suggestion.",
                    "previous_state": system_previous_state,
                    "current_state": system_current_state
                },
            }
        ],
    }
    return payload


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


def new_suggestion_event(host, platform_metadata, system_previous_state, system_current_state, producer):
    request_id = platform_metadata.get('request_id')
    payload = notification_payload(host, system_previous_state, system_current_state)
    bytes_ = json.dumps(payload).encode('utf-8')
    producer.produce(
        NOTIFICATIONS_TOPIC,
        bytes_,
        on_delivery=lambda err, msg: delivery_report(err, msg, host.get('id'), request_id, NOTIFICATIONS_TOPIC)
    )
    producer.poll()


def produce_report_processor_event(payload, platform_metadata, producer):
    request_id = platform_metadata.get('request_id')
    bytes_ = json.dumps(payload).encode('utf-8')
    host = payload.get('host')
    producer.produce(
        topic=ROS_EVENTS_TOPIC,
        value=bytes_,
        key=payload.get('id'),
        on_delivery=lambda err, msg: delivery_report(err, msg, host.get('id'), request_id, ROS_EVENTS_TOPIC)
    )
    producer.poll()
