from prometheus_client import Counter

add_host_success = Counter(
    "ros_add_host_success", "Total amount of successfully added hosts", ["reporter"]
)
add_host_failure = Counter(
    "ros_add_host_failure", "Total amount of failures adding hosts", ["reporter"]
)
