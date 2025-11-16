"""
Synthetic test data generator for scale testing.

Generates 100,000+ projects with realistic distributions for performance validation.
"""

from __future__ import annotations

import asyncio
import random
from datetime import datetime, timedelta, timezone
from typing import Any

import asyncpg


async def generate_projects(conn: asyncpg.Connection, count: int = 100000) -> None:
    """Generate projects with realistic data distributions."""
    accounts = [f"acc_{i:04d}" for i in range(100)]
    customers = [f"Customer_{i}" for i in range(500)]
    statuses = ["draft", "estimating", "submitted", "accepted", "rejected"]
    
    print(f"Generating {count} projects...")
    
    for i in range(count):
        project_id = f"proj_{i:08d}"
        account_id = random.choice(accounts)
        customer = random.choice(customers)
        status = random.choices(statuses, weights=[30, 25, 20, 15, 10])[0]
        confidence = round(random.uniform(0.6, 1.0), 3)
        constants_version = "constants_v1.0.0"
        
        await conn.execute(
            """
            INSERT INTO projects (
                project_id, account_id, name, customer, status, 
                created_by, updated_by, constants_version, confidence
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """,
            project_id, account_id, f"Project {i}", customer, status,
            "load_test", "load_test", constants_version, confidence
        )
        
        if (i + 1) % 10000 == 0:
            print(f"  Generated {i + 1:,} projects")


async def generate_payloads(conn: asyncpg.Connection, count: int = 100000) -> None:
    """Generate payloads for projects."""
    modules = [
        "signage.single_pole.direct_burial",
        "signage.single_pole.base_plate",
        "signage.two_pole.direct_burial",
    ]
    
    print(f"Generating {count} payloads...")
    
    for i in range(count):
        project_id = f"proj_{i:08d}"
        module = random.choice(modules)
        config = {
            "height_ft": random.randint(15, 40),
            "material": random.choice(["steel", "aluminum", "titanium"]),
            "wind_speed_mph": random.randint(80, 120),
        }
        files: list[str] = []
        cost_snapshot = {"base": 150.0, "addons": random.randint(0, 100)}
        sha256 = f"{hash(str(config)):064x}"
        
        await conn.execute(
            """
            INSERT INTO project_payloads (
                project_id, module, config, files, cost_snapshot, sha256
            ) VALUES ($1, $2, $3, $4, $5, $6)
            """,
            project_id, module, config, files, cost_snapshot, sha256
        )
        
        if (i + 1) % 10000 == 0:
            print(f"  Generated {i + 1:,} payloads")


async def generate_events(conn: asyncpg.Connection, count: int = 300000) -> None:
    """Generate events (multiple per project)."""
    event_types = [
        "project.created",
        "file.attached",
        "design.completed",
        "estimate.generated",
        "report.generated",
    ]
    
    print(f"Generating {count} events...")
    
    for i in range(count):
        project_id = f"proj_{(i // 3) % 100000:08d}"
        event_type = random.choice(event_types)
        actor = "load_test"
        data: dict[str, Any] = {}
        
        await conn.execute(
            """
            INSERT INTO project_events (project_id, event_type, actor, data)
            VALUES ($1, $2, $3, $4)
            """,
            project_id, event_type, actor, data
        )
        
        if (i + 1) % 50000 == 0:
            print(f"  Generated {i + 1:,} events")


async def main() -> None:
    """Run data generation."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate test data for scale testing")
    parser.add_argument("--projects", type=int, default=100000, help="Number of projects")
    parser.add_argument("--payloads", type=int, default=100000, help="Number of payloads")
    parser.add_argument("--events", type=int, default=300000, help="Number of events")
    args = parser.parse_args()
    
    print("Starting synthetic data generation...")
    start_time = datetime.now()
    
    conn = await asyncpg.connect("postgresql://apex:apex@localhost:5432/apex")
    try:
        await generate_projects(conn, args.projects)
        await generate_payloads(conn, args.payloads)
        await generate_events(conn, args.events)
        await conn.execute("ANALYZE projects, project_payloads, project_events")
        print("\nAnalysis complete")
    finally:
        await conn.close()
    
    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"\nData generation complete in {elapsed:.1f}s")
    print(f"Generated: {args.projects:,} projects, {args.payloads:,} payloads, {args.events:,} events")


if __name__ == "__main__":
    asyncio.run(main())

