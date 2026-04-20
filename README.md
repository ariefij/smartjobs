SmartJobs adalah project AI berbahasa Indonesia untuk membantu pencarian dan analisis lowongan kerja melalui **chat**, **query data lowongan**, dan **unggah CV** dalam bentuk **teks, PDF, PDF hasil scan, maupun gambar**. Project ini memakai **SQLite** sebagai basis data terstruktur, **Qdrant** sebagai vector database untuk pencarian semantik, **OpenAI API** untuk enrichment dan runtime LLM, **FastAPI** sebagai backend API, **Streamlit** sebagai UI demo, serta **Langfuse** untuk **prompt management** dan **observability**.

Arsitektur project ini mengikuti requirement bahwa peran LLM muncul di beberapa titik penting:

1. **enrichment dataset** saat membentuk SQLite,
2. **embedding/chunking** saat membentuk Qdrant,
3. **intent routing** saat menerima pertanyaan user,
4. **analisis CV** teks atau gambar,
5. **generasi jawaban akhir** dalam dua bentuk output.

---

## Tujuan sistem

Project ini dirancang untuk menangani kebutuhan berikut:

- chat seputar lowongan kerja,
- query data lowongan dengan jalur **text-to-SQL aman**,
- analisis CV dari teks, PDF, PDF hasil scan, dan gambar,
- rekomendasi pekerjaan berdasarkan CV,
- konsultasi gap skill terhadap role tertentu.

---

## Stack utama

- **Python 3.11**
- **FastAPI** untuk backend API
- **Streamlit** untuk UI/demo
- **SQLite** untuk exact match, data relasional, dan jalur text-to-SQL aman
- **Qdrant** untuk semantic search berbasis embedding
- **OpenAI API** untuk enrichment, intent router, analisis CV, OCR vision, dan response generation
- **LangChain + LangChain OpenAI + LangChain Qdrant** untuk integrasi embedding/vector store
- **Langfuse** untuk prompt dan observability/tracing
- **Docker** untuk container image
- **Google Cloud Build + Artifact Registry + Cloud Run** untuk build dan deployment API

---

## Arsitektur end-to-end

Secara garis besar alurnya adalah:

1. **Dataset mentah** dimuat dari `dataset/raw/jobs.jsonl`.
2. Dataset diproses dengan metode **ELT** untuk membentuk **SQLite**.
3. Hasil SQLite dibaca lagi, di-*chunk*, di-*embed*, lalu diindeks ke **Qdrant**.
4. Saat runtime, user dapat bertanya lewat chat atau mengunggah CV.
5. Supervisor multi-agent merutekan request ke agent yang tepat.
6. Sistem mengembalikan **2 output**:
   - `output_1_json_terstruktur` untuk sistem/data pipeline,
   - `output_2_summary_natural` untuk user di **UI Streamlit**.


## 1) Pengolahan dataset menjadi SQLite dengan LLM enrichment

### Sumber data

Pipeline dimulai dari file:

```text
dataset/raw/jobs.jsonl
```

Script utama untuk tahap ini adalah:

```bash
python script/build_sqlite.py
```

### Konsep ELT yang dipakai

Pada project ini, tahap pembentukan database dapat dipahami sebagai alur **ELT** berikut:

#### E — Extract / Load

- Python membaca setiap baris JSONL dari `dataset/raw/jobs.jsonl`.
- Setiap record divalidasi terlebih dahulu dengan schema `RawJobRecord` di `src/smartjobs/schemas.py`.

#### L — LLM enrichment

Setelah record mentah dimuat, project menggunakan **OpenAI API** melalui `OpenAIJobLLM.enrich_job()` di `src/smartjobs/llm.py` untuk enrichment per record.

Peran LLM pada tahap ini adalah melakukan parsing, cleaning, dan normalisasi seperti:

- standardize job title,
- fix casing,
- remove noise,
- rapikan teks,
- hapus karakter aneh,
- normalisasi whitespace,
- memastikan 1 input menghasilkan 1 record yang konsisten,
- menyusun field hasil yang cocok untuk SQLite dan Qdrant.

Prompt enrichment dikelola lewat `PromptRegistry` di `src/smartjobs/prompt_registry.py`.

- Bila kredensial Langfuse aktif, prompt dapat diambil dari **Langfuse**.
- Bila tidak, sistem memakai prompt lokal dari `src/smartjobs/prompts.py`.

### Validasi hasil enrichment

Setelah LLM mengembalikan JSON, hasilnya tidak langsung dipercaya. Project tetap melakukan validasi dengan pendekatan berikut:

- **Pydantic** untuk schema validation (`EnrichedJobRecord`),
- **rule-based normalizer** dan fallback lokal di `src/smartjobs/normalizers.py`,
- **regex/rule-based checks** pada beberapa bagian parsing dan routing.

Jadi, walaupun ada LLM enrichment, hasil akhir tetap dijaga kontraknya oleh validator aplikasi.

### T — Transform ke schema SQLite

Setelah record lolos validasi, field hasil enrichment ditransformasikan ke schema tabel `jobs`, antara lain:

- `raw_job_title`
- `standardized_job_title`
- `company_name`
- `location`, `city`, `province`
- `work_type`
- `salary_raw`, `salary_min`, `salary_max`, `currency`
- `seniority`
- `skills`
- `description_clean`
- `search_text`
- `scraped_at`
- `raw_json`

Skema lengkapnya dapat dilihat di `docs/sqlite_schema.md`.

### Simpan ke SQLite (non-LLM)

Penyimpanan ke database dilakukan secara deterministik oleh `SQLiteJobStore.rebuild()` di `src/smartjobs/sqlite_store.py`.

Tahap ini **bukan** pekerjaan LLM. Database dibangun secara lokal oleh SQLite, termasuk:

- membuat tabel `jobs`,
- membuat index penting,
- membuat virtual table `jobs_fts` untuk FTS5,
- menulis ulang isi tabel dari hasil record terstruktur.

### Output tahap SQLite

Tahap ini menghasilkan:

- `dataset/processed/jobs_cleaned.jsonl`
- `dataset/processed/data.sqlite`

### Menjalankan build SQLite


```bash
poetry run python script/build_sqlite.py --disable-llm
```

```bash
PYTHONUNBUFFERED=1 poetry run python script/build_sqlite.py --progress-every 10
```

## 2) Pembentukan vector database Qdrant

Setelah SQLite selesai, project membangun vector database Qdrant dari data yang sudah bersih.

Script utama:

```bash
python script/build_qdrant.py
```

### Alur pembentukan Qdrant

1. Record dibaca ulang dari `data.sqlite` melalui `SQLiteJobStore.load_all_records()`.
2. Setiap lowongan diubah menjadi satu atau lebih chunk dengan `build_chunk_documents()` di `src/smartjobs/chunking.py`.
3. Setiap chunk di-*embed* memakai model OpenAI embedding (`text-embedding-3-small` secara default).
4. Chunk lalu diindeks ke koleksi Qdrant melalui `QdrantJobStore.index_records()`.

### Catatan penting tentang embedding

Di repo ini, embedding dilakukan dengan **OpenAI embeddings** melalui LangChain, bukan dengan model lokal. Karena itu build Qdrant memerlukan:

- `OPENAI_API_KEY`
- `QDRANT_URL`
- `QDRANT_API_KEY` bila cluster Qdrant menggunakannya

### Preview chunk sebelum indexing

```bash
poetry run python script/build_qdrant.py --preview-only
```

Output preview:

- `dataset/processed/chunks_preview.jsonl`

### Index penuh ke Qdrant

```bash
poetry run python script/build_qdrant.py
```

---

## 3) Pipeline runtime untuk user query dan upload CV

Project ini memakai pola **multi-agent** dengan **supervisor** sebagai router utama.

Komponen utamanya:

- `SmartJobsAgent` di `src/smartjobs/agent.py`
- `SupervisorAgent` di `src/smartjobs/agents/supervisor.py`
- agent spesialis di folder `src/smartjobs/agents/`

#AI vision** untuk OCR.
- **Gambar CV**: sistem memakai **GPT-4 Vision / OpenAI vision** untuk ekstraksi teks.

---

## 4) Dua output response yang wajib

Project ini secara eksplisit mengharuskan **2 output** di response runtime.

### Output 1 — JSON terstruktur

### Output 2 — Summary natural

---

## 5) Peran Streamlit UI

UI ini menampilkan dua area utama:

- **Output 2 - Summary natural** untuk user,
- **Output 1 - JSON terstruktur** untuk kebutuhan sistem/debug/pipeline.

Mode yang tersedia di UI:

- Chat lowongan
- Kueri data lowongan
- Analisis CV / rekomendasi
- Konsultasi gap skill

Secara praktis, Streamlit di repo ini berfungsi sebagai **demo UI** yang memanggil FastAPI.

---

## 6) Prompt management dan observability dengan Langfuse

Project ini memakai **Langfuse** di dua area:

### Prompt management

`PromptRegistry` membaca metadata prompt dari `langfuse_prompts.json`.


### Observability / tracing

`LangfuseObserver` di `src/smartjobs/observability.py` 

Dengan kata lain, repo ini memang sudah memasukkan **prompt** dan **observability** ke dalam integrasi Langfuse.

---

## 7) Endpoint API utama


- `/obrolan` → chat lowongan, analisis CV, rekomendasi CV, atau routing lain via supervisor
- `/kueri-lowongan` → jalur text-to-SQL aman
- `/analisis-gap-skill` → fokus ke evaluasi gap skill
- `/unggah-cv` → menerima file CV dan memproses teks / vision OCR sesuai tipe file

---

## 8) Konfigurasi environment

Salin dulu template environment:

```bash
cp .env.example .env
```

Lalu isi nilai yang diperlukan.

### Catatan

- Build SQLite dengan LLM, build Qdrant, chat runtime, OCR vision, analisis CV, intent router, dan response generation semuanya membutuhkan `OPENAI_API_KEY`.
- Untuk deployment API ke Cloud Run, `QDRANT_URL` harus menunjuk ke **Qdrant eksternal** yang bisa diakses dari internet/Cloud Run.

---

## 9) Menjalankan project secara lokal

### Install dependency

```bash
poetry install
cp .env.example .env
```

### Langkah kerja lokal yang disarankan

#### 1. Build SQLite

```bash
PYTHONUNBUFFERED=1 poetry run python script/build_sqlite.py --progress-every 10
```

#### 2. Preview chunk

```bash
poetry run python script/build_qdrant.py --preview-only
```

#### 3. Index ke Qdrant

```bash
poetry run python script/build_qdrant.py
```

#### 4. Jalankan FastAPI

```bash
poetry run uvicorn smartjobs.server:app --host 0.0.0.0 --port 8000 --app-dir src
```

Swagger docs tersedia di:

```text
http://localhost:8000/docs
```

#### 5. Jalankan Streamlit UI

```bash
poetry run streamlit run src/smartjobs/simulation.py
```

UI Streamlit biasanya terbuka di:

```text
http://localhost:8501
```

Pastikan `API_URL` di `.env` mengarah ke URL API yang benar.

---

## 10) Docker build

Repo ini memiliki `Dockerfile` untuk menjalankan **FastAPI API**.

### Build image

```bash
docker build -t smartjobs-api .
```

### Jalankan container API

```bash
docker run --rm -p 8080:8080 --env-file .env smartjobs-api
```

Setelah itu API tersedia di:

```text
http://localhost:8080
http://localhost:8080/docs
```

### Tentang `docker-compose.yml`

Repo ini juga masih memiliki `docker-compose.yml` untuk kebutuhan lokal/development, yang mendefinisikan:

- `qdrant`
- `api`
- `streamlit`

Jalankan dengan:

```bash
docker compose up --build
```

Catatan penting:

- `docker-compose.yml` berguna untuk **demo lokal**.
- Untuk **deployment Cloud Run**, project mengasumsikan **Qdrant eksternal**, bukan service `qdrant` lokal dari compose.
- Streamlit di compose adalah UI lokal; deployment produksi API dijelaskan di bagian Cloud Run.

---

## 11) Build image ke Google Artifact Registry

Pendekatan yang dipakai repo ini adalah:

1. siapkan data lokal lebih dulu,
2. build container image,
3. push image ke **Artifact Registry**,
4. deploy image ke **Cloud Run**.

### Langkah A — siapkan artefak data sebelum build image

Karena folder `dataset/` ikut tersalin ke image, sebaiknya hasil preprocessing sudah siap sebelum `docker build` atau `gcloud builds submit` dijalankan.

Minimal siapkan:

- `dataset/processed/data.sqlite`
- `dataset/processed/jobs_cleaned.jsonl`

Bila semantic search ingin langsung aktif setelah deploy, pastikan Qdrant collection juga sudah dibangun.

### Langkah B — set variabel GCP

```bash
export PROJECT_ID=$(gcloud config get-value project)
export REGION=asia-southeast2
export REPOSITORY=smartjobs-repo
export IMAGE_NAME=smartjobs-api
export IMAGE_URI=$REGION-docker.pkg.dev/$PROJECT_ID/$REPOSITORY/$IMAGE_NAME
```

### Langkah C — aktifkan API yang dibutuhkan

```bash
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com
```

### Langkah D — buat repository Artifact Registry

```bash
gcloud artifacts repositories create $REPOSITORY \
  --repository-format=docker \
  --location=$REGION \
  --description="Docker repository for SmartJobs"
```

### Langkah E — cek service account Cloud Build

```bash
export BUILD_SA=$(gcloud builds get-default-service-account)
echo $BUILD_SA
```

Jika perlu, beri izin push image:

```bash
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$BUILD_SA" \
  --role="roles/artifactregistry.writer"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$BUILD_SA" \
  --role="roles/logging.logWriter"
```

### Langkah F — build dan push image dengan Cloud Build

```bash
gcloud builds submit --tag $IMAGE_URI
```

Setelah sukses, image API tersedia di Artifact Registry.

---

## 12) Deploy ke Google Cloud Run

Cloud Run di repo ini diposisikan untuk **API FastAPI**, bukan untuk UI Streamlit.

### Deploy image

```bash
ENV_VARS=$(grep -v '^#' .env | grep -v '^$' | xargs | sed 's/ /,/g')

gcloud run deploy smartjobs-api \
  --image $IMAGE_URI \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --set-env-vars="$ENV_VARS"
```

---

