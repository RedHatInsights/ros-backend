from ros.utils import redhatcloud, sources
from ros.lib.config import get_logger, SOURCES_ROS_AUTHTYPES, SOURCES_RESOURCE_TYPE
from ros.lib.utils import get_or_create
from ros.lib.app import app, db
from ros.lib.models import CloudAccount, RhAccount

LOG = get_logger(__name__)


def create_from_sources_kafka_message(message, headers):
    """
    Create our model objects from the Sources Kafka message.

    Because the Sources API may not always be available, this task must
    gracefully retry if communication with Sources fails unexpectedly.

    If this function succeeds, it spawns another async task to set up the
    customer's AWS account (configure_customer_aws_and_create_cloud_account).

    Args:
        message (dict): the "value" attribute of a message from a Kafka
            topic generated by the Sources service and having event type
            "ApplicationAuthentication.create"
        headers (list): the headers of a message from a Kafka topic
            generated by the Sources service and having event type
            "ApplicationAuthentication.create"

    """
    authentication_id = message.get("authentication_id", None)
    application_id = message.get("application_id", None)
    account_number, org_id = redhatcloud.extract_ids_from_kafka_message(message, headers)

    if (account_number is None and org_id is None) or authentication_id is None or application_id is None:
        LOG.error("Aborting creation. Incorrect message details.")
        return

    application, authentication = _get_and_verify_sources_data(
        account_number, application_id, authentication_id
    )
    if application is None or authentication is None:
        return

    authtype = authentication.get("authtype")
    if authtype not in SOURCES_ROS_AUTHTYPES:
        LOG.error(f"Invalid authtype {authtype}")
        return

    resource_type = authentication.get("resource_type")
    resource_id = authentication.get("resource_id")
    if resource_type != SOURCES_RESOURCE_TYPE:
        LOG.error(f"Resource_type should be {SOURCES_RESOURCE_TYPE}"
                  f"but found {resource_type} with ID {resource_id}")
        return

    source_id = application.get("source_id")
    source_type = sources.get_source_type(account_number, source_id)
    authentication_token = authentication.get("username") or authentication.get(
        "password"
    )

    if not authentication_token:
        LOG.error("Authentication token not found")
        return

    with app.app_context():
        ros_account = get_or_create(
                        db.session, RhAccount, 'account',
                        account=account_number,
                        org_id=org_id
                    )
        if source_type == 'amazon':
            get_or_create(
                db.session, CloudAccount, ['ros_account_id', 'platform_application_id'],
                ros_account_id=ros_account.id,
                platform_authentication_id=authentication_id,
                platform_application_id=application_id,
                platform_source_id=source_id,
                platform_source_type=source_type
            )
        db.session.commit()


def _get_and_verify_sources_data(account_number, application_id, authentication_id):
    """
    Call the sources API and look up the object IDs we were given.

    Args:
        account_number (str): User account number.
        application_id (int): The application object id.
        authentication_id (int): the authentication object id.

    Returns:
        (dict, dict): application and authentication dicts if present and valid,
            otherwise None.
    """
    application = sources.get_application(account_number, application_id)
    if not application:
        LOG.info(
                "Application ID {application_id} for account number "
                "{account_number} does not exist; aborting cloud account creation."
        )
        return None, None

    application_type = application["application_type_id"]
    if application_type is not sources.get_ros_application_type_id(
        account_number
    ):
        LOG.info("Aborting creation. Application Type is not ros.")
        return None, None

    authentication = sources.get_authentication(account_number, authentication_id)
    if not authentication:
        LOG.error("Aborting creation. Error in getting authentication object.")
        return application, None
    return application, authentication
