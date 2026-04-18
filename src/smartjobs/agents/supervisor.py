from __future__ import annotations

from dataclasses import dataclass

from ..cv import extract_cv_text
from ..llm import OpenAIJobLLM
from ..schemas import SearchRequest, SearchResponse
from ..sqlite_store import SQLiteJobStore
from .analisis_cv import AnalisisCVAgent
from .gap_skill import GapSkillAgent
from .konsultasi import KonsultasiLowonganAgent
from .query_sql import QuerySQLAgent
from .rekomendasi_cv import RekomendasiCVAgent
from .search_lowongan import SearchLowonganAgent


@dataclass
class SupervisorAgent:
    settings: object
    sqlite_store: SQLiteJobStore
    llm: OpenAIJobLLM

    def __post_init__(self) -> None:
        self.search_agent = SearchLowonganAgent(self.sqlite_store, self.llm, self.settings)
        self.konsultasi_agent = KonsultasiLowonganAgent(self.search_agent, self.llm)
        self.query_sql_agent = QuerySQLAgent(self.sqlite_store, self.llm)
        self.analisis_cv_agent = AnalisisCVAgent(self.llm, self.search_agent)
        self.rekomendasi_cv_agent = RekomendasiCVAgent(self.llm, self.search_agent)
        self.gap_skill_agent = GapSkillAgent(self.llm, self.search_agent)

    def run(self, request: SearchRequest) -> SearchResponse:
        intent, target_role = self.llm.classify_intent(request.query, has_cv=bool(request.cv_text))
        request.target_role = request.target_role or target_role
        if intent == "kueri_sql":
            return self.query_sql_agent.run_as_search_response(request.query, limit=request.limit)
        if intent == "konsultasi_gap_skill":
            return self.gap_skill_agent.run(request)
        if intent == "rekomendasi_cv":
            return self.rekomendasi_cv_agent.run(request)
        if intent == "analisis_cv":
            return self.analisis_cv_agent.run(request)
        return self.konsultasi_agent.run(request)

    def run_from_file(
        self,
        file_bytes: bytes,
        filename: str,
        content_type: str | None,
        query: str = "",
        history: str = "",
        limit: int = 5,
    ) -> SearchResponse:
        cv_text, mode = extract_cv_text(file_bytes, filename, content_type, self.llm, self.settings)
        request = SearchRequest(query=query, history=history, cv_text=cv_text, limit=limit)
        response = self.run(request)
        response.catatan.append(f"CV file diproses dengan mode: {mode}.")
        return response
