-- Load test data generation for performance benchmarking

-- Generate 10,000 test projects across 100 accounts
INSERT INTO projects (
    project_id, account_id, name, customer, description, status,
    created_by, updated_by, constants_version, confidence
)
SELECT 
    'proj_' || LPAD(s.id::text, 8, '0') as project_id,
    'acc_' || LPAD((s.id % 100)::text, 3, '0') as account_id,
    'Test Project ' || s.id as name,
    'Customer ' || (s.id % 50) as customer,
    'Load test project for performance benchmarking' as description,
    CASE (s.id % 5)
        WHEN 0 THEN 'draft'
        WHEN 1 THEN 'estimating'
        WHEN 2 THEN 'submitted'
        WHEN 3 THEN 'accepted'
        WHEN 4 THEN 'rejected'
    END as status,
    'load_test_user' as created_by,
    'load_test_user' as updated_by,
    'constants_v1.0.0' as constants_version,
    (RANDOM() * 0.4 + 0.6) as confidence  -- 0.6 to 1.0 range
FROM generate_series(1, 10000) s(id);

-- Generate payloads for each project
INSERT INTO project_payloads (
    project_id, module, config, files, cost_snapshot, sha256
)
SELECT 
    'proj_' || LPAD(s.id::text, 8, '0') as project_id,
    CASE (s.id % 3)
        WHEN 0 THEN 'signage.single_pole.direct_burial'
        WHEN 1 THEN 'signage.single_pole.base_plate'
        WHEN 2 THEN 'signage.two_pole.direct_burial'
    END as module,
    jsonb_build_object(
        'height_ft', 20 + (s.id % 15),
        'material', CASE (s.id % 3) WHEN 0 THEN 'steel' WHEN 1 THEN 'aluminum' ELSE 'titanium' END,
        'wind_speed_mph', 90 + (s.id % 40)
    ) as config,
    '[]'::jsonb as files,
    '{}'::jsonb as cost_snapshot,
    'sha256_' || LPAD(s.id::text, 32, '0') as sha256
FROM generate_series(1, 10000) s(id);

-- Generate events (3 events per project)
INSERT INTO project_events (
    project_id, event_type, actor, data
)
SELECT 
    'proj_' || LPAD(s.id::text, 8, '0') as project_id,
    e.event as event_type,
    'load_test_user' as actor,
    '{}'::jsonb as data
FROM generate_series(1, 10000) s(id)
CROSS JOIN (
    VALUES ('project.created'), ('file.attached'), ('design.completed')
) e(event);

-- Analyze tables for query planner
ANALYZE projects;
ANALYZE project_payloads;
ANALYZE project_events;

-- Show row counts
SELECT 
    'projects' as table_name,
    COUNT(*) as row_count,
    pg_size_pretty(pg_total_relation_size('projects')) as size
FROM projects
UNION ALL
SELECT 
    'project_payloads' as table_name,
    COUNT(*) as row_count,
    pg_size_pretty(pg_total_relation_size('project_payloads')) as size
FROM project_payloads
UNION ALL
SELECT 
    'project_events' as table_name,
    COUNT(*) as row_count,
    pg_size_pretty(pg_total_relation_size('project_events')) as size
FROM project_events;

