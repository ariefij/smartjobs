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
