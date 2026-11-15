"""notulen — catatan kerja pribadi: tasklist, tutorial, command, SOP, workflow, notulen rapat."""

import hashlib
import hmac
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import markdown as md
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from markupsafe import Markup, escape

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("DB_PATH", BASE_DIR.parent / "data" / "notulen.db"))
PASSWORD = os.environ.get("APP_PASSWORD", "").strip()
COOKIE = "notulen_auth"
KINDS = ("task", "tutorial", "command", "sop", "workflow", "meeting")
KIND_LABELS = {
    "task": "Task",
    "tutorial": "Tutorial",
    "command": "Command",
    "sop": "SOP",
    "workflow": "Workflow",
    "meeting": "Notulen",
}

app = FastAPI(title="notulen")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def render_markdown(text: str) -> Markup:
    return Markup(md.markdown(escape(text), extensions=["fenced_code", "tables", "nl2br"]))


templates.env.filters["markdown"] = render_markdown
templates.env.globals["kind_labels"] = KIND_LABELS


def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = db()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS entry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL,
                title TEXT NOT NULL,
                body TEXT NOT NULL DEFAULT '',
                tags TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


init_db()


def token() -> str:
    return hashlib.sha256(PASSWORD.encode()).hexdigest() if PASSWORD else ""


def render(request: Request, name: str, status_code: int = 200, **ctx) -> HTMLResponse:
    ctx.setdefault("auth_on", bool(PASSWORD))
    return templates.TemplateResponse(request, name, ctx, status_code=status_code)


@app.middleware("http")
async def require_password(request: Request, call_next):
    if PASSWORD:
        path = request.url.path
        if not (path.startswith("/static") or path in ("/health", "/login")):
            if not hmac.compare_digest(request.cookies.get(COOKIE, ""), token()):
                return RedirectResponse("/login", status_code=303)
    return await call_next(request)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    if not PASSWORD:
        return RedirectResponse("/", status_code=303)
    return render(request, "login.html", error=None)


@app.post("/login")
def login(request: Request, password: str = Form("")):
    if not PASSWORD:
        return RedirectResponse("/", status_code=303)
    if not hmac.compare_digest(password, PASSWORD):
        return render(request, "login.html", status_code=401, error="Password salah.")
    response = RedirectResponse("/", status_code=303)
    response.set_cookie(COOKIE, token(), httponly=True, samesite="lax", max_age=60 * 60 * 24 * 30)
    return response


@app.get("/logout")
def logout():
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(COOKIE)
    return response


@app.get("/", response_class=HTMLResponse)
def index(request: Request, kind: str = "", q: str = ""):
    where, args = [], []
    if kind in KINDS:
        where.append("kind = ?")
        args.append(kind)
    term = q.strip()
    if term:
        like = f"%{term}%"
        where.append("(title LIKE ? OR body LIKE ? OR tags LIKE ?)")
        args += [like, like, like]
    sql = "SELECT * FROM entry"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY created_at DESC, id DESC"
    conn = db()
    try:
        rows = conn.execute(sql, args).fetchall()
    finally:
        conn.close()
    return render(request, "list.html", entries=rows, kind=kind, q=term)


@app.get("/entry/{entry_id}", response_class=HTMLResponse)
def show(request: Request, entry_id: int):
    conn = db()
    try:
        row = conn.execute("SELECT * FROM entry WHERE id = ?", (entry_id,)).fetchone()
    finally:
        conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail="Catatan tidak ditemukan")
    return render(request, "entry.html", entry=row)


@app.get("/new", response_class=HTMLResponse)
def new_form(request: Request, kind: str = "task"):
    return render(
        request,
        "form.html",
        entry=None,
        action="/entry",
        selected=kind if kind in KINDS else "task",
    )


@app.post("/entry")
def create(
    kind: str = Form("task"),
    title: str = Form(""),
    body: str = Form(""),
    tags: str = Form(""),
):
    if kind not in KINDS:
        raise HTTPException(status_code=400, detail="Jenis catatan tidak dikenal")
    if not title.strip():
        raise HTTPException(status_code=400, detail="Judul wajib diisi")
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    conn = db()
    try:
        cur = conn.execute(
            "INSERT INTO entry (kind, title, body, tags, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (kind, title.strip(), body, tags.strip(), now, now),
        )
        conn.commit()
        entry_id = cur.lastrowid
    finally:
        conn.close()
    return RedirectResponse(f"/entry/{entry_id}", status_code=303)


@app.get("/entry/{entry_id}/edit", response_class=HTMLResponse)
def edit_form(request: Request, entry_id: int):
    conn = db()
    try:
        row = conn.execute("SELECT * FROM entry WHERE id = ?", (entry_id,)).fetchone()
    finally:
        conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail="Catatan tidak ditemukan")
    return render(
        request,
        "form.html",
        entry=row,
        action=f"/entry/{entry_id}",
        selected=row["kind"],
    )


@app.post("/entry/{entry_id}")
def update(
    entry_id: int,
    kind: str = Form("task"),
    title: str = Form(""),
    body: str = Form(""),
    tags: str = Form(""),
):
    if kind not in KINDS:
        raise HTTPException(status_code=400, detail="Jenis catatan tidak dikenal")
    if not title.strip():
        raise HTTPException(status_code=400, detail="Judul wajib diisi")
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    conn = db()
    try:
        cur = conn.execute(
            "UPDATE entry SET kind = ?, title = ?, body = ?, tags = ?, updated_at = ? WHERE id = ?",
            (kind, title.strip(), body, tags.strip(), now, entry_id),
        )
        conn.commit()
        found = cur.rowcount
    finally:
        conn.close()
    if not found:
        raise HTTPException(status_code=404, detail="Catatan tidak ditemukan")
    return RedirectResponse(f"/entry/{entry_id}", status_code=303)


@app.post("/entry/{entry_id}/delete")
def delete(entry_id: int):
    conn = db()
    try:
        cur = conn.execute("DELETE FROM entry WHERE id = ?", (entry_id,))
        conn.commit()
        found = cur.rowcount
    finally:
        conn.close()
    if not found:
        raise HTTPException(status_code=404, detail="Catatan tidak ditemukan")
    return RedirectResponse("/", status_code=303)
