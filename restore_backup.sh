#!/bin/bash

# Restore script for email redirect tool backups
# Usage: ./restore_backup.sh BACKUP_TIMESTAMP

if [ -z "$1" ]; then
    echo "Usage: $0 <backup_timestamp>"
    echo "Available backups:"
    ls backups/
    exit 1
fi

BACKUP_DIR="backups/$1"

if [ ! -d "$BACKUP_DIR" ]; then
    echo "Backup directory $BACKUP_DIR does not exist"
    exit 1
fi

echo "Restoring from backup: $BACKUP_DIR"

# Backup current state first
CURRENT_BACKUP="backups/pre_restore_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$CURRENT_BACKUP"
cp *.py requirements.txt *.db "$CURRENT_BACKUP/" 2>/dev/null
echo "Current state backed up to: $CURRENT_BACKUP"

# Restore files
echo "Restoring Python files..."
cp "$BACKUP_DIR"/*.py .
cp "$BACKUP_DIR"/requirements.txt .
cp "$BACKUP_DIR"/*.db . 2>/dev/null

# Restore frontend if exists
if [ -d "$BACKUP_DIR/frontend_src" ]; then
    echo "Restoring frontend source..."
    cp -r "$BACKUP_DIR"/frontend_src/* frontend/src/
fi

if [ -d "$BACKUP_DIR/frontend_build" ]; then
    echo "Restoring frontend build..."
    cp -r "$BACKUP_DIR"/frontend_build/* frontend/build/
fi

echo "Restore completed from backup: $1"