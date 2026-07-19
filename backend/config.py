"""
Application configuration using pydantic-settings.
Reads values from environment variables or a .env file.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from pathlib import Path


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM
    gemini_api_key: str = ""
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    llm_provider: str = "gemini"
    llm_model: str = "gemini-2.5-flash"
    embedding_provider: str = "gemini"  # 'gemini' | 'openai' | 'local'

    # OCR
    ocr_confidence_threshold: float = 70.0

    # Database
    sqlite_db_path: str = "./data/reports.db"

    # Chroma
    chroma_persist_dir: str = "./data/chroma"
    report_collection: str = "report_chunks"
    reference_collection: str = "reference_corpus"

    # Retrieval
    retrieval_top_k: int = 3

    # Server
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    backend_url: str = "http://localhost:8000"

    @property
    def db_path(self) -> Path:
        p = Path(self.sqlite_db_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def chroma_path(self) -> Path:
        p = Path(self.chroma_persist_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
