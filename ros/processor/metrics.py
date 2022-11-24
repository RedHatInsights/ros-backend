from prometheus_client import Counter

processor_requests_success = Counter(
    "ros_processor_requests_success",
    "Number of requests for systems processed successfully",
    ["reporter", "org_id"]
)

processor_requests_failures = Counter(
    "ros_processor_requests_failures",
    "Number of failures while processing systems messages",
    ["reporter", "org_id"]
)

kafka_failures = Counter(
    "ros_kafka_failures",
    "Number of kafka failures",
    ["reporter"]
)

archive_downloaded_success = Counter(
    "ros_archive_downloaded_success",
    "Number of archives downloaded successfully",
    ["org_id"]
)

archive_failed_to_download = Counter(
    "ros_archive_failed_to_download",
    "Number of archives that failed to download",
    ["org_id"]
)

ec2_instance_lookup_failures = Counter(
    "failed_to_lookup_ec2_instance_type",
    "Number of AWS EC2 instance type lookup failures",
    ["org_id"]
)
