#!/bin/bash

# Startup script for the application with database backup
echo "🚀 Starting Email Redirect Tool..."

# Ensure data directory exists
if [ ! -d "/opt/render/project/data" ]; then
    echo "📁 Creating data directory..."
    mkdir -p /opt/render/project/data
fi

# Check database status
if [ -f "/opt/render/project/data/redirect_tool.db" ]; then
    echo "✅ Database found at: /opt/render/project/data/redirect_tool.db"
    echo "📊 Database size: $(du -h /opt/render/project/data/redirect_tool.db | cut -f1)"

    # Create a backup of the database before starting
    BACKUP_NAME="/opt/render/project/data/redirect_tool_backup_$(date +%Y%m%d_%H%M%S).db"
    cp /opt/render/project/data/redirect_tool.db "$BACKUP_NAME"
    echo "💾 Created database backup: $BACKUP_NAME"

    # Keep only the 3 most recent backups to save space
    cd /opt/render/project/data
    ls -t redirect_tool_backup_*.db 2>/dev/null | tail -n +4 | xargs rm -f 2>/dev/null
    echo "🧹 Cleaned old backups (keeping 3 most recent)"
else
    echo "📝 No existing database found, will create new one"
fi

# Set environment variable to ensure app uses persistent path
export DATABASE_PATH=/opt/render/project/data/redirect_tool.db

echo "🌐 Starting Gunicorn server..."
exec gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 600 --graceful-timeout 600 app:app