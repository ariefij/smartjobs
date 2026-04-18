# SmartJobs

SmartJobs adalah project AI berbahasa Indonesia untuk menjawab pertanyaan seputar lowongan kerja melalui chat, kueri data lowongan dengan text-to-SQL aman, analisis CV teks maupun gambar/PDF, rekomendasi pekerjaan berdasarkan CV, dan konsultasi gap skill.

Project ini memakai:
- SQLite untuk exact match dan query aman
- Qdrant untuk semantic search
- OpenAI API untuk enrichment, analisis CV, embedding, dan vision OCR
- LangChain + Langfuse untuk orkestrasi, prompt registry, dan observability
- FastAPI untuk API
- Streamlit untuk UI/UX demo
- Docker + GCP untuk deployment

> Catatan: `dataset/processed/data.sqlite` yang ikut dibundel dibuat dari dataset yang Anda unggah. Jika `OPENAI_API_KEY` tersedia, pipeline ELT akan memakai OpenAI untuk enrichment dan indexing Qdrant.

## Fitur utama

- ELT dari `jobs.jsonl` -> validasi Pydantic -> normalisasi -> `data.sqlite`
- Enrichment record lowongan dengan LLM. Runtime chat/CV/output dibuat LLM-based.
- Chunking dan embedding ke Qdrant
- Arsitektur multi-agent:
  - `supervisor_agent`
  - `search_lowongan_agent`
  - `text_to_sql_agent`
  - `analisis_cv_agent`
  - `rekomendasi_cv_agent`
  - `gap_skill_agent`
  - `konsultasi_lowongan_agent`
- Text-to-SQL aman berbasis template terbatas
- Analisis CV dari:
  - teks biasa
  - DOCX
  - PDF dengan text layer
  - PDF hasil scan / gambar via GPT-4 vision
- Dua output respons yang wajib dibuat oleh LLM:
  - `output_1_json_terstruktur` untuk pipeline sistem
  - `output_2_summary_natural` untuk pengguna akhir / Streamlit
- Prompt registry + observability Langfuse

## Struktur folder

```text
smartjobs/
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── README.md
├── deployment_gcp.md
├── flow.svg
├── langfuse_prompts.json
├── pyproject.toml
├── dataset/
│   ├── raw/
│   │   └── jobs.jsonl
│   └── processed/
│       ├── chunks_preview.jsonl
│       ├── data.sqlite
│       └── jobs_cleaned.jsonl
├── docs/
│   ├── multi_agent_schema.md
│   ├── project_smartjobs_requirements.md
│   ├── sqlite_schema.md
│   └── text_to_sql_aman.md
├── script/
│   ├── build_qdrant.py
│   └── build_sqlite.py
├── src/
│   └── smartjobs/
│       ├── agents/
│       ├── agent.py
│       ├── chunking.py
│       ├── config.py
│       ├── cv.py
│       ├── llm.py
│       ├── normalizers.py
│       ├── observability.py
│       ├── prompt_registry.py
│       ├── prompts.py
│       ├── qdrant_store.py
│       ├── schemas.py
│       ├── server.py
│       ├── simulation.py
│       ├── sql_guard.py
│       └── sqlite_store.py
└── tests/
    ├── test_api_output.py
    ├── test_normalizers.py
    ├── test_sql_guard.py
    ├── test_sql_summary.py
    ├── test_sqlite_store.py
    └── test_supervisor.py
```

## Alur arsitektur

1. **ELT ke SQLite**
   - load `jobs.jsonl`
   - validasi dengan Pydantic
   - parsing, cleaning, normalisasi, dan enrichment
   - transform ke skema SQLite
   - simpan ke `dataset/processed/data.sqlite`

2. **Index ke Qdrant**
   - baca data bersih dari SQLite
   - chunking per record
   - embedding dengan OpenAI
   - upsert ke koleksi Qdrant

3. **Runtime query**
   - supervisor menentukan intent
   - exact match ke SQLite bila cocok persis
   - semantic search ke Qdrant bila tidak cocok persis
   - text-to-SQL aman untuk kueri data lowongan
   - CV teks/gambar/PDF diparsing dulu lalu dianalisis sebelum pencarian

4. **Output**
   - `output_1_json_terstruktur`: JSON untuk sistem
   - `output_2_summary_natural`: narasi bahasa natural untuk UI Streamlit atau consumer API

## Mulai cepat

### 1) Instal dependensi

```bash
poetry install
cp .env.example .env
```

### 2) Bangun ulang SQLite tanpa LLM

```bash
poetry run python script/build_sqlite.py --disable-llm
```

### 3) Bangun ulang SQLite dengan enrichment OpenAI

```bash
poetry run python script/build_sqlite.py
```

### 4) Buat preview chunking

```bash
poetry run python script/build_qdrant.py --preview-only
```

### 5) Index ke Qdrant

```bash
docker compose up -d qdrant
poetry run python script/build_qdrant.py
```

### 6) Jalankan FastAPI

```bash
poetry run python -m smartjobs.server
```

Dokumentasi API tersedia di `http://localhost:8000/docs`.

> Penting: runtime API ini wajib memakai `OPENAI_API_KEY`. Tanpa key, endpoint chat/CV/vision/response akan mengembalikan HTTP 503 karena seluruh jalur runtime dibuat LLM-based sesuai requirement.

### 7) Jalankan Streamlit

```bash
poetry run streamlit run src/smartjobs/simulation.py
```

## Endpoint utama

### `POST /obrolan`
Untuk:
- chat seputar lowongan kerja
- konsultasi lowongan kerja
- analisis CV teks
- rekomendasi pekerjaan berdasarkan CV

Contoh request:

```json
{
  "pertanyaan": "Analis Data Jakarta",
  "riwayat": "",
  "teks_cv": null,
  "batas": 5
}
```

Contoh shape response berhasil:

```json
{
  "jalur": "sqlite_exact",
  "jenis_respons": "chat_lowongan",
  "nama_agen": "konsultasi_lowongan_agent",
  "pertanyaan_dipakai": "Analis Data Jakarta",
  "output_1_json_terstruktur": {
    "sumber": "sqlite_exact",
    "pertanyaan_dipakai": "Analis Data Jakarta",
    "total_hasil": 3,
    "analisis_cv": null,
    "hasil": [],
    "hasil_sql": null,
    "analisis_gap_skill": null,
    "intent": "chat_lowongan",
    "nama_agen": "konsultasi_lowongan_agent"
  },
  "output_2_summary_natural": "Ringkasan natural untuk user.",
  "catatan": []
}
```

### `POST /kueri-lowongan`
Untuk kueri data lowongan dengan text-to-SQL aman.

Contoh request:

```json
{
  "pertanyaan": "berapa jumlah lowongan data analyst di jakarta",
  "batas": 20
}
```

### `POST /analisis-gap-skill`
Untuk konsultasi gap skill terhadap role tertentu.

Contoh request:

```json
{
  "pertanyaan": "cek gap skill saya untuk data scientist",
  "teks_cv": "...isi CV...",
  "target_role": "Data Scientist",
  "batas": 5
}
```

### `POST /unggah-cv`
Untuk analisis CV dari teks, PDF, PDF hasil scan, dan gambar.

Multipart form-data:
- `pertanyaan` (opsional)
- `riwayat` (opsional)
- `batas`
- `target_role` (opsional)
- `file`


## Docker

Jalankan seluruh stack lokal:

```bash
docker compose up --build
```

Service yang tersedia:
- API FastAPI: `http://localhost:8000`
- Streamlit: `http://localhost:8501`
- Qdrant: `http://localhost:6333`

## Kontrak output sesuai requirement

Response runtime wajib mengikuti dua output berikut:
- `output_1_json_terstruktur`: untuk system di data pipeline
- `output_2_summary_natural`: untuk user di UI/UX Streamlit

Keduanya dibuat oleh LLM, bukan fallback template.

## Catatan implementasi

- Detail multi-agent ada di `docs/multi_agent_schema.md`.
- Aturan text-to-SQL aman ada di `docs/text_to_sql_aman.md`.
- Prompt registry lokal didefinisikan di `langfuse_prompts.json` dan dapat memakai Langfuse bila kredensial tersedia.
- Observability berjalan lewat trace lokal dan handler Langfuse bila dikonfigurasi.
