#!/bin/bash
# Create monthly partition for project_events

set -e

YEAR="${1:-$(date +%Y)}"
MONTH="${2:-$(date +%m)}"

if ! [[ "$MONTH" =~ ^[01][0-9]$ ]]; then
    echo "Invalid month: $MONTH (must be 01-12)"
    exit 1
fi

if ! [[ "$YEAR" =~ ^[0-9]{4}$ ]]; then
    echo "Invalid year: $YEAR (must be YYYY)"
    exit 1
fi

PARTITION_NAME="project_events_${YEAR}_${MONTH}"
START_DATE="${YEAR}-${MONTH}-01"

# Calculate next month
if [ "$MONTH" = "12" ]; then
    NEXT_YEAR=$((YEAR + 1))
    NEXT_MONTH="01"
else
    NEXT_YEAR="$YEAR"
    NEXT_MONTH=$(printf "%02d" $((10#$MONTH + 1)))
fi

END_DATE="${NEXT_YEAR}-${NEXT_MONTH}-01"

echo "Creating partition: $PARTITION_NAME"
echo "Date range: $START_DATE to $END_DATE"

psql -U apex apex <<EOF
-- Create partition
CREATE TABLE IF NOT EXISTS ${PARTITION_NAME} PARTITION OF project_events
FOR VALUES FROM ('${START_DATE}') TO ('${END_DATE}');

-- Register in metadata
INSERT INTO partition_metadata (table_name, partition_name, partition_type, partition_key)
VALUES ('project_events', '${PARTITION_NAME}', 'range', '${START_DATE} to ${END_DATE}')
ON CONFLICT DO NOTHING;

-- Create indexes on partition
CREATE INDEX IF NOT EXISTS ix_${PARTITION_NAME}_project_id ON ${PARTITION_NAME}(project_id);
CREATE INDEX IF NOT EXISTS ix_${PARTITION_NAME}_event_type ON ${PARTITION_NAME}(event_type);
CREATE INDEX IF NOT EXISTS ix_${PARTITION_NAME}_timestamp ON ${PARTITION_NAME}(timestamp DESC);
EOF

echo "Partition created: $PARTITION_NAME"

