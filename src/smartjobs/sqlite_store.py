from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from .normalizers import standardize_job_title
from .schemas import EnrichedJobRecord, SearchMatch


class SQLiteJobStore:
    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_schema(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id TEXT NOT NULL UNIQUE,
                    source_file TEXT NOT NULL,
                    raw_job_title TEXT NOT NULL,
                    standardized_job_title TEXT NOT NULL,
                    company_name TEXT NOT NULL,
                    location TEXT NOT NULL,
                    city TEXT,
                    province TEXT,
                    work_type TEXT NOT NULL,
                    salary_raw TEXT,
                    salary_min INTEGER,
                    salary_max INTEGER,
                    currency TEXT,
                    seniority TEXT,
                    skills TEXT NOT NULL,
                    description_clean TEXT NOT NULL,
                    search_text TEXT NOT NULL,
                    scraped_at TEXT,
                    raw_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_jobs_title ON jobs(standardized_job_title);
                CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs(company_name);
                CREATE INDEX IF NOT EXISTS idx_jobs_source_id ON jobs(source_id);
                CREATE VIRTUAL TABLE IF NOT EXISTS jobs_fts USING fts5(
                    standardized_job_title,
                    company_name,
                    location,
                    description_clean,
                    search_text
                );
                """
            )
            conn.commit()

    def rebuild(self, records: list[EnrichedJobRecord]) -> None:
        unique_records: list[EnrichedJobRecord] = []
        seen_source_ids: set[str] = set()
        for record in records:
            if record.source_id in seen_source_ids:
                continue
            seen_source_ids.add(record.source_id)
            unique_records.append(record)

        self.init_schema()
        with self.connect() as conn:
            conn.execute("DELETE FROM jobs")
            conn.execute("DELETE FROM jobs_fts")
            for record in unique_records:
                cursor = conn.execute(
                    """
                    INSERT INTO jobs (
                        source_id, source_file, raw_job_title, standardized_job_title,
                        company_name, location, city, province, work_type,
                        salary_raw, salary_min, salary_max, currency,
                        seniority, skills, description_clean, search_text,
                        scraped_at, raw_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.source_id,
                        record.source_file,
                        record.raw_job_title,
                        record.standardized_job_title,
                        record.company_name,
                        record.location,
                        record.city,
                        record.province,
                        record.work_type,
                        record.salary_raw,
                        record.salary_min,
                        record.salary_max,
                        record.currency,
                        record.seniority,
                        json.dumps(record.skills, ensure_ascii=False),
                        record.description_clean,
                        record.search_text,
                        record.scraped_at,
                        record.raw_json,
                    ),
                )
                rowid = cursor.lastrowid
                conn.execute(
                    "INSERT INTO jobs_fts(rowid, standardized_job_title, company_name, location, description_clean, search_text) VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        rowid,
                        record.standardized_job_title,
                        record.company_name,
                        record.location,
                        record.description_clean,
                        record.search_text,
                    ),
                )
            conn.commit()

    def exact_search(self, query: str, limit: int = 5) -> list[SearchMatch]:
        normalized = standardize_job_title(query).lower()
        sql = """
            SELECT * FROM jobs
            WHERE lower(standardized_job_title) = ?
               OR lower(raw_job_title) = ?
               OR lower(company_name) = ?
            ORDER BY standardized_job_title ASC
            LIMIT ?
        """
        with self.connect() as conn:
            rows = conn.execute(sql, (normalized, query.lower().strip(), query.lower().strip(), limit)).fetchall()
        return [self._row_to_match(row, source="sqlite_exact") for row in rows]

    def keyword_search(self, query: str, limit: int = 5) -> list[SearchMatch]:
        safe_query = " ".join(query.replace('"', ' ').split())
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT jobs.*
                FROM jobs_fts
                JOIN jobs ON jobs_fts.rowid = jobs.id
                WHERE jobs_fts MATCH ?
                LIMIT ?
                """,
                (safe_query, limit),
            ).fetchall()
        return [self._row_to_match(row, source="sqlite_fts") for row in rows]

    def run_safe_query(self, sql: str, params: list[Any] | tuple[Any, ...] | None = None) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(sql, params or []).fetchall()
        return [dict(row) for row in rows]

    def load_all_records(self) -> list[EnrichedJobRecord]:
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM jobs ORDER BY id ASC").fetchall()
        records: list[EnrichedJobRecord] = []
        for row in rows:
            payload = dict(row)
            payload["skills"] = json.loads(payload["skills"] or "[]")
            payload.pop("id", None)
            payload.pop("created_at", None)
            records.append(EnrichedJobRecord.model_validate(payload))
        return records

    def _row_to_match(self, row: sqlite3.Row, source: str) -> SearchMatch:
        skills = json.loads(row["skills"] or "[]")
        return SearchMatch(
            job_id=row["id"],
            source_id=row["source_id"],
            title=row["standardized_job_title"],
            company_name=row["company_name"],
            location=row["location"],
            work_type=row["work_type"],
            seniority=row["seniority"],
            score=1.0 if source == "sqlite_exact" else None,
            source=source,
            snippet=(row["description_clean"] or "")[:320],
            skills=skills,
        )
