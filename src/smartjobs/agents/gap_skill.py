from __future__ import annotations

from dataclasses import dataclass

from ..llm import OpenAIJobLLM
from ..schemas import SearchRequest, SearchResponse, StructuredOutput
from .search_lowongan import SearchLowonganAgent


@dataclass
class GapSkillAgent:
    llm: OpenAIJobLLM
    search_agent: SearchLowonganAgent

    def run(self, request: SearchRequest) -> SearchResponse:
        cv_analysis = self.llm.analyze_cv_text(request.cv_text or "")
        target_role = request.target_role or self.llm.extract_target_role(request.query or "") or (cv_analysis.peran_kandidat[0] if cv_analysis.peran_kandidat else "Data Analyst")
        search_response = self.search_agent.run(target_role, limit=request.limit, cv_analysis=cv_analysis)
        gap = self.llm.analyze_skill_gap(target_role, cv_analysis, search_response.output_terstruktur.hasil)
        structured, summary = self.llm.generate_outputs(
            request.query or target_role,
            search_response.jalur,
            search_response.output_terstruktur.hasil,
            cv_analysis,
            intent="konsultasi_gap_skill",
            nama_agen="gap_skill_agent",
            analisis_gap_skill=gap,
        )
        structured.analisis_gap_skill = gap
        structured.intent = "konsultasi_gap_skill"
        structured.nama_agen = "gap_skill_agent"
        return SearchResponse(
            route=search_response.jalur,
            jenis_respons="konsultasi_gap_skill",
            nama_agen="gap_skill_agent",
            query_used=request.query or target_role,
            structured_output=structured,
            summary=summary,
            notes=["Gap skill dihitung dari CV kandidat dan skill pada lowongan yang relevan."],
        )
