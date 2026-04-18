from __future__ import annotations

import re
from dataclasses import dataclass

from .schemas import SQLPlan

DENYLIST = re.compile(r"(;|--|/\*|\*/|\b(insert|update|delete|drop|alter|attach|pragma|replace|create)\b)", re.I)


@dataclass
class FilterSet:
    role: str | None = None
    location: str | None = None
    company: str | None = None
    work_type: str | None = None
    seniority: str | None = None


def normalize_text(text: str) -> str:
    return " ".join((text or "").strip().split())


def extract_filters(question: str) -> FilterSet:
    q = normalize_text(question)
    lowered = q.lower()
    filters = FilterSet()

    locations = [
        "jakarta", "bandung", "surabaya", "yogyakarta", "medan", "semarang", "bali", "depok", "tangerang",
    ]
    for city in locations:
        if city in lowered:
            filters.location = city.title()
            break

    role_patterns = [
        r"(?:role|posisi|jabatan|untuk|sebagai)\s+([a-zA-Z][a-zA-Z\-/ ]{2,40})",
        r"\b(data analyst|data scientist|data engineer|business analyst|software engineer|product manager|ui ux designer)\b",
    ]
    for pattern in role_patterns:
        match = re.search(pattern, lowered, re.I)
        if match:
            value = match.group(1).strip() if match.lastindex else match.group(0).strip()
            filters.role = " ".join(word.capitalize() for word in value.split())
            break

    if "remote" in lowered:
        filters.work_type = "Remote"
    elif "hybrid" in lowered:
        filters.work_type = "Hybrid"
    elif "full time" in lowered or "full-time" in lowered:
        filters.work_type = "Full-time"
    elif "part time" in lowered or "part-time" in lowered or "paruh waktu" in lowered:
        filters.work_type = "Part-time"
    elif "kontrak" in lowered:
        filters.work_type = "Contract"

    for token, label in [("intern", "Intern"), ("junior", "Junior"), ("senior", "Senior"), ("manager", "Manager")]:
        if re.search(rf"(?<![a-z]){re.escape(token)}(?![a-z])", lowered):
            filters.seniority = label
            break

    company_match = re.search(r"(?:perusahaan|company)\s+([a-zA-Z0-9 .,&-]{2,60})", q, re.I)
    if company_match:
        filters.company = company_match.group(1).strip()

    return filters



def _build_where(filters: FilterSet) -> tuple[list[str], list[object]]:
    clauses: list[str] = []
    params: list[object] = []
    if filters.role:
        clauses.append("lower(standardized_job_title) LIKE ?")
        params.append(f"%{filters.role.lower()}%")
    if filters.location:
        clauses.append("lower(location) LIKE ?")
        params.append(f"%{filters.location.lower()}%")
    if filters.company:
        clauses.append("lower(company_name) LIKE ?")
        params.append(f"%{filters.company.lower()}%")
    if filters.work_type:
        clauses.append("lower(work_type) = ?")
        params.append(filters.work_type.lower())
    if filters.seniority:
        clauses.append("lower(seniority) = ?")
        params.append(filters.seniority.lower())
    return clauses, params



def build_safe_sql(question: str, limit: int = 20) -> SQLPlan:
    normalized = normalize_text(question)
    lowered = normalized.lower()
    if not normalized:
        return SQLPlan(aman=True, sql="SELECT standardized_job_title AS judul, company_name AS perusahaan, location AS lokasi FROM jobs ORDER BY standardized_job_title LIMIT ?", parameter=[limit], alasan="Pertanyaan kosong, tampilkan data contoh.", template="listing")

    filters = extract_filters(normalized)
    clauses, params = _build_where(filters)
    where_sql = f" WHERE {' AND '.join(clauses)}" if clauses else ""

    if any(token in lowered for token in ["berapa", "jumlah", "banyak", "total"]):
        sql = f"SELECT COUNT(*) AS total_lowongan FROM jobs{where_sql}"
        return SQLPlan(aman=True, sql=sql, parameter=params, alasan="Deteksi intent agregasi jumlah lowongan.", template="count")

    if "rata" in lowered and "gaji" in lowered:
        sql = f"SELECT AVG(salary_min) AS rata_rata_gaji_min, AVG(salary_max) AS rata_rata_gaji_max FROM jobs WHERE salary_min IS NOT NULL AND salary_max IS NOT NULL"
        if where_sql:
            sql += " AND " + " AND ".join(clauses)
        return SQLPlan(aman=True, sql=sql, parameter=params, alasan="Deteksi intent agregasi gaji.", template="salary_avg")

    if "perusahaan" in lowered and any(token in lowered for token in ["top", "terbanyak", "paling banyak"]):
        sql = f"SELECT company_name AS perusahaan, COUNT(*) AS total_lowongan FROM jobs{where_sql} GROUP BY company_name ORDER BY total_lowongan DESC, perusahaan ASC LIMIT ?"
        return SQLPlan(aman=True, sql=sql, parameter=[*params, limit], alasan="Deteksi intent ranking perusahaan.", template="top_company")

    sql = f"SELECT standardized_job_title AS judul, company_name AS perusahaan, location AS lokasi, work_type AS tipe_kerja, seniority AS senioritas, salary_min, salary_max FROM jobs{where_sql} ORDER BY standardized_job_title ASC LIMIT ?"
    return SQLPlan(aman=True, sql=sql, parameter=[*params, limit], alasan="Deteksi intent listing lowongan dengan filter aman.", template="listing")



def validate_sql_plan(plan: SQLPlan) -> SQLPlan:
    sql = normalize_text(plan.sql)
    if DENYLIST.search(sql):
        raise ValueError("SQL ditolak karena mengandung pola berbahaya.")
    if not sql.lower().startswith("select "):
        raise ValueError("Hanya query SELECT yang diizinkan.")
    if " from jobs" not in sql.lower() and " from jobs_fts" not in sql.lower():
        raise ValueError("Query hanya boleh mengakses tabel jobs/jobs_fts.")
    return SQLPlan(aman=True, sql=sql, parameter=plan.parameter, alasan=plan.alasan, template=plan.template)
