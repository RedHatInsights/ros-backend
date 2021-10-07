from prometheus_client import Counter

processor_requests_success = Counter(
    "ros_processor_requests_success",
    "Total number of requests for systems processed successfully",
    ["reporter", "account_number"]
)

processor_requests_failures = Counter(
    "ros_processor_requests_failures",
    "Total number of failures while processing systems messages",
    ["reporter", "account_number"]
)

kafka_failures = Counter(
    "ros_kafka_failures",
    "Total number of kafka failures while processing messages",
    ["reporter", "account_number"]
)

archive_downloaded_success = Counter(
    "ros_archive_downloaded_success",
    "Total number of archive downloaded successfully",
    ["account_number"]
)

archive_failed_to_download = Counter(
    "ros_archive_failed_to_download",
    "Total number of archives that failed to download",
    ["account_number"]
)
