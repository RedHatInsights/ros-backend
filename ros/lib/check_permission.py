from http import HTTPStatus
from flask_restful import abort
from .config import ENABLE_RBAC, ENABLE_KESSEL
import json
from ros.lib.config import get_logger
from flask import request
from ros.lib.rbac_interface import query_rbac
from ros.lib.kessel.kessel_interface import query_kessel

AUTH_HEADER_NAME = "X-RH-IDENTITY"
LOG = get_logger(__name__)
host_group_attr = 'host_groups'
access_all_systems = 'able_to_access_all_systems'


def check_permission(**kwargs):
    """
    Ensure permission exists. kwargs needs to contain:
    permissions, application, app_name, request, logger
    """

    if not ENABLE_RBAC and not ENABLE_KESSEL:
        return

    auth_key = request.headers.get(AUTH_HEADER_NAME)

    if _is_mgmt_url(request.path):
        return  # allow request

    if not auth_key:
        abort(
            HTTPStatus.BAD_REQUEST, message="Identity not found in request"
        )

    if ENABLE_RBAC:
        rbac_response = query_rbac(kwargs["application"], auth_key, kwargs["logger"])
        perms = [perm["permission"] for perm in rbac_response.get("data")]
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

    if ENABLE_KESSEL and not ENABLE_RBAC:
        kessel_response = query_kessel(auth_key)
        if kessel_response["host_groups"]:
            host_groups = kessel_response["host_groups"]
            setattr(request, host_group_attr, host_groups)
            LOG.info(f"Kessel Enabled - User has host groups {host_groups}")
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
        LOG.warning("Warning: The response from RBAC does not contain 'data' list to fetch group details")
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
            if 'key' not in attrfilter or 'value' not in attrfilter:
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
