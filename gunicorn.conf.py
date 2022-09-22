bind = '0.0.0.0:8000'
workers = 2
accesslog = '-'

# Allow HTTP headers upto 16k
# https://issues.redhat.com/browse/RHCLOUD-21245
limit_request_field_size = 16384
