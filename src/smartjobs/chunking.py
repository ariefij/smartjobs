from __future__ import annotations

from .schemas import EnrichedJobRecord


def chunk_text(text: str, chunk_size: int = 900, overlap: int = 150) -> list[str]:
    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == len(text):
            break
        start = max(0, end - overlap)
    return chunks


def build_chunk_documents(record: EnrichedJobRecord, chunk_size: int = 900, overlap: int = 150) -> list[dict]:
    base_text = (
        f"Judul: {record.standardized_job_title}\n"
        f"Perusahaan: {record.company_name}\n"
        f"Lokasi: {record.location}\n"
        f"Tipe Kerja: {record.work_type}\n"
        f"Senioritas: {record.seniority or '-'}\n"
        f"Keahlian: {', '.join(record.skills)}\n\n"
        f"Deskripsi:\n{record.description_clean}"
    )
    chunks = chunk_text(base_text, chunk_size=chunk_size, overlap=overlap)
    return [
        {
            "source_id": record.source_id,
            "chunk_index": idx,
            "text": chunk,
            "metadata": {
                "source_id": record.source_id,
                "title": record.standardized_job_title,
                "company_name": record.company_name,
                "location": record.location,
                "work_type": record.work_type,
                "seniority": record.seniority,
                "skills": record.skills,
                "chunk_index": idx,
            },
        }
        for idx, chunk in enumerate(chunks)
    ]
