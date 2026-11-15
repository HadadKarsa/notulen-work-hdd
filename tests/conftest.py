import os
import sqlite3
import tempfile
from pathlib import Path

os.environ["DB_PATH"] = str(Path(tempfile.mkdtemp()) / "test.db")
os.environ.pop("APP_PASSWORD", None)

import pytest
from fastapi.testclient import TestClient

from app.main import app, db


@pytest.fixture()
def client():
    with TestClient(app) as c:
        conn = db()
        try:
            conn.execute("DELETE FROM entry")
            conn.commit()
        finally:
            conn.close()
        yield c


@pytest.fixture()
def make_entry(client):
    def _make(kind="task", title="Catatan", body="", tags=""):
        r = client.post(
            "/entry",
            data={"kind": kind, "title": title, "body": body, "tags": tags},
            follow_redirects=False,
        )
        assert r.status_code == 303, r.text
        return int(r.headers["location"].rsplit("/", 1)[-1])

    return _make


V1_SCHEMA = """
CREATE TABLE entry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL DEFAULT '',
    tags TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""


@pytest.fixture()
def v1_database():
    """A database exactly as v1 left it: no pinned column, one row of data."""
    path = Path(tempfile.mkdtemp()) / "v1.db"
    conn = sqlite3.connect(path)
    try:
        conn.execute(V1_SCHEMA)
        conn.execute(
            "INSERT INTO entry (kind, title, body, tags, created_at, updated_at)"
            " VALUES ('command', 'Cek disk', 'df -h', 'disk', '2026-01-01T00:00:00+00:00',"
            " '2026-01-01T00:00:00+00:00')"
        )
        conn.commit()
    finally:
        conn.close()
    return path
