# SmartJobs

SmartJobs adalah project AI berbahasa Indonesia untuk pencarian dan analisis lowongan kerja. Project ini menggabungkan **SQLite** untuk exact match dan query terstruktur, **Qdrant eksternal** untuk semantic search, **OpenAI API** untuk enrichment dan embedding, serta **FastAPI** sebagai API runtime.

Target deployment project ini adalah **single Docker image** yang dijalankan di **Google Cloud Run**.

## Stack utama

- **FastAPI** untuk API
- **SQLite** untuk exact match dan text-to-SQL aman
- **Qdrant eksternal** untuk semantic search
- **OpenAI API** untuk:
  - enrichment lowongan ke SQLite
  - embedding untuk Qdrant
  - analisis CV / vision di runtime
- **Poetry** untuk dependency management
- **Dockerfile tunggal** untuk build image
- **Cloud Run** untuk deployment

## Alur data

1. **Build SQLite**
   - baca `dataset/raw/jobs.jsonl`
   - validasi dan normalisasi record
   - optional enrichment dengan OpenAI
   - simpan hasil ke:
     - `dataset/processed/jobs_cleaned.jsonl`
     - `dataset/processed/data.sqlite`

2. **Build Qdrant**
   - baca hasil data bersih
   - chunking per lowongan
   - embedding dengan OpenAI
   - index ke koleksi Qdrant eksternal

3. **Runtime API**
   - supervisor menentukan intent
   - exact match / SQL aman memakai SQLite
   - semantic retrieval memakai Qdrant
   - CV teks / PDF / gambar diproses di jalur LLM runtime

## Struktur penting

```text
smartjobs/
├── .env.example
├── .dockerignore
├── Dockerfile
├── README.md
├── cloudbuild.yaml
├── deployment_gcp.md
├── dataset/
│   ├── raw/
│   │   └── jobs.jsonl
│   └── processed/
│       ├── jobs_cleaned.jsonl
│       ├── data.sqlite
│       └── chunks_preview.jsonl
├── script/
│   ├── build_sqlite.py
│   └── build_qdrant.py
├── src/smartjobs/
│   ├── config.py
│   ├── llm.py
│   ├── sqlite_store.py
│   ├── qdrant_store.py
│   └── server.py
└── tests/
```

## Persiapan

Install dependency lalu buat file environment:

```bash
poetry install
cp .env.example .env
```

Setelah itu **edit `.env`**. Jangan langsung lanjut tanpa mengisi nilai yang dibutuhkan.

## Environment minimum

### Wajib untuk build SQLite dengan LLM

```env
OPENAI_API_KEY=REPLACE_ME
LLM_MODEL=gpt-4o-mini
```

### Wajib untuk build Qdrant

```env
OPENAI_API_KEY=REPLACE_ME
EMBEDDING_MODEL=text-embedding-3-small
QDRANT_URL=https://<cluster>.gcp.cloud.qdrant.io
QDRANT_API_KEY=...
QDRANT_COLLECTION_NAME=smartjobs_jobs
```

### Wajib untuk runtime API / Cloud Run

```env
OPENAI_API_KEY=REPLACE_ME
PORT=8080
```

### Opsi runtime LLM

```env
LLM_REQUEST_TIMEOUT_SECONDS=60
LLM_MAX_RETRIES=3
LLM_RETRY_BACKOFF_SECONDS=2
```

## Build SQLite

### 1. Tanpa LLM

Gunakan ini untuk validasi cepat pipeline dasar:

```bash
poetry run python script/build_sqlite.py --disable-llm
```

Output:
- `dataset/processed/jobs_cleaned.jsonl`
- `dataset/processed/data.sqlite`

### 2. Dengan LLM

Gunakan ini bila ingin enrichment OpenAI aktif:

```bash
PYTHONUNBUFFERED=1 poetry run python script/build_sqlite.py --progress-every 10
```

### 3. Tes kecil dulu

Disarankan sebelum build penuh:

```bash
PYTHONUNBUFFERED=1 poetry run python script/build_sqlite.py --limit 3 --progress-every 1 --show-llm-errors
```

Kalau ingin proses langsung berhenti saat error LLM pertama:

```bash
PYTHONUNBUFFERED=1 poetry run python script/build_sqlite.py --limit 3 --progress-every 1 --strict-llm
```

### Hasil yang sehat

Untuk build SQLite by LLM yang benar, Anda seharusnya melihat progress seperti ini:

```text
Mode SQLite build: OpenAI enrichment aktif (model=gpt-4o-mini)
Progress SQLite build: 1 record selesai diproses | fallback=0
...
Basis data SQLite berhasil dibuat di .../dataset/processed/data.sqlite
Total fallback lokal selama build SQLite: 0
Selesai build SQLite.
```

## Build Qdrant

### 1. Preview chunking

```bash
poetry run python script/build_qdrant.py --preview-only
```

Ini akan membuat preview chunk ke:
- `dataset/processed/chunks_preview.jsonl`

### 2. Index penuh ke Qdrant eksternal

```bash
poetry run python script/build_qdrant.py
```

Hasil yang sehat:

```text
Preview chunk ditulis ke .../chunks_preview.jsonl dengan total 1332 chunk
Berhasil mengindeks 1332 chunk ke koleksi Qdrant 'smartjobs_jobs'
```

## Urutan kerja yang disarankan

Urutan paling aman untuk baseline produksi:

```bash
poetry install
cp .env.example .env
# edit .env
PYTHONUNBUFFERED=1 poetry run python script/build_sqlite.py --limit 3 --progress-every 1 --show-llm-errors
PYTHONUNBUFFERED=1 poetry run python script/build_sqlite.py --progress-every 10
poetry run python script/build_qdrant.py --preview-only
poetry run python script/build_qdrant.py
```

## Running Locally

### Streamlit Simulation
```bash
poetry run streamlit run src/agent_st/simulation.py
```

### FastAPI Server
```bash
poetry run python src/agent_st/server.py
```
The API will be available at `http://localhost:8000`. You can visit `http://localhost:8000/docs` for the interactive API documentation.

## Build Docker image

Build image production:

```bash
docker build -t smartjobs-api .
```

Tes lokal container:

```bash
docker run --rm -p 8090:8080 --env-file .env smartjobs-api
```

Akses endpoint:
- `/`
- `/kesehatan`
- `/docs`

## Deploy ke Google Cloud Run

Project ini menggunakan **single Dockerfile** dan tidak memakai `docker-compose`.

Ikuti panduan lengkap di:
- `deployment_gcp.md`

Ringkasnya:

```bash
gcloud builds submit --tag gcr.io/finpro-493407/smartjobs-api .
# Lihat daftar project yang Anda miliki
gcloud projects list


gcloud run deploy smartjobs-api \
  --image gcr.io/finpro-493407/smartjobs-api \
  --platform managed \
  --region asia-southeast2 \
  --allow-unauthenticated
```

Pastikan environment variable penting ikut diset saat deploy, terutama:
- `OPENAI_API_KEY`
- `QDRANT_URL`
- `QDRANT_API_KEY`
- `QDRANT_COLLECTION_NAME`
- `PORT=8080`

## Endpoint utama

### `POST /obrolan`

Untuk:
- chat seputar lowongan
- konsultasi lowongan
- analisis CV
- rekomendasi pekerjaan

Contoh request:

```json
{
  "pertanyaan": "Analis Data Jakarta",
  "riwayat": "",
  "teks_cv": null,
  "batas": 5
}
```

### `POST /kueri-lowongan`

Untuk text-to-SQL aman berbasis pertanyaan lowongan.

Contoh request:

```json
{
  "pertanyaan": "berapa jumlah lowongan data analyst di jakarta",
  "batas": 20
}
```

### `POST /analisis-gap-skill`

Untuk analisis gap skill terhadap role tertentu.

## Troubleshooting

### `build_sqlite.py` terasa diam / macet

Gunakan mode unbuffered dan tes kecil dulu:

```bash
PYTHONUNBUFFERED=1 poetry run python script/build_sqlite.py --limit 3 --progress-every 1 --show-llm-errors
```

### Semua record masuk fallback lokal

Cek:
- `OPENAI_API_KEY`
- `LLM_MODEL`
- output `--show-llm-errors`

### Qdrant gagal dengan `point ID`

Gunakan source terbaru project ini. Qdrant hanya menerima **unsigned integer** atau **UUID** sebagai point ID.

### Qdrant gagal konek

Cek:
- `QDRANT_URL` harus endpoint eksternal valid
- `QDRANT_API_KEY` harus benar
- `OPENAI_API_KEY` harus ada untuk embedding

### SQLite gagal dengan `UNIQUE constraint failed: jobs.source_id`

Gunakan source terbaru project ini. Jalur rebuild SQLite sudah didedup agar record duplikat tidak menjatuhkan build.

## Catatan penting

- Project ini **tidak lagi memakai `docker-compose`**.
- `QDRANT_URL` harus mengarah ke **Qdrant eksternal**, bukan service lokal `qdrant`.
- Runtime API bersifat **LLM-based**, jadi tanpa `OPENAI_API_KEY` beberapa endpoint akan gagal atau mengembalikan error.
- Setelah `cp .env.example .env`, selalu cek ulang isi `.env` sebelum menjalankan build.
```