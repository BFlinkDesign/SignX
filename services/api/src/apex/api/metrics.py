from __future__ import annotations

from prometheus_client import Counter, Gauge
from prometheus_fastapi_instrumentator import Instrumentator

REQUEST_LATENCY = None  # Instrumentator provides http metrics
ABSTAIN_TOTAL = Counter("apex_abstain_total", "Count of abstain responses")
MATERIALS_REQUESTS_TOTAL = Counter(
    "apex_materials_requests_total", "Count of materials gateway requests", labelnames=("status",)
)
MATERIALS_NORMALIZED_WEIGHTS_TOTAL = Counter(
    "apex_materials_normalized_weights_total", "Count of requests where weights were normalized"
)
MATERIALS_IMPUTED_QUALITATIVE_TOTAL = Counter(
    "apex_materials_imputed_qualitative_total", "Count of requests where qualitative was imputed"
)
CELERY_QUEUE_DEPTH = Gauge("apex_celery_queue_depth", "Depth of Celery default queue")
PG_POOL_USED = Gauge("apex_pg_pool_used", "Number of used connections in the Postgres pool")
CACHE_HIT_RATIO = Gauge("apex_cache_hit_ratio", "Cache hit ratio (0..1), -1 if unknown")


def setup_metrics(app):  # type: ignore[no-untyped-def]
    Instrumentator().instrument(app).expose(app, endpoint="/metrics")
    # Background task creation moved to startup event handler in main.py


