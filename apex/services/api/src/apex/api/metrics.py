from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Gauge, Histogram


CELERY_QUEUE_DEPTH = Gauge("apex_celery_queue_depth", "Depth of Celery queue")
PG_POOL_USED = Gauge("apex_pg_pool_used", "Used Postgres pool conns")
CACHE_HIT_RATIO = Gauge("apex_cache_hit_ratio", "Cache hit ratio (0..1), -1 unknown")
REQUEST_LATENCY = Histogram(
    "apex_request_latency_seconds",
    "API request latency seconds",
    labelnames=("route", "status"),
)


def setup_metrics(app):
    Instrumentator().instrument(app).expose(app, endpoint="/metrics")


