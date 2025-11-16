# APEX Database Backup Strategy

## Daily Backups

### Automated via Cron

```bash
# Add to crontab (daily at 2am UTC)
0 2 * * * /path/to/services/api/backups/dump.sh >> /var/log/apex_backups.log 2>&1
```

### Manual Backup

```bash
cd services/api/backups
./dump.sh
```

### Restore from Backup

```bash
# List available backups
ls -lh /backups/apex_full_*.dump

# Restore latest
pg_restore -h localhost -U apex -d apex --clean --if-exists /backups/apex_full_YYYYMMDD_HHMMSS.dump
```

## PITR Setup (Point-in-Time Recovery)

### WAL Archiving to MinIO

```bash
# Configure in postgresql.conf (via compose command args)
wal_level = replica
archive_mode = on
archive_command = 'aws s3 cp %p s3://apex-backups/wal/%f'

# Or to MinIO
archive_command = 'mc cp %p minio/apex-backups/wal/%f'
```

### PITR Recovery Test

```bash
# Create test DB
docker compose -f ../../infra/compose.yaml exec db createdb -U apex apex_test

# Restore base backup + WAL
docker compose -f ../../infra/compose.yaml exec db \
  pg_basebackup -h localhost -U apex -D /var/lib/postgresql/data_test -Ft -z

# Enable PITR recovery
echo "restore_command = 'mc cp minio/apex-backups/wal/%f %p'" > /var/lib/postgresql/data_test/recovery.conf
```

## Retention Policy

- **Daily backups**: 30 days
- **Weekly backups**: 12 weeks
- **Monthly backups**: 12 months
- **WAL archives**: 7 days (PITR window)

## Verification

```bash
# Check backup size
du -h /backups/apex_full_*.dump

# Verify backup integrity
pg_restore --list /backups/apex_full_YYYYMMDD.dump | head -20
```

