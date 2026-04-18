from __future__ import annotations

from dataclasses import dataclass

from ..llm import OpenAIJobLLM
from ..schemas import SearchRequest, SearchResponse
from .search_lowongan import SearchLowonganAgent


@dataclass
class KonsultasiLowonganAgent:
    search_agent: SearchLowonganAgent
    llm: OpenAIJobLLM

    def run(self, request: SearchRequest) -> SearchResponse:
        response = self.search_agent.run(request.query, limit=request.limit)
        response.jenis_respons = "chat_lowongan"
        response.nama_agen = "konsultasi_lowongan_agent"
        response.output_terstruktur.intent = "chat_lowongan"
        response.output_terstruktur.nama_agen = "konsultasi_lowongan_agent"
        return response
