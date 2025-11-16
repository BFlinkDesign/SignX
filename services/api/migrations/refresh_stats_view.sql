-- Refresh materialized view concurrently to avoid locking
-- Run via cron: */5 * * * * psql $DATABASE_URL -f refresh_stats_view.sql

REFRESH MATERIALIZED VIEW CONCURRENTLY project_stats;

-- Optional: VACUUM ANALYZE for query planner updates
VACUUM ANALYZE project_stats;
VACUUM ANALYZE projects;
VACUUM ANALYZE project_payloads;
VACUUM ANALYZE project_events;

