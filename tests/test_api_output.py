from smartjobs.schemas import SearchMatch, SearchResponse, StructuredOutput


def test_search_response_uses_required_output_keys():
    payload = SearchResponse(
        route="sqlite_exact",
        jenis_respons="chat_lowongan",
        nama_agen="konsultasi_lowongan_agent",
        query_used="data analyst jakarta",
        structured_output=StructuredOutput(
            source="sqlite_exact",
            query_used="data analyst jakarta",
            total_results=1,
            results=[
                SearchMatch(
                    title="Data Analyst",
                    company_name="PT Maju",
                    location="Jakarta",
                    work_type="Full-time",
                    seniority="Junior",
                    source="sqlite_exact",
                )
            ],
            intent="chat_lowongan",
            nama_agen="konsultasi_lowongan_agent",
        ),
        summary="Ringkasan natural untuk user",
        notes=[],
    ).model_dump(by_alias=False)
    assert "output_1_json_terstruktur" in payload
    assert "output_2_summary_natural" in payload
    assert "output_terstruktur" not in payload
    assert "ringkasan" not in payload
    assert "summary" not in payload
