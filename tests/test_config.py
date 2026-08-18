"""Tests for application settings."""

import pytest
from pydantic import ValidationError

from app.config import Settings


def test_defaults_are_usable_without_env() -> None:
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.chunk_size > 0
    assert settings.retrieval_top_k > 0


def test_collection_name_encodes_chunking_config() -> None:
    """One Qdrant collection per chunking config, so ablations coexist."""
    settings = Settings(_env_file=None, chunk_size=1000, chunk_overlap=200)  # type: ignore[call-arg]
    assert settings.collection_name == "chunks_1000_200"


def test_differing_chunk_configs_get_differing_collections() -> None:
    a = Settings(_env_file=None, chunk_size=500, chunk_overlap=100)  # type: ignore[call-arg]
    b = Settings(_env_file=None, chunk_size=700, chunk_overlap=100)  # type: ignore[call-arg]
    assert a.collection_name != b.collection_name


def test_rejects_non_positive_chunk_size() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, chunk_size=0)  # type: ignore[call-arg]


def test_reads_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CHUNK_SIZE", "1234")
    assert Settings(_env_file=None).chunk_size == 1234  # type: ignore[call-arg]


def test_api_key_is_not_exposed_by_repr(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-secret-value")
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert "sk-ant-secret-value" not in repr(settings)
