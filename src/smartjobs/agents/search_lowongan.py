from __future__ import annotations

from dataclasses import dataclass

from ..llm import OpenAIJobLLM
from ..schemas import ParsedCV, SearchResponse
from ..sqlite_store import SQLiteJobStore


@dataclass
class SearchLowonganAgent:
    sqlite_store: SQLiteJobStore
    llm: OpenAIJobLLM
    settings: object

    def run(self, query: str, limit: int = 5, cv_analysis: ParsedCV | None = None) -> SearchResponse:
        exact_results = self.sqlite_store.exact_search(query, limit=limit)
        notes: list[str] = []
        if exact_results:
            route = "sqlite_exact"
            structured, summary = self.llm.generate_outputs(
                query,
                route,
                exact_results,
                cv_analysis,
                intent="chat_lowongan",
                nama_agen="search_lowongan_agent",
            )
            return SearchResponse(
                route=route,
                jenis_respons="chat_lowongan",
                nama_agen="search_lowongan_agent",
                query_used=query,
                structured_output=structured,
                summary=summary,
                notes=notes,
            )

        try:
            from ..qdrant_store import QdrantJobStore

            semantic_results = QdrantJobStore(self.settings).semantic_search(query, limit=limit)
            route = semantic_results[0].sumber if semantic_results else "qdrant_semantic"
        except Exception:
            semantic_results = self.sqlite_store.keyword_search(query, limit=limit)
            route = "sqlite_fts" if semantic_results else "qdrant_semantic"
            notes.append("Pencarian semantik tidak tersedia, sistem memakai fallback ke SQLite FTS.")

        structured, summary = self.llm.generate_outputs(
            query,
            route,
            semantic_results,
            cv_analysis,
            intent="chat_lowongan",
            nama_agen="search_lowongan_agent",
        )
        return SearchResponse(
            route=route,
            jenis_respons="chat_lowongan",
            nama_agen="search_lowongan_agent",
            query_used=query,
            structured_output=structured,
            summary=summary,
            notes=notes,
        )
