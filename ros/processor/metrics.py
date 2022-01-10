from prometheus_client import Counter

processor_requests_success = Counter(
    "ros_processor_requests_success",
    "Number of requests for systems processed successfully",
    ["reporter", "account_number"]
)

processor_requests_failures = Counter(
    "ros_processor_requests_failures",
    "Number of failures while processing systems messages",
    ["reporter", "account_number"]
)

kafka_failures = Counter(
    "ros_kafka_failures",
    "Number of kafka failures",
    ["reporter"]
)

archive_downloaded_success = Counter(
    "ros_archive_downloaded_success",
    "Number of archives downloaded successfully",
    ["account_number"]
)

archive_failed_to_download = Counter(
    "ros_archive_failed_to_download",
    "Number of archives that failed to download",
    ["account_number"]
)
