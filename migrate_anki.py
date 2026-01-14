"""
Migration script to add Anki spaced repetition fields to the Word table.
Run this script once to update the database schema.
"""

import sqlite3
from datetime import datetime

def migrate():
    conn = sqlite3.connect('instance/database.db')
    cursor = conn.cursor()
    
    # Check which columns already exist
    cursor.execute("PRAGMA table_info(word)")
    existing_columns = {row[1] for row in cursor.fetchall()}
    
    # Add new columns if they don't exist
    new_columns = [
        ("ease_factor", "REAL DEFAULT 2.5"),
        ("interval", "INTEGER DEFAULT 0"),
        ("repetitions", "INTEGER DEFAULT 0"),
        ("due_date", "DATETIME"),
    ]
    
    for column_name, column_def in new_columns:
        if column_name not in existing_columns:
            print(f"Adding column: {column_name}")
            cursor.execute(f"ALTER TABLE word ADD COLUMN {column_name} {column_def}")
        else:
            print(f"Column already exists: {column_name}")
    
    # Set default due_date for existing words that have NULL
    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute(f"UPDATE word SET due_date = ? WHERE due_date IS NULL", (now,))
    updated_rows = cursor.rowcount
    print(f"Updated {updated_rows} words with default due_date")
    
    conn.commit()
    conn.close()
    print("Migration completed successfully!")

if __name__ == "__main__":
    migrate()
