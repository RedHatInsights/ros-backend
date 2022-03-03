"""
This module helps with streaming app logs to AWS CloudWatch.
The logs are then sent to Kibana through an in-place AWS Lambda function.
Reference: https://consoledot.pages.redhat.com/docs/dev/platform-documentation/tools/logging.html
"""
import logging

import boto3
import watchtower
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
        AWS_LOG_GROUP,
        CW_LOGGING_FORMAT,
    )


module_prefix = 'CLOUDWATCH LOGGING'


def commence_cw_log_streaming(stream_name):
    logger = get_logger(__name__)
    root_logger = logging.getLogger()

    if CW_ENABLED is False:
        logger.warning(f"{module_prefix} - Disabled")
        return

    if all((AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION_NAME, AWS_LOG_GROUP)) is False:
        logger.error(f"{module_prefix} - Insufficient constant values")
        return

    try:
        boto3_client = boto3.client(
            'logs',
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION_NAME
        )

        watchtower_handler = watchtower.CloudWatchLogHandler(
            boto3_client=boto3_client,
            log_group=AWS_LOG_GROUP,
            stream_name=stream_name
        )
    except ClientError as e:
        logger.exception(f"{module_prefix} - Failed; error: {e}")
    else:
        logger.info(f"{module_prefix} - Streaming in progress - Log group: {AWS_LOG_GROUP}")
        watchtower_handler.setLevel(logging.INFO)
        watchtower_handler.setFormatter(logging.Formatter(fmt=CW_LOGGING_FORMAT))
        root_logger.addHandler(watchtower_handler)
