"""Celery client utilities for enqueueing tasks from API services.

This module provides a unified interface for calling Celery tasks
from the APEX API or other services.
"""

from __future__ import annotations

import os
from typing import Any

from celery import Celery
import logging

logger = logging.getLogger(__name__)

# Singleton Celery client to avoid creating new instances on every call
_celery_client: Celery | None = None


def get_celery_client() -> Celery:
    """Get Celery client for enqueueing tasks (singleton pattern).
    
    The client is configured to connect to the same broker as workers,
    using environment variables for configuration.
    
    Returns:
        Configured Celery client instance
    """
    global _celery_client
    if _celery_client is None:
        broker = os.getenv("CELERY_BROKER_URL", os.getenv("REDIS_URL", "redis://cache:6379/0"))
        backend = os.getenv("CELERY_RESULT_BACKEND", os.getenv("REDIS_URL", broker))
        
        _celery_client = Celery("apex-client", broker=broker, backend=backend)
        _celery_client.conf.update(
            task_serializer="json",
            result_serializer="json",
            accept_content=["json"],
            timezone="UTC",
            enable_utc=True,
        )
    return _celery_client


def enqueue_materials_score(spec: dict[str, Any]) -> str:
    """Enqueue materials scoring task.
    
    Args:
        spec: Material specification dict
        
    Returns:
        Task ID for tracking
    """
    celery = get_celery_client()
    result = celery.send_task("materials.score", args=[spec])
    return result.id


def enqueue_dfma_analysis(geometry: dict[str, Any]) -> str:
    """Enqueue DFMA analysis task.
    
    Args:
        geometry: Design geometry dict
        
    Returns:
        Task ID for tracking
    """
    celery = get_celery_client()
    result = celery.send_task("dfma.analyze", args=[geometry])
    return result.id


def enqueue_stackup_calculation(layers: list[dict[str, Any]]) -> str:
    """Enqueue material stackup calculation task.
    
    Args:
        layers: List of layer dicts
        
    Returns:
        Task ID for tracking
    """
    celery = get_celery_client()
    result = celery.send_task("stackup.calculate", args=[layers])
    return result.id


def enqueue_cad_macro_generation(design: dict[str, Any], format: str = "freecad") -> str:
    """Enqueue CAD macro generation task.
    
    Args:
        design: Design specification dict
        format: CAD format ("freecad", "openscad", etc.)
        
    Returns:
        Task ID for tracking
    """
    celery = get_celery_client()
    result = celery.send_task("cad.generate_macro", args=[design, format])
    return result.id


def enqueue_standards_check(design: dict[str, Any], standards: list[str]) -> str:
    """Enqueue standards compliance check task.
    
    Args:
        design: Design specification dict
        standards: List of standard codes to check
        
    Returns:
        Task ID for tracking
    """
    celery = get_celery_client()
    result = celery.send_task("standards.check", args=[design, standards])
    return result.id


def enqueue_health_ping() -> str:
    """Enqueue health ping task.
    
    Returns:
        Task ID for tracking
    """
    celery = get_celery_client()
    result = celery.send_task("health.ping")
    return result.id


def get_task_result(task_id: str, timeout: float = 5.0) -> dict[str, Any] | None:
    """Get result from a Celery task (synchronous wait).
    
    Args:
        task_id: Task ID returned from send_task
        timeout: Maximum seconds to wait
        
    Returns:
        Task result dict, or None if timeout or error
    """
    celery = get_celery_client()
    try:
        result = celery.AsyncResult(task_id)
        return result.get(timeout=timeout)
    except Exception as e:
        logger.warning("Exception in worker_client.py: %s", str(e))
        return None

