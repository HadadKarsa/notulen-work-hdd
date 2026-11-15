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

## Persistence

> **Volume WAJIB dipasang di `/data`.** Tanpa itu, semua catatan hilang saat container dibuat ulang
> — diam-diam, tanpa error, dan baru ketahuan ketika datanya sudah tidak ada.

Database SQLite ada di `/data/notulen.db` (diatur lewat env var `DB_PATH`). Direktori `/data`
dideklarasikan sebagai `VOLUME` di Dockerfile, jadi docker membuat volume anonim kalau kamu tidak
menyebut satu pun — itu tetap menyimpan data, tapi sulit ditemukan dan mudah terlewat saat migrasi.
Sebut volumenya secara eksplisit:

```bash
docker run -d --name notulen -p 8000:8000 \
  -v notulen-data:/data \
  -e APP_PASSWORD='rahasia' \
  notulen
```

Atau dengan bind mount, seperti di contoh `docker run` di atas (`-v "$PWD/data:/data"`).

Di luar container, kalau `DB_PATH` tidak diset, database jatuh ke `<root repo>/data/notulen.db`.

Skema dibuat otomatis saat aplikasi start (`CREATE TABLE IF NOT EXISTS`), tidak ada langkah migrasi.
Untuk backup, cukup salin berkas `notulen.db` saat container berhenti — atau pakai
`docker run --rm -v notulen-data:/data -v "$PWD:/backup" alpine cp /data/notulen.db /backup/`.

## Test

```bash
pytest -q
```
