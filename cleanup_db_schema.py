#!/usr/bin/env python3
"""
Cleanup legacy columns from the SQLite database used by this app.

This repo previously had extra columns in `word`/`sentence` (e.g. `interval_days`,
`last_reviewed`, `next_review`) that are no longer used by the current SQLAlchemy
models. This script removes those columns safely.

What it does:
- Creates a timestamped backup of `instance/database.db`
- Drops known legacy columns if they exist (SQLite 3.35+ required)
- Prints before/after columns for the affected tables

Usage:
  python3 cleanup_db_schema.py
"""

from __future__ import annotations

import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path("instance/database.db")

LEGACY_COLUMNS: dict[str, list[str]] = {
    "word": ["interval_days", "last_reviewed", "next_review"],
    "sentence": ["interval_days", "last_reviewed", "next_review"],
}


def table_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    cur = conn.execute(f"PRAGMA table_info({table})")
    # (cid, name, type, notnull, dflt_value, pk)
    return [row[1] for row in cur.fetchall()]


def main() -> None:
    if not DB_PATH.exists():
        raise SystemExit(f"Database not found at: {DB_PATH.resolve()}")

    backup_path = DB_PATH.with_suffix(
        DB_PATH.suffix + f".bak-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    )
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(DB_PATH, backup_path)

    print(f"DB:      {DB_PATH.resolve()}")
    print(f"Backup:  {backup_path.resolve()}")

    conn = sqlite3.connect(DB_PATH)
    try:
        # Drop-column is supported on SQLite 3.35+. We print the version for clarity.
        sqlite_ver = conn.execute("select sqlite_version()").fetchone()[0]
        print(f"SQLite:  {sqlite_ver}")
        print()

        for table, cols_to_drop in LEGACY_COLUMNS.items():
            before = table_columns(conn, table)
            print(f"== {table} ==")
            print("Before:", before)

            existing = set(before)
            dropped_any = False

            for col in cols_to_drop:
                if col not in existing:
                    continue
                print(f" - dropping column: {col}")
                conn.execute(f"ALTER TABLE {table} DROP COLUMN {col}")
                dropped_any = True

            if dropped_any:
                conn.commit()

            after = table_columns(conn, table)
            print("After: ", after)
            print()

        # Optional: reclaim space and rebuild file structure.
        # This can take a moment but the DB is small.
        print("Running VACUUM…")
        conn.execute("VACUUM")
        print("Done.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()

