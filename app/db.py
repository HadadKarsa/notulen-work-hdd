"""SQLite access for notulen: connection helper, schema creation and the v1 to v2 migration."""

import os
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("DB_PATH", BASE_DIR.parent / "data" / "notulen.db"))

CREATE_ENTRY = """
CREATE TABLE IF NOT EXISTS entry (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    kind       TEXT    NOT NULL,
    title      TEXT    NOT NULL,
    body       TEXT    NOT NULL DEFAULT '',
    tags       TEXT    NOT NULL DEFAULT '',
    pinned     INTEGER NOT NULL DEFAULT 0,
    created_at TEXT    NOT NULL,
    updated_at TEXT    NOT NULL
)
"""

INDEXES = (
    "CREATE INDEX IF NOT EXISTS idx_entry_created ON entry(created_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_entry_kind ON entry(kind)",
    "CREATE INDEX IF NOT EXISTS idx_entry_pinned ON entry(pinned DESC, created_at DESC)",
)


def connect(path=None) -> sqlite3.Connection:
    conn = sqlite3.connect(Path(path) if path else DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def migrate(conn: sqlite3.Connection) -> None:
    """Add v2 columns to a database created by v1, and only the columns that are missing."""
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(entry)")}
    if "pinned" not in columns:
        conn.execute("ALTER TABLE entry ADD COLUMN pinned INTEGER NOT NULL DEFAULT 0")


def init_db(path=None) -> None:
    target = Path(path) if path else DB_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = connect(target)
    try:
        conn.execute(CREATE_ENTRY)
        migrate(conn)
        for statement in INDEXES:
            conn.execute(statement)
        conn.commit()
    finally:
        conn.close()
