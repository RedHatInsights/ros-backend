from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from werkzeug.exceptions import HTTPException

from ros.lib import config, rbac_interface

IDENTITY = {"X-RH-IDENTITY": "abc"}


def _ok_response():
    return MagicMock(status_code=200, json=MagicMock(return_value={"data": []}))


def _v2(mocker, endpoint):
    return mocker.patch.object(config, "get_v2_dependency_endpoint", return_value=endpoint, create=True)


@pytest.mark.parametrize("authenticated, ca, expected_auth", [
    (True, "/cdapp/certs/ewgw-ca.crt", True),
    (True, None, True),
    (False, None, False),
    (None, None, False),
])
def test_resolve_rbac_endpoint_from_v2(mocker, authenticated, ca, expected_auth):
    helper = _v2(mocker, SimpleNamespace(uri="https://rbac:443", ca_certificate=ca, authenticated=authenticated))
    assert config.resolve_rbac_endpoint() == ("https://rbac:443", ca, expected_auth)
    helper.assert_called_once_with("rbac", "service")


@pytest.mark.parametrize("endpoint", [None, SimpleNamespace(uri=None, ca_certificate=None, authenticated=False)])
def test_resolve_rbac_endpoint_missing_raises(mocker, endpoint):
    _v2(mocker, endpoint)
    with pytest.raises(ValueError):
        config.resolve_rbac_endpoint()


def test_unauthenticated_sends_no_bearer(mocker):
    mocker.patch.object(rbac_interface, "RBAC_AUTHENTICATED", False)
    mocker.patch.object(rbac_interface, "RBAC_CA_PATH", None)
    creds = mocker.patch.object(rbac_interface, "get_cached_kessel_auth_credentials")
    request = mocker.patch.object(rbac_interface.requests, "request", return_value=_ok_response())

    rbac_interface.fetch_url("http://rbac/x", IDENTITY, MagicMock())

    creds.assert_not_called()
    request.assert_called_once_with("get", "http://rbac/x", headers=IDENTITY, auth=None, verify=True)


@pytest.mark.parametrize("ca, expected_verify", [("/ewgw-ca.crt", "/ewgw-ca.crt"), (None, True)])
def test_authenticated_adds_bearer_and_keeps_identity(mocker, ca, expected_verify):
    mocker.patch.object(rbac_interface, "RBAC_AUTHENTICATED", True)
    mocker.patch.object(rbac_interface, "RBAC_CA_PATH", ca)
    shared_creds = MagicMock()
    shared_creds.get_token.return_value = SimpleNamespace(access_token="tok")
    mocker.patch.object(rbac_interface, "get_cached_kessel_auth_credentials", return_value=shared_creds)
    request = mocker.patch.object(rbac_interface.requests, "request", return_value=_ok_response())

    rbac_interface.fetch_url("https://ewgw/x", IDENTITY, MagicMock())

    kwargs = request.call_args.kwargs
    assert kwargs["headers"] == IDENTITY
    assert kwargs["verify"] == expected_verify
    assert kwargs["auth"].credentials is shared_creds
    prepared = kwargs["auth"](SimpleNamespace(headers={}))
    assert prepared.headers["Authorization"] == "Bearer tok"


@pytest.mark.parametrize("creds", [None, MagicMock(get_token=MagicMock(side_effect=RuntimeError("sso down")))])
def test_authenticated_without_token_fails_closed(mocker, creds):
    mocker.patch.object(rbac_interface, "RBAC_AUTHENTICATED", True)
    mocker.patch.object(rbac_interface, "get_cached_kessel_auth_credentials", return_value=creds)
    request = mocker.patch.object(rbac_interface.requests, "request")

    with pytest.raises(HTTPException) as exc:
        rbac_interface.fetch_url("https://ewgw/x", IDENTITY, MagicMock())

    assert exc.value.code == 502
    request.assert_not_called()
