# Ringkasan requirement project_smartjobs

Dokumen ini merangkum requirement dari file `project_smartjobs.docx` ke format markdown agar mudah direview di repository.

## Requirement inti

1. Buat satu folder project bernama `smartjobs` berdasarkan dataset jobs.
2. Project menggunakan AI untuk menjawab pertanyaan pekerjaan melalui chat request maupun file CV berupa teks atau gambar.
3. Project dimulai dengan mengolah dataset menjadi SQLite dan Qdrant dengan metode ELT.
4. Persiapan database menggunakan OpenAI API untuk parsing, pembersihan, dan normalisasi:
   - standardize job title
   - fix casing
   - remove noise
   - rapikan teks
   - hapus karakter aneh
   - normalisasi whitespace
   - pisah per dokumen / per record
   - ensure consistency
   - output SQL: `data.sqlite`
5. Gunakan Pydantic, regex, dan rule-based check untuk validasi.
6. Untuk Qdrant lakukan pemotongan chunk dan embedding.
7. Pipeline query:
   - exact match di SQLite bila query persis ada
   - jika tidak ada, gunakan pencarian semantik dari Qdrant
   - CV teks dianalisis dengan LLM lalu diproses seperti query pengguna
   - CV gambar/PDF scan memakai GPT-4 vision
8. Output respons harus 2 bentuk:
   - JSON terstruktur untuk pipeline sistem
   - ringkasan natural untuk pengguna di Streamlit
9. Stack: SQLite, Qdrant, LangChain, Langfuse, FastAPI, Docker, GCloud.
