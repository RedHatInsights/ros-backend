import json
from ros.lib.config import ROS_EVENTS_TOPIC
from ros.lib.produce import delivery_report


def no_pcp_raw_payload(payload):
    host = payload.get('host')

    payload = {
        "type": payload.get('type'),
        "org_id": host.get('org_id'),
        "platform_metadata": payload.get('platform_metadata'),
        "id": host.get('id'),
        "display_name": host.get('display_name'),
        "fqdn": host.get('fqdn'),
        "stale_timestamp": host.get('stale_timestamp'),
        "groups": host.get('groups'),
        "operating_system": host.get('system_profile').get('operating_system'),
        "cloud_provider": host.get('system_profile').get('cloud_provider')
    }
    compact_payload = {key: value for key, value in payload.items() if value is not None}

    return compact_payload


def produce_report_processor_event(payload, producer):
    request_id = payload.get('metadata').get('request_id')
    host = payload.get('host')
    tailored_payload = no_pcp_raw_payload(payload)
    bytes_ = json.dumps(tailored_payload).encode('utf-8')
    producer.produce(
        topic=ROS_EVENTS_TOPIC,
        value=bytes_,
        key=host.get('id'),
        on_delivery=lambda err, msg: delivery_report(err, msg, host.get('id'), request_id, ROS_EVENTS_TOPIC)
    )
    producer.poll()
