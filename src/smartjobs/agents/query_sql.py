from __future__ import annotations

from dataclasses import dataclass

from ..llm import OpenAIJobLLM
from ..schemas import HasilSQL, SQLQueryResponse, SearchResponse, StructuredOutput
from ..sql_guard import build_safe_sql, validate_sql_plan
from ..sqlite_store import SQLiteJobStore


@dataclass
class QuerySQLAgent:
    sqlite_store: SQLiteJobStore
    llm: OpenAIJobLLM

    def run(self, question: str, limit: int = 20) -> SQLQueryResponse:
        plan = validate_sql_plan(build_safe_sql(question, limit=limit))
        rows = self.sqlite_store.run_safe_query(plan.sql, plan.parameter)
        hasil_sql = HasilSQL(sql_aman=plan, baris=rows, total_baris=len(rows))
        _, summary = self.llm.generate_outputs(
            question,
            "sqlite_text_to_sql",
            [],
            None,
            intent="kueri_sql",
            nama_agen="text_to_sql_agent",
            hasil_sql=hasil_sql.model_dump(),
        )
        return SQLQueryResponse(
            pertanyaan_dipakai=question,
            hasil_sql=hasil_sql,
            ringkasan=summary,
            catatan=["Query dibangun dari template aman dan hanya mengakses tabel jobs."],
        )

    def run_as_search_response(self, question: str, limit: int = 20) -> SearchResponse:
        sql_response = self.run(question, limit=limit)
        structured = StructuredOutput(
            sumber="sqlite_text_to_sql",
            pertanyaan_dipakai=sql_response.pertanyaan_dipakai,
            total_hasil=0,
            hasil_sql=sql_response.hasil_sql,
            intent="kueri_sql",
            nama_agen="text_to_sql_agent",
        )
        return SearchResponse(
            route="sqlite_text_to_sql",
            jenis_respons="kueri_sql",
            nama_agen="text_to_sql_agent",
            query_used=sql_response.pertanyaan_dipakai,
            structured_output=structured,
            summary=sql_response.ringkasan,
            notes=sql_response.catatan,
        )
