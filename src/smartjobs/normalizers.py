from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from typing import Iterable

from .schemas import EnrichedJobRecord, RawJobRecord

WS_RE = re.compile(r"\s+")
NOISE_RE = re.compile(r"[\u200b\u200c\u200d\ufeff]")
MULTI_PUNCT_RE = re.compile(r"[|•·]+")
NON_STANDARD_CHAR_RE = re.compile(r"[^\S\r\n]+")

WORK_TYPE_MAP = {
    "full time": "Full-time",
    "full-time": "Full-time",
    "paruh waktu": "Part-time",
    "part time": "Part-time",
    "part-time": "Part-time",
    "kasual": "Casual",
    "kontrak/temporer": "Contract",
    "kontrak": "Contract",
    "contract": "Contract",
    "temporary": "Contract",
}

SENIORITY_HINTS = [
    ("magang", "Intern"),
    ("intern", "Intern"),
    ("junior", "Junior"),
    ("staff", "Staff"),
    ("associate", "Associate"),
    ("specialist", "Specialist"),
    ("senior", "Senior"),
    ("lead", "Lead"),
    ("supervisor", "Supervisor"),
    ("manager", "Manager"),
    ("head", "Head"),
]

SKILL_PATTERNS = [
    "sql", "python", "excel", "power bi", "tableau", "r", "statistics",
    "machine learning", "data visualization", "etl", "dashboard", "communication",
    "analysis", "analytics", "reporting", "tensorflow", "pandas", "spark",
]


def normalize_whitespace(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "")
    text = NOISE_RE.sub("", text)
    text = text.replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = NON_STANDARD_CHAR_RE.sub(" ", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    return text.strip()


def clean_text(text: str) -> str:
    text = normalize_whitespace(text)
    text = MULTI_PUNCT_RE.sub(" ", text)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    text = WS_RE.sub(" ", text.replace("\n", " "))
    return text.strip()


def title_case_keep_acronyms(text: str) -> str:
    acronyms = {"AI", "BI", "HR", "IT", "QA", "UI", "UX", "SQL", "RPA", "SEO", "SEM"}
    words: list[str] = []
    for token in clean_text(text).split():
        plain = token.strip("()/,-")
        if plain.upper() in acronyms:
            words.append(token.replace(plain, plain.upper()))
        else:
            words.append(token.capitalize())
    return " ".join(words)


def standardize_job_title(text: str) -> str:
    text = clean_text(text)
    text = re.sub(r"\burgent\b|\bneeded\b|\bvacancy\b|\blower\b", "", text, flags=re.IGNORECASE)
    text = WS_RE.sub(" ", text).strip(" -|/")
    return title_case_keep_acronyms(text)


def standardize_work_type(text: str) -> str:
    key = clean_text(text).lower()
    return WORK_TYPE_MAP.get(key, title_case_keep_acronyms(key))


def split_location(location: str) -> tuple[str | None, str | None]:
    cleaned = clean_text(location)
    parts = [part.strip() for part in cleaned.split(",") if part.strip()]
    if not parts:
        return None, None
    if len(parts) == 1:
        return parts[0], None
    return parts[0], parts[-1]


def parse_salary(salary: str | None) -> tuple[int | None, int | None, str | None]:
    if not salary or salary.strip().lower() == "none":
        return None, None, None
    digits = [int(part.replace('.', '').replace(',', '')) for part in re.findall(r"\d[\d\.,]*", salary)]
    if not digits:
        return None, None, None
    if len(digits) == 1:
        return digits[0], digits[0], "IDR"
    return min(digits), max(digits), "IDR"


def infer_seniority(job_title: str, description: str) -> str | None:
    haystack = f"{job_title} {description}".lower()
    for token, label in SENIORITY_HINTS:
        if re.search(rf"(?<![a-z]){re.escape(token)}(?![a-z])", haystack):
            return label
    return None


def infer_skills(texts: Iterable[str]) -> list[str]:
    haystack = " ".join(clean_text(text).lower() for text in texts)
    found: list[str] = []
    for skill in SKILL_PATTERNS:
        if skill in haystack:
            found.append(title_case_keep_acronyms(skill))
    return found


def build_search_text(record: dict) -> str:
    parts = [
        record.get("standardized_job_title", ""),
        record.get("company_name", ""),
        record.get("location", ""),
        record.get("work_type", ""),
        record.get("seniority", ""),
        " ".join(record.get("skills", [])),
        record.get("description_clean", ""),
    ]
    return clean_text(" ".join(part for part in parts if part))


def make_source_id(raw: RawJobRecord) -> str:
    payload = json.dumps(raw.model_dump(by_alias=True), sort_keys=True, ensure_ascii=False)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def fallback_enrich_job(raw: RawJobRecord) -> EnrichedJobRecord:
    cleaned_desc = clean_text(raw.job_description)
    title = standardize_job_title(raw.job_title)
    company = title_case_keep_acronyms(raw.company_name)
    location = title_case_keep_acronyms(raw.location)
    city, province = split_location(location)
    salary_min, salary_max, currency = parse_salary(raw.salary)
    seniority = infer_seniority(raw.job_title, raw.job_description)
    skills = infer_skills([raw.job_title, raw.job_description])

    payload = {
        "source_id": make_source_id(raw),
        "raw_job_title": clean_text(raw.job_title),
        "standardized_job_title": title,
        "company_name": company,
        "location": location,
        "city": city,
        "province": province,
        "work_type": standardize_work_type(raw.work_type),
        "salary_raw": clean_text(raw.salary or "") or None,
        "salary_min": salary_min,
        "salary_max": salary_max,
        "currency": currency,
        "seniority": seniority,
        "skills": skills,
        "description_clean": cleaned_desc,
        "search_text": "",
        "scraped_at": raw.scrape_timestamp,
        "raw_json": json.dumps(raw.model_dump(by_alias=True), ensure_ascii=False),
    }
    payload["search_text"] = build_search_text(payload)
    return EnrichedJobRecord.model_validate(payload)
