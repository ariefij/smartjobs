# Jalur Text-to-SQL Aman

SmartJobs menyediakan jalur query data lowongan berbasis bahasa natural.

## Prinsip keamanan

- hanya query `SELECT`
- tidak mengizinkan `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `PRAGMA`, komentar SQL, atau multiple statement
- hanya boleh membaca tabel `jobs` dan `jobs_fts`
- parameter user selalu dimasukkan lewat placeholder
- template query dibatasi ke:
  - hitung jumlah lowongan
  - rata-rata gaji
  - top perusahaan
  - daftar lowongan dengan filter aman

## Komponen

- `src/smartjobs/sql_guard.py`
  - ekstraksi filter
  - generator template SQL aman
  - validator SQL
- `src/smartjobs/agents/query_sql.py`
  - orkestrasi text-to-SQL
  - eksekusi query
  - pembentukan ringkasan hasil
