#!/usr/bin/env python
"""
AISC Database Verification for SIGN X Studio
Tests that the AISC shapes database is properly imported and functional
"""

import asyncio
import asyncpg
from datetime import datetime
import sys
import logging

logger = logging.getLogger(__name__)

# Database connection
DATABASE_URL = "postgresql://apex:apex@localhost:5432/apex"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def print_header(text):
    logger.info(f"\n{Colors.BLUE}{'='*60}{Colors.RESET}")
    logger.info(f"{Colors.BLUE}{text.center(60)}{Colors.RESET}")
    logger.info(f"{Colors.BLUE}{'='*60}{Colors.RESET}\n")

def print_pass(text):
    logger.info(f"{Colors.GREEN}[PASS]:{Colors.RESET} {text}")

def print_fail(text):
    logger.error(f"{Colors.RED}[FAIL]:{Colors.RESET} {text}")

def print_info(text):
    logger.info(f"{Colors.YELLOW}[INFO]:{Colors.RESET} {text}")


async def test_database_connection():
    """Test 1: Database Connection"""
    print_header("TEST 1: Database Connection")
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        await conn.close()
        print_pass("Connected to PostgreSQL database")
        return True
    except Exception as e:
        print_fail(f"Cannot connect to database: {e}")
        return False


async def test_aisc_table_exists(conn):
    """Test 2: AISC Table Exists"""
    print_header("TEST 2: AISC Table Structure")
    
    # Check if table exists
    exists = await conn.fetchval("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'aisc_shapes_v16'
        )
    """)
    
    if not exists:
        print_fail("aisc_shapes_v16 table does not exist")
        return False
    
    print_pass("aisc_shapes_v16 table exists")
    
    # Check columns
    columns = await conn.fetch("""
        SELECT column_name, data_type 
        FROM information_schema.columns
        WHERE table_name = 'aisc_shapes_v16'
        ORDER BY ordinal_position
    """)
    
    print_info(f"Table has {len(columns)} columns")
    essential_cols = ['aisc_manual_label', 'type', 'w', 'd', 'ix', 'sx']
    for col in essential_cols:
        if any(c['column_name'] == col for c in columns):
            print_pass(f"Column '{col}' present")
        else:
            print_fail(f"Column '{col}' missing")
            return False
    
    return True


async def test_shape_counts(conn):
    """Test 3: Shape Inventory"""
    print_header("TEST 3: AISC Shape Inventory")
    
    # Total count
    total = await conn.fetchval("SELECT COUNT(*) FROM aisc_shapes_v16")
    print_info(f"Total shapes in database: {total}")
    
    if total == 0:
        print_fail("Database is empty!")
        return False
    elif total < 1000:
        print_fail(f"Only {total} shapes found (expected 1500+)")
        return False
    else:
        print_pass(f"{total} shapes found (expected 1500+)")
    
    # Count by type
    logger.info("\n  Shape breakdown by type:")
    type_counts = await conn.fetch("""
        SELECT type, COUNT(*) as count
        FROM aisc_shapes_v16
        GROUP BY type
        ORDER BY count DESC
    """)
    
    for row in type_counts:
        logger.info(f"    {row['type']:15s}: {row['count']:4d} shapes")
    
    # Check for expected types
    types = [r['type'] for r in type_counts]
    expected_types = ['HSS', 'PIPE', 'W', 'C', 'L', 'WT']
    
    for expected in expected_types:
        if expected in types:
            print_pass(f"Type '{expected}' present")
        else:
            print_fail(f"Type '{expected}' missing")
    
    return True


async def test_a1085_flags(conn):
    """Test 4: ASTM A1085 Flags"""
    print_header("TEST 4: ASTM A1085 HSS Shapes")
    
    a1085_count = await conn.fetchval("""
        SELECT COUNT(*) FROM aisc_shapes_v16 
        WHERE is_astm_a1085 = true
    """)
    
    print_info(f"A1085 HSS shapes: {a1085_count}")
    
    if a1085_count == 0:
        print_fail("No A1085 shapes marked (expected ~94)")
        return False
    elif a1085_count < 80:
        print_fail(f"Only {a1085_count} A1085 shapes (expected ~94)")
        return False
    else:
        print_pass(f"{a1085_count} A1085 shapes marked")
    
    # Show some examples
    examples = await conn.fetch("""
        SELECT aisc_manual_label, w, d
        FROM aisc_shapes_v16
        WHERE is_astm_a1085 = true
        ORDER BY w
        LIMIT 5
    """)
    
    logger.info("\n  Example A1085 sections:")
    for ex in examples:
        logger.info(f"    {ex['aisc_manual_label']:20s} W={ex['w']:.1f} lb/ft, D={ex['d']:.2f} in")
    
    return True


async def test_indexes(conn):
    """Test 5: Performance Indexes"""
    print_header("TEST 5: Database Indexes")
    
    indexes = await conn.fetch("""
        SELECT indexname, indexdef
        FROM pg_indexes
        WHERE tablename = 'aisc_shapes_v16'
        ORDER BY indexname
    """)
    
    print_info(f"Found {len(indexes)} indexes")
    
    essential_indexes = ['idx_aisc_type', 'idx_aisc_weight', 'idx_aisc_ix']
    for idx_name in essential_indexes:
        if any(idx_name in idx['indexname'] for idx in indexes):
            print_pass(f"Index '{idx_name}' exists")
        else:
            print_fail(f"Index '{idx_name}' missing (performance impact)")
    
    return True


async def test_eagle_sign_queries(conn):
    """Test 6: Real Eagle Sign Queries"""
    print_header("TEST 6: Eagle Sign Project Queries")
    
    # Test 1: 8" monument pole selection
    logger.info("\n  Query 1: 8\" diameter poles for monument sign")
    start = datetime.now()
    results = await conn.fetch("""
        SELECT aisc_manual_label, w, d, ix, sx
        FROM aisc_shapes_v16
        WHERE type IN ('HSS', 'PIPE') 
          AND nominal_depth = 8
          AND w <= 50
        ORDER BY w
        LIMIT 5
    """)
    elapsed = (datetime.now() - start).total_seconds() * 1000
    
    if len(results) > 0:
        print_pass(f"Found {len(results)} suitable 8\" poles in {elapsed:.1f}ms")
        for r in results:
            logger.info(f"    {r['aisc_manual_label']:20s} W={r['w']:.1f} lb/ft, Ix={r['ix']:.1f} in⁴")
    else:
        print_fail("No 8\" poles found")
        return False
    
    # Test 2: Cantilever arm sections
    logger.info("\n  Query 2: HSS sections for cantilever arms")
    start = datetime.now()
    results = await conn.fetch("""
        SELECT aisc_manual_label, w, d, tw, ix
        FROM aisc_shapes_v16
        WHERE type = 'HSS'
          AND w <= 50
          AND d >= 6
          AND d <= 12
        ORDER BY ix DESC
        LIMIT 5
    """)
    elapsed = (datetime.now() - start).total_seconds() * 1000
    
    if len(results) > 0:
        print_pass(f"Found {len(results)} cantilever sections in {elapsed:.1f}ms")
        for r in results:
            logger.info(f"    {r['aisc_manual_label']:20s} W={r['w']:.1f} lb/ft, Ix={r['ix']:.1f} in⁴")
    else:
        print_fail("No cantilever sections found")
        return False
    
    # Test 3: Cost-optimized selection
    logger.info("\n  Query 3: Cost-optimized pole (moment=150 kip-ft)")
    start = datetime.now()
    results = await conn.fetch("""
        SELECT aisc_manual_label, w, d, ix, sx, (w * 0.90) as cost_per_ft
        FROM aisc_shapes_v16
        WHERE type = 'HSS'
          AND nominal_depth >= 10
          AND ix > 300
          AND w < 100
        ORDER BY (w * 0.90) ASC
        LIMIT 5
    """)
    elapsed = (datetime.now() - start).total_seconds() * 1000
    
    if len(results) > 0:
        print_pass(f"Found {len(results)} cost-optimized options in {elapsed:.1f}ms")
        logger.info(f"    (Material cost @ $0.90/lb)")
        for r in results:
            logger.info(f"    {r['aisc_manual_label']:20s} ${r['cost_per_ft']:.2f}/ft, Ix={r['ix']:.1f} in⁴")
    else:
        print_fail("No cost-optimized sections found")
        return False
    
    return True


async def test_cantilever_tables(conn):
    """Test 7: Cantilever Table Integration"""
    print_header("TEST 7: Cantilever Tables")
    
    # Check if cantilever tables exist
    tables = ['cantilever_configs', 'cantilever_results']
    
    for table in tables:
        exists = await conn.fetchval(f"""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = '{table}'
            )
        """)
        
        if exists:
            print_pass(f"Table '{table}' exists")
        else:
            print_fail(f"Table '{table}' missing")
            return False
    
    # Check foreign keys to AISC
    fkeys = await conn.fetch("""
        SELECT
            tc.table_name,
            kcu.column_name,
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
          ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage AS ccu
          ON ccu.constraint_name = tc.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY'
          AND tc.table_name LIKE 'cantilever%'
          AND ccu.table_name = 'aisc_shapes_v16'
    """)
    
    if len(fkeys) > 0:
        print_pass(f"Found {len(fkeys)} foreign keys to AISC catalog")
        for fk in fkeys:
            logger.info(f"    {fk['table_name']}.{fk['column_name']} -> {fk['foreign_table_name']}.{fk['foreign_column_name']}")
    else:
        print_fail("No foreign keys to AISC catalog found")
    
    return True


async def main():
    """Run all verification tests"""
    print_header("SIGN X Studio - AISC Database Verification")
    logger.info(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test 1: Connection
    if not await test_database_connection():
        logger.info("\n" + Colors.RED + "ABORT: Cannot connect to database" + Colors.RESET)
        return False
    
    # Connect for remaining tests
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        tests = [
            test_aisc_table_exists,
            test_shape_counts,
            test_a1085_flags,
            test_indexes,
            test_eagle_sign_queries,
            test_cantilever_tables,
        ]
        
        results = []
        for test in tests:
            try:
                result = await test(conn)
                results.append(result)
            except Exception as e:
                print_fail(f"Test error: {e}")
                results.append(False)
        
        # Summary
        print_header("VERIFICATION SUMMARY")
        passed = sum(results)
        total = len(results)
        
        logger.info(f"\nTests passed: {passed}/{total}")
        
        if passed == total:
            logger.info(f"\n{Colors.GREEN}{'='*60}{Colors.RESET}")
            logger.info(f"{Colors.GREEN}{'ALL TESTS PASSED'.center(60)}{Colors.RESET}")
            logger.info(f"{Colors.GREEN}AISC database is fully functional for Eagle Sign projects{Colors.RESET}")
            logger.info(f"{Colors.GREEN}{'='*60}{Colors.RESET}\n")
            return True
        else:
            logger.info(f"\n{Colors.RED}{'='*60}{Colors.RESET}")
            logger.error(f"{Colors.RED}{f'{total - passed} TESTS FAILED'.center(60)}{Colors.RESET}")
            logger.error(f"{Colors.RED}Review errors above and fix issues{Colors.RESET}")
            logger.info(f"{Colors.RED}{'='*60}{Colors.RESET}\n")
            return False
            
    finally:
        await conn.close()


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
