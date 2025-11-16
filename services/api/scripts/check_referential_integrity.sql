-- Data integrity validation: Check foreign keys, constraints, and orphaned records

\echo '=== Foreign Key Integrity ==='

-- Check project_payloads.project_id references
SELECT 
    'project_payloads orphaned' as check_name,
    COUNT(*) as violations
FROM project_payloads pp
LEFT JOIN projects p ON pp.project_id = p.project_id
WHERE p.project_id IS NULL

UNION ALL

-- Check project_events.project_id references
SELECT 
    'project_events orphaned',
    COUNT(*)
FROM project_events pe
LEFT JOIN projects p ON pe.project_id = p.project_id
WHERE p.project_id IS NULL;

\echo '=== Constraint Validation ==='

-- Check confidence range
SELECT 
    'confidence out of range' as check_name,
    COUNT(*) as violations
FROM projects
WHERE confidence < 0.0 OR confidence > 1.0

UNION ALL

-- Check status values
SELECT 
    'invalid status',
    COUNT(*)
FROM projects
WHERE status NOT IN ('draft', 'estimating', 'submitted', 'accepted', 'rejected')

UNION ALL

-- Check etag uniqueness
SELECT 
    'duplicate etags',
    COUNT(*) - COUNT(DISTINCT etag)
FROM projects
WHERE etag IS NOT NULL;

\echo '=== Data Quality Metrics ==='

-- Projects with complete payloads (all modules expected)
SELECT 
    'projects with all payloads' as metric,
    COUNT(*) as count
FROM (
    SELECT project_id
    FROM project_payloads
    GROUP BY project_id
    HAVING COUNT(DISTINCT module) = 3
) complete;

-- Projects with valid confidence scores
SELECT 
    'projects with confidence',
    COUNT(*)
FROM projects
WHERE confidence IS NOT NULL AND confidence >= 0.0 AND confidence <= 1.0;

-- Events with valid project_id
SELECT 
    'valid event references',
    COUNT(*)
FROM project_events pe
JOIN projects p ON pe.project_id = p.project_id;

\echo '=== Summary ==='

-- Overall integrity score
SELECT 
    'Overall Integrity' as metric,
    CASE 
        WHEN SUM(violations) = 0 THEN 'PASS'
        ELSE 'FAIL'
    END as status
FROM (
    SELECT COUNT(*) as violations
    FROM project_payloads pp
    LEFT JOIN projects p ON pp.project_id = p.project_id
    WHERE p.project_id IS NULL
    UNION ALL
    SELECT COUNT(*) FROM project_events pe
    LEFT JOIN projects p ON pe.project_id = p.project_id
    WHERE p.project_id IS NULL
    UNION ALL
    SELECT COUNT(*) FROM projects WHERE confidence < 0.0 OR confidence > 1.0
) integrity_checks;

