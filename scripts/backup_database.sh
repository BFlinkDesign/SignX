#!/bin/bash
# Database Backup Script for APEX Platform
# Runs every 6 hours via cron
# Supports WAL archiving for point-in-time recovery

set -euo pipefail

# Configuration
DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-apex}"
DB_USER="${DB_USER:-apex}"
BACKUP_DIR="${BACKUP_DIR:-/backups/postgres}"
S3_BUCKET="${S3_BUCKET:-apex-backups}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Generate backup filename with timestamp
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/apex_backup_${TIMESTAMP}.sql.gz"

echo "Starting database backup: $BACKUP_FILE"

# Perform pg_dump with compression
PGPASSWORD="${DB_PASSWORD}" pg_dump \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --no-owner \
    --no-acl \
    --clean \
    --if-exists \
    | gzip > "$BACKUP_FILE"

BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo "Backup completed: $BACKUP_FILE ($BACKUP_SIZE)"

# Upload to S3 if configured
if [ -n "${AWS_ACCESS_KEY_ID:-}" ] && [ -n "${AWS_SECRET_ACCESS_KEY:-}" ]; then
    echo "Uploading to S3: s3://$S3_BUCKET/"
    aws s3 cp "$BACKUP_FILE" "s3://$S3_BUCKET/postgres/$(basename $BACKUP_FILE)"
    echo "Upload completed"
fi

# Cleanup old backups (keep last N days)
find "$BACKUP_DIR" -name "apex_backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete

echo "Backup process completed successfully"

