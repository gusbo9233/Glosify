#!/usr/bin/env python3
"""Initialize the database and create all tables."""

from app import app, db, User, Quiz, Word, Variant, Sentence, Folder
import sqlite3
import os

def init_database():
    """Create all database tables."""
    with app.app_context():
        # Get the actual database path
        db_uri = app.config['SQLALCHEMY_DATABASE_URI']
        print(f"Database URI: {db_uri}")
        
        # Create all tables
        db.create_all()
        db.session.commit()
        
        print("✓ Database tables created successfully!")
        
        # Check both possible database locations
        db_paths = ['database.db', 'instance/database.db']
        
        for db_path in db_paths:
            if os.path.exists(db_path):
                print(f"\nChecking {db_path}:")
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                print(f"  Tables found: {tables}")
                
                if 'user' in tables:
                    print("  ✓ User table exists!")
                    cursor.execute("PRAGMA table_info(user)")
                    columns = cursor.fetchall()
                    print("  User table structure:")
                    for col in columns:
                        col_name, col_type = col[1], col[2]
                        nullable = "NULL" if not col[3] else "NOT NULL"
                        pk = "PRIMARY KEY" if col[5] else ""
                        print(f"    - {col_name}: {col_type} {nullable} {pk}")
                else:
                    print("  ✗ User table NOT found!")
                
                conn.close()

if __name__ == '__main__':
    init_database()
