# SPEC.md — notulen v2 (revamp)

The contract between the people building this. Read DESIGN.md for the visual direction; this file
is the behaviour, the data, and who owns what. If something here is wrong, change it here first.

## What v2 is

v1 was a working CRUD list. v2 is the notebook the owner actually reaches for: it must be fast to
search, fast to copy a command out of, and pleasant at 23:40 on a phone.

## Non-goals

No accounts, no sharing, no attachments, no audio, no notifications, no JS framework, no build
step, no CDN, no external fonts, no second database, no ORM. Single user, single process.

## Stack (unchanged)

Python 3.12, FastAPI, Jinja2, stdlib `sqlite3`, `markdown`, one stylesheet, system fonts.
`pytest` for tests. No new runtime dependency beyond what v1 already had.

## Data model

One table, `entry`. v2 adds two columns; the migration must be idempotent and must not lose data
from a v1 database.

```sql
CREATE TABLE IF NOT EXISTS entry (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    kind       TEXT    NOT NULL,          -- task|tutorial|command|sop|workflow|meeting
    title      TEXT    NOT NULL,
    body       TEXT    NOT NULL DEFAULT '',
    tags       TEXT    NOT NULL DEFAULT '',   -- comma separated, normalised lowercase on write
    pinned     INTEGER NOT NULL DEFAULT 0,    -- NEW in v2
    created_at TEXT    NOT NULL,              -- ISO8601 UTC, seconds
    updated_at TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_entry_created ON entry(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_entry_kind    ON entry(kind);
CREATE INDEX IF NOT EXISTS idx_entry_pinned  ON entry(pinned DESC, created_at DESC);
```

Migration rule: after `CREATE TABLE IF NOT EXISTS`, read `PRAGMA table_info(entry)` and
`ALTER TABLE entry ADD COLUMN pinned INTEGER NOT NULL DEFAULT 0` only when the column is absent.
A v1 database must open, migrate and render with no manual step.

## Routes

| Method | Path | Behaviour |
|---|---|---|
| GET | `/` | list. Query: `kind`, `tag`, `q`, `pinned=1`. Pinned entries first, then newest. |
| GET | `/entry/{id}` | one entry. 404 page (not a JSON error) when missing. |
| GET | `/new` | form, `kind` preselects. |
| POST | `/entry` | create, 303 to the entry. 400 with a rendered form + inline error on bad input. |
| GET | `/entry/{id}/edit` | form. |
| POST | `/entry/{id}` | update, 303 to the entry. |
| POST | `/entry/{id}/delete` | delete, 303 to `/`. |
| POST | `/entry/{id}/pin` | toggle pinned, 303 back to the referring page. |
| GET | `/tags` | every tag with its count, as a page. Real counts only, from the database. |
| GET | `/health` | `{"status":"ok"}`, no auth, never touches the database. |
| GET/POST | `/login`, `/logout` | unchanged from v1. |

Errors render as HTML pages with the same shell, a heading, one sentence, and a way back. A 404
must not be a bare FastAPI JSON body.

## Search

`q` matches title, tags and body, case-insensitive. Results are ranked: title match first, then
tag match, then body match, then newest. Ranking is done in SQL or in Python, but it must be
deterministic and covered by a test.

`tag` filters exactly (case-insensitive), and `kind` and `tag` and `q` combine.

## Tags

Stored comma separated, normalised on write: strip, lowercase, drop empties, drop duplicates,
join with `,`. Tags are clickable everywhere they appear and lead to `/?tag=<tag>`.

## Pin

`pinned` is 0 or 1. Pinned entries sort above unpinned in every list view. The pin control is a
`<form method="post">` with a `<button>`, never a link, because it changes state.

## Copy a code block

Every `<pre>` in a rendered entry gets a copy control. It is a `<button>` with an accessible name,
it copies the block's text, and it confirms visibly for about two seconds. No clipboard API
fallback chain longer than: `navigator.clipboard` then a hidden textarea + `execCommand`. If
neither works the button says so instead of pretending.

## Theme

Warm light by default, dark available. The toggle is a real control, keyboard operable, with an
accessible name that reflects what it will do. The choice persists across visits and is applied
before first paint (no flash of the wrong theme). With no stored choice, follow
`prefers-color-scheme`. Both themes are verified at WCAG AA.

## UI states (R-27)

- **Empty list**: says what is missing and offers the one useful action.
- **Empty search result**: says which query found nothing and offers to clear it.
- **Error**: 404 and 500 render the shell with a real message.
- **Loading**: this is a server-rendered app with no client fetch, so there is no loading state to
  fake. Say so in the gate report rather than inventing a spinner.
- **Form error**: the submitted values come back, the failing field is marked, the message is
  next to it.

## Accessibility floor

`<html lang="id">`, unique `<title>` per page, `header`/`nav`/`main`/`footer`, one `h1`, no skipped
levels. Every control is a native element with an accessible name. Visible focus ring on
everything focusable. Tap targets at least 44px. No `outline: none` without a replacement.

## Mobile

390px is the reference width, not a breakpoint to survive. No horizontal overflow anywhere,
including long command lines inside `pre` (those scroll inside their own box, the page does not).
Test at 320, 390, 768, 1280.

## Ownership

| Area | Owner | Files |
|---|---|---|
| Data model, migration, search ranking, routes, errors, tests | wowo | `app/main.py`, `app/db.py`, `tests/` |
| Templates, CSS, theme, copy button, accessibility, mobile | wiwi | `app/templates/`, `app/static/` |
| Dockerfile, CI, README, .dockerignore, deploy contract | fufu | `Dockerfile`, `.github/`, `README.md`, `.dockerignore` |
| DESIGN.md, SPEC.md, final review, report, handoff to becik | brenour | `DESIGN.md`, `SPEC.md`, `REPORT-*.md` |

Nobody edits another owner's files. A change that crosses a boundary is requested, not made.

## Definition of done

1. `pytest -q` passes, with tests for: migration from a v1 database, search ranking, tag
   normalisation, pin ordering, 404 rendering, auth on/off.
2. The app runs and every interactive element has been clicked through, with the list recorded.
3. Both themes checked for contrast; 320/390/768/1280 with no horizontal overflow.
4. The antislop Delivery Gate is run and reported PASS per item, with evidence.
5. A report in the fixed 10-line block, pushed to `feat/v2`, with the full 40-char SHA.
