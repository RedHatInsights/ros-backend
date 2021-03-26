import pytest
import json
from ros.processor.insights_engine_result_consumer import InsightsEngineResultConsumer
from tests.helpers.db_helper import db_get_host


@pytest.fixture(scope="session")
def engine_result_message():
    f = open("sample-files/insights-engine-result.json")
    msg = json.loads(f.read())
    yield msg
    f.close


@pytest.fixture
def engine_consumer():
    return InsightsEngineResultConsumer()


def test_handle_msg(engine_result_message, engine_consumer, mocker):
    mocker.patch.object(engine_consumer, 'process_report', return_value=True, autospec=True)
    engine_consumer.handle_msg(engine_result_message)
    engine_consumer.process_report.assert_called_once()


def test_process_report(engine_result_message, engine_consumer, db_setup):
    host = engine_result_message["input"]["host"]
    ros_reports = engine_result_message["results"]["reports"][4]
    engine_consumer.process_report(host, ros_reports)
    data = db_get_host(host['id'])
    assert str(data.inventory_id) == host['id']
