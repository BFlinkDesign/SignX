"""OpenSearch indexing utilities with DB fallback and retry logic."""

from __future__ import annotations

import asyncio
from typing import Any, Optional

import aiohttp
import structlog
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_log,
    after_log,
)

from ..deps import settings

logger = structlog.get_logger(__name__)

# Retry configuration for transient failures
OPENSEARCH_RETRY = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=5),
    retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
    before=before_log(logger, "info"),
    after=after_log(logger, "info"),
    reraise=False,  # Don't reraise - we have fallback logic
)


@OPENSEARCH_RETRY
async def _index_with_retry(project_id: str, project_data: dict[str, Any]) -> bool:
    """Internal function to index with retry logic."""
    async with aiohttp.ClientSession() as session:
        url = f"{settings.OPENSEARCH_URL}/projects/_doc/{project_id}"
        async with session.put(
            url,
            json=project_data,
            headers={"Content-Type": "application/json"},
            timeout=aiohttp.ClientTimeout(total=5),
        ) as resp:
            if resp.status in (200, 201):
                return True
            elif resp.status >= 500:
                # Server error - worth retrying
                raise aiohttp.ClientError(f"Server error: {resp.status}")
            else:
                # Client error - don't retry
                return False


async def index_project(project_id: str, project_data: dict[str, Any]) -> bool:
    """Index project in OpenSearch with retry logic.
    
    Returns: True if indexed, False if failed (will fallback to DB)
    """
    try:
        result = await _index_with_retry(project_id, project_data)
        if result:
            logger.info("search.indexed", project_id=project_id)
            # Track success metric
            logger.info("metrics.search.index.success", project_id=project_id)
        else:
            logger.warning("search.index_failed", project_id=project_id)
            # Track failure metric
            logger.info("metrics.search.index.failure", project_id=project_id)
        return result
    except Exception as e:
        logger.warning("search.index_error", project_id=project_id, error=str(e))
        # Track fallback metric
        logger.info("metrics.search.index.fallback", project_id=project_id)
        return False


@OPENSEARCH_RETRY
async def _search_with_retry(query: dict[str, Any]) -> Optional[list[dict[str, Any]]]:
    """Internal function to search with retry logic."""
    async with aiohttp.ClientSession() as session:
        url = f"{settings.OPENSEARCH_URL}/projects/_search"
        async with session.post(
            url,
            json=query,
            headers={"Content-Type": "application/json"},
            timeout=aiohttp.ClientTimeout(total=5),
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                hits = data.get("hits", {}).get("hits", [])
                results = [hit["_source"] for hit in hits]
                return results
            elif resp.status >= 500:
                # Server error - worth retrying
                raise aiohttp.ClientError(f"Server error: {resp.status}")
            else:
                # Client error - don't retry
                return None


async def search_projects(query: dict[str, Any], fallback_db_query: Any = None) -> tuple[list[dict[str, Any]], bool]:
    """Search projects in OpenSearch with DB fallback and retry logic.
    
    Args:
        query: OpenSearch query dict
        fallback_db_query: Callable that returns DB results if search fails
    
    Returns:
        (results, used_fallback)
    """
    try:
        results = await _search_with_retry(query)
        if results is not None:
            logger.info("search.success", count=len(results))
            # Track success metric
            logger.info("metrics.search.query.success", count=len(results))
            return results, False
        else:
            logger.warning("search.query_failed")
            # Track failure metric
            logger.info("metrics.search.query.failure")
            if fallback_db_query:
                results = await fallback_db_query()
                logger.info("metrics.search.query.fallback", count=len(results))
                return results, True
            return [], True
    except Exception as e:
        logger.warning("search.query_error", error=str(e))
        # Track error metric
        logger.info("metrics.search.query.error")
        if fallback_db_query:
            results = await fallback_db_query()
            logger.info("metrics.search.query.fallback", count=len(results))
            return results, True
        return [], True


async def ensure_index_exists() -> bool:
    """Ensure OpenSearch index exists with proper mapping."""
    try:
        async with aiohttp.ClientSession() as session:
            # Check if index exists
            url = f"{settings.OPENSEARCH_URL}/projects"
            async with session.head(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    return True
            
            # Create index with mapping
            mapping = {
                "mappings": {
                    "properties": {
                        "project_id": {"type": "keyword"},
                        "name": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                        "status": {"type": "keyword"},
                        "customer": {"type": "text"},
                        "created_at": {"type": "date"},
                        "updated_at": {"type": "date"},
                    }
                }
            }
            async with session.put(url, json=mapping, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status in (200, 201):
                    logger.info("search.index_created")
                    return True
                return False
    except Exception as e:
        logger.warning("search.setup_error", error=str(e))
        return False

