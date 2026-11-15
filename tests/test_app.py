from app.main import db


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
