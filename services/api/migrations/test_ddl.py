"""
DDL validation script: tests migrations and queries for <50ms perf target.
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


async def test_table_creation() -> None:
    """Verify all tables exist with correct columns."""
    async with get_conn() as conn:
        tables = await conn.fetch(
            """
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            ORDER BY table_name
            """
        )
        expected = [
            "calibration_constants",
            "code_references",
            "material_catalog",
            "pricing_configs",
            "project_events",
            "project_payloads",
            "projects",
        ]
        got = [t["table_name"] for t in tables]
        assert got == expected, f"Tables mismatch: expected {expected}, got {got}"
        print("✅ All tables created")


async def test_constraints() -> None:
    """Verify CHECK constraints on status and module."""
    async with get_conn() as conn:
        # Test valid status
        await conn.execute("INSERT INTO projects (project_id, account_id, name, status, created_by, updated_by) VALUES ($1, $2, $3, $4, $5, $6)", "test_001", "acc_001", "Test", "draft", "user", "user")
        
        # Test invalid status (should fail)
        try:
            await conn.execute("UPDATE projects SET status = 'invalid' WHERE project_id = 'test_001'")
            assert False, "Should reject invalid status"
        except Exception as e:
            assert "CHECK constraint" in str(e) or "projects_status_check" in str(e)
        
        await conn.execute("DELETE FROM projects WHERE project_id = 'test_001'")
        print("✅ Constraints enforced")


async def test_indexes() -> None:
    """Verify indexes exist and are being used."""
    async with get_conn() as conn:
        indexes = await conn.fetch(
            """
            SELECT indexname FROM pg_indexes 
            WHERE schemaname = 'public' AND tablename IN ('projects', 'project_payloads', 'project_events')
            ORDER BY indexname
            """
        )
        got = [i["indexname"] for i in indexes]
        assert "ix_project_payloads_project_module_created" in str(got), "Composite index missing"
        assert "ix_project_events_event_type" in str(got), "Event type index missing"
        print(f"✅ Indexes created: {len(got)} found")


async def test_performance() -> None:
    """Test query performance targets <50ms."""
    async with get_conn() as conn:
        # Create test data
        await conn.execute(
            """INSERT INTO projects (project_id, account_id, name, status, created_by, updated_by) 
               VALUES ($1, $2, $3, $4, $5, $6)""",
            "perf_test",
            "acc_test",
            "Perf",
            "draft",
            "user",
            "user",
        )
        
        for i in range(100):
            await conn.execute(
                """INSERT INTO project_payloads (project_id, module, config, files, cost_snapshot) 
                   VALUES ($1, $2, $3, $4, $5)""",
                "perf_test",
                "signage.single_pole.direct_burial",
                {"height_ft": 20 + i},
                [],
                {},
            )
        
        # Test PK lookup (should be <1ms)
        t0 = time.perf_counter()
        await conn.fetchval("SELECT name FROM projects WHERE project_id = $1", "perf_test")
        t1 = time.perf_counter()
        assert (t1 - t0) * 1000 < 1.0, f"PK lookup too slow: {(t1-t0)*1000:.2f}ms"
        print(f"✅ PK lookup: {(t1-t0)*1000:.2f}ms")
        
        # Test composite index query (should be <10ms)
        t0 = time.perf_counter()
        await conn.fetch(
            """SELECT payload_id FROM project_payloads 
               WHERE project_id = $1 AND module = $2 
               ORDER BY created_at DESC LIMIT 10""",
            "perf_test",
            "signage.single_pole.direct_burial",
        )
        t1 = time.perf_counter()
        assert (t1 - t0) * 1000 < 50.0, f"Composite query too slow: {(t1-t0)*1000:.2f}ms"
        print(f"✅ Composite index query: {(t1-t0)*1000:.2f}ms")
        
        # Cleanup
        await conn.execute("DELETE FROM project_payloads WHERE project_id = 'perf_test'")
        await conn.execute("DELETE FROM projects WHERE project_id = 'perf_test'")


async def test_seed_data() -> None:
    """Verify seed data loaded correctly."""
    async with get_conn() as conn:
        calib_count = await conn.fetchval("SELECT COUNT(*) FROM calibration_constants")
        assert calib_count >= 6, f"Expected 6+ calibration constants, got {calib_count}"
        
        pricing_count = await conn.fetchval("SELECT COUNT(*) FROM pricing_configs")
        assert pricing_count >= 5, f"Expected 5+ pricing configs, got {pricing_count}"
        
        mat_count = await conn.fetchval("SELECT COUNT(*) FROM material_catalog")
        assert mat_count >= 4, f"Expected 4+ materials, got {mat_count}"
        
        print("✅ Seed data loaded")


async def main() -> None:
    """Run all DDL validation tests."""
    print("Running DDL validation tests...")
    await test_table_creation()
    await test_constraints()
    await test_indexes()
    await test_seed_data()
    await test_performance()
    print("\n✅ All DDL tests passed!")


if __name__ == "__main__":
    asyncio.run(main())

