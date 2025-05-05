import json
from base64 import b64decode
from ros.lib.config import KESSEL_SVC_URL
from ros.lib.config import get_logger

from ros.lib.kessel.kessel_client import KesselClient
from ros.lib.kessel.dataclasses_and_enum import ObjectType, Resource, UserAllowed

LOG = get_logger(__name__)


def query_kessel(auth_key):
    try:
        token = json.loads(b64decode(auth_key).decode("utf-8"))
    except json.decoder.JSONDecodeError:
        LOG.error("Unable to decode the auth_key")
    user_id = token.get("identity", {}).get("user", {}).get("user_id")
    client = KesselClient(KESSEL_SVC_URL)

    ros_read_analysis = client.default_workspace_check("ros_read_analysis", Resource.principal(user_id))

    if ros_read_analysis is UserAllowed.TRUE:
        try:
            workspaces = [w.resource_id for w in client.get_resources(ObjectType.workspace(),
                                                                      "inventory_host_view",
                                                                      Resource.principal(user_id))]
        except Exception as err:
            LOG.info(f"Failed to fetch the workspaces {err}")
    else:
        workspaces = []

    return {
        "ros_can_read": ros_read_analysis,
        "host_groups": set(workspaces)
    }
