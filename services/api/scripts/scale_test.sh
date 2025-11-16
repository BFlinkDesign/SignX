#!/bin/bash
# Scale testing suite: Run load tests and measure performance

set -e

echo "=== APEX Database Scale Testing ==="
echo "Starting at $(date)"

# Ensure we have metrics directory
mkdir -p logs/scale_tests

# Scenario 1: Concurrent project creation
echo "Scenario 1: 100 concurrent project creations"
for i in {1..100}; do
    psql -U apex apex -c "INSERT INTO projects (project_id, account_id, name, status, created_by, updated_by) VALUES ('scenario1_$i', 'acc_test', 'Load Test $i', 'draft', 'test', 'test')" &
done
wait

# Scenario 2: Concurrent reads
echo "Scenario 2: 1000 concurrent read queries"
time (
    for i in {1..1000}; do
        psql -U apex apex -t -c "SELECT COUNT(*) FROM projects WHERE status = 'draft'" > /dev/null &
    done
    wait
)

# Scenario 3: Complex queries under load
echo "Scenario 3: Complex queries"
psql -U apex apex <<EOF
\timing on

-- Dashboard query
SELECT status, COUNT(*) as count, AVG(confidence) as avg_conf
FROM projects
WHERE account_id = 'acc_test'
GROUP BY status;

-- Latest payload query
SELECT p.project_id, pp.config
FROM projects p
LEFT JOIN LATERAL (
    SELECT * FROM project_payloads pp2
    WHERE pp2.project_id = p.project_id
    ORDER BY pp2.created_at DESC LIMIT 1
) pp ON true
WHERE p.status = 'estimating'
LIMIT 100;

-- Event audit query
SELECT e.event_type, COUNT(*) as count
FROM project_events e
JOIN projects p ON e.project_id = p.project_id
WHERE p.account_id = 'acc_test'
  AND e.timestamp > NOW() - INTERVAL '7 days'
GROUP BY e.event_type;
EOF

echo "Scale testing complete at $(date)"

