import pytest
from pytest_mock_resources import RedisConfig, create_redis_fixture
from redis import Redis


@pytest.fixture(scope="session")
def pmr_redis_config():
    # redis-py 5+ defaults to RESP3 (HELLO 3); PMR's default redis:5.0.7 does not support it.
    return RedisConfig(image="redis:6")


redis = create_redis_fixture()


@pytest.fixture(scope="function")
def redis_client(redis):
    from ros.extensions import cache
    from ros.lib.app import app

    creds = redis.pmr_credentials.as_redis_kwargs()
    cache.init_app(app, config={
        'CACHE_TYPE': 'RedisCache',
        'CACHE_REDIS_URL': f"redis://{creds['host']}:{creds['port']}/{creds['db']}",
        'CACHE_DEFAULT_TIMEOUT': 300,
    })

    client = Redis(**creds)
    yield client
    client.flushdb()
