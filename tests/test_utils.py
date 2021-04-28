from ros.lib.app import app
from ros.lib import utils
from unittest import mock


def test_is_valid_uuid():
    valid_uuid = "f57c5d02-a180-4bf9-9a05-ae4efd212c1f"
    invalid_uuid = "f57c5d02"
    result = utils.is_valid_uuid(valid_uuid)
    assert result

    result = utils.is_valid_uuid(invalid_uuid)
    assert not result


def test_identity(mocker):
    request = mock.Mock()
    request.headers = {"X-RH-IDENTITY": "eyJpZGVudGl0eSI6IHsiYWNjb3VudF9udW1iZXIiOiAiMDAwMDAwMSIsICJ0eXB"
                       "lIjogIlVzZXIiLCAiaW50ZXJuYWwiOiB7Im9yZ19pZCI6ICIwMDAwMDEifX19Cg=="}
    expected_result = {'identity': {'account_number': '0000001', 'type': 'User', 'internal': {'org_id': '000001'}}}
    result = utils.identity(request)
    assert expected_result == result

    with app.app_context():
        empty_header_request = mock.Mock()
        empty_header_request.headers = {}
        mocker.patch('ros.lib.utils.abort')
        utils.identity(empty_header_request)
        utils.abort.assert_called_once()


def test_user_data_from_identity():
    identity_obj = {"internal": {"org_id": "001122"}, "account_number": "000", "auth_type": "basic-auth",
                    "user": {"is_active": "true", "user_id": "123123"}, "type": "User"}
    expected_result = {"is_active": "true", "user_id": "123123"}
    result = utils.user_data_from_identity(identity_obj)
    assert result == expected_result

    invalid_identity_obj = {"internal": {"org_id": "001122"}, "account_number": "000",
                            "auth_type": "token", "type": "User"}
    result = utils.user_data_from_identity(invalid_identity_obj)
    assert not result
