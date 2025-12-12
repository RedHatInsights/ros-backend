import json
from datetime import datetime, timezone
from ros.lib.config import ROS_EVENTS_TOPIC
from ros.lib.produce import delivery_report
from ros.lib.utils import cast_iops_as_float
from ros.lib.constants import SystemStatesWithKeys
from ros.rules.rules_engine import cloud_metadata, report_metadata

# Constants for payload processing
DEFAULT_LINKS = {
    "jira": ["https://issues.redhat.com/browse/CEECBA-5875"],
    "kcs": []  # No KCS or doc yet
}

NO_RECOMMENDATION_STATES = ["OPTIMIZED", "NO_PCP_DATA"]
ROS_RULE_PREFIX = "ros_instance_evaluation"
TELEMETRY_COMPONENT = "telemetry.rules.plugins.ros.ros_instance_evaluation.report"
TELEMETRY_COMPONENT_NO_DATA = "telemetry.rules.plugins.ros.ros_instance_evaluation.report_no_data"


def _build_base_payload(payload):
    """Build base payload with system information.

    This creates the common base payload structure used for all event types.
    Performance profile data is added separately based on the scenario.

    Args:
        payload: The original payload with host information

    Returns:
        dict: Base payload with system information (None values removed)
    """
    host = payload.get('host')

    base_payload = {
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

    # Remove None values
    return {key: value for key, value in base_payload.items() if value is not None}


def _extract_system_states(report_output):
    """Extract CPU, IO, and memory states from report output."""
    states = report_output.get("states", {})
    return {
        "cpu_states": states.get("cpu"),
        "io_states": states.get("io"),
        "memory_states": states.get("memory")
    }


def _calculate_performance_utilization(report_metadata_output, error_key=None):
    """Calculate performance utilization metrics with max_io.

    Matches insights_engine_consumer.py behavior (lines 194-216):
    - NO_PCP_DATA: returns default values (-1, -1, -1.0, {})
    - Other states: uses real values from metadata
    - Converts cpu and memory to integers (not strings)
    """
    # For NO_PCP_DATA state, return default utilization values
    # This matches insights_engine_consumer.py lines 196-216
    if error_key == 'NO_PCP_DATA':
        return {
            "memory": -1,
            "cpu": -1,
            "max_io": -1.0,
            "io": {}
        }

    # For other states, use real utilization values from metadata
    performance_utilization = {
        "memory": int(report_metadata_output.get("mem_utilization")),
        "cpu": int(report_metadata_output.get("cpu_utilization")),
        "io": cast_iops_as_float(report_metadata_output.get("io_utilization", {}))
    }

    # Calculate max_io for sorting systems endpoint response
    io_values = performance_utilization.get('io', {}).values()
    performance_utilization['max_io'] = max(io_values) if io_values else 0

    return performance_utilization


def _build_rule_hit_details(error_key, report_output, system_id):
    """Construct rule hit details array matching process_report structure.

    Matches insights_engine_consumer.py behavior (line 227):
    - OPTIMIZED: returns empty array [] (no reports)
    - NO_PCP_DATA: returns array with the report (reports[0] exists)
    - Other states: returns array with the report
    - Skipped/invalid reports: returns empty array []
    """
    # For OPTIMIZED state or when there are no valid recommendations, return empty array
    if error_key is None or error_key == "OPTIMIZED":
        return []

    # Check if report is skipped/invalid (no valid recommendations)
    details = report_output.get("details", {})
    if isinstance(details, dict) and details.get("type") == "skip":
        return []

    # For NO_PCP_DATA and other states, include the report in rule_hit_details
    # This matches insights_engine_consumer.py line 227: "rule_hit_details": reports
    # Use different component name for NO_PCP_DATA to match expected format
    component = TELEMETRY_COMPONENT_NO_DATA if error_key == 'NO_PCP_DATA' else TELEMETRY_COMPONENT

    return [{
        "key": error_key,
        "tags": [],
        "type": "rule",
        "links": DEFAULT_LINKS,
        "details": report_output,
        "rule_id": f"{ROS_RULE_PREFIX}|{error_key}" if error_key else f"{ROS_RULE_PREFIX}|UNKNOWN",
        "component": component,
        "system_id": system_id
    }]


def _determine_candidates(report_output, error_key):
    """Determine top candidate and price with proper fallbacks."""
    # For OPTIMIZED state or when error_key is None, return None (no recommendations)
    if error_key is None or error_key in NO_RECOMMENDATION_STATES:
        return None, None

    candidates = report_output.get("candidates", [[None, None]])
    if not candidates:
        return None, None

    top_candidate = candidates[0][0] if candidates[0] else None
    top_candidate_price = candidates[0][1] if candidates[0] else None
    return top_candidate, top_candidate_price


def _calculate_recommendations_count(error_key):
    """Calculate number of recommendations using process_report logic.

    Matches insights_engine_consumer.py behavior:
    - NO_PCP_DATA: -1 (unknown)
    - OPTIMIZED or None: 0 (no recommendations)
    - Other states: 1 (or len(reports) in insights_engine_consumer, but here we have single report)
    """
    if error_key == 'NO_PCP_DATA':
        return -1
    elif error_key is None or error_key == 'OPTIMIZED':
        return 0
    else:
        return 1


def _prepare_performance_record(report_perf_profile):
    """Prepare performance record by removing unnecessary keys.

    Matches insights_engine_consumer.py behavior exactly:
    - get_performance_profile() already removes 'type' key (process_archive.py line 69)
    - Then process_report() removes 'instance_type' and 'region' (insights_engine_consumer.py lines 218-219)
    - Note: process_archive.py's performance_profile does NOT include 'cloud_provider',
      but rules_engine.py's performance_profile_rule does, so we remove it here to match
    """
    performance_record = report_perf_profile.copy()
    keys_to_remove = ['instance_type', 'region', 'cloud_provider', 'type']
    for key in keys_to_remove:
        if key in performance_record:
            del performance_record[key]
    return performance_record


def _create_no_pcp_data_mock(payload, report_metadata_output=None, cloud_metadata_obj=None):
    """Create mock NO_PCP_DATA structure matching insights_engine_consumer.py behavior.

    This is used when is_pcp_raw_data_collected=False and no PCP data is available.
    Matches the structure shown in no-pcp-data-diff for insights_engine_consumer.py.

    Args:
        payload: The original payload with host information
        report_metadata_output: Optional metadata from report_metadata rule (extracted from archive)
        cloud_metadata_obj: Optional cloud_metadata object from rules engine (for instance_type/region)

    Returns:
        tuple: (report_metadata_output, report_output, report_perf_profile) mock data
    """
    host = payload.get('host')
    system_profile = host.get('system_profile', {})
    operating_system = system_profile.get('operating_system', {})

    # Extract instance_type and region from cloud_metadata_obj if available (from archive),
    # otherwise try system_profile
    instance_type = None
    region = None
    cloud_provider = None

    if cloud_metadata_obj:
        # Use cloud_metadata from archive extraction (most reliable)
        instance_type = cloud_metadata_obj.type
        region = cloud_metadata_obj.region
        cloud_provider = cloud_metadata_obj.provider
    else:
        # Fallback to system_profile if cloud_metadata not available
        cloud_meta = system_profile.get('cloud_metadata', {})
        instance_type = (system_profile.get('instance_type') or
                         cloud_meta.get('instance_type'))
        region = (system_profile.get('region') or
                  cloud_meta.get('region'))
        cloud_provider = system_profile.get('cloud_provider')

    # Use report_metadata_output if provided, otherwise create minimal mock
    if report_metadata_output:
        # Use actual metadata from archive extraction
        # report_metadata_output is a metadata object from insights framework (dict-like)
        if isinstance(report_metadata_output, dict):
            metadata_output = report_metadata_output.copy()
        else:
            # Convert to dict if it's a metadata object
            metadata_output = dict(report_metadata_output) if hasattr(report_metadata_output, '__iter__') else {}
        # Ensure system_id is set
        if 'system_id' not in metadata_output:
            metadata_output['system_id'] = host.get('id')
    else:
        # Create minimal mock metadata
        metadata_output = {
            "system_id": host.get('id'),
            "psi_enabled": False,
            # No utilization data available for NO_PCP_DATA
        }
        if cloud_provider:
            metadata_output['cloud_provider'] = cloud_provider

    # Build RHEL version string if available
    rhel_version = None
    if operating_system.get('name') == 'RHEL':
        major = operating_system.get('major')
        minor = operating_system.get('minor')
        if major is not None:
            rhel_version = f"{major}.{minor}" if minor is not None else str(major)

    # Mock report_output for NO_PCP_DATA
    report_output = {
        "error_key": "NO_PCP_DATA",
        "instance_type": instance_type,
        "region": region,
        "states": {},
        "details": {
            "rhel": rhel_version,
            "type": "rule",
            "error_key": "NO_PCP_DATA",
            "instance_type": instance_type,
            "cloud_provider": cloud_provider
        }
    }

    # Mock report_perf_profile - minimal performance record
    # insights_engine_consumer.py shows performance_record as {"total_cpus": 2}
    # We'll use minimal data since we don't have PCP data
    report_perf_profile = {
        "instance_type": instance_type,
        "region": region,
        "cloud_provider": cloud_provider
    }

    return metadata_output, report_output, report_perf_profile


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

    # Check if report is skipped/invalid (no valid recommendations)
    # This indicates OPTIMIZED state - no recommendations available
    details = report_output.get("details", {})
    is_skipped_report = isinstance(details, dict) and details.get("type") == "skip"

    # If error_key is None or report is skipped, treat as OPTIMIZED
    if error_key is None or is_skipped_report:
        error_key = "OPTIMIZED"

    state = SystemStatesWithKeys[error_key].value if error_key else None
    system_states = _extract_system_states(report_output)

    # Process performance data
    performance_record = _prepare_performance_record(report_perf_profile)
    performance_utilization = _calculate_performance_utilization(report_metadata_output, error_key)

    # Build recommendations and rule details
    rule_hit_details = _build_rule_hit_details(error_key, report_output, report_metadata_output.get("system_id"))
    number_of_recommendations = _calculate_recommendations_count(error_key)
    top_candidate, top_candidate_price = _determine_candidates(report_output, error_key)

    # Extract instance_type and region, with fallback to performance_record
    # This matches insights_engine_consumer.py behavior where these come from performance_record
    instance_type = report_output.get("instance_type") or report_perf_profile.get("instance_type")
    region = report_output.get("region") or report_perf_profile.get("region")

    # Assemble final payload
    return {
        **system_states,  # cpu_states, io_states, memory_states
        "state": state,
        "instance_type": instance_type,
        "region": region,
        "performance_record": performance_record,
        "performance_utilization": performance_utilization,
        "report_date": datetime.now(timezone.utc).isoformat(),
        "rule_hit_details": rule_hit_details,
        "number_of_recommendations": number_of_recommendations,
        "psi_enabled": report_metadata_output.get("psi_enabled"),
        "top_candidate": top_candidate,
        "top_candidate_price": top_candidate_price
    }


def _extract_from_rules_runner(rules_runner, report_metadata_output=None):
    """Extract report_metadata_output and cloud_metadata from rules_runner.

    Args:
        rules_runner: Rules runner result dictionary
        report_metadata_output: Optional existing report_metadata_output to use as fallback

    Returns:
        tuple: (report_metadata_output, cloud_metadata_obj)
    """
    extracted_report_metadata_output = report_metadata_output
    cloud_metadata_obj = None

    if rules_runner is not None:
        # Extract report_metadata_output from rules_runner
        try:
            extracted_report_metadata_output = rules_runner.get(report_metadata)
        except (KeyError, AttributeError):
            # report_metadata might not be available
            pass

        # Extract cloud_metadata from rules_runner
        # cloud_metadata is a condition used by report_metadata, so it's available in the runner
        try:
            cloud_metadata_obj = rules_runner.get(cloud_metadata)
        except (KeyError, AttributeError):
            # cloud_metadata might not be available if archive doesn't have cloud instance info
            pass

    return extracted_report_metadata_output, cloud_metadata_obj


def _build_pcp_data_payload(report_metadata_output, report_output, report_perf_profile):
    """Build payload for events with PCP data.

    Args:
        report_metadata_output: Metadata from report processing
        report_output: Main report output with states and recommendations
        report_perf_profile: Performance profile data

    Returns:
        dict: Performance profile and rules payload
    """
    return perf_profile_and_rule_payload(
        report_metadata_output, report_output, report_perf_profile
    )


def _build_no_pcp_data_payload(payload, rules_runner=None, report_metadata_output=None):
    """Build payload for events without PCP data (NO_PCP_DATA state).

    Args:
        payload: The original payload with host information
        rules_runner: Optional rules runner result dictionary (from archive extraction)
        report_metadata_output: Optional metadata from report processing

    Returns:
        dict: Performance profile and rules payload for NO_PCP_DATA
    """
    # Extract report_metadata_output and cloud_metadata from rules_runner if available
    extracted_report_metadata_output, cloud_metadata_obj = _extract_from_rules_runner(
        rules_runner, report_metadata_output
    )

    # Create NO_PCP_DATA mock data
    mock_metadata, mock_output, mock_perf = _create_no_pcp_data_mock(
        payload,
        report_metadata_output=extracted_report_metadata_output,
        cloud_metadata_obj=cloud_metadata_obj
    )

    # Build the payload
    return perf_profile_and_rule_payload(mock_metadata, mock_output, mock_perf)


def _send_event(producer, final_payload, host_id, request_id):
    """Serialize and send the event to Kafka.

    Args:
        producer: Kafka producer instance
        final_payload: Complete payload to send
        host_id: Host inventory ID for the message key
        request_id: Request ID for logging
    """
    bytes_ = json.dumps(final_payload).encode('utf-8')
    producer.produce(
        topic=ROS_EVENTS_TOPIC,
        value=bytes_,
        key=host_id,
        on_delivery=lambda err, msg: delivery_report(err, msg, host_id, request_id, ROS_EVENTS_TOPIC)
    )
    producer.poll()


def produce_report_processor_event(
    payload,
    producer,
    is_pcp_raw_data_collected=False,
    report_metadata_output=None,
    report_output=None,
    report_perf_profile=None,
    is_api_call=False,
    rules_runner=None
):
    """
    Unified method to produce report processor events.

    Handles three scenarios:
    1. With PCP data: Uses provided report data to build complete payload
    2. NO PCP data (not API call): Extracts from rules_runner, creates NO_PCP_DATA mock
    3. API call: Only System fields, no PerformanceProfile

    Args:
        payload: The base payload containing metadata and host information
        producer: Kafka producer instance
        is_pcp_raw_data_collected: Whether PCP data was collected (False means no PCP data available)
        report_metadata_output: Optional metadata from report processing (for PCP data)
        report_output: Optional main report output with states and recommendations (for PCP data)
        report_perf_profile: Optional performance profile data (for PCP data)
        is_api_call: If True, this is an API update - only update System, no PerformanceProfile
        rules_runner: Optional rules runner result dictionary (for extracting data when NO_PCP_DATA)
    """
    request_id = payload.get('metadata').get('request_id')
    host = payload.get('host')
    host_id = host.get('id')

    # Start with the base payload
    final_payload = _build_base_payload(payload)

    # Determine scenario and build appropriate payload
    has_pcp_data = all(param is not None for param in [report_metadata_output, report_output, report_perf_profile])

    if has_pcp_data:
        # Scenario 1: With PCP data - use provided report data
        perf_profile_payload = _build_pcp_data_payload(
            report_metadata_output, report_output, report_perf_profile
        )
        final_payload = {**final_payload, **perf_profile_payload}
    elif not is_pcp_raw_data_collected and not is_api_call:
        # Scenario 2: NO PCP data (not API call) - create NO_PCP_DATA mock
        perf_profile_payload = _build_no_pcp_data_payload(
            payload, rules_runner=rules_runner, report_metadata_output=report_metadata_output
        )
        final_payload = {**final_payload, **perf_profile_payload}
    # Scenario 3: API call - only System fields, no PerformanceProfile (final_payload already has base fields)

    # Send the event
    _send_event(producer, final_payload, host_id, request_id)
