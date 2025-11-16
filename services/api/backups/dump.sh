#!/bin/bash
# Daily PostgreSQL backup script with retention

set -e

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="${BACKUP_DIR:-/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
DB_NAME="${DB_NAME:-apex}"
DB_USER="${DB_USER:-apex}"
DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"

export PGPASSWORD="${POSTGRES_PASSWORD:-apex}"

echo "Starting backup at $(date)"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Full database dump
pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
  --format=custom \
  --compress=9 \
  --verbose \
  --file="$BACKUP_DIR/apex_full_${DATE}.dump"

echo "Backup completed: apex_full_${DATE}.dump"

# Calculate size
SIZE=$(du -h "$BACKUP_DIR/apex_full_${DATE}.dump" | cut -f1)
echo "Backup size: $SIZE"

# Cleanup old backups
find "$BACKUP_DIR" -name "apex_full_*.dump" -mtime +$RETENTION_DAYS -delete
echo "Cleaned up backups older than $RETENTION_DAYS days"

echo "Backup script finished at $(date)"

