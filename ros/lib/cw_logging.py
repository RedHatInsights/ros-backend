"""
This module helps with streaming app logs to AWS CloudWatch.
The logs are then sent to Kibana through an in-place AWS Lambda function.
Reference: https://consoledot.pages.redhat.com/docs/dev/platform-documentation/tools/logging.html
"""

import watchtower
from boto3.session import Session
from botocore.exceptions import ClientError

from ros.lib.config import (
    get_logger,
    CW_ENABLED,
)

if CW_ENABLED is True:
    from ros.lib.config import (
        AWS_ACCESS_KEY_ID,
        AWS_SECRET_ACCESS_KEY,
        AWS_REGION_NAME,
        AWS_LOG_GROUP
    )


module_prefix = 'CLOUDWATCH LOGGING'


def commence_cw_log_streaming(stream_name):
    logger = get_logger(__name__)
    key_id = AWS_ACCESS_KEY_ID
    secret_key = AWS_SECRET_ACCESS_KEY
    region_name = AWS_REGION_NAME
    log_group = AWS_LOG_GROUP

    if CW_ENABLED is False:
        logger.warning(f"{module_prefix} - Disabled")
        return

    if all((key_id, secret_key, region_name, log_group)) is False:
        logger.error(f"{module_prefix} - Insufficient secret values")
        return

    try:
        boto3_session = Session(
            aws_access_key_id=key_id,
            aws_secret_access_key=secret_key,
            region_name=region_name
        )

        watchtower_handler = watchtower.CloudWatchLogHandler(
            boto3_session=boto3_session,
            log_group=log_group,
            stream_name=stream_name
        )
    except ClientError as e:
        logger.exception(f"{module_prefix} - Failed; error: {e}")
    else:
        logger.addHandler(watchtower_handler)
        logger.info(f"{module_prefix} - Streaming in-progress")
