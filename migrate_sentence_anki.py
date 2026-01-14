#!/usr/bin/env python3
"""
Migration script to add Anki spaced repetition fields to the Sentence table.
"""

import sqlite3
from datetime import datetime

DB_PATH = 'instance/database.db'

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if columns already exist
    cursor.execute("PRAGMA table_info(sentence)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'ease_factor' not in columns:
        print("Adding ease_factor column to sentence table...")
        cursor.execute("ALTER TABLE sentence ADD COLUMN ease_factor REAL DEFAULT 2.5")
    else:
        print("ease_factor column already exists")
    
    if 'interval' not in columns:
        print("Adding interval column to sentence table...")
        cursor.execute("ALTER TABLE sentence ADD COLUMN interval INTEGER DEFAULT 0")
    else:
        print("interval column already exists")
    
    if 'repetitions' not in columns:
        print("Adding repetitions column to sentence table...")
        cursor.execute("ALTER TABLE sentence ADD COLUMN repetitions INTEGER DEFAULT 0")
    else:
        print("repetitions column already exists")
    
    if 'due_date' not in columns:
        print("Adding due_date column to sentence table...")
        cursor.execute("ALTER TABLE sentence ADD COLUMN due_date DATETIME")
        # Set default due_date to now for existing sentences
        cursor.execute("UPDATE sentence SET due_date = ?", (datetime.utcnow().isoformat(),))
    else:
        print("due_date column already exists")
    
    conn.commit()
    conn.close()
    print("Migration completed successfully!")

if __name__ == "__main__":
    migrate()
