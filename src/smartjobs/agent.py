from __future__ import annotations

from dataclasses import dataclass

from .agents.supervisor import SupervisorAgent
from .config import Settings
from .llm import OpenAIJobLLM
from .observability import get_observer
from .schemas import SearchRequest, SearchResponse
from .sqlite_store import SQLiteJobStore


@dataclass
class SmartJobsAgent:
    settings: Settings

    def __post_init__(self) -> None:
        self.sqlite_store = SQLiteJobStore(self.settings.sqlite_path)
        self.observer = get_observer(self.settings)
        self.llm = OpenAIJobLLM(self.settings, observer=self.observer)
        self.supervisor = SupervisorAgent(self.settings, self.sqlite_store, self.llm)

    def search(self, request: SearchRequest) -> SearchResponse:
        with self.observer.trace("smartjobs.search", {"query": request.query, "has_cv": bool(request.cv_text)}):
            return self.supervisor.run(request)

    def search_from_file(
        self,
        file_bytes: bytes,
        filename: str,
        content_type: str | None,
        query: str = "",
        history: str = "",
        limit: int = 5,
    ) -> SearchResponse:
        with self.observer.trace("smartjobs.search_from_file", {"filename": filename, "content_type": content_type}):
            return self.supervisor.run_from_file(file_bytes, filename, content_type, query, history, limit)
