import sqlite3

from app import db as database
from app.main import db, normalise_tags


def get_entry(entry_id):
    conn = db()
    try:
        return conn.execute("SELECT * FROM entry WHERE id = ?", (entry_id,)).fetchone()
    finally:
        conn.close()


def test_health_returns_200_without_auth(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_create_entry(client, make_entry):
    entry_id = make_entry(kind="tutorial", title="Cara backup", body="pakai restic", tags="backup,restic")
    row = get_entry(entry_id)
    assert row["kind"] == "tutorial"
    assert row["title"] == "Cara backup"
    assert row["tags"] == "backup,restic"
    assert row["created_at"] and row["updated_at"]
    assert row["pinned"] == 0


def test_list_is_newest_first(client, make_entry):
    make_entry(title="Pertama")
    make_entry(title="Kedua")
    r = client.get("/")
    assert r.status_code == 200
    assert r.text.index("Kedua") < r.text.index("Pertama")


def test_filter_by_kind(client, make_entry):
    make_entry(kind="sop", title="SOP deploy")
    make_entry(kind="command", title="Perintah disk")
    r = client.get("/?kind=sop")
    assert "SOP deploy" in r.text
    assert "Perintah disk" not in r.text


def test_search_matches_title_body_and_tags(client, make_entry):
    make_entry(title="Restore database", body="langkah restic restore")
    make_entry(title="Lain", body="tidak relevan")
    make_entry(title="Ketiga", body="apa saja", tags="zabbix")
    assert "Restore database" in client.get("/?q=restic").text
    assert "Ketiga" in client.get("/?q=zabbix").text
    assert "Restore database" not in client.get("/?q=zabbix").text


def test_search_ranks_title_then_tag_then_body(client, make_entry):
    make_entry(title="Catatan biasa", body="kata ada di isi")
    make_entry(title="Catatan lain", body="isi tanpa kata itu", tags="kata")
    make_entry(title="Kata di judul", body="isi lain")

    r = client.get("/?q=kata")
    assert r.status_code == 200
    positions = [
        r.text.index("Kata di judul"),
        r.text.index("Catatan lain"),
        r.text.index("Catatan biasa"),
    ]
    assert positions == sorted(positions)


def test_search_ranking_is_deterministic(client, make_entry):
    make_entry(title="Sama satu", body="isi")
    make_entry(title="Sama dua", body="isi")
    assert client.get("/?q=sama").text == client.get("/?q=sama").text


def test_search_does_not_return_unrelated(client, make_entry):
    make_entry(title="Relevan", body="kata")
    make_entry(title="Tidak", body="lain")
    r = client.get("/?q=kata")
    assert "Relevan" in r.text
    assert "Tidak" not in r.text


def test_tag_filter_is_exact(client, make_entry):
    make_entry(title="Punya docker", tags="docker,backup")
    make_entry(title="Punya dockers", tags="dockers")
    r = client.get("/?tag=docker")
    assert "Punya docker" in r.text
    assert "Punya dockers" not in r.text
    assert "Punya docker" in client.get("/?tag=DOCKER").text


def test_kind_tag_and_q_combine(client, make_entry):
    make_entry(kind="command", title="Disk penuh", tags="disk", body="df -h")
    make_entry(kind="task", title="Disk penuh", tags="disk", body="df -h")
    make_entry(kind="command", title="Memori", tags="mem", body="free -m")
    r = client.get("/?kind=command&tag=disk&q=df")
    assert "Disk penuh" in r.text
    assert "Memori" not in r.text
    assert r.text.count("Disk penuh") == 1


def test_tags_page_counts_from_database(client, make_entry):
    make_entry(title="A", tags="docker,backup")
    make_entry(title="B", tags="docker")
    make_entry(title="C", tags="")
    r = client.get("/tags")
    assert r.status_code == 200
    assert "docker" in r.text
    assert "2" in r.text


def test_tag_normalisation_on_write(client, make_entry):
    entry_id = make_entry(title="Tag", tags="  Docker , backup,,  DOCKER ,  ")
    assert get_entry(entry_id)["tags"] == "docker,backup"


def test_normalise_tags_helper():
    assert normalise_tags("  B , a,,A ,, ") == "b,a"
    assert normalise_tags("") == ""
    assert normalise_tags(" , , ") == ""


def test_pinned_entries_sort_first(client, make_entry):
    old_id = make_entry(title="Lama dipin")
    make_entry(title="Baru tidak dipin")
    r = client.post(f"/entry/{old_id}/pin", follow_redirects=False)
    assert r.status_code == 303
    assert get_entry(old_id)["pinned"] == 1
    r = client.get("/")
    assert r.text.index("Lama dipin") < r.text.index("Baru tidak dipin")


def test_pin_toggles_back(client, make_entry):
    entry_id = make_entry(title="Toggle")
    client.post(f"/entry/{entry_id}/pin", follow_redirects=False)
    client.post(f"/entry/{entry_id}/pin", follow_redirects=False)
    assert get_entry(entry_id)["pinned"] == 0


def test_pin_redirects_to_referring_page(client, make_entry):
    entry_id = make_entry(title="Kembali")
    r = client.post(
        f"/entry/{entry_id}/pin",
        headers={"referer": "http://testserver/?kind=task&q=kem"},
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert r.headers["location"] == "/?kind=task&q=kem"


def test_pin_ignores_foreign_referer(client, make_entry):
    entry_id = make_entry(title="Asing")
    r = client.post(
        f"/entry/{entry_id}/pin",
        headers={"referer": "https://evil.example/x"},
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert r.headers["location"] == "/"


def test_pinned_filter(client, make_entry):
    entry_id = make_entry(title="Dipin")
    make_entry(title="Tidak dipin")
    client.post(f"/entry/{entry_id}/pin", follow_redirects=False)
    r = client.get("/?pinned=1")
    assert "Dipin" in r.text
    assert "Tidak dipin" not in r.text


def test_update_entry(client, make_entry):
    entry_id = make_entry(title="Lama", body="isi lama")
    r = client.post(
        f"/entry/{entry_id}",
        data={"kind": "meeting", "title": "Baru", "body": "isi baru", "tags": "rapat"},
        follow_redirects=False,
    )
    assert r.status_code == 303
    row = get_entry(entry_id)
    assert row["kind"] == "meeting"
    assert row["title"] == "Baru"
    assert row["body"] == "isi baru"
    assert row["tags"] == "rapat"


def test_delete_entry(client, make_entry):
    entry_id = make_entry(title="Akan dihapus")
    r = client.post(f"/entry/{entry_id}/delete", follow_redirects=False)
    assert r.status_code == 303
    assert get_entry(entry_id) is None
    assert client.get(f"/entry/{entry_id}").status_code == 404


def test_markdown_is_rendered_and_html_escaped(client, make_entry):
    entry_id = make_entry(title="XSS", body="**tebal** <script>alert(1)</script>")
    r = client.get(f"/entry/{entry_id}")
    assert "<strong>tebal</strong>" in r.text
    assert "<script>alert(1)</script>" not in r.text
    assert "&lt;script&gt;" in r.text


def test_missing_entry_renders_html_404(client):
    r = client.get("/entry/999999")
    assert r.status_code == 404
    assert r.headers["content-type"].startswith("text/html")
    assert "tidak ditemukan" in r.text.lower()


def test_unknown_path_renders_html_404(client):
    r = client.get("/tidak-ada-halaman-ini")
    assert r.status_code == 404
    assert r.headers["content-type"].startswith("text/html")
    assert "<" in r.text


def test_non_numeric_entry_id_renders_html(client):
    r = client.get("/entry/abc")
    assert r.status_code == 400
    assert r.headers["content-type"].startswith("text/html")


def test_internal_error_renders_html(monkeypatch):
    import sqlite3

    import app.main as main
    from fastapi.testclient import TestClient

    def boom():
        raise sqlite3.OperationalError("boom")

    monkeypatch.setattr(main, "db", boom)
    with TestClient(main.app, raise_server_exceptions=False) as c:
        r = c.get("/")
    assert r.status_code == 500
    assert r.headers["content-type"].startswith("text/html")


def test_bad_kind_rerenders_form_with_400(client):
    r = client.post(
        "/entry",
        data={"kind": "ngawur", "title": "Judul tetap", "body": "isi", "tags": "a"},
        follow_redirects=False,
    )
    assert r.status_code == 400
    assert r.headers["content-type"].startswith("text/html")
    assert 'name="title"' in r.text
    assert client.get("/").text.count("Judul tetap") == 0


def test_empty_title_rerenders_form_with_400(client):
    r = client.post(
        "/entry",
        data={"kind": "task", "title": "   ", "body": "isi tetap", "tags": "a"},
        follow_redirects=False,
    )
    assert r.status_code == 400
    assert r.headers["content-type"].startswith("text/html")
    assert 'name="title"' in r.text


def test_update_with_bad_input_keeps_entry(client, make_entry):
    entry_id = make_entry(title="Asli")
    r = client.post(
        f"/entry/{entry_id}",
        data={"kind": "task", "title": "", "body": "x", "tags": ""},
        follow_redirects=False,
    )
    assert r.status_code == 400
    assert get_entry(entry_id)["title"] == "Asli"


def test_migration_adds_pinned_to_v1_database(v1_database):
    conn = sqlite3.connect(v1_database)
    try:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(entry)")}
        assert "pinned" not in columns
    finally:
        conn.close()

    database.init_db(v1_database)

    conn = sqlite3.connect(v1_database)
    conn.row_factory = sqlite3.Row
    try:
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(entry)")}
        assert "pinned" in columns
        rows = conn.execute("SELECT * FROM entry").fetchall()
        assert len(rows) == 1
        assert rows[0]["title"] == "Cek disk"
        assert rows[0]["pinned"] == 0
        indexes = {row["name"] for row in conn.execute("PRAGMA index_list(entry)")}
        assert {"idx_entry_created", "idx_entry_kind", "idx_entry_pinned"} <= indexes
    finally:
        conn.close()


def test_migration_is_idempotent(v1_database):
    database.init_db(v1_database)
    database.init_db(v1_database)
    conn = sqlite3.connect(v1_database)
    try:
        assert conn.execute("SELECT COUNT(*) FROM entry").fetchone()[0] == 1
    finally:
        conn.close()


def test_auth_off_serves_the_list(client):
    assert client.get("/").status_code == 200


def test_auth_on_redirects_to_login(monkeypatch, make_entry):
    import app.main as main
    from fastapi.testclient import TestClient

    monkeypatch.setattr(main, "PASSWORD", "rahasia")
    with TestClient(main.app) as c:
        r = c.get("/", follow_redirects=False)
        assert r.status_code == 303
        assert r.headers["location"] == "/login"
        assert c.get("/health").status_code == 200
        bad = c.post("/login", data={"password": "salah"}, follow_redirects=False)
        assert bad.status_code == 401
        good = c.post("/login", data={"password": "rahasia"}, follow_redirects=False)
        assert good.status_code == 303
        assert c.get("/").status_code == 200
