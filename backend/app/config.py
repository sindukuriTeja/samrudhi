"""SAMRUDHI Agentic OS — backend configuration."""
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "SAMRUDHI Agentic OS"
    environment: str = "pilot"

    # --- LLM / Ollama ---
    # "ollama" uses the local Ollama server; "mock" is a deterministic offline
    # engine so the whole system runs even with no model pulled.
    llm_provider: Literal["ollama", "mock"] = "ollama"
    # Default to localhost for bare-metal runs; docker-compose overrides this
    # with the `ollama` service hostname.
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"
    ollama_timeout: float = 120.0
    # When True, any Ollama error automatically falls back to the mock engine
    # for that single call (keeps the pipeline alive).
    llm_fallback_to_mock: bool = True

    # --- Persistence ---
    db_path: str = "data/samrudhi.db"
    data_dir: str = "data"

    # --- Runtime ---
    max_concurrent_runs: int = 3
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8080,http://127.0.0.1:8080"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()