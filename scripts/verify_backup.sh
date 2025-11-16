#!/bin/bash
# Backup Verification Script
# Verifies backup functionality and restore procedures

set -e

echo "=== Backup Verification ==="
echo ""

# Check backups directory exists
echo "1. Checking backups directory..."
if [ -d "infra/backups" ]; then
    echo "   ✅ Backups directory exists"
else
    echo "   ⚠️  Backups directory missing, creating..."
    mkdir -p infra/backups
    chmod 755 infra/backups
fi

# Test database backup
echo ""
echo "2. Testing database backup..."
cd infra

if docker compose ps db | grep -q "running"; then
    BACKUP_FILE="backups/test_backup_$(date +%Y%m%d_%H%M%S).sql"
    
    if docker compose exec -T db pg_dump -U apex apex > "../$BACKUP_FILE" 2>/dev/null; then
        BACKUP_SIZE=$(stat -f%z "../$BACKUP_FILE" 2>/dev/null || stat -c%s "../$BACKUP_FILE" 2>/dev/null || echo "0")
        if [ "$BACKUP_SIZE" -gt 0 ]; then
            echo "   ✅ Backup created successfully ($(numfmt --to=iec-i --suffix=B $BACKUP_SIZE 2>/dev/null || echo "${BACKUP_SIZE} bytes"))"
            echo "   Backup file: $BACKUP_FILE"
            
            # Clean up test backup
            rm -f "../$BACKUP_FILE"
        else
            echo "   ❌ Backup file is empty"
            exit 1
        fi
    else
        echo "   ❌ Backup failed"
        exit 1
    fi
else
    echo "   ⚠️  Database not running, skipping backup test"
fi

# Verify backup script exists
echo ""
echo "3. Checking backup scripts..."
if [ -f "services/api/backups/dump.sh" ]; then
    echo "   ✅ Backup script exists"
    if [ -x "services/api/backups/dump.sh" ]; then
        echo "   ✅ Backup script is executable"
    else
        echo "   ⚠️  Backup script not executable (chmod +x)"
    fi
else
    echo "   ⚠️  Backup script not found"
fi

# Check volume backups
echo ""
echo "4. Checking volume backup strategy..."
VOLUMES=$(docker volume ls | grep apex | wc -l)
if [ "$VOLUMES" -gt 0 ]; then
    echo "   ✅ $VOLUMES Docker volumes found"
    echo "   ℹ️  Volume backups should be handled by infrastructure (Docker volume snapshots)"
else
    echo "   ℹ️  No volumes yet (will be created on first deployment)"
fi

# Verify restore procedure documented
echo ""
echo "5. Verifying restore documentation..."
if [ -f "docs/operations/disaster-recovery.md" ]; then
    echo "   ✅ Disaster recovery documentation exists"
else
    echo "   ⚠️  Disaster recovery documentation not found"
fi

echo ""
echo "=== Backup Verification Complete ==="

