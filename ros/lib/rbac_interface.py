from base64 import b64decode
from urllib.parse import urljoin
from http import HTTPStatus
from flask_restful import abort
from .config import RBAC_SVC_URL, ENABLE_RBAC, TLS_CA_PATH, ENABLE_KESSEL, KESSEL_SVC_URL
import requests
import json
from ros.lib.config import get_logger
from flask import request

from .kessel import KesselClient, ObjectType, Resource, Allowed

RBAC_SVC_ENDPOINT = "/api/rbac/v1/access/?application=%s"
AUTH_HEADER_NAME = "X-RH-IDENTITY"
VALID_HTTP_VERBS = ["get", "options", "head", "post", "put", "patch", "delete"]
LOG = get_logger(__name__)
host_group_attr = 'host_groups'
access_all_systems = 'able_to_access_all_systems'


def fetch_url(url, auth_header, logger, method="get"):
    """
    Helper to make a single request.
    """
    if method not in VALID_HTTP_VERBS:
        abort(
            HTTPStatus.METHOD_NOT_ALLOWED, message="'%s' is not valid HTTP method." % method
        )
    response = requests.request(
        method, url, headers=auth_header, verify=TLS_CA_PATH)
    _validate_service_response(response, logger, auth_header)
    return response.json()


def _validate_service_response(response, logger, auth_header):
    """
    Raise an exception if the response was not what we expected.
    """
    if response.status_code in [requests.codes.forbidden, requests.codes.unauthorized]:
        logger.info(
            f"{response.status_code} error received from service"
        )
        # Log identity header if 401 (unauthorized)
        if response.status_code == requests.codes.unauthorized:
            if isinstance(auth_header, dict) and AUTH_HEADER_NAME in auth_header:
                logger.info(f"Identity {get_key_from_headers(auth_header)}")
            else:
                logger.info("No identity or no key")
        abort(
            response.status_code, message="Unable to retrieve permissions."
        )
    else:
        if response.status_code == requests.codes.not_found:
            logger.error(f"{response.status_code} error received from service.")
            abort(
                response.status_code, message="The requested URL was not found."
            )
        if response.status_code != requests.codes.ok:
            logger.error(f"{response.status_code} error received from service.")
            abort(
                response.status_code, message="Error received from backend service"
            )


def get_key_from_headers(incoming_headers):
    """
    return auth key from header
    """
    return incoming_headers.get(AUTH_HEADER_NAME)


def query_rbac(application, auth_key, logger):
    """
    check if user has a permission
    """
    auth_header = {AUTH_HEADER_NAME: auth_key}
    rbac_location = urljoin(RBAC_SVC_URL, RBAC_SVC_ENDPOINT) % application
    rbac_result = fetch_url(
        rbac_location, auth_header, logger)
    return rbac_result


def query_kessel(auth_key):
    token = json.loads(b64decode(auth_key).decode("utf-8"))
    username = token.get("identity", {}).get("user", {}).get("username")
    client = KesselClient(KESSEL_SVC_URL)

    ros_read_analysis = client.default_workspace_check("ros_read_analysis", Resource.principal(username))

    if ros_read_analysis is Allowed.TRUE:
        workspaces = [w.resource_id for w in client.get_resources(ObjectType.workspace(), "inventory_host_view", Resource.principal(username))]
    else:
        workspaces = []

    return {
        "ros_can_read": ros_read_analysis,
        "host_groups": set(workspaces)
    }


def ensure_has_permission(**kwargs):
    """
    Ensure permission exists. kwargs needs to contain:
    permissions, application, app_name, request, logger
    """

    if not ENABLE_RBAC and not ENABLE_KESSEL:
        return

    auth_key = request.headers.get('X-RH-IDENTITY')

    if _is_mgmt_url(request.path):
        return  # allow request

    if not auth_key:
        abort(
            HTTPStatus.BAD_REQUEST, message="Identity not found in request"
        )

    if ENABLE_RBAC:
        rbac_response = query_rbac(kwargs["application"], auth_key, kwargs["logger"])
        perms = [perm["permission"] for perm in rbac_response["data"]]
        if perms:
            for p in perms:
                if p in kwargs["permissions"]:
                    # Allow access and
                    # Try to set group details on request if any
                    try:
                        set_host_groups(rbac_response)
                    except Exception as err:
                        LOG.info(f"Failed to fetch group details {err}")
                    return
        # if wrong permissions
        abort(
            HTTPStatus.FORBIDDEN,
            message='User does not have correct permissions to access the service'
        )

    if ENABLE_KESSEL:
        kessel_response = query_kessel(auth_key)
        if kessel_response["host_groups"]:
            host_groups = kessel_response["host_groups"]
            setattr(request, host_group_attr, host_groups)
            LOG.info(f"User has host groups {host_groups}")
        else:
            abort(
                HTTPStatus.FORBIDDEN,
                message='User does not have correct permissions to access the service'
            )

        # Set admin to false - Kessel will return exactly the workspaces we have access to
        setattr(request, access_all_systems, False)


def _is_mgmt_url(path):
    """
    Small helper to test if URL is for management API.
    """
    return path.startswith("/mgmt/")


def set_host_groups(rbac_response):
    """
    We now also have to store the host group information we get from inventory.
    This comes in the resource definition within the RBAC response:

    {
      "resourceDefinitions": [
        {
          "attributeFilter": {
            "key": "group.id",
            "value": [
              "group 1",
              "group 2"
            ],
            "operation": "in"
          }
        }
      ],
      "permission": "inventory:hosts:read"
    }

    If the permission is 'inventory:hosts:read', we find one of the resource
    definitions that has an attribute filter key of 'group.id', and
    we get the list of inventory groups from its value. We currently ignore
    the operation value.
    """

    if rbac_response is None:
        return  # we can't store any host groups on None

    if 'data' not in rbac_response:
        LOG.info("Warning: The response from RBAC does not contain 'data' list to fetch group details")
        return

    role_list = rbac_response['data']
    host_groups = set()
    able_to_access_all_systems = False
    for role in role_list:
        if 'permission' not in role:
            continue
        if role['permission'] not in ['inventory:hosts:read', 'inventory:hosts:*', 'inventory:*:read', 'inventory:*:*']:
            continue

        # ignore the failure modes, try moving on to other roles that
        # also match this permission
        if 'resourceDefinitions' not in role:
            continue
        if not isinstance(role['resourceDefinitions'], list):
            continue

        if len(role['resourceDefinitions']) == 0 and role['permission'] in ['inventory:hosts:*', 'inventory:hosts:read',
                                                                            'inventory:*:*', 'inventory:*:read']:
            able_to_access_all_systems = True
            # If user is inventory or hosts admin then we break the loop and don't check for next roles
            break

        for rscdef in role['resourceDefinitions']:
            if not isinstance(rscdef, dict):
                continue
            if 'attributeFilter' not in rscdef:
                continue
            attrfilter = rscdef['attributeFilter']
            if not isinstance(attrfilter, dict):
                continue
            if 'key' not in attrfilter and 'value' not in attrfilter:
                continue
            if attrfilter['key'] != 'group.id':
                continue
            value = attrfilter['value']
            # Early versions of the spec say the value is a list; later
            # versions say it's a string with a JSON-encoded list.  Let's try
            # to cope with the latter by converting it into the former.
            if isinstance(value, str) and value[0] == '[' and value[-1] == ']':
                value = json.loads(value)
            if not isinstance(value, list):
                continue
            # Finally, we have the right key: add them to our list
            # The host_groups may have duplicate group_ids
            host_groups.update(value)

    # If we found any host groups at the end of that, store them
    if host_groups:
        setattr(request, host_group_attr, host_groups)
        LOG.info(f"User has host groups {host_groups}")

    # Set admin even if we don't find it true
    setattr(request, access_all_systems, able_to_access_all_systems)
