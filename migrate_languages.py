"""
Migration script to add source_language and target_language fields to the Quiz table.
Run this script once to update the database schema.
"""

import sqlite3

def migrate():
    conn = sqlite3.connect('instance/database.db')
    cursor = conn.cursor()
    
    # Check which columns already exist
    cursor.execute("PRAGMA table_info(quiz)")
    existing_columns = {row[1] for row in cursor.fetchall()}
    
    # Add new columns if they don't exist
    new_columns = [
        ("source_language", "VARCHAR(50)"),
        ("target_language", "VARCHAR(50)"),
    ]
    
    for column_name, column_type in new_columns:
        if column_name not in existing_columns:
            print(f"Adding column: {column_name}")
            cursor.execute(f"ALTER TABLE quiz ADD COLUMN {column_name} {column_type}")
        else:
            print(f"Column already exists: {column_name}")
    
    conn.commit()
    conn.close()
    print("Migration completed successfully!")

if __name__ == "__main__":
    migrate()
