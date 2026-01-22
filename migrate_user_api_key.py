import sqlite3


def column_exists(cursor, table_name, column_name):
    cursor.execute(f"PRAGMA table_info({table_name})")
    return any(row[1] == column_name for row in cursor.fetchall())


def main():
    conn = sqlite3.connect("instance/database.db")
    cursor = conn.cursor()

    if not column_exists(cursor, "user", "api_key_encrypted"):
        cursor.execute("ALTER TABLE user ADD COLUMN api_key_encrypted TEXT")
        print("Added api_key_encrypted to user table.")
    else:
        print("api_key_encrypted already exists.")

    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
