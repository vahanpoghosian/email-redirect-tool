#!/usr/bin/env python3
"""
Database utilities for backup, restore, and maintenance
"""

import os
import shutil
import sqlite3
from datetime import datetime
import json

def backup_database(source_path=None, backup_dir=None):
    """Create a backup of the database"""
    if not source_path:
        source_path = os.environ.get('DATABASE_PATH', 'redirect_tool.db')

    if not backup_dir:
        backup_dir = os.path.dirname(source_path) if '/' in source_path else '.'

    if not os.path.exists(source_path):
        print(f"❌ Database not found at: {source_path}")
        return None

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f"redirect_tool_backup_{timestamp}.db"
    backup_path = os.path.join(backup_dir, backup_name)

    try:
        shutil.copy2(source_path, backup_path)
        print(f"✅ Database backed up to: {backup_path}")
        return backup_path
    except Exception as e:
        print(f"❌ Backup failed: {e}")
        return None

def restore_database(backup_path, target_path=None):
    """Restore database from backup"""
    if not target_path:
        target_path = os.environ.get('DATABASE_PATH', 'redirect_tool.db')

    if not os.path.exists(backup_path):
        print(f"❌ Backup not found at: {backup_path}")
        return False

    try:
        # Create a safety backup of current database if it exists
        if os.path.exists(target_path):
            safety_backup = f"{target_path}.before_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy2(target_path, safety_backup)
            print(f"💾 Created safety backup: {safety_backup}")

        # Restore from backup
        shutil.copy2(backup_path, target_path)
        print(f"✅ Database restored from: {backup_path}")
        return True
    except Exception as e:
        print(f"❌ Restore failed: {e}")
        return False

def export_database_to_json(db_path=None, output_path=None):
    """Export database to JSON for migration"""
    if not db_path:
        db_path = os.environ.get('DATABASE_PATH', 'redirect_tool.db')

    if not output_path:
        output_path = f"database_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        export_data = {}

        # Export all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()

        for table_row in tables:
            table_name = table_row['name']
            cursor.execute(f"SELECT * FROM {table_name}")
            rows = cursor.fetchall()

            export_data[table_name] = []
            for row in rows:
                export_data[table_name].append(dict(row))

        conn.close()

        # Write to JSON
        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)

        print(f"✅ Database exported to: {output_path}")
        return output_path
    except Exception as e:
        print(f"❌ Export failed: {e}")
        return None

def import_database_from_json(json_path, db_path=None):
    """Import database from JSON"""
    if not db_path:
        db_path = os.environ.get('DATABASE_PATH', 'redirect_tool.db')

    if not os.path.exists(json_path):
        print(f"❌ JSON file not found: {json_path}")
        return False

    try:
        # Read JSON
        with open(json_path, 'r') as f:
            import_data = json.load(f)

        # Initialize database with schema
        from models import Database
        db = Database(db_path)

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Import data for each table
        for table_name, rows in import_data.items():
            if table_name == 'sqlite_sequence':
                continue  # Skip system table

            for row in rows:
                # Build INSERT query
                columns = list(row.keys())
                placeholders = ['?' for _ in columns]
                values = [row[col] for col in columns]

                query = f"INSERT OR REPLACE INTO {table_name} ({','.join(columns)}) VALUES ({','.join(placeholders)})"

                try:
                    cursor.execute(query, values)
                except Exception as row_error:
                    print(f"⚠️ Error importing row to {table_name}: {row_error}")

        conn.commit()
        conn.close()

        print(f"✅ Database imported from: {json_path}")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def check_database_health(db_path=None):
    """Check database health and statistics"""
    if not db_path:
        db_path = os.environ.get('DATABASE_PATH', 'redirect_tool.db')

    if not os.path.exists(db_path):
        print(f"❌ Database not found at: {db_path}")
        return False

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        print(f"\n📊 Database Health Check: {db_path}")
        print(f"📁 File size: {os.path.getsize(db_path) / 1024 / 1024:.2f} MB")

        # Check each table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()

        for table_row in tables:
            table_name = table_row[0]
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"  📋 {table_name}: {count} records")

        # Run integrity check
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()[0]

        if result == "ok":
            print("✅ Database integrity: PASSED")
        else:
            print(f"❌ Database integrity: FAILED - {result}")

        conn.close()
        return True
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python db_utils.py backup [source_path] [backup_dir]")
        print("  python db_utils.py restore <backup_path> [target_path]")
        print("  python db_utils.py export [db_path] [output_json]")
        print("  python db_utils.py import <json_path> [db_path]")
        print("  python db_utils.py health [db_path]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "backup":
        source = sys.argv[2] if len(sys.argv) > 2 else None
        backup_dir = sys.argv[3] if len(sys.argv) > 3 else None
        backup_database(source, backup_dir)

    elif command == "restore":
        if len(sys.argv) < 3:
            print("❌ Please specify backup path")
            sys.exit(1)
        backup_path = sys.argv[2]
        target = sys.argv[3] if len(sys.argv) > 3 else None
        restore_database(backup_path, target)

    elif command == "export":
        db_path = sys.argv[2] if len(sys.argv) > 2 else None
        output = sys.argv[3] if len(sys.argv) > 3 else None
        export_database_to_json(db_path, output)

    elif command == "import":
        if len(sys.argv) < 3:
            print("❌ Please specify JSON path")
            sys.exit(1)
        json_path = sys.argv[2]
        db_path = sys.argv[3] if len(sys.argv) > 3 else None
        import_database_from_json(json_path, db_path)

    elif command == "health":
        db_path = sys.argv[2] if len(sys.argv) > 2 else None
        check_database_health(db_path)

    else:
        print(f"❌ Unknown command: {command}")
        sys.exit(1)