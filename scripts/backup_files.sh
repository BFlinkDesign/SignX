#!/bin/bash
# File Backup Script for APEX Platform
# Replicates MinIO files to S3 for disaster recovery
# Runs every 6 hours via cron

set -euo pipefail

# Configuration
MINIO_ENDPOINT="${MINIO_ENDPOINT:-http://object:9000}"
MINIO_ACCESS_KEY="${MINIO_ACCESS_KEY:-minioadmin}"
MINIO_SECRET_KEY="${MINIO_SECRET_KEY:-minioadmin}"
MINIO_BUCKET="${MINIO_BUCKET:-apex-uploads}"
S3_BACKUP_BUCKET="${S3_BACKUP_BUCKET:-apex-backups}"
S3_PREFIX="${S3_PREFIX:-files/}"

echo "Starting file backup from MinIO to S3"

# Use MinIO client (mc) or rclone for replication
if command -v mc &> /dev/null; then
    # Configure MinIO client
    mc alias set backup "$MINIO_ENDPOINT" "$MINIO_ACCESS_KEY" "$MINIO_SECRET_KEY" --api s3v4
    
    # Mirror to S3
    echo "Mirroring $MINIO_BUCKET to s3://$S3_BACKUP_BUCKET/$S3_PREFIX"
    mc mirror --remove "backup/$MINIO_BUCKET" "s3://$S3_BACKUP_BUCKET/$S3_PREFIX"
    
elif command -v rclone &> /dev/null; then
    # Configure rclone
    rclone config create minio_backup s3 \
        provider MinIO \
        endpoint "$MINIO_ENDPOINT" \
        access_key_id "$MINIO_ACCESS_KEY" \
        secret_access_key "$MINIO_SECRET_KEY"
    
    # Copy to S3
    echo "Copying files to S3"
    rclone copy "minio_backup:$MINIO_BUCKET" "s3:$S3_BACKUP_BUCKET/$S3_PREFIX" \
        --progress \
        --checksum \
        --transfers 10
else
    echo "ERROR: Neither 'mc' nor 'rclone' found. Install one to enable file backups."
    exit 1
fi

echo "File backup completed successfully"

