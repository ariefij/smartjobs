# Skema Multi Agent SmartJobs

SmartJobs memakai pola **supervisor + specialized agents**.

## Agen utama

1. `supervisor_agent`
   - merutekan intent user
   - memilih sub-agent berdasarkan pertanyaan, riwayat, dan ada/tidaknya CV

2. `search_lowongan_agent`
   - exact match ke SQLite
   - fallback ke semantic search Qdrant
   - fallback terakhir ke SQLite FTS bila Qdrant tidak tersedia

3. `text_to_sql_agent`
   - mengubah pertanyaan natural menjadi query SQL aman berbasis template
   - hanya mengizinkan `SELECT`
   - hanya mengakses tabel `jobs` / `jobs_fts`

4. `analisis_cv_agent`
   - menganalisis CV teks
   - membangun query pencarian dari hasil analisis CV

5. `rekomendasi_cv_agent`
   - menggabungkan query user dan analisis CV
   - menghasilkan rekomendasi lowongan yang relevan

6. `gap_skill_agent`
   - membandingkan skill kandidat dengan skill pada lowongan relevan untuk role target
   - menghasilkan gap skill dan saran belajar

7. `konsultasi_lowongan_agent`
   - menjawab pertanyaan umum seputar lowongan kerja dengan konteks hasil pencarian

## Alur routing

- tanpa CV + pertanyaan umum -> `konsultasi_lowongan_agent`
- tanpa CV + pertanyaan data/agregasi -> `text_to_sql_agent`
- dengan CV + analisis umum -> `analisis_cv_agent`
- dengan CV + kata kunci rekomendasi/cocok -> `rekomendasi_cv_agent`
- dengan CV + kata kunci gap skill -> `gap_skill_agent`
