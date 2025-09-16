import json
from datetime import datetime, timezone
from ros.lib.config import ROS_EVENTS_TOPIC
from ros.lib.produce import delivery_report
from ros.lib.utils import cast_iops_as_float
from ros.lib.constants import SystemStatesWithKeys

# Constants for payload processing
DEFAULT_LINKS = {
    "jira": ["https://issues.redhat.com/browse/CEECBA-5875"],
    "kcs": []  # No KCS or doc yet
}

NO_RECOMMENDATION_STATES = ["OPTIMIZED", "NO_PCP_DATA"]
ROS_RULE_PREFIX = "ros_instance_evaluation"
TELEMETRY_COMPONENT = "telemetry.rules.plugins.ros.ros_instance_evaluation.report"


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


def _extract_system_states(report_output):
    """Extract CPU, IO, and memory states from report output."""
    states = report_output.get("states", {})
    return {
        "cpu_states": states.get("cpu"),
        "io_states": states.get("io"),
        "memory_states": states.get("memory")
    }


def _calculate_performance_utilization(report_metadata_output):
    """Calculate performance utilization metrics with max_io."""
    performance_utilization = {
        "memory": report_metadata_output.get("mem_utilization"),
        "cpu": report_metadata_output.get("cpu_utilization"),
        "io": cast_iops_as_float(report_metadata_output.get("io_utilization", {}))
    }

    # Calculate max_io for sorting systems endpoint response
    io_values = performance_utilization.get('io', {}).values()
    performance_utilization['max_io'] = max(io_values) if io_values else 0

    return performance_utilization


def _build_rule_hit_details(error_key, report_output, system_id):
    """Construct rule hit details array matching process_report structure."""
    return [{
        "key": error_key,
        "tags": [],
        "type": "rule",
        "links": DEFAULT_LINKS,
        "details": report_output,
        "rule_id": f"{ROS_RULE_PREFIX}|{error_key}" if error_key else f"{ROS_RULE_PREFIX}|UNKNOWN",
        "component": TELEMETRY_COMPONENT,
        "system_id": system_id
    }]


def _determine_candidates(report_output, error_key):
    """Determine top candidate and price with proper fallbacks."""
    if error_key in NO_RECOMMENDATION_STATES:
        return None, None

    candidates = report_output.get("candidates", [[None, None]])
    if not candidates:
        return None, None

    top_candidate = candidates[0][0] if candidates[0] else None
    top_candidate_price = candidates[0][1] if candidates[0] else None
    return top_candidate, top_candidate_price


def _calculate_recommendations_count(error_key):
    """Calculate number of recommendations using process_report logic."""
    return -1 if error_key == 'NO_PCP_DATA' else 1


def _prepare_performance_record(report_perf_profile):
    """Prepare performance record by removing unnecessary keys."""
    # Remove the 'type' key as it's not required
    report_perf_profile.pop('type', None)
    return report_perf_profile


def perf_profile_and_rule_payload(report_metadata_output, report_output, report_perf_profile):
    """Build performance profile and rules payload for event publishing.

    Args:
        report_metadata_output: Metadata from report processing
        report_output: Main report output with states and recommendations
        report_perf_profile: Performance profile data

    Returns:
        dict: Complete payload for event publishing
    """
    # Extract basic data
    error_key = report_output.get("error_key")
    state = SystemStatesWithKeys[error_key].value if error_key else None
    system_states = _extract_system_states(report_output)

    # Process performance data
    performance_record = _prepare_performance_record(report_perf_profile)
    performance_utilization = _calculate_performance_utilization(report_metadata_output)

    # Build recommendations and rule details
    rule_hit_details = _build_rule_hit_details(error_key, report_output, report_metadata_output.get("system_id"))
    number_of_recommendations = _calculate_recommendations_count(error_key)
    top_candidate, top_candidate_price = _determine_candidates(report_output, error_key)

    # Assemble final payload
    return {
        **system_states,  # cpu_states, io_states, memory_states
        "state": state,
        "instance_type": report_output.get("instance_type"),
        "region": report_output.get("region"),
        "performance_record": performance_record,
        "performance_utilization": performance_utilization,
        "report_date": datetime.now(timezone.utc).isoformat(),
        "rule_hit_details": rule_hit_details,
        "number_of_recommendations": number_of_recommendations,
        "psi_enabled": report_metadata_output.get("psi_enabled"),
        "top_candidate": top_candidate,
        "top_candidate_price": top_candidate_price
    }


def produce_report_processor_event(
    payload,
    producer,
    report_metadata_output=None,
    report_output=None,
    report_perf_profile=None
):
    """
    Unified method to produce report processor events.

    Args:
        payload: The base payload containing metadata and host information
        producer: Kafka producer instance
        report_metadata_output: Optional metadata from report processing (for PCP data)
        report_output: Optional main report output with states and recommendations (for PCP data)
        report_perf_profile: Optional performance profile data (for PCP data)
    """
    request_id = payload.get('metadata').get('request_id')
    host = payload.get('host')

    # Start with the basic tailored payload
    final_payload = api_and_no_pcp_raw_payload(payload)

    # If PCP-related data is provided, enhance the payload with performance and rule data
    if all(param is not None for param in [report_metadata_output, report_output, report_perf_profile]):
        perf_profile_and_rule = perf_profile_and_rule_payload(
            report_metadata_output, report_output, report_perf_profile
        )
        final_payload = {**final_payload, **perf_profile_and_rule}

    # Serialize and send the event
    bytes_ = json.dumps(final_payload).encode('utf-8')
    producer.produce(
        topic=ROS_EVENTS_TOPIC,
        value=bytes_,
        key=host.get('id'),
        on_delivery=lambda err, msg: delivery_report(err, msg, host.get('id'), request_id, ROS_EVENTS_TOPIC)
    )
    producer.poll()
