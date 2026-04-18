from smartjobs.config import get_settings
from smartjobs.llm import OpenAIJobLLM


def test_sql_summary_uses_actual_aggregate_value():
    llm = OpenAIJobLLM(get_settings())
    text = llm._fallback_summary(
        query_used="berapa jumlah lowongan data analyst di jakarta",
        route="sqlite_text_to_sql",
        matches=[],
        cv_analysis=None,
        hasil_sql={
            "baris": [{"total_lowongan": 16}],
            "total_baris": 1,
        },
        analisis_gap_skill=None,
        intent="kueri_sql",
    )
    assert "16" in text
    assert "Nilai total lowongan adalah 16" in text
