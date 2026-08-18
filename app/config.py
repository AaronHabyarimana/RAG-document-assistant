"""Application configuration, loaded from the environment / .env file."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Runtime configuration.

    Every value that an experiment might vary is a setting, never a literal.
    Phase 5 sweeps chunking and retrieval parameters, so they must be
    injectable from a config file rather than edited in place.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Secrets -----------------------------------------------------------
    anthropic_api_key: SecretStr | None = None

    # --- Infrastructure ----------------------------------------------------
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: SecretStr | None = None

    # --- Paths -------------------------------------------------------------
    data_dir: Path = PROJECT_ROOT / "data"
    cache_dir: Path = PROJECT_ROOT / ".cache"
    eval_dir: Path = PROJECT_ROOT / "eval"

    # --- Chunking (varied in phase 5 — never hardcode these) ---------------
    chunk_size: int = Field(default=700, gt=0, description="Target chunk size in tokens.")
    chunk_overlap: int = Field(default=100, ge=0, description="Overlap between chunks in tokens.")

    # --- Embedding ---------------------------------------------------------
    embedding_model: str = "intfloat/multilingual-e5-large"
    embedding_query_prefix: str = "query: "
    embedding_passage_prefix: str = "passage: "

    # --- Retrieval ---------------------------------------------------------
    retrieval_top_k: int = Field(default=5, gt=0)
    rerank_candidates: int = Field(default=20, gt=0)

    # --- Generation --------------------------------------------------------
    llm_model: str = "claude-sonnet-5"
    llm_max_tokens: int = 4096

    @property
    def collection_name(self) -> str:
        """Qdrant collection for the current chunking configuration.

        One collection per chunking config so that phase 5 ablations can be
        held side by side instead of re-indexing between every run.
        """
        return f"chunks_{self.chunk_size}_{self.chunk_overlap}"


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings."""
    return Settings()
