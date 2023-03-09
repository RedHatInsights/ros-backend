from flask_caching import Cache
from ros.lib.config import REDIS_URL
from prometheus_flask_exporter import RESTfulPrometheusMetrics
from flask_sqlalchemy import SQLAlchemy


cache = Cache(config={'CACHE_TYPE': 'RedisCache', 'CACHE_REDIS_URL': REDIS_URL, 'CACHE_DEFAULT_TIMEOUT': 300})
metrics = RESTfulPrometheusMetrics.for_app_factory(defaults_prefix='ros', group_by='url_rule')
db = SQLAlchemy()
