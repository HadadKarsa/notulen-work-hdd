# notulen

Catatan kerja pribadi dalam satu tempat: tasklist, tutorial, daftar perintah, SOP, workflow, dan notulen rapat.
Satu pengguna, tanpa kolaborasi, tanpa audio. Dioptimalkan untuk mencatat cepat dan menemukan cepat.

## Menjalankan secara lokal

```bash
python3.12 -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
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
  -v "$PWD/data:/data" \
  -e APP_PASSWORD='rahasia' \
  notulen
curl -s localhost:8000/health
```

## Di mana database disimpan

SQLite, satu berkas. Lokasi ditentukan env var `DB_PATH`:

- di container: `/data/notulen.db` (mount volume ke `/data`, kalau tidak datanya hilang saat container dibuang)
- di luar container, kalau `DB_PATH` tidak diset: `<root repo>/data/notulen.db`

Skema dibuat otomatis saat aplikasi start.

## Test

```bash
pytest -q
```
