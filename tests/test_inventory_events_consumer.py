import pytest
import json

from ros.lib.app import app
from ros.processor.inventory_events_consumer import InventoryEventsConsumer
from tests.helpers.db_helper import db_get_host


@pytest.fixture(scope="session")
def inventory_event_message():
    f = open("sample-files/events-message.json")
    msg = json.loads(f.read())
    yield msg
    f.close()


@pytest.fixture
def inventory_event_consumer():
    return InventoryEventsConsumer()


def test_process_system_details(inventory_event_consumer, inventory_event_message, db_setup):
    inventory_event_consumer.process_system_details(inventory_event_message)
    with app.app_context():
        host = db_get_host(inventory_event_message['host']['id'])
        assert str(host.inventory_id) == inventory_event_message['host']['id']


def test_host_create_events(inventory_event_consumer, inventory_event_message, db_setup, mocker):
    mocker.patch.object(
        inventory_event_consumer,
        'process_system_details',
        side_effect=inventory_event_consumer.process_system_details,
        autospec=True
    )
    inventory_event_message['type'] = 'created'  # Setup to meet test case conditions
    inventory_event_consumer.host_create_update_events(inventory_event_message)
    inventory_event_consumer.process_system_details.assert_called_once()
    inventory_event_consumer.process_system_details(msg=inventory_event_message)
    with app.app_context():
        assert db_get_host(inventory_event_message['host']['id']).display_name == \
               inventory_event_message['host']['display_name']
        assert type(db_get_host(inventory_event_message['host']['id'])).__name__ == 'System'


def test_host_update_events(inventory_event_consumer, inventory_event_message, db_setup, mocker):
    mocker.patch.object(
        inventory_event_consumer,
        'process_system_details',
        side_effect=inventory_event_consumer.process_system_details,
        autospec=True
    )

    # Setup to meet test case conditions
    inventory_event_message['type'] = 'created'
    inventory_event_consumer.host_create_update_events(inventory_event_message)  # creating system for test
    inventory_event_message['type'] = 'updated'
    inventory_event_message['platform_metadata'] = None
    updated_display_name = 'Test - Display Name Update'  # Test case change
    inventory_event_message['host']['display_name'] = updated_display_name
    inventory_event_consumer.host_create_update_events(inventory_event_message)
    inventory_event_consumer.process_system_details.call_count = 2
    inventory_event_consumer.process_system_details(msg=inventory_event_message)
    with app.app_context():
        updated_system = db_get_host(inventory_event_message['host']['id'])
        assert updated_system.display_name == updated_display_name


def test_host_delete_event(inventory_event_consumer, db_setup):
    msg = {"type": "delete", "insights_id": "677fb960-e164-48a4-929f-59e2d917b444",
           "id": "ee0b9978-fe1b-4191-8408-cbadbd47f7a2",
           "account": '0000001'}
    inventory_event_consumer.host_delete_event(msg)
    host = db_get_host(msg['id'])
    assert host is None
