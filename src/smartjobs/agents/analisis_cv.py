from __future__ import annotations

from dataclasses import dataclass

from ..llm import OpenAIJobLLM
from ..schemas import SearchRequest, SearchResponse
from .search_lowongan import SearchLowonganAgent


@dataclass
class AnalisisCVAgent:
    llm: OpenAIJobLLM
    search_agent: SearchLowonganAgent

    def run(self, request: SearchRequest) -> SearchResponse:
        cv_analysis = self.llm.analyze_cv_text(request.cv_text or "")
        query = request.query or cv_analysis.kueri_pencarian
        response = self.search_agent.run(query, limit=request.limit, cv_analysis=cv_analysis)
        response.jenis_respons = "analisis_cv"
        response.nama_agen = "analisis_cv_agent"
        response.output_terstruktur.intent = "analisis_cv"
        response.output_terstruktur.nama_agen = "analisis_cv_agent"
        response.output_terstruktur.analisis_cv = cv_analysis
        response.catatan.append("CV teks dianalisis dengan LLM sebelum pencarian.")
        return response
