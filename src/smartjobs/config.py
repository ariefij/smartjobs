from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SmartJobs"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    api_url: str = "http://localhost:8000"

    openai_api_key: str | None = None
    openai_base_url: str | None = None
    llm_model: str = "gpt-4.1-mini"
    vision_model: str = "gpt-4.1-mini"
    embedding_model: str = "text-embedding-3-small"

    qdrant_url: str = "http://localhost:6333"
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


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
