# notulen

Catatan kerja pribadi dalam satu tempat: tasklist, tutorial, daftar perintah, SOP, workflow, dan notulen rapat.
Satu pengguna, tanpa kolaborasi, tanpa audio. Dioptimalkan untuk mencatat cepat dan menemukan cepat.

## Menjalankan secara lokal

```bash
python3.12 -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
export DB_PATH="$PWD/data/notulen.db"
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Buka <http://127.0.0.1:8000>.

Opsional, satu password untuk seluruh aplikasi:

```bash
export APP_PASSWORD='rahasia'
```

Kalau `APP_PASSWORD` tidak diisi, aplikasi berjalan tanpa login (untuk pemakaian lokal).

## Menjalankan dengan docker

```bash
docker build -t notulen .
docker run -d --name notulen -p 8000:8000 \
  -v notulen-data:/data \
  -e APP_PASSWORD='rahasia' \
  notulen
curl -s localhost:8000/health
```

## Persistence

Data lives in one SQLite file at `/data/notulen.db` inside the container, set by `DB_PATH`.
The image declares `VOLUME ["/data"]`, so mount a named volume or a host directory at `/data`
(`-v notulen-data:/data`). Without that mount the database is written into the container's
writable layer and is lost the moment the container is removed or recreated: every note, tag
and pin goes with it. Back up that one file and the whole notebook is backed up.

Outside a container, if `DB_PATH` is unset, the file is `<repo root>/data/notulen.db`.

## Environment variables

| Variable | Default | What it does |
|---|---|---|
| `DB_PATH` | `/data/notulen.db` in the image, `<repo>/data/notulen.db` locally | SQLite file location |
| `APP_PASSWORD` | unset | When set, every page except `/health` and `/login` needs a login |

The schema is created and migrated at startup, so a database from v1 opens without a manual step.

## Test

```bash
.venv/bin/python -m pytest -q
```

## Image

CI builds and pushes `ghcr.io/hadadkarsa/notulen-work-hdd` on every push to `main`, tagged with
the commit SHA and `latest`. Deployment is a separate step.
