# Deployment ke Google Cloud

Target yang paling cocok untuk project ini adalah **Cloud Run** untuk API FastAPI dan **Qdrant Cloud** atau Qdrant self-hosted terpisah.

## Opsi deployment yang direkomendasikan

1. **Cloud Run** untuk service API FastAPI
2. **Cloud Storage** untuk menyimpan unggahan CV sementara jika dibutuhkan
3. **Secret Manager** untuk `OPENAI_API_KEY`, `QDRANT_API_KEY`, dan kredensial Langfuse
4. **Qdrant Cloud** atau VM terpisah untuk basis data vektor
5. **Cloud Build** untuk membangun image

## Langkah ringkas Cloud Run

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/smartjobs-api
gcloud run deploy smartjobs-api \
  --image gcr.io/YOUR_PROJECT_ID/smartjobs-api \
  --platform managed \
  --region asia-southeast2 \
  --allow-unauthenticated \
  --set-env-vars APP_HOST=0.0.0.0,APP_PORT=8080 \
  --set-secrets OPENAI_API_KEY=OPENAI_API_KEY:latest
```

## Variabel environment yang wajib di Cloud Run

- `OPENAI_API_KEY`
- `LLM_MODEL`
- `VISION_MODEL`
- `EMBEDDING_MODEL`
- `QDRANT_URL`
- `QDRANT_API_KEY`
- `QDRANT_COLLECTION_NAME`
- `LANGFUSE_PUBLIC_KEY`
- `LANGFUSE_SECRET_KEY`
- `LANGFUSE_HOST`

## Catatan

- UI Streamlit bisa dipisah ke service Cloud Run kedua, atau dijalankan lokal/internal saja.
- SQLite cocok sebagai basis data demo yang dibundel, tetapi untuk production multi-writer sebaiknya sinkronkan ke database operasional terpisah.
- Unggah file CV akan lebih aman bila memakai signed URL dan bucket sementara.
