# Skema SQLite

Tabel utama: `jobs`

| Kolom | Tipe | Keterangan |
|---|---|---|
| id | INTEGER PK | row id lokal |
| source_id | TEXT UNIQUE | hash stabil dari data sumber |
| raw_job_title | TEXT | judul asli dari dataset |
| standardized_job_title | TEXT | judul hasil pembersihan / standardisasi |
| company_name | TEXT | nama perusahaan |
| location | TEXT | lokasi asli |
| city | TEXT | kota hasil pemisahan lokasi |
| province | TEXT | provinsi hasil pemisahan lokasi |
| work_type | TEXT | tipe kerja yang sudah dinormalisasi |
| salary_raw | TEXT | gaji mentah |
| salary_min | INTEGER | gaji minimum yang berhasil diparse bila ada |
| salary_max | INTEGER | gaji maksimum yang berhasil diparse bila ada |
| currency | TEXT | default IDR bila terdeteksi |
| seniority | TEXT | inferensi tingkat senioritas |
| skills | TEXT | string JSON array |
| description_clean | TEXT | deskripsi yang sudah dirapikan |
| search_text | TEXT | gabungan field untuk pencarian |
| scraped_at | TEXT | timestamp scrape |
| source_file | TEXT | nama file sumber |
| raw_json | TEXT | payload asli untuk audit |
| created_at | TEXT | waktu insert |

Tabel pencarian teks: `jobs_fts`

- FTS5 virtual table untuk `standardized_job_title`, `company_name`, `location`, `description_clean`, dan `search_text`.
