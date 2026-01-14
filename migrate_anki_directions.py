#!/usr/bin/env python3
"""
Migration script to add reverse direction Anki fields to Word and Sentence tables.
"""

import sqlite3
from datetime import datetime

DB_PATH = 'instance/database.db'

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check and add columns to Word table
    cursor.execute("PRAGMA table_info(word)")
    word_columns = [col[1] for col in cursor.fetchall()]
    
    word_new_columns = [
        ('ease_factor_reverse', 'REAL', '2.5'),
        ('interval_reverse', 'INTEGER', '0'),
        ('repetitions_reverse', 'INTEGER', '0'),
        ('due_date_reverse', 'DATETIME', None)
    ]
    
    for col_name, col_type, default in word_new_columns:
        if col_name not in word_columns:
            print(f"Adding {col_name} column to word table...")
            if default:
                cursor.execute(f"ALTER TABLE word ADD COLUMN {col_name} {col_type} DEFAULT {default}")
            else:
                cursor.execute(f"ALTER TABLE word ADD COLUMN {col_name} {col_type}")
            if col_name == 'due_date_reverse':
                cursor.execute(f"UPDATE word SET {col_name} = ?", (datetime.utcnow().isoformat(),))
        else:
            print(f"{col_name} column already exists in word table")
    
    # Check and add columns to Sentence table
    cursor.execute("PRAGMA table_info(sentence)")
    sentence_columns = [col[1] for col in cursor.fetchall()]
    
    sentence_new_columns = [
        ('ease_factor_reverse', 'REAL', '2.5'),
        ('interval_reverse', 'INTEGER', '0'),
        ('repetitions_reverse', 'INTEGER', '0'),
        ('due_date_reverse', 'DATETIME', None)
    ]
    
    for col_name, col_type, default in sentence_new_columns:
        if col_name not in sentence_columns:
            print(f"Adding {col_name} column to sentence table...")
            if default:
                cursor.execute(f"ALTER TABLE sentence ADD COLUMN {col_name} {col_type} DEFAULT {default}")
            else:
                cursor.execute(f"ALTER TABLE sentence ADD COLUMN {col_name} {col_type}")
            if col_name == 'due_date_reverse':
                cursor.execute(f"UPDATE sentence SET {col_name} = ?", (datetime.utcnow().isoformat(),))
        else:
            print(f"{col_name} column already exists in sentence table")
    
    conn.commit()
    conn.close()
    print("Migration completed successfully!")

if __name__ == "__main__":
    migrate()
