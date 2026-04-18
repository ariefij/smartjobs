from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from time import perf_counter
from typing import Any, Iterator

from .config import Settings


@dataclass
class TraceEvent:
    nama: str
    metadata: dict[str, Any] = field(default_factory=dict)
    durasi_ms: float | None = None


class NoOpLangfuseObserver:
    def __init__(self) -> None:
        self.events: list[TraceEvent] = []

    @contextmanager
    def trace(self, nama: str, metadata: dict[str, Any] | None = None) -> Iterator[None]:
        start = perf_counter()
        event = TraceEvent(nama=nama, metadata=metadata or {})
        try:
            yield
        finally:
            event.durasi_ms = round((perf_counter() - start) * 1000, 2)
            self.events.append(event)


class LangfuseObserver(NoOpLangfuseObserver):
    def __init__(self, settings: Settings):
        super().__init__()
        self.handler = None
        self.client = None
        if settings.langfuse_public_key and settings.langfuse_secret_key:
            try:
                from langfuse import Langfuse
                from langfuse.callback import CallbackHandler
            except Exception:
                self.handler = None
                self.client = None
            else:
                try:
                    self.client = Langfuse(
                        public_key=settings.langfuse_public_key,
                        secret_key=settings.langfuse_secret_key,
                        host=settings.langfuse_host,
                    )
                except Exception:
                    self.client = None
                try:
                    self.handler = CallbackHandler(
                        public_key=settings.langfuse_public_key,
                        secret_key=settings.langfuse_secret_key,
                        host=settings.langfuse_host,
                    )
                except Exception:
                    self.handler = None


def get_langfuse_handler(settings: Settings) -> Any | None:
    observer = LangfuseObserver(settings)
    return observer.handler



def get_observer(settings: Settings) -> NoOpLangfuseObserver:
    return LangfuseObserver(settings)
