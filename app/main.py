"""notulen - catatan kerja pribadi: tasklist, tutorial, command, SOP, workflow, notulen rapat."""

import hashlib
import hmac
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlsplit

import markdown as md
from fastapi import FastAPI, Form, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jinja2 import TemplateNotFound
from markupsafe import Markup, escape
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import db as database

BASE_DIR = Path(__file__).resolve().parent
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
    return database.connect()


def init_db() -> None:
    database.init_db()


init_db()


def token() -> str:
    return hashlib.sha256(PASSWORD.encode()).hexdigest() if PASSWORD else ""


def render(request: Request, name: str, status_code: int = 200, **ctx) -> HTMLResponse:
    ctx.setdefault("auth_on", bool(PASSWORD))
    return templates.TemplateResponse(request, name, ctx, status_code=status_code)


FALLBACK_ERROR = """<!doctype html>
<html lang="id"><head><meta charset="utf-8"><title>{status} - notulen</title></head>
<body><main><h1>{heading}</h1><p>{message}</p><p><a href="/">Kembali ke daftar</a></p></main></body></html>
"""


def render_error(request: Request, status: int, heading: str, message: str) -> HTMLResponse:
    """Render the shared shell. Falls back to a bare page while error.html is being written."""
    try:
        return render(
            request,
            "error.html",
            status_code=status,
            status=status,
            heading=heading,
            message=message,
        )
    except TemplateNotFound:
        return HTMLResponse(
            FALLBACK_ERROR.format(status=status, heading=escape(heading), message=escape(message)),
            status_code=status,
        )


@app.exception_handler(StarletteHTTPException)
async def http_error(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return render_error(
            request,
            404,
            "Halaman tidak ditemukan",
            "Alamat ini tidak ada. Mungkin catatannya sudah dihapus.",
        )
    return render_error(request, exc.status_code, "Terjadi kesalahan", str(exc.detail))


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    return render_error(
        request, 400, "Permintaan tidak valid", "Alamat atau isian ini tidak bisa dibaca."
    )


@app.exception_handler(Exception)
async def server_error(request: Request, exc: Exception):
    return render_error(
        request,
        500,
        "Ada yang salah",
        "Permintaan ini gagal diproses. Coba lagi sebentar lagi.",
    )


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


def normalise_tags(raw: str) -> str:
    """Strip, lowercase, drop empties and duplicates, keep first-seen order."""
    seen = []
    for part in raw.split(","):
        tag = part.strip().lower()
        if tag and tag not in seen:
            seen.append(tag)
    return ",".join(seen)


def entry_where(kind: str, tag: str, q: str) -> tuple[str, list]:
    where, args = [], []
    if kind in KINDS:
        where.append("kind = ?")
        args.append(kind)
    tag = tag.strip().lower()
    if tag:
        where.append("instr(',' || tags || ',', ?) > 0")
        args.append(f",{tag},")
    term = q.strip()
    if term:
        like = f"%{term}%"
        where.append("(title LIKE ? OR tags LIKE ? OR body LIKE ?)")
        args += [like, like, like]
    return (" WHERE " + " AND ".join(where)) if where else "", args


@app.get("/", response_class=HTMLResponse)
def index(request: Request, kind: str = "", tag: str = "", q: str = "", pinned: str = ""):
    where, args = entry_where(kind, tag, q)
    if pinned == "1":
        where = (where + " AND " if where else " WHERE ") + "pinned = 1"

    term = q.strip()
    order = "pinned DESC, created_at DESC, id DESC"
    if term:
        like = f"%{term}%"
        rank = (
            "CASE WHEN title LIKE ? THEN 0 "
            "WHEN tags LIKE ? THEN 1 "
            "WHEN body LIKE ? THEN 2 ELSE 3 END"
        )
        sql = f"SELECT *, {rank} AS rank FROM entry{where}"
        args = [like, like, like] + args
        order = "pinned DESC, rank, created_at DESC, id DESC"
    else:
        sql = f"SELECT * FROM entry{where}"
    sql += " ORDER BY " + order

    conn = db()
    try:
        rows = conn.execute(sql, args).fetchall()
    finally:
        conn.close()
    return render(
        request,
        "list.html",
        entries=rows,
        kind=kind,
        tag=tag.strip().lower(),
        q=term,
        pinned=pinned,
    )


@app.get("/tags", response_class=HTMLResponse)
def tags_page(request: Request):
    conn = db()
    try:
        rows = conn.execute("SELECT tags FROM entry WHERE tags != ''").fetchall()
    finally:
        conn.close()
    counts: dict[str, int] = {}
    for row in rows:
        for tag in row["tags"].split(","):
            tag = tag.strip()
            if tag:
                counts[tag] = counts.get(tag, 0) + 1
    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    try:
        return render(request, "tags.html", tags=ordered)
    except TemplateNotFound:
        items = "".join(
            f'<li><a href="/?tag={quote(tag)}">{escape(tag)}</a> ({count})</li>'
            for tag, count in ordered
        )
        return HTMLResponse(
            '<!doctype html><html lang="id"><head><meta charset="utf-8">'
            f"<title>Tag - notulen</title></head><body><main><h1>Tag</h1><ul>{items}</ul>"
            '<p><a href="/">Kembali ke daftar</a></p></main></body></html>'
        )


@app.get("/entry/{entry_id}", response_class=HTMLResponse)
def show(request: Request, entry_id: int):
    conn = db()
    try:
        row = conn.execute("SELECT * FROM entry WHERE id = ?", (entry_id,)).fetchone()
    finally:
        conn.close()
    if row is None:
        return render_error(
            request, 404, "Catatan tidak ditemukan", "Catatan ini sudah tidak ada atau belum pernah dibuat."
        )
    return render(request, "entry.html", entry=row)


@app.get("/new", response_class=HTMLResponse)
def new_form(request: Request, kind: str = "task"):
    return render(
        request,
        "form.html",
        entry=None,
        values=None,
        action="/entry",
        selected=kind if kind in KINDS else "task",
        errors={},
        error=None,
    )


def form_error(
    request: Request,
    status: int,
    errors: dict,
    action: str,
    kind: str,
    title: str,
    body: str,
    tags: str,
    entry=None,
) -> HTMLResponse:
    """Re-render the form with what was submitted and the message next to the field.

    Context: entry is the stored row (None when creating), values is what the user typed,
    errors maps a field name to its message. form.html renders values into the inputs and
    errors beside the fields.
    """
    values = {"kind": kind, "title": title, "body": body, "tags": tags}
    return render(
        request,
        "form.html",
        status_code=status,
        entry=entry,
        values=values,
        action=action,
        selected=kind if kind in KINDS else "task",
        errors=errors,
        error=next(iter(errors.values()), None),
    )


def validate(kind: str, title: str) -> dict:
    errors = {}
    if kind not in KINDS:
        errors["kind"] = "Jenis catatan tidak dikenal."
    if not title.strip():
        errors["title"] = "Judul wajib diisi."
    return errors


@app.post("/entry")
def create(
    request: Request,
    kind: str = Form("task"),
    title: str = Form(""),
    body: str = Form(""),
    tags: str = Form(""),
):
    errors = validate(kind, title)
    if errors:
        return form_error(request, 400, errors, "/entry", kind, title, body, tags)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    conn = db()
    try:
        cur = conn.execute(
            "INSERT INTO entry (kind, title, body, tags, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (kind, title.strip(), body, normalise_tags(tags), now, now),
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
        return render_error(
            request, 404, "Catatan tidak ditemukan", "Catatan ini sudah tidak ada atau belum pernah dibuat."
        )
    return render(
        request,
        "form.html",
        entry=row,
        values=None,
        action=f"/entry/{entry_id}",
        selected=row["kind"],
        errors={},
        error=None,
    )


@app.post("/entry/{entry_id}")
def update(
    request: Request,
    entry_id: int,
    kind: str = Form("task"),
    title: str = Form(""),
    body: str = Form(""),
    tags: str = Form(""),
):
    conn = db()
    try:
        existing = conn.execute("SELECT * FROM entry WHERE id = ?", (entry_id,)).fetchone()
    finally:
        conn.close()
    if existing is None:
        return render_error(
            request, 404, "Catatan tidak ditemukan", "Catatan ini sudah tidak ada atau belum pernah dibuat."
        )
    errors = validate(kind, title)
    if errors:
        return form_error(
            request, 400, errors, f"/entry/{entry_id}", kind, title, body, tags, entry=existing
        )
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    conn = db()
    try:
        conn.execute(
            "UPDATE entry SET kind = ?, title = ?, body = ?, tags = ?, updated_at = ? WHERE id = ?",
            (kind, title.strip(), body, normalise_tags(tags), now, entry_id),
        )
        conn.commit()
    finally:
        conn.close()
    return RedirectResponse(f"/entry/{entry_id}", status_code=303)


@app.post("/entry/{entry_id}/delete")
def delete(request: Request, entry_id: int):
    conn = db()
    try:
        cur = conn.execute("DELETE FROM entry WHERE id = ?", (entry_id,))
        conn.commit()
        found = cur.rowcount
    finally:
        conn.close()
    if not found:
        return render_error(
            request, 404, "Catatan tidak ditemukan", "Catatan ini sudah tidak ada atau belum pernah dibuat."
        )
    return RedirectResponse("/", status_code=303)


def back_to(request: Request, fallback: str = "/") -> str:
    """Return to the page the form was submitted from, but never off this site."""
    referer = request.headers.get("referer", "")
    if referer:
        parts = urlsplit(referer)
        if parts.netloc and parts.netloc != request.headers.get("host", ""):
            return fallback
        path = parts.path or "/"
        if path.startswith("/") and not path.startswith("//"):
            return path + (f"?{parts.query}" if parts.query else "")
    return fallback


@app.post("/entry/{entry_id}/pin")
def pin(request: Request, entry_id: int):
    conn = db()
    try:
        row = conn.execute("SELECT pinned FROM entry WHERE id = ?", (entry_id,)).fetchone()
        if row is None:
            conn.close()
            return render_error(
                request, 404, "Catatan tidak ditemukan", "Catatan ini sudah tidak ada atau belum pernah dibuat."
            )
        conn.execute(
            "UPDATE entry SET pinned = ? WHERE id = ?", (0 if row["pinned"] else 1, entry_id)
        )
        conn.commit()
    finally:
        conn.close()
    return RedirectResponse(back_to(request), status_code=303)
