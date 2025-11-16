"""
Performance validation for migration 005: indexes, timeouts, materialized views.
"""

from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager

import asyncpg


@asynccontextmanager
async def get_conn():
    conn = await asyncpg.connect("postgresql://apex:apex@localhost:5432/apex")
    try:
        yield conn
    finally:
        await conn.close()


async def test_index_usage() -> None:
    """Verify EXPLAIN ANALYZE shows index scans."""
    async with get_conn() as conn:
        # Test: status + created_at query
        plan = await conn.fetchrow(
            """
            EXPLAIN ANALYZE
            SELECT * FROM projects 
            WHERE status = 'estimating' 
            ORDER BY created_at DESC LIMIT 100
            """
        )
        assert "Index Scan" in plan["QUERY PLAN"] or "Bitmap Heap Scan" in plan["QUERY PLAN"]
        assert "ix_projects_status_created" in plan["QUERY PLAN"] or "projects_created_at_idx" in plan["QUERY PLAN"]
        print("✅ Status query uses index")
        
        # Test: project_id + sha256 lookup
        plan = await conn.fetchrow(
            """
            EXPLAIN ANALYZE
            SELECT payload_id FROM project_payloads 
            WHERE project_id = 'test_001' AND sha256 = 'abc123'
            """
        )
        assert "Index Scan" in plan["QUERY PLAN"]
        print("✅ Payload dedup query uses composite index")


async def test_performance_targets() -> None:
    """Test all queries <50ms."""
    async with get_conn() as conn:
        queries = [
            ("status", "SELECT * FROM projects WHERE status = 'draft' ORDER BY created_at DESC LIMIT 50"),
            ("latest_payload", "SELECT * FROM project_payloads WHERE project_id = 'test_001' ORDER BY created_at DESC LIMIT 1"),
            ("events", "SELECT * FROM project_events WHERE project_id = 'test_001' ORDER BY timestamp DESC LIMIT 100"),
            ("materialized_view", "SELECT * FROM project_stats WHERE account_id = 'acc_001'"),
        ]
        
        for name, query in queries:
            t0 = time.perf_counter()
            await conn.fetch(query)
            t1 = time.perf_counter()
            elapsed_ms = (t1 - t0) * 1000
            assert elapsed_ms < 50.0, f"{name} query took {elapsed_ms:.2f}ms (target <50ms)"
            print(f"✅ {name}: {elapsed_ms:.2f}ms")


async def test_index_hit_rate() -> None:
    """Verify index hit rate >95%."""
    async with get_conn() as conn:
        hit_rate = await conn.fetchval(
            """
            SELECT 
                CASE WHEN sum(idx_scan + seq_scan) = 0 THEN 100
                ELSE (sum(idx_scan)::float / sum(idx_scan + seq_scan)) * 100
                END as hit_rate
            FROM pg_stat_user_tables
            WHERE schemaname = 'public'
            """
        )
        assert hit_rate >= 95.0, f"Index hit rate {hit_rate}% below 95% target"
        print(f"✅ Index hit rate: {hit_rate:.1f}%")


async def test_foreign_keys() -> None:
    """Verify foreign key constraints exist."""
    async with get_conn() as conn:
        fks = await conn.fetch(
            """
            SELECT conname, conrelid::regclass
            FROM pg_constraint 
            WHERE contype = 'f' AND conrelid IN (
                'project_payloads'::regclass, 'project_events'::regclass
            )
            """
        )
        fk_names = [f["conname"] for f in fks]
        assert "fk_payloads_project_id" in fk_names
        assert "fk_events_project_id" in fk_names
        print("✅ Foreign keys created")


async def test_pg_stat_statements() -> None:
    """Verify pg_stat_statements extension is enabled."""
    async with get_conn() as conn:
        enabled = await conn.fetchval(
            "SELECT COUNT(*) FROM pg_extension WHERE extname = 'pg_stat_statements'"
        )
        assert enabled == 1, "pg_stat_statements not enabled"
        print("✅ pg_stat_statements enabled")


async def test_timeout() -> None:
    """Verify statement_timeout is set to 30s."""
    async with get_conn() as conn:
        timeout = await conn.fetchval("SHOW statement_timeout")
        assert timeout == "30s", f"Timeout is {timeout}, expected 30s"
        print("✅ Statement timeout set to 30s")


async def main() -> None:
    """Run all performance tests."""
    print("Running performance validation for migration 005...")
    await test_index_usage()
    await test_performance_targets()
    await test_index_hit_rate()
    await test_foreign_keys()
    await test_pg_stat_statements()
    await test_timeout()
    print("\n✅ All performance tests passed!")


if __name__ == "__main__":
    asyncio.run(main())

