#!/usr/bin/env python3
"""Migrate database from root directory to instance/ directory.

This script:
1. Checks if database.db exists in the root
2. Copies it to instance/database.db (if it doesn't already exist)
3. Verifies the migration was successful
4. Optionally backs up the old file
"""

import os
import shutil
import sqlite3
from pathlib import Path

OLD_DB_PATH = 'database.db'
NEW_DB_PATH = 'instance/database.db'


def verify_database(db_path):
    """Verify that a database file exists and has tables."""
    if not os.path.exists(db_path):
        return False, "File does not exist"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        if not tables:
            return False, "Database exists but has no tables"
        
        return True, f"Database has {len(tables)} tables: {', '.join(tables)}"
    except Exception as e:
        return False, f"Error reading database: {e}"


def migrate_database():
    """Migrate database from old location to new location."""
    print("=" * 60)
    print("Database Migration Script")
    print("=" * 60)
    print()
    
    # Check if old database exists
    old_exists = os.path.exists(OLD_DB_PATH)
    new_exists = os.path.exists(NEW_DB_PATH)
    
    print(f"Old database location: {OLD_DB_PATH}")
    print(f"  Exists: {old_exists}")
    if old_exists:
        old_valid, old_msg = verify_database(OLD_DB_PATH)
        print(f"  Status: {old_msg}")
        old_size = os.path.getsize(OLD_DB_PATH)
        print(f"  Size: {old_size:,} bytes")
    
    print()
    print(f"New database location: {NEW_DB_PATH}")
    print(f"  Exists: {new_exists}")
    if new_exists:
        new_valid, new_msg = verify_database(NEW_DB_PATH)
        print(f"  Status: {new_msg}")
        new_size = os.path.getsize(NEW_DB_PATH)
        print(f"  Size: {new_size:,} bytes")
    
    print()
    
    # Determine what to do
    if not old_exists:
        print("✓ No old database found. Nothing to migrate.")
        if new_exists:
            print(f"✓ New database already exists at {NEW_DB_PATH}")
        else:
            print(f"⚠ New database doesn't exist. Run 'python init_db.py' to create it.")
        return True
    
    if new_exists:
        print("⚠ Both old and new databases exist!")
        print()
        response = input("Do you want to overwrite the new database with the old one? (yes/no): ").strip().lower()
        if response not in ['yes', 'y']:
            print("Migration cancelled.")
            return False
        
        # Backup the new database first
        backup_path = f"{NEW_DB_PATH}.backup"
        print(f"Backing up existing new database to {backup_path}...")
        shutil.copy2(NEW_DB_PATH, backup_path)
        print("✓ Backup created")
    
    # Ensure instance directory exists
    os.makedirs('instance', exist_ok=True)
    
    # Copy the database
    print()
    print(f"Copying {OLD_DB_PATH} to {NEW_DB_PATH}...")
    try:
        shutil.copy2(OLD_DB_PATH, NEW_DB_PATH)
        print("✓ Copy successful!")
    except Exception as e:
        print(f"✗ Error copying database: {e}")
        return False
    
    # Verify the new database
    print()
    print("Verifying new database...")
    new_valid, new_msg = verify_database(NEW_DB_PATH)
    if new_valid:
        print(f"✓ {new_msg}")
        print()
        print("=" * 60)
        print("Migration completed successfully!")
        print("=" * 60)
        print()
        print(f"The database is now at: {NEW_DB_PATH}")
        print(f"The old database is still at: {OLD_DB_PATH}")
        print()
        print("You can now:")
        print("1. Test the app to make sure everything works")
        print("2. Delete the old database.db file if you're satisfied")
        print("3. Commit instance/database.db to git")
        return True
    else:
        print(f"✗ Verification failed: {new_msg}")
        return False


if __name__ == '__main__':
    success = migrate_database()
    exit(0 if success else 1)
