import pytest
import json
from pathlib import Path
from ros.lib.app import app
from ros.extensions import cache
from ros.processor.inventory_events_consumer import InventoryEventsConsumer
from tests.helpers.db_helper import db_get_host
from ros.lib.config import CACHE_KEYWORD_FOR_DELETED_SYSTEM


PERFORMANCE_RECORD = {'total_cpus': 1, 'instance_type': 't2.micro', 'mem.physmem': 825152.0,
                      'mem.util.used': 663245.405, 'kernel.all.cpu.user': 0.003, 'kernel.all.cpu.sys': 0.001,
                      'kernel.all.cpu.nice': 0.001, 'kernel.all.cpu.steal': 0.0, 'kernel.all.cpu.idle': 0.994,
                      'disk.all.total': 2.727, 'mem.util.cached': 351730.563, 'mem.util.bufmem': 335.552,
                      'mem.util.free': 161906.595, 'region': 'ap-south-1'}


@pytest.fixture(scope="function")
def inventory_event_message():
    f = open(f"{Path(__file__).parent}/data_files/events-message.json")
    msg = json.loads(f.read())
    yield msg
    f.close()


@pytest.fixture(scope="function")
def inventory_event_consumer():
    return InventoryEventsConsumer()


def test_process_system_details(inventory_event_consumer, inventory_event_message, db_setup, redis_setup):
    inventory_event_message['type'] = 'created'
    inventory_event_consumer.process_system_details(inventory_event_message)
    with app.app_context():
        host = db_get_host(inventory_event_message['host']['id'])
        assert str(host.inventory_id) == inventory_event_message['host']['id']


def test_host_create_events(inventory_event_consumer, inventory_event_message, db_setup, redis_setup, mocker):
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
        assert db_get_host(inventory_event_message['host']['id']).operating_system == \
               inventory_event_message['host']['system_profile']['operating_system']
        assert db_get_host(inventory_event_message['host']['id']).groups == \
               inventory_event_message['host']['groups']


def test_host_update_events(inventory_event_consumer, inventory_event_message, db_setup, redis_setup, mocker):
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
    inventory_event_message['platform_metadata'] = {'org_id': '000001'}
    updated_display_name = 'Test - Display Name Update'  # Test case change
    inventory_event_message['host']['display_name'] = updated_display_name
    inventory_event_message['host']['groups'] = []
    inventory_event_consumer.host_create_update_events(inventory_event_message)
    inventory_event_consumer.process_system_details.call_count = 2
    inventory_event_consumer.process_system_details(msg=inventory_event_message)
    with app.app_context():
        updated_system = db_get_host(inventory_event_message['host']['id'])
        assert updated_system.display_name == updated_display_name
        assert updated_system.groups == []


def test_host_update_event_no_cp(inventory_event_consumer, inventory_event_message, db_setup, redis_setup, mocker):
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
    inventory_event_message['platform_metadata'] = {'org_id': '000001'}
    updated_display_name = 'Test - Display Name Update'  # Test case change
    inventory_event_message['host']['display_name'] = updated_display_name
    inventory_event_message['host']['system_profile']['cloud_provider'] = None
    inventory_event_consumer.host_create_update_events(inventory_event_message)
    inventory_event_consumer.process_system_details.call_count = 2
    with app.app_context():
        updated_system = db_get_host(inventory_event_message['host']['id'])
        assert updated_system.display_name != updated_display_name


def test_host_delete_event(inventory_event_consumer, inventory_event_message, db_setup, redis_setup, mocker):
    mocker.patch.object(
        inventory_event_consumer,
        'process_system_details',
        side_effect=inventory_event_consumer.process_system_details,
        autospec=True
    )
    inventory_event_message['type'] = 'created'
    inventory_event_consumer.host_create_update_events(inventory_event_message)

    msg = {"type": "delete",
           "insights_id": "677fb960-e164-48a4-929f-59e2d917b444",
           "id": "ee0b9978-fe1b-4191-8408-cbadbd47f7a2",
           "account": '0000001', 'org_id': '000001'}
    inventory_event_consumer.host_delete_event(msg)
    with app.app_context():
        cached_deleted_sys = cache.get(
            f"{msg['org_id']}{CACHE_KEYWORD_FOR_DELETED_SYSTEM}{msg['id']}"
        )
        assert cached_deleted_sys == 1

    host = db_get_host(msg['id'])
    assert host is None


def test_recreate_remove_cached_key(inventory_event_consumer, inventory_event_message, db_setup, redis_setup, mocker):
    msg = {"type": "delete",
           "insights_id": "677fb960-e164-48a4-929f-59e2d917b444",
           "id": "bb0b9978-fe1b-4191-8408-cbadbd47f7a3",
           "account": '0000002', 'org_id': '000002'}
    cached_skey = f"{msg['org_id']}{CACHE_KEYWORD_FOR_DELETED_SYSTEM}{msg['id']}"
    with app.app_context():
        cache.set(cached_skey, 1)
        assert cache.get(cached_skey) == 1

    mocker.patch.object(
        inventory_event_consumer,
        'process_system_details',
        side_effect=inventory_event_consumer.process_system_details,
        autospec=True
    )
    inventory_event_message['type'] = 'created'
    inventory_event_message['host']['id'] = 'bb0b9978-fe1b-4191-8408-cbadbd47f7a3'
    inventory_event_message['host']['account'] = '0000002'
    inventory_event_message['host']['org_id'] = '000002'
    inventory_event_message['platform_metadata']['account'] = '0000002'
    inventory_event_message['platform_metadata']['org_id'] = '000002'
    inventory_event_consumer.host_create_update_events(inventory_event_message)

    with app.app_context():
        cached_sys_val = cache.get(cached_skey)
        assert cached_sys_val is None
