from ros.lib.app import app
from ros.lib import utils
from unittest import mock
from http.server import HTTPServer
import requests
import threading
import time


def test_is_valid_uuid():
    valid_uuid = "f57c5d02-a180-4bf9-9a05-ae4efd212c1f"
    invalid_uuid = "f57c5d02"
    result = utils.is_valid_uuid(valid_uuid)
    assert result

    result = utils.is_valid_uuid(invalid_uuid)
    assert not result


def test_identity(mocker):
    request = mock.Mock()
    str_ident = "eyJpZGVudGl0eSI6IHsiYWNjb3VudF9udW1iZXIiOiAiMDAwMDAwMSIsICJ0eXB" \
                "lIjogIlVzZXIiLCAiaW50ZXJuYWwiOiB7Im9yZ19pZCI6ICIwMDAwMDEifX19Cg=="
    request.headers = {"X-RH-IDENTITY": str_ident}
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
    identity_obj = {"internal": {"org_id": "001122"}, "account_number": "000", "auth_type": "jwt-auth",
                    "user": {"is_active": "true", "user_id": "123123"}, "type": "User"}
    expected_result = {"is_active": "true", "user_id": "123123"}
    result = utils.user_data_from_identity(identity_obj)
    assert result == expected_result

    invalid_identity_obj = {"internal": {"org_id": "001122"}, "account_number": "000",
                            "auth_type": "token", "type": "User"}
    result = utils.user_data_from_identity(invalid_identity_obj)
    assert not result


def test_service_user_data_from_identity():
    identity_obj = {"account_number": "111111", "auth_type": "jwt-auth", "internal": {}, "org_id": "555555",
                    "service_account": {"client_id": "0000", "username": "test"}, "type": "ServiceAccount"}
    expected_result = {"client_id": "0000", "username": "test"}
    result = utils.service_account_from_identity(identity_obj)
    assert result == expected_result


def setup_threads():
    engine_processor_thread = mock.Mock()
    engine_processor_thread.name = 'process-engine-results'
    engine_processor_thread.processor_name = 'process-engine-results'

    events_processor_thread = mock.Mock()
    events_processor_thread.name = 'events-processor'
    events_processor_thread.processor_name = 'events-processor'

    return engine_processor_thread, events_processor_thread


def test_monitoring_handler():
    engine_processor_thread, events_processor_thread = setup_threads()
    PROCESSOR_INSTANCES = [engine_processor_thread, events_processor_thread]
    with mock.patch('ros.lib.utils.PROCESSOR_INSTANCES', PROCESSOR_INSTANCES):
        with mock.patch('ros.lib.utils.threading.enumerate',
                        return_value=[engine_processor_thread, events_processor_thread]):
            with HTTPServer(("127.0.0.1", 8005), utils.MonitoringHandler) as server:
                server_thread = threading.Thread(target=server.handle_request)
                server_thread.start()
                # Allow thread and server to start
                time.sleep(1)
                response = requests.get('http://127.0.0.1:8005')
                assert response.status_code == 200
                assert response.text == "All Processor and Threads are running"


def test_monitoring_handler_with_dead_thread():
    engine_processor_thread, events_processor_thread = setup_threads()
    PROCESSOR_INSTANCES = [engine_processor_thread, events_processor_thread]
    with mock.patch('ros.lib.utils.PROCESSOR_INSTANCES', PROCESSOR_INSTANCES):
        with mock.patch('ros.lib.utils.threading.enumerate', return_value=[events_processor_thread]):
            with HTTPServer(("127.0.0.1", 8005), utils.MonitoringHandler) as server:
                server_thread = threading.Thread(target=server.handle_request)
                server_thread.start()
                # Allow thread and server to start
                time.sleep(1)
                response = requests.get('http://127.0.0.1:8005')
                assert response.status_code == 500
                assert response.text == "ERROR: Processor thread exited"
