
from urllib.parse import urljoin
from http import HTTPStatus
from flask_restful import abort
from .config import RBAC_SVC_URL, RBAC_CA_PATH, RBAC_AUTHENTICATED
import requests

from ros.lib.config import get_logger

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
    verify = RBAC_CA_PATH or True
    if RBAC_AUTHENTICATED:
        from ros.lib.kessel.kessel_shared import get_cached_kessel_auth_credentials
        credentials = get_cached_kessel_auth_credentials()
        if not credentials:
            raise RuntimeError(
                "RBAC V2 endpoint requires bearer authentication but "
                "OAuth2 credentials are not available"
            )
        token_response = credentials.get_token()
        auth_header = dict(auth_header) if auth_header else {}
        auth_header["Authorization"] = f"Bearer {token_response.access_token}"
    response = requests.request(
        method, url, headers=auth_header, verify=verify)
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
