import requests
import http
import json
from ros.lib.config import SOURCES_API_EXTERNAL_BASE_URL, SOURCES_API_INTERNAL_BASE_URL, SOURCES_PSK, get_logger
from ros.utils.exceptions import SourcesAPINotOkStatus, SourcesAPINotJsonContent


LOG = get_logger(__name__)


def get_application(account_number, application_id):
    """
    Get an Application object from the Sources API.

    If the `requests.get` itself fails unexpectedly, let the exception bubble
    up to be handled by a higher level in the stack.

    Args:
        account_number (str): account number identifier for Insights auth
        application_id (int): the requested application's id

    Returns:
        dict response payload from the sources api.
    """
    url = f"{SOURCES_API_EXTERNAL_BASE_URL}/applications/{application_id}"
    headers = generate_sources_headers(account_number)
    return make_sources_call(account_number, url, headers)


def get_authentication(account_number, authentication_id):
    """
    Get an Authentication objects from the Sources API.

    If the `requests.get` itself fails unexpectedly, let the exception bubble
    up to be handled by a higher level in the stack.

    Args:
        account_number (str): account number identifier for Insights auth
        authentication_id (int): the requested authentication's id

    Returns:
        dict response payload from the sources api.

    """
    url = (
        f"{SOURCES_API_INTERNAL_BASE_URL}"
        f"/authentications/{authentication_id}"
    )
    headers = generate_sources_headers(account_number)
    params = {"expose_encrypted_attribute[]": "password"}
    return make_sources_call(account_number, url, headers, params)


def get_source_type(account_number, source_id):
    """
    Get an source type objects from the Sources API.

    If the `requests.get` itself fails unexpectedly, let the exception bubble
    up to be handled by a higher level in the stack.

    Args:
        account_number (str): account number identifier for Insights auth
        source_id (int): the requested Source's id

    Returns:
        dict response payload from the sources api.

    """
    url = (
        f"{SOURCES_API_EXTERNAL_BASE_URL}"
        f"/sources/{source_id}"
    )
    headers = generate_sources_headers(account_number)
    source = make_sources_call(account_number, url, headers)

    url = (
        f"{SOURCES_API_EXTERNAL_BASE_URL}"
        f"/source_types/{source['source_type_id']}"
    )
    source_type = make_sources_call(account_number, url, headers)
    if source_type:
        return source_type.get('name')
    return None


def generate_sources_headers(account_number, include_psk=True):
    """
    Return the headers needed for accessing Sources.

    The Sources API requires the x-rh-sources-account-number
    as well as the x-rh-sources-psk for service to service
    communication instead of the earlier x-rh-identity.

    By default we include the PSK, but for Kafka messages,
    the PSK is not required, so we can optionally exclude it.

    Args:
        account_number (str): Account number identifier
        include_psk (boolean): Whether or not to include the PSK
    """
    headers = {"x-rh-sources-account-number": account_number}

    if include_psk:
        if not SOURCES_PSK:
            raise SourcesAPINotOkStatus(
                "Failed to generate headers for Sources, SOURCES_PSK is not defined"
            )
        else:
            headers["x-rh-sources-psk"] = SOURCES_PSK

    return headers


def get_ros_application_type_id(account_number):
    """Get the ROS application type id from sources."""
    url = (
        f"{SOURCES_API_EXTERNAL_BASE_URL}/application_types"
        f"?filter[name]=/insights/platform/ros"
    )

    headers = generate_sources_headers(account_number)
    ros_application_type = make_sources_call(account_number, url, headers)
    if ros_application_type:
        return ros_application_type.get("data")[0].get("id")
    return None


def make_sources_call(account_number, url, headers, params=None):
    """
    Make an API call to the Sources API.

    If the `requests.get` itself fails unexpectedly, let the exception bubble
    up to be handled by a higher level in the stack.

    Args:
        account_number (str): account number identifier for Insights auth
        url (str): the requested url
        headers (dict): a dict of headers for the request.
        params (dict): a dict of params for the request

    Returns:
        dict response payload from the sources api or None if not found.
    """
    response = requests.get(url, headers=headers, params=params)

    if response.status_code == http.HTTPStatus.NOT_FOUND:
        return None
    elif response.status_code != http.HTTPStatus.OK:
        message = f"unexpected status {response.status_code} using account {account_number} at {url}"
        LOG.info(message)
        LOG.info(f"sources-api response content: {response.text}")
        raise SourcesAPINotOkStatus(message)

    try:
        response_json = response.json()
    except json.decoder.JSONDecodeError:
        message = f"unexpected non-json response using account {account_number} at {url}"
        LOG.info(message)
        LOG.info(f"sources-api response content: {response.text}")
        raise SourcesAPINotJsonContent(message)

    return response_json
