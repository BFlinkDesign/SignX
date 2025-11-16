#!/bin/bash
# Create backup directories with proper ownership

set -e

echo "Creating backup directories..."
mkdir -p backups/postgres backups/redis backups/config backups/minio
mkdir -p backups/logs/api backups/logs/worker backups/logs/db

echo "Setting permissions..."
chmod -R 755 backups/
chmod -R 777 backups/postgres backups/redis backups/minio
chmod -R 755 backups/config

echo "✅ Backup directories created successfully"

