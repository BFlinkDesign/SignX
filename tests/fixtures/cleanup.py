"""Test data cleanup utilities."""

from __future__ import annotations

import asyncio
from typing import Any

import asyncpg


async def truncate_test_tables(database_url: str) -> None:
    """Truncate all test tables to clean state."""
    
    conn = await asyncpg.connect(database_url)
    
    try:
        # Truncate tables in correct order (respecting foreign keys)
        await conn.execute("TRUNCATE TABLE project_events CASCADE")
        await conn.execute("TRUNCATE TABLE project_payloads CASCADE")
        await conn.execute("TRUNCATE TABLE projects CASCADE")
        
        # Reset sequences
        await conn.execute("ALTER SEQUENCE IF EXISTS projects_id_seq RESTART WITH 1")
        await conn.execute("ALTER SEQUENCE IF EXISTS project_events_id_seq RESTART WITH 1")
        
    finally:
        await conn.close()


async def clear_redis_keys(redis_url: str, pattern: str = "test_*") -> None:
    """Clear test-related keys from Redis."""
    
    from redis.asyncio import Redis
    
    redis = Redis.from_url(redis_url)
    
    try:
        # Scan and delete keys matching pattern
        cursor = 0
        while True:
            cursor, keys = await redis.scan(cursor, match=pattern, count=100)
            if keys:
                await redis.delete(*keys)
            if cursor == 0:
                break
    finally:
        await redis.aclose()


async def cleanup_test_artifacts(minio_config: dict[str, Any]) -> None:
    """Clean up test artifacts from MinIO."""
    
    # Note: Would use MinIO client to delete test files
    # Placeholder for future implementation
    pass

