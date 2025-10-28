import json
from base64 import b64decode
from ros.lib.config import KESSEL_URL
from ros.lib.config import get_logger

from ros.lib.kessel.kessel_client import KesselClient
from ros.lib.kessel.dataclasses_and_enum import ObjectType, Resource, UserAllowed

LOG = get_logger(__name__)


def query_kessel(auth_key):
    try:
        token = json.loads(b64decode(auth_key).decode("utf-8"))
    except json.decoder.JSONDecodeError:
        LOG.error("Unable to decode the auth_key")
        return {"ros_can_read": UserAllowed.FALSE, "host_groups": set()}

    identity = token.get("identity", {})
    user_id = None
    identity_type = identity.get('type')

    if identity_type == 'ServiceAccount':
        user_id = identity.get("service_account", {}).get("user_id")
    elif identity_type == 'User':
        user_id = identity.get("user", {}).get("user_id")
    else:
        LOG.error(f"Unsupported identity type: {identity_type}")
        return {"ros_can_read": UserAllowed.FALSE, "host_groups": set()}

    if not user_id:
        LOG.error("user_id not found in identity")
        return {"ros_can_read": UserAllowed.FALSE, "host_groups": set()}

    org_id = identity.get("org_id")
    if not org_id:
        LOG.error("org_id not found in identity")
        return {"ros_can_read": UserAllowed.FALSE, "host_groups": set()}

    # Initialize KesselClient with org_id for workspace-based authentication
    client = KesselClient(KESSEL_URL, org_id=org_id)
    workspaces = []

    try:
        workspaces = [
            w.resource_id for w in client.get_resources(
                ObjectType.workspace(),
                "ros_read_analysis",
                Resource.principal(user_id)
            )
        ]
    except Exception as err:
        LOG.info(f"Failed to fetch the workspaces {err}")

    return {
        "ros_can_read": len(workspaces) > 0,
        "host_groups": set(workspaces)
    }
