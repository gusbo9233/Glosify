#!/usr/bin/env python3
"""Verify the User table exists in the database."""

from app import app, db, User
import sqlite3
import os


def verify_table():
    """Verify User table exists and show its structure."""
    with app.app_context():
        # Method 1: Using SQLAlchemy inspector
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()
        print("Method 1 - SQLAlchemy Inspector:")
        print(f"  Tables found: {tables}")
        print(f"  User table exists: {'user' in tables}")

        if 'user' in tables:
            columns = inspector.get_columns('user')
            print("  User table columns:")
            for col in columns:
                print(f"    - {col['name']}: {col['type']}")

        # Method 2: Direct SQLite query (check both possible locations)
        print("\nMethod 2 - Direct SQLite Query:")
        db_paths = ['database.db', 'instance/database.db']
        for db_path in db_paths:
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if user table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user'")
        result = cursor.fetchone()
        print(f"  User table exists: {result is not None}")

        if result:
            # Get table schema
            cursor.execute("PRAGMA table_info(user)")
            columns = cursor.fetchall()
            print("  User table schema:")
            for col in columns:
                print(f"    - {col[1]} ({col[2]}) - {'NOT NULL' if col[3] else 'NULL'} - Primary Key: {bool(col[5])}")

                conn.close()
                break

        # Method 3: Try to query the User model
        print("\nMethod 3 - SQLAlchemy Model Query:")
        try:
            user_count = User.query.count()
            print(f"  User model is accessible")
            print(f"  Current user count: {user_count}")
        except Exception as e:
            print(f"  Error querying User model: {e}")


if __name__ == '__main__':
    verify_table()
