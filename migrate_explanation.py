#!/usr/bin/env python3
"""Migration script to add explanation field to Word table."""

from app import app, db
from sqlalchemy import text

def migrate_database():
    """Add explanation column to word table."""
    with app.app_context():
        try:
            # Check if word table exists
            inspector = db.inspect(db.engine)
            existing_tables = inspector.get_table_names()
            
            if 'word' not in existing_tables:
                print("✗ Word table does not exist!")
                return
            
            # Check if word table has explanation column
            word_columns = [col['name'] for col in inspector.get_columns('word')]
            if 'explanation' not in word_columns:
                print("Adding explanation column to word table...")
                db.session.execute(text('ALTER TABLE word ADD COLUMN explanation TEXT'))
                db.session.commit()
                print("✓ explanation column added to word table!")
            else:
                print("✓ explanation column already exists in word table")
            
            print("\n✓ Migration completed successfully!")
            
        except Exception as e:
            print(f"✗ Migration error: {e}")
            db.session.rollback()
            raise

if __name__ == '__main__':
    migrate_database()
