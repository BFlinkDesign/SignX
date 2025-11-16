#!/bin/bash
# Database Restore Script for APEX Platform
# Restores from backup file or S3

set -euo pipefail

# Configuration
DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-apex}"
DB_USER="${DB_USER:-apex}"
BACKUP_FILE="${1:-}"
S3_BACKUP_PATH="${S3_BACKUP_PATH:-}"

if [ -z "$BACKUP_FILE" ] && [ -z "$S3_BACKUP_PATH" ]; then
    echo "Usage: $0 <backup_file.sql.gz>"
    echo "   or: $0 --s3 s3://bucket/path/to/backup.sql.gz"
    exit 1
fi

# Download from S3 if specified
if [ -n "$S3_BACKUP_PATH" ]; then
    echo "Downloading backup from S3: $S3_BACKUP_PATH"
    BACKUP_FILE="/tmp/restore_$(basename $S3_BACKUP_PATH)"
    aws s3 cp "$S3_BACKUP_PATH" "$BACKUP_FILE"
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "ERROR: Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "WARNING: This will DROP and recreate the database!"
echo "Press Ctrl+C to cancel, or Enter to continue..."
read

# Restore database
echo "Restoring database from: $BACKUP_FILE"

# Drop and recreate (from --clean flag in backup)
gunzip -c "$BACKUP_FILE" | \
    PGPASSWORD="${DB_PASSWORD}" psql \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME"

echo "Database restore completed successfully"

# Cleanup temp file if from S3
if [ -n "$S3_BACKUP_PATH" ]; then
    rm -f "$BACKUP_FILE"
fi

