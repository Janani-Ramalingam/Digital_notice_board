#!/usr/bin/env python
"""
Fix database migration for last_reminder_run field
Run this script to add the missing column to the database
"""

import os
import sys
import django
import sqlite3

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'digital_notice_board.settings')
django.setup()

from django.conf import settings

def fix_database_migration():
    """Add the missing last_reminder_run column to SystemSettings table"""
    try:
        # Get database path
        db_path = settings.DATABASES['default']['NAME']
        
        print(f"🔧 Fixing database migration...")
        print(f"Database: {db_path}")
        
        # Connect to SQLite database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if column already exists
        cursor.execute("PRAGMA table_info(admin_app_systemsettings)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'last_reminder_run' in columns:
            print("✅ Column 'last_reminder_run' already exists in database")
            return True
        
        # Add the missing column
        print("➕ Adding 'last_reminder_run' column...")
        cursor.execute("""
            ALTER TABLE admin_app_systemsettings 
            ADD COLUMN last_reminder_run DATETIME NULL
        """)
        
        # Commit changes
        conn.commit()
        conn.close()
        
        print("✅ Successfully added 'last_reminder_run' column to database")
        
        # Mark migration as applied
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO django_migrations (app, name, applied) 
                VALUES ('admin_app', '0006_systemsettings_last_reminder_run', datetime('now'))
            """)
        
        print("✅ Migration marked as applied in django_migrations table")
        return True
        
    except Exception as e:
        print(f"❌ Error fixing database migration: {str(e)}")
        return False

if __name__ == '__main__':
    print("🔧 Database Migration Fix Tool")
    success = fix_database_migration()
    
    if success:
        print("\n✅ Database migration fixed successfully!")
        print("You can now access the admin settings page.")
    else:
        print("\n❌ Failed to fix database migration.")
        print("Please check the error messages above.")
