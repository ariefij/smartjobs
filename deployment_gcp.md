# Deploy SmartJobs ke Google Cloud Run (Artifact Registry)

Panduan ini disesuaikan untuk project **SmartJobs** yang sekarang memakai:

- **single Dockerfile**
- **Cloud Run**
- **Artifact Registry** sebagai registry utama
- **Qdrant eksternal**
- **SQLite + LLM** dibangun **sebelum** image dibuat

## 1. Asumsi arsitektur

Flow project ini adalah:

1. Build dataset lokal:
   - `build_sqlite.py`
   - `build_qdrant.py`
2. Build container image dari project yang **sudah** memiliki hasil preprocessing terbaru
3. Push image ke **Artifact Registry**
4. Deploy image ke **Cloud Run**

Penting:

- Project ini **tidak** lagi memakai `docker-compose`
- `QDRANT_URL` harus mengarah ke **Qdrant eksternal**
- Karena `Dockerfile` menyalin folder `dataset/`, maka file seperti `dataset/processed/data.sqlite` harus sudah dibuat **sebelum** `docker build`

---

## 2. Prasyarat

Pastikan Anda sudah punya:

1. Project Google Cloud aktif
2. Billing aktif
3. `gcloud` CLI terpasang dan sudah login
4. Docker terpasang
5. File `.env` yang berisi kredensial runtime yang valid

Contoh env minimum:

```env
OPENAI_API_KEY=REPLACE_ME
LLM_MODEL=gpt-4o-mini
VISION_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small

QDRANT_URL=https://<cluster>.gcp.cloud.qdrant.io
QDRANT_API_KEY=...
QDRANT_COLLECTION_NAME=smartjobs_jobs
```

---

## 3. Siapkan data aplikasi terlebih dahulu

Jalankan dari root project:

```bash
poetry install
cp .env.example .env
```

### Opsi cepat untuk tes LLM

```bash
PYTHONUNBUFFERED=1 poetry run python script/build_sqlite.py --limit 3 --progress-every 1 --show-llm-errors
```

### Build SQLite penuh dengan LLM

```bash
PYTHONUNBUFFERED=1 poetry run python script/build_sqlite.py --progress-every 10
```

### Build Qdrant eksternal

```bash
poetry run python script/build_qdrant.py
```

Setelah langkah ini selesai, minimal file berikut harus sudah tersedia:

- `dataset/processed/data.sqlite`
- `dataset/processed/jobs_cleaned.jsonl`

---

## 4. Inisialisasi project GCP

```bash
gcloud auth login
gcloud projects list
gcloud config set project PROJECT_ID
```

Aktifkan API yang dibutuhkan:

```bash
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com
```

---

## 5. Buat repository di Artifact Registry

Contoh memakai region `us-central1` dan nama repository `smartjobs`:

```bash
export PROJECT_ID=$(gcloud config get-value project)
export REGION=asia-southeast2
export REPOSITORY=smartjobs-repo
export IMAGE_NAME=smartjobs-api

gcloud artifacts repositories create $REPOSITORY \
  --repository-format=docker \
  --location=$REGION \
  --description="Docker repository for SmartJobs"
```

Kalau repository sudah ada, perintah ini bisa dilewati.

Format image yang akan dipakai:

```bash
asia-southeast2-docker.pkg.dev/finpro-493407/smartjobs-repo/smartjobs-api
```

---

## 6. Cek service account Cloud Build yang aktif

Default service account Cloud Build bisa berbeda antar project. Cek dulu service account yang benar-benar dipakai:

```bash
gcloud builds get-default-service-account
```

Simpan hasilnya, misalnya:

```bash
export BUILD_SA=$(gcloud builds get-default-service-account)
echo $BUILD_SA
```

Kalau build nanti gagal karena izin push image, berikan minimal role berikut ke service account tersebut:

```bash
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$BUILD_SA" \
  --role="roles/artifactregistry.writer"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$BUILD_SA" \
  --role="roles/logging.logWriter"
```

Catatan:
- Banyak project baru memakai `PROJECT_NUMBER-compute@developer.gserviceaccount.com`
- Beberapa project lama masih bisa memakai legacy Cloud Build service account
- Karena itu **jangan hardcode** service account; selalu cek dulu dengan `gcloud builds get-default-service-account`

---

## 7. Build dan push image dengan Cloud Build

Build image langsung ke Artifact Registry:

```bash
export IMAGE_URI=$REGION-docker.pkg.dev/$PROJECT_ID/$REPOSITORY/$IMAGE_NAME

gcloud builds submit --tag $IMAGE_URI
```

Kalau berhasil, image sekarang tersedia di Artifact Registry.

---

## 8. Smoke test lokal sebelum deploy

Sebelum deploy ke Cloud Run, sangat disarankan tes image secara lokal:

```bash
docker build -t smartjobs-api .
docker run --rm -p 8080:8080 --env-file .env smartjobs-api
```

Aplikasi harus listen di:

```text
http://localhost:8080
http://localhost:8080/docs
```

---

## 9. Deploy ke Cloud Run

Cloud Run mewajibkan container mendengarkan port `8080`. Project ini sudah disiapkan untuk memakai `${PORT:-8080}`.

Contoh deploy:

```bash
ENV_VARS=$(grep -v '^#' .env | grep -v '^$' | xargs | sed 's/ /,/g')

gcloud run deploy smartjobs-api \
  --image $IMAGE_URI \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --set-env-vars="$ENV_VARS"
```
# yang benar Opsi kalau memang mau pakai Artifact Registry

Berarti Anda harus build/push ke path itu dulu, misalnya:
export PROJECT_ID=finpro-493407
export REGION=us-central1
export REPOSITORY=smartjobs
export IMAGE_NAME=smartjobs-api
export IMAGE_URI=$REGION-docker.pkg.dev/$PROJECT_ID/$REPOSITORY/$IMAGE_NAME

gcloud builds submit --tag $IMAGE_URI .

# lalu deploy
ENV_VARS=$(grep -v '^#' .env | grep -v '^$' | xargs | sed 's/ /,/g')

gcloud run deploy smartjobs-api \
  --image $IMAGE_URI \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --set-env-vars="$ENV_VARS"

# Paling cepat, deploy image yang sudah ada
Anda sudah berhasil push ke:
gcr.io/finpro-493407/smartjobs-api:latest

# Jadi langsung deploy itu saja:
ENV_VARS=$(grep -v '^#' .env | grep -v '^$' | xargs | sed 's/ /,/g')

gcloud run deploy smartjobs-api \
  --image gcr.io/finpro-493407/smartjobs-api:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars="$ENV_VARS"

Setelah deploy selesai, Google Cloud akan mengembalikan **Service URL**.
Service [smartjobs-api] revision [smartjobs-api-00002-ghv] has been deployed and is serving 100 percent of traffic.
Service URL: https://smartjobs-api-94453605119.us-central1.run.app

Cek:

- root API
- `/docs`

Contoh:

```text
https://smartjobs-api-xxxxx-uc.a.run.app/docs
```

---

## 10. Catatan penting runtime

### Qdrant
- `QDRANT_URL` harus endpoint **eksternal**
- jangan isi `qdrant`, `localhost`, atau `127.0.0.1` saat deploy ke Cloud Run

### SQLite
- `data.sqlite` dibawa ke image saat `docker build`
- kalau Anda membangun ulang data lokal, Anda harus **build image ulang** agar SQLite terbaru ikut masuk

### OpenAI
- `OPENAI_API_KEY` wajib tersedia di runtime bila endpoint API masih membutuhkan enrichment, semantic search, atau fitur LLM lain

---

## 11. Troubleshooting

### A. Build Qdrant gagal karena point ID tidak valid
Contoh error:
```text
is not a valid point ID
```

Artinya source project belum memakai patch UUID point ID yang benar. Pakai versi project terbaru yang sudah diperbaiki.

### B. Build SQLite gagal karena `UNIQUE constraint failed: jobs.source_id`
Artinya project belum memakai patch dedup/source ID stability terbaru. Pakai versi project yang sudah diperbaiki.

### C. Build SQLite terlihat macet
Gunakan mode debug kecil:

```bash
PYTHONUNBUFFERED=1 poetry run python script/build_sqlite.py --limit 3 --progress-every 1 --show-llm-errors
```

### D. Cloud Build gagal push image
Cek default service account:

```bash
gcloud builds get-default-service-account
```

Lalu pastikan service account itu punya setidaknya:

- `roles/artifactregistry.writer`
- `roles/logging.logWriter`

### E. Cloud Run container gagal start
Pastikan `Dockerfile` menjalankan app dengan:

```dockerfile
CMD ["sh", "-c", "uvicorn smartjobs.server:app --host 0.0.0.0 --port ${PORT:-8080}"]
```

### F. Deploy masih memakai `gcr.io`
Gunakan Artifact Registry sebagai default. `Container Registry` sudah deprecated dan penulisan image ke sana sudah dihentikan. Jika Anda masih melihat URL `gcr.io`, pastikan itu memang repository `gcr.io` yang sudah di-host oleh Artifact Registry, atau pindahkan contoh command ke format `LOCATION-docker.pkg.dev/...`.

---

## 12. Ringkasan command yang paling aman

```bash
poetry install
cp .env.example .env

PYTHONUNBUFFERED=1 poetry run python script/build_sqlite.py --progress-every 10
poetry run python script/build_qdrant.py

export PROJECT_ID=$(gcloud config get-value project)
export REGION=us-central1
export REPOSITORY=smartjobs
export IMAGE_NAME=smartjobs-api
export IMAGE_URI=$REGION-docker.pkg.dev/$PROJECT_ID/$REPOSITORY/$IMAGE_NAME

gcloud artifacts repositories create $REPOSITORY \
  --repository-format=docker \
  --location=$REGION \
  --description="Docker repository for SmartJobs"

gcloud builds submit --tag $IMAGE_URI

ENV_VARS=$(grep -v '^#' .env | grep -v '^$' | xargs | sed 's/ /,/g')

gcloud run deploy smartjobs-api \
  --image $IMAGE_URI \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --set-env-vars="$ENV_VARS"
