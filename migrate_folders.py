#!/usr/bin/env python3
"""Migration script to add folder support to existing database."""

from app import app, db, Folder
from sqlalchemy import text

def migrate_database():
    """Add folder table and folder_id column to quiz table."""
    with app.app_context():
        try:
            # Check if folder table already exists
            inspector = db.inspect(db.engine)
            existing_tables = inspector.get_table_names()
            
            if 'folder' not in existing_tables:
                print("Creating folder table...")
                db.create_all()
                print("✓ Folder table created!")
            else:
                print("✓ Folder table already exists")
            
            # Check if quiz table has folder_id column
            if 'quiz' in existing_tables:
                quiz_columns = [col['name'] for col in inspector.get_columns('quiz')]
                if 'folder_id' not in quiz_columns:
                    print("Adding folder_id column to quiz table...")
                    db.session.execute(text('ALTER TABLE quiz ADD COLUMN folder_id INTEGER'))
                    db.session.commit()
                    print("✓ folder_id column added to quiz table!")
                else:
                    print("✓ folder_id column already exists in quiz table")
            
            print("\n✓ Migration completed successfully!")
            
        except Exception as e:
            print(f"✗ Migration error: {e}")
            db.session.rollback()
            raise

if __name__ == '__main__':
    migrate_database()
