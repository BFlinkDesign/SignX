"""
Transaction Metrics Stub - REPL for metric implementation.

This module defines transaction metrics to be implemented.
Import and use in transaction decorators/context managers.

Usage:
    from .metrics_stub import (
        DB_TRANSACTIONS_TOTAL,
        DB_TRANSACTION_DURATION,
        DB_TRANSACTION_FAILURES,
        DB_ROLLBACKS_TOTAL,
    )
    
    # In transaction context manager
    with DB_TRANSACTION_DURATION.labels(operation="create_project").time():
        DB_TRANSACTIONS_TOTAL.labels(operation="create_project", status="start").inc()
        try:
            # ... database operations ...
            DB_TRANSACTIONS_TOTAL.labels(operation="create_project", status="success").inc()
        except Exception:
            DB_ROLLBACKS_TOTAL.labels(operation="create_project").inc()
            DB_TRANSACTION_FAILURES.labels(operation="create_project").inc()
            DB_TRANSACTIONS_TOTAL.labels(operation="create_project", status="failure").inc()
            raise
"""

from __future__ import annotations

from prometheus_client import Counter, Histogram

# Database Transaction Metrics

DB_TRANSACTIONS_TOTAL = Counter(
    "apex_db_transactions_total",
    "Total database transactions",
    labelnames=("operation", "status"),  # status: start, success, failure
)

DB_TRANSACTION_DURATION = Histogram(
    "apex_db_transaction_duration_seconds",
    "Database transaction duration in seconds",
    labelnames=("operation",),
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0),
)

DB_TRANSACTION_FAILURES = Counter(
    "apex_db_transaction_failures_total",
    "Failed database transactions",
    labelnames=("operation",),
)

DB_ROLLBACKS_TOTAL = Counter(
    "apex_db_rollbacks_total",
    "Database transaction rollbacks",
    labelnames=("operation",),
)

# Search Metrics

SEARCH_REQUESTS_TOTAL = Counter(
    "apex_search_requests_total",
    "Total search requests",
    labelnames=("index", "status"),  # status: success, failure, fallback
)

SEARCH_FAILURES_TOTAL = Counter(
    "apex_search_failures_total",
    "Failed search requests",
    labelnames=("index",),
)

SEARCH_FALLBACK_TOTAL = Counter(
    "apex_search_fallback_total",
    "Search fallback to database",
    labelnames=("index",),
)

SEARCH_DURATION = Histogram(
    "apex_search_duration_seconds",
    "Search request duration",
    labelnames=("index",),
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0),
)

# Celery Task Metrics

CELERY_TASKS_TOTAL = Counter(
    "apex_celery_tasks_total",
    "Total Celery tasks",
    labelnames=("task_name", "status"),  # status: enqueued, started, success, failure
)

CELERY_TASK_DURATION = Histogram(
    "apex_celery_task_duration_seconds",
    "Celery task duration",
    labelnames=("task_name",),
    buckets=(1.0, 5.0, 10.0, 30.0, 60.0, 300.0),
)

CELERY_TASK_FAILURES = Counter(
    "apex_celery_task_failures_total",
    "Failed Celery tasks",
    labelnames=("task_name",),
)

CELERY_TASK_RETRIES = Counter(
    "apex_celery_task_retries_total",
    "Celery task retries",
    labelnames=("task_name",),
)

# External Service Metrics

EXTERNAL_API_REQUESTS_TOTAL = Counter(
    "apex_external_api_requests_total",
    "External API requests",
    labelnames=("service", "endpoint", "status"),  # service: geocode, weather, pm, email
)

EXTERNAL_API_FAILURES_TOTAL = Counter(
    "apex_external_api_failures_total",
    "External API request failures",
    labelnames=("service", "endpoint"),
)

EXTERNAL_API_DURATION = Histogram(
    "apex_external_api_duration_seconds",
    "External API request duration",
    labelnames=("service", "endpoint"),
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0),
)

# Circuit Breaker Metrics

CIRCUIT_BREAKER_STATE = Histogram(
    "apex_circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=open)",
    labelnames=("breaker_name",),
)

CIRCUIT_BREAKER_FAILURES = Counter(
    "apex_circuit_breaker_failures_total",
    "Circuit breaker recorded failures",
    labelnames=("breaker_name",),
)

