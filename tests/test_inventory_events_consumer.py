import pytest
import json
from ros.processor.inventory_events_consumer import InventoryEventsConsumer
from tests.helpers.db_helper import db_get_host

PERFORMANCE_RECORD = {'total_cpus': 1, 'instance_type': 't2.micro', 'mem.physmem': 825152.0,
                      'mem.util.used': 663245.405, 'kernel.all.cpu.user': 0.003, 'kernel.all.cpu.sys': 0.001,
                      'kernel.all.cpu.nice': 0.001, 'kernel.all.cpu.steal': 0.0, 'kernel.all.cpu.idle': 0.994,
                      'disk.all.total': 2.727, 'mem.util.cached': 351730.563, 'mem.util.bufmem': 335.552,
                      'mem.util.free': 161906.595}


@pytest.fixture(scope="session")
def inventory_event_message():
    f = open("sample-files/events-message.json")
    msg = json.loads(f.read())
    yield msg
    f.close


@pytest.fixture
def inventory_event_consumer():
    return InventoryEventsConsumer()


def test_host_delete_event(inventory_event_consumer, db_create_system):
    msg = {"type": "delete", "insights_id": "677fb960-e164-48a4-929f-59e2d917b444",
           "id": "ee0b9978-fe1b-4191-8408-cbadbd47f7a2",
           "account": '0000001'}
    inventory_event_consumer.host_delete_event(msg)
    host = db_get_host(msg['id'])
    assert not host


def test_host_create_update_events(inventory_event_consumer, inventory_event_message, mocker):
    mocker.patch.object(inventory_event_consumer, 'process_system_details', return_value=True, autospec=True)
    inventory_event_consumer.host_create_update_events(inventory_event_message)
    inventory_event_consumer.process_system_details.assert_called_once()


def test_process_system_details(inventory_event_consumer, inventory_event_message, mocker):
    mocker.patch('ros.processor.inventory_events_consumer.get_performance_profile',
                 return_value=PERFORMANCE_RECORD, autospec=True)
    inventory_event_consumer.process_system_details(inventory_event_message)
    host = db_get_host(inventory_event_message['host']['id'])
    assert str(host.inventory_id) == inventory_event_message['host']['id']
