"""
This module helps with streaming app logs to AWS CloudWatch.
The logs are then sent to Kibana through an in-place AWS Lambda function.
Reference: https://consoledot.pages.redhat.com/docs/dev/platform-documentation/tools/logging.html
"""

import watchtower
from boto3 import Session
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

    if CW_ENABLED is False:
        logger.warning(f"{module_prefix} - Disabled")
        return

    if all((AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION_NAME, AWS_LOG_GROUP)) is False:
        logger.error(f"{module_prefix} - Insufficient constant values")
        return

    try:
        boto3_session = Session(
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION_NAME
        )

        watchtower_handler = watchtower.CloudWatchLogHandler(
            boto3_client=boto3_session,
            log_group=AWS_LOG_GROUP,
            stream_name=stream_name
        )
    except ClientError as e:
        logger.exception(f"{module_prefix} - Failed; error: {e}")
    else:
        logger.addHandler(watchtower_handler)
        logger.info(f"{module_prefix} - Streaming in-progress")
