from ros.lib.utils import validate_ros_payload


def system_allowed_in_ros(msg, processor):
    is_ros = msg["input"]["platform_metadata"].get("is_ros")
    cloud_provider = ''
    if processor == 'InsightsEngineConsumer':
        cloud_provider = msg["results"]["system"]["metadata"].get('cloud_provider')
    elif processor == 'InventoryEventsConsumer':
        cloud_provider = msg['host']['system_profile'].get('cloud_provider')
    return validate_ros_payload(is_ros, cloud_provider)
