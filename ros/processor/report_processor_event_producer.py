import json
from datetime import datetime, timezone
from ros.lib.config import ROS_EVENTS_TOPIC
from ros.lib.produce import delivery_report
from ros.lib.utils import cast_iops_as_float
from ros.lib.constants import SystemStatesWithKeys
from ros.rules.rules_engine import psi_enabled

def api_and_no_pcp_raw_payload(payload):
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
        "operating_system": host.get('system_profile', {}).get('operating_system'),
        "cloud_provider": host.get('system_profile', {}).get('cloud_provider')
    }
    compact_payload = {key: value for key, value in payload.items() if value is not None}

    return compact_payload


def perf_profile_and_rules_payload(report_metadata_output, report_output, report_perf_profile):
    LINKS = {
        "jira": [
            "https://issues.redhat.com/browse/CEECBA-5875",
        ],
        "kcs": [],  # No KCS or doc yet
    }

    cpu_states = report_output.get("states", {}).get("cpu")
    io_states = report_output.get("states", {}).get("io")
    memory_states = report_output.get("states", {}).get("memory")

    error_key = report_output.get("error_key")
    state = SystemStatesWithKeys[error_key].value if error_key else None
    instance_type = report_output.get("instance_type")
    region = report_output.get("region")
    # remove the 'type' key as its not required
    report_perf_profile.pop('type', None)
    performance_record = report_perf_profile
    performance_utilization = {"memory": report_metadata_output.get("mem_utilization"),
                               "cpu": report_metadata_output.get("cpu_utilization"),
                               "io": cast_iops_as_float(report_metadata_output.get("io_utilization", {}))
                               }

    # max_io will be used to sort systems endpoint response instead of io
    io_values = performance_utilization.get('io', {}).values()
    performance_utilization.update(
                        {'max_io': max(io_values) if io_values else 0}
                    )
    #     "system_id": {
    #         "type": "int",
    #         "source": "'id' from System table"
    #     },

    # Construct rule hit details as array to match process_report structure
    rule_hit_details = [{
        "key": error_key,
        "tags": [],
        "type": "rule",
        "links": LINKS,
        "details": report_output,
        "rule_id": f"ros_instance_evaluation|{error_key}" if error_key else "ros_instance_evaluation|UNKNOWN",
        "component": "telemetry.rules.plugins.ros.ros_instance_evaluation.report",
        "system_id": report_metadata_output.get("system_id")
    }]
    
    # Use same logic as process_report: -1 for NO_PCP_DATA, otherwise 1 (since we have single report)
    number_of_recommendations = -1 if error_key == 'NO_PCP_DATA' else 1


    psi_enabled = report_metadata_output.get("psi_enabled")
    if error_key in ["OPTIMIZED", "NO_PCP_DATA"]:
        top_candidate, top_candidate_price = None, None
    else:
        candidates = report_output.get("candidates", [[None, None]])
        top_candidate = candidates[0][0] if candidates else None
        top_candidate_price = candidates[0][1] if candidates else None

    tailored_payload = {
        "cpu_states": cpu_states,
        "io_states": io_states,
        "memory_states": memory_states,
        "state": state,
        "instance_type": instance_type,
        "region": region,
        "performance_record": performance_record,
        "performance_utilization": performance_utilization,
        "report_date": datetime.now(timezone.utc).isoformat(),
        "rule_hit_details": rule_hit_details,
        "number_of_recommendations": number_of_recommendations,
        "psi_enabled": psi_enabled,
        "top_candidate": top_candidate,
        "top_candidate_price": top_candidate_price
    }
    return tailored_payload


def produce_report_processor_event_pcp_raw_data(payload, report_metadata_output, report_output, report_perf_profile, producer):
    request_id = payload.get('metadata').get('request_id')
    host = payload.get('host')
    tailored_payload = api_and_no_pcp_raw_payload(payload)
    perf_profile_and_rules = perf_profile_and_rules_payload(report_metadata_output, report_output, report_perf_profile)

    # Combine both payloads
    combined_payload = {**tailored_payload, **perf_profile_and_rules}
    
    bytes_ = json.dumps(combined_payload).encode('utf-8')
    producer.produce(
        topic=ROS_EVENTS_TOPIC,
        value=bytes_,
        key=host.get('id'),
        on_delivery=lambda err, msg: delivery_report(err, msg, host.get('id'), request_id, ROS_EVENTS_TOPIC)
    )
    producer.poll()


def produce_report_processor_event(payload, producer):
    request_id = payload.get('metadata').get('request_id')
    host = payload.get('host')
    tailored_payload = api_and_no_pcp_raw_payload(payload)
    bytes_ = json.dumps(tailored_payload).encode('utf-8')
    producer.produce(
        topic=ROS_EVENTS_TOPIC,
        value=bytes_,
        key=host.get('id'),
        on_delivery=lambda err, msg: delivery_report(err, msg, host.get('id'), request_id, ROS_EVENTS_TOPIC)
    )
    producer.poll()
