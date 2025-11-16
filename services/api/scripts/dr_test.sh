#!/bin/bash
# Disaster recovery test script

set -e

BACKUP_FILE="${1:-/backups/apex_full_$(date +%Y%m%d).dump}"
TEST_DB="${TEST_DB:-apex_test}"
MAIN_DB="${MAIN_DB:-apex}"

echo "DR Test: Starting at $(date)"
echo "Backup file: $BACKUP_FILE"
echo "Test database: $TEST_DB"

# Create test database
createdb -U apex "$TEST_DB" || echo "Test DB already exists"

# Restore backup
echo "Restoring backup to test database..."
pg_restore -h localhost -U apex -d "$TEST_DB" --clean --if-exists --verbose "$BACKUP_FILE"

# Verify row counts
echo "Verifying row counts..."
psql -U apex -d "$TEST_DB" -c "
SELECT 
    'projects' as table_name,
    COUNT(*) as row_count
FROM projects
UNION ALL
SELECT 
    'project_payloads' as table_name,
    COUNT(*) as row_count
FROM project_payloads
UNION ALL
SELECT 
    'project_events' as table_name,
    COUNT(*) as row_count
FROM project_events;
"

# Test critical queries
echo "Testing critical queries..."

psql -U apex -d "$TEST_DB" -c "
\timing on
-- Test 1: Status filtering
SELECT COUNT(*) FROM projects WHERE status = 'draft';

-- Test 2: Latest payload
SELECT COUNT(*) FROM project_payloads ORDER BY created_at DESC LIMIT 100;

-- Test 3: Event audit
SELECT COUNT(*) FROM project_events WHERE timestamp > NOW() - INTERVAL '30 days';
"

echo "DR Test: Completed at $(date)"
echo "Test database preserved for manual inspection: $TEST_DB"
echo "Drop with: dropdb -U apex $TEST_DB"

