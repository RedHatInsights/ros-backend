from urllib.parse import urljoin
from http import HTTPStatus
from flask_restful import abort
from .config import RBAC_SVC_URL, PATH_PREFIX
from .rbac_denied_exception import RBACDenied
import requests


RBAC_SVC_ENDPOINT = "/api/rbac/v1/access/?application=%s"
AUTH_HEADER_NAME = "X-RH-IDENTITY"
VALID_HTTP_VERBS = ["get", "options", "head", "post", "put", "patch", "delete"]


def fetch_url(url, auth_header, logger, method="get"):
    """
    Helper to make a single request.
    """
    if method not in VALID_HTTP_VERBS:
        abort(
            HTTPStatus.METHOD_NOT_ALLOWED, message="'%s' is not valid HTTP method." % method
        )
    response = requests.request(method, url, headers=auth_header)
    _validate_service_response(response, logger, auth_header)
    return response.json()


def _validate_service_response(response, logger, auth_header):
    """
    Raise an exception if the response was not what we expected.
    """
    if response.status_code in [requests.codes.forbidden, requests.codes.unauthorized]:
        logger.info(
            "%s error received from service" % response.status_code
        )
        # Log identity header if 401 (unauthorized)
        if response.status_code == requests.codes.unauthorized:
            if isinstance(auth_header, dict) and AUTH_HEADER_NAME in auth_header:
                logger.info("identity '%s'" % get_key_from_headers(auth_header))
            else:
                logger.info("no identity or no key")
        abort(
            response.status_code, message="Unable to retrieve permissions."
        )
    else:
        if response.status_code == requests.codes.not_found:
            logger.error("%s error received from service." % response.status_code)
            abort(
                response.status_code, message="Not Found"  # find a better msg for 404
            )
        if response.status_code != requests.codes.ok:
            logger.error("%s error received from service." % response.status_code)
            abort(
                response.status_code, message="error received from backend service"
            )


def get_key_from_headers(incoming_headers):
    """
    return auth key from header
    """
    return incoming_headers.get(AUTH_HEADER_NAME)


def get_perms(application, auth_key, logger):
    """
    check if user has a permission
    """

    auth_header = {AUTH_HEADER_NAME: auth_key}

    rbac_location = urljoin(RBAC_SVC_URL, RBAC_SVC_ENDPOINT) % application

    rbac_result = fetch_url(
        rbac_location, auth_header, logger)
    perms = [perm["permission"] for perm in rbac_result["data"]]

    return perms


def ensure_has_permission(**kwargs):
    """
    Ensure permission exists. kwargs needs to contain:
    permissions, application, app_name, request, logger
    """

    rbac_enabled = True
    request = kwargs["request"]
    auth_key = request.headers.get('X-RH-IDENTITY')

    if not rbac_enabled:
        return

    if _is_mgmt_url(request.path) or _is_openapi_url(request.path, kwargs["app_name"]):
        return  # allow request
    if auth_key:
        try:
            perms = get_perms(
                kwargs["application"],
                auth_key,
                kwargs["logger"]
            )
            for p in perms:
                if p in kwargs["permissions"]:
                    return  # allow

            # if wrong permissions
            abort(
                HTTPStatus.FORBIDDEN,
                message='user does not have access to %s' % kwargs["permissions"]
            )
        # if something wrong inside `try`
        except RBACDenied:
            abort(
                HTTPStatus.FORBIDDEN,
                message="request to retrieve permissions from RBAC was forbidden"
            )
    else:
        # if no auth_key
        abort(
            HTTPStatus.BAD_REQUEST, message="identity not found on request"
        )


def _is_mgmt_url(path):
    """
    Small helper to test if URL is for management API.
    """
    return path.startswith("/mgmt/")


def _is_openapi_url(path, app_name):
    """
    Small helper to test if URL is the openapi spec
    """
    return path == "%s%s/v0/openapi.json" % (PATH_PREFIX, app_name)
