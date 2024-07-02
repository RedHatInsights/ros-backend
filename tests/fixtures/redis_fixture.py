import pytest
from pytest_mock_resources import create_redis_fixture
from redis import Redis

redis = create_redis_fixture()


@pytest.fixture(scope="function")
def redis_setup(redis):
    yield Redis(**redis.pmr_credentials.as_redis_kwargs())
