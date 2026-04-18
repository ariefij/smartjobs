import json

from smartjobs.schemas import EnrichedJobRecord
from smartjobs.sqlite_store import SQLiteJobStore


def test_exact_search(tmp_path):
    db_path = tmp_path / "test.sqlite"
    store = SQLiteJobStore(db_path)
    record = EnrichedJobRecord(
        source_id="abc",
        raw_job_title="Data Analyst",
        standardized_job_title="Data Analyst",
        company_name="PT Test",
        location="Jakarta Selatan, Jakarta Raya",
        city="Jakarta Selatan",
        province="Jakarta Raya",
        work_type="Full-time",
        salary_raw=None,
        salary_min=None,
        salary_max=None,
        currency=None,
        seniority="Junior",
        skills=["SQL", "Python"],
        description_clean="Menganalisis data dan membuat dashboard.",
        search_text="Data Analyst PT Test Jakarta SQL Python",
        scraped_at=None,
        raw_json=json.dumps({"job_title": "Data Analyst"}),
    )
    store.rebuild([record])
    results = store.exact_search("Data Analyst")
    assert len(results) == 1
    assert results[0].company_name == "PT Test"


def test_rebuild_deduplicates_duplicate_source_ids(tmp_path):
    db_path = tmp_path / "test.sqlite"
    store = SQLiteJobStore(db_path)
    first = EnrichedJobRecord(
        source_id="dup-id",
        raw_job_title="Data Analyst",
        standardized_job_title="Data Analyst",
        company_name="PT Test",
        location="Jakarta Selatan, Jakarta Raya",
        city="Jakarta Selatan",
        province="Jakarta Raya",
        work_type="Full-time",
        salary_raw=None,
        salary_min=None,
        salary_max=None,
        currency=None,
        seniority="Junior",
        skills=["SQL"],
        description_clean="Analisis data.",
        search_text="Data Analyst PT Test Jakarta SQL",
        scraped_at=None,
        raw_json=json.dumps({"job_title": "Data Analyst"}),
    )
    second = EnrichedJobRecord(
        source_id="dup-id",
        raw_job_title="Business Analyst",
        standardized_job_title="Business Analyst",
        company_name="PT Other",
        location="Bandung, Jawa Barat",
        city="Bandung",
        province="Jawa Barat",
        work_type="Hybrid",
        salary_raw=None,
        salary_min=None,
        salary_max=None,
        currency=None,
        seniority="Mid",
        skills=["SQL", "Excel"],
        description_clean="Analisis bisnis.",
        search_text="Business Analyst PT Other Bandung SQL Excel",
        scraped_at=None,
        raw_json=json.dumps({"job_title": "Business Analyst"}),
    )
    store.rebuild([first, second])
    rows = store.run_safe_query("SELECT source_id, raw_job_title, company_name FROM jobs")
    assert rows == [{"source_id": "dup-id", "raw_job_title": "Data Analyst", "company_name": "PT Test"}]
