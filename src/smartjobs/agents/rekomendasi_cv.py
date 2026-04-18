from __future__ import annotations

from dataclasses import dataclass

from ..llm import OpenAIJobLLM
from ..schemas import SearchRequest, SearchResponse
from .search_lowongan import SearchLowonganAgent


@dataclass
class RekomendasiCVAgent:
    llm: OpenAIJobLLM
    search_agent: SearchLowonganAgent

    def run(self, request: SearchRequest) -> SearchResponse:
        cv_analysis = self.llm.analyze_cv_text(request.cv_text or "")
        if request.query:
            query = f"{request.query}; {cv_analysis.kueri_pencarian}"
        else:
            query = cv_analysis.kueri_pencarian
        response = self.search_agent.run(query, limit=request.limit, cv_analysis=cv_analysis)
        response.jenis_respons = "rekomendasi_cv"
        response.nama_agen = "rekomendasi_cv_agent"
        response.output_terstruktur.intent = "rekomendasi_cv"
        response.output_terstruktur.nama_agen = "rekomendasi_cv_agent"
        response.output_terstruktur.analisis_cv = cv_analysis
        response.catatan.append("Rekomendasi lowongan dibuat dari ringkasan CV dan pencarian semantik.")
        return response
