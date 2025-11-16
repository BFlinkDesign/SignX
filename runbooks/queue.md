# CeleryQueueBacklog

Symptom: Alert fires when `apex_celery_queue_depth` > threshold for sustained period.

Checks:
- /metrics: verify `apex_celery_queue_depth`
- Redis: `LLEN celery`

Actions:
- Scale workers: `docker compose up --scale worker=3 -d`
- Identify hot tasks; consider backoff/tuning
- Inspect poison messages; add DLQ if needed

