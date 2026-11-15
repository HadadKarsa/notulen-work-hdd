import os
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
