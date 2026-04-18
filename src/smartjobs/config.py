from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SmartJobs"
    app_host: str = "0.0.0.0"
    app_port: int = Field(default=8000, validation_alias=AliasChoices("APP_PORT", "PORT"))
    api_url: str = "https://your-cloud-run-service-url"

    openai_api_key: str | None = None
    openai_base_url: str | None = None
    llm_model: str = "gpt-4o-mini"
    vision_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    llm_request_timeout_seconds: float = 60.0
    llm_max_retries: int = 3
    llm_retry_backoff_seconds: float = 2.0

    qdrant_url: str | None = None
    qdrant_api_key: str | None = None
    qdrant_collection_name: str = "smartjobs_jobs"

    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_host: str = "https://cloud.langfuse.com"

    sqlite_path: Path = Path("dataset/processed/data.sqlite")
    raw_dataset_path: Path = Path("dataset/raw/jobs.jsonl")
    cleaned_jsonl_path: Path = Path("dataset/processed/jobs_cleaned.jsonl")
    chunks_preview_path: Path = Path("dataset/processed/chunks_preview.jsonl")

    default_search_limit: int = 5
    chunk_size: int = 900
    chunk_overlap: int = 150
    max_vision_pages: int = 5

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def require_openai_api_key(self, purpose: str = "runtime LLM") -> str:
        value = (self.openai_api_key or "").strip()
        if not value:
            raise RuntimeError(
                f"OPENAI_API_KEY wajib diisi untuk {purpose}. Project ini memakai SQLite + LLM dan embedding OpenAI."
            )
        return value

    def require_qdrant_url(self) -> str:
        value = (self.qdrant_url or "").strip()
        if not value:
            raise RuntimeError(
                "QDRANT_URL wajib diisi ke endpoint Qdrant eksternal yang valid. Jangan kosongkan nilainya."
            )

        lowered = value.lower()
        invalid_examples = {
            "https://your-qdrant-host",
            "http://your-qdrant-host",
            "qdrant",
            "http://qdrant:6333",
            "https://qdrant:6333",
        }
        if lowered in invalid_examples or "your-qdrant-host" in lowered:
            raise RuntimeError(
                "QDRANT_URL masih berupa placeholder. Ganti dengan endpoint Qdrant Cloud / Qdrant eksternal Anda yang sebenarnya."
            )

        parsed = urlparse(value)
        hostname = (parsed.hostname or "").lower()
        if hostname in {"localhost", "127.0.0.1", "0.0.0.0", "qdrant"}:
            raise RuntimeError(
                "QDRANT_URL masih menunjuk ke host lokal / service internal. Untuk deployment ini, gunakan Qdrant eksternal yang bisa diakses dari Cloud Run."
            )
        if not parsed.scheme or not hostname:
            raise RuntimeError(
                "QDRANT_URL tidak valid. Isi dengan format URL lengkap, misalnya https://<cluster>.gcp.cloud.qdrant.io"
            )
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
