import pytest
import json
from unittest.mock import MagicMock, patch

from ros.processor.system_eraser import SystemEraser


@pytest.fixture
def mock_app_context():
    with patch("ros.lib.app.app.app_context") as mock_ctx:
        yield mock_ctx


@pytest.fixture
def mock_db_session():
    with patch("ros.extensions.db.session") as mock_db:
        mock_db.session.execute = MagicMock()
        mock_db.session.commit = MagicMock()
        yield mock_db


@pytest.fixture
def mock_consumer():
    with patch("ros.processor.system_eraser.consume.init_consumer") as mock_consumer_init:
        consumer = MagicMock()
        mock_consumer_init.return_value = consumer
        yield consumer


def test_delete_system_success(mock_app_context, mock_db_session, mock_consumer):
    eraser = SystemEraser()

    mock_query_object = MagicMock()
    with patch("ros.extensions.db.delete", return_value=mock_query_object):
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_db_session.execute.return_value = mock_result

        result = eraser.delete_system("host-123")

    assert result is True
    mock_db_session.commit.assert_called_once()


def test_delete_system_not_found(mock_app_context, mock_db_session, mock_consumer):
    eraser = SystemEraser()

    mock_result = MagicMock()
    mock_result.rowcount = 0
    mock_db_session.execute.return_value = mock_result

    result = eraser.delete_system("missing-host")

    assert result is False
    mock_db_session.commit.assert_called_once()


def test_delete_system_exception(mock_app_context, mock_db_session, mock_consumer):
    eraser = SystemEraser()

    mock_db_session.execute.side_effect = Exception("DB error")

    result = eraser.delete_system("host-err")

    assert result is False
    mock_db_session.commit.assert_not_called()


def test_run_processes_delete_message(mock_app_context, mock_db_session, mock_consumer):
    eraser = SystemEraser()

    payload = {"type": "delete", "host": {"id": "host-999"}}
    message = MagicMock()
    message.value.return_value = json.dumps(payload).encode("utf-8")

    # Consumer should return the message once then None
    mock_consumer.poll.side_effect = [message, None]

    with patch.object(eraser, "delete_system", return_value=True) as mock_delete:
        eraser.running = True
        eraser.run()
        mock_delete.assert_called_once_with("host-999")


def test_run_ignores_non_delete_message(mock_app_context, mock_db_session, mock_consumer):
    eraser = SystemEraser()

    payload = {"type": "update", "host": {"id": "host-777"}}
    message = MagicMock()
    message.value.return_value = json.dumps(payload).encode("utf-8")

    mock_consumer.poll.side_effect = [message, None]

    with patch.object(eraser, "delete_system") as mock_delete:
        eraser.running = True
        eraser.run()
        mock_delete.assert_not_called()


def test_run_handles_invalid_json(mock_app_context, mock_db_session, mock_consumer):
    eraser = SystemEraser()

    message = MagicMock()
    message.value.return_value = b"{invalid json}"

    mock_consumer.poll.side_effect = [message, None]

    with patch.object(eraser, "delete_system") as mock_delete:
        eraser.running = True
        eraser.run()
        mock_delete.assert_not_called()
