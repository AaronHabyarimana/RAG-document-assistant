"""Core Pydantic schemas.

These types encode the project invariants documented in CLAUDE.md. Breaking
them does not fail loudly — it fails four phases later, when the evaluation
harness silently measures nothing. Hence the validators.
"""

from __future__ import annotations

import hashlib

from pydantic import BaseModel, Field, model_validator

CHUNK_ID_LENGTH = 16


def make_chunk_id(document_name: str, char_start: int, char_end: int) -> str:
    """Build a deterministic chunk id from its document-level character span.

    Determinism matters: re-indexing the same file with the same chunking
    configuration must produce identical ids, otherwise nothing downstream is
    reproducible.
    """
    digest = hashlib.sha256(f"{document_name}|{char_start}|{char_end}".encode())
    return digest.hexdigest()[:CHUNK_ID_LENGTH]


class DocumentSpan(BaseModel):
    """A half-open character range ``[char_start, char_end)`` in a source document.

    This is the unit evaluation gold labels are expressed in. Gold labels are
    never chunk ids: phase 5 varies chunk size, which changes every chunk id,
    which would invalidate the entire eval set.
    """

    document_name: str = Field(min_length=1)
    char_start: int = Field(ge=0)
    char_end: int = Field(gt=0)

    @model_validator(mode="after")
    def _check_range(self) -> DocumentSpan:
        if self.char_end <= self.char_start:
            msg = f"char_end ({self.char_end}) must be greater than char_start ({self.char_start})"
            raise ValueError(msg)
        return self

    def overlaps(self, other: DocumentSpan) -> bool:
        """Whether this span shares at least one character with ``other``.

        This is the primitive behind Recall@K: a retrieved chunk counts as a
        hit when it overlaps the gold span, regardless of chunk boundaries.
        """
        if self.document_name != other.document_name:
            return False
        return self.char_start < other.char_end and other.char_start < self.char_end


class Chunk(BaseModel):
    """A retrievable passage extracted from a source document."""

    chunk_id: str = Field(min_length=1)
    document_name: str = Field(min_length=1)
    text: str = Field(min_length=1)

    # Offsets into the *whole document*, not into the chunk or the page.
    char_start: int = Field(ge=0)
    char_end: int = Field(gt=0)

    # A chunk may straddle page boundaries, so this is a list. The page
    # citation is the headline feature of the product; losing it during
    # chunking makes everything downstream worthless.
    page_numbers: list[int] = Field(min_length=1)

    @model_validator(mode="after")
    def _check_invariants(self) -> Chunk:
        if self.char_end <= self.char_start:
            msg = f"char_end ({self.char_end}) must be greater than char_start ({self.char_start})"
            raise ValueError(msg)
        if any(page < 1 for page in self.page_numbers):
            msg = f"page_numbers must be 1-indexed, got {self.page_numbers}"
            raise ValueError(msg)
        if self.page_numbers != sorted(self.page_numbers):
            msg = f"page_numbers must be sorted, got {self.page_numbers}"
            raise ValueError(msg)
        if len(set(self.page_numbers)) != len(self.page_numbers):
            msg = f"page_numbers must not contain duplicates, got {self.page_numbers}"
            raise ValueError(msg)
        return self

    @property
    def span(self) -> DocumentSpan:
        """The chunk's position in its source document."""
        return DocumentSpan(
            document_name=self.document_name,
            char_start=self.char_start,
            char_end=self.char_end,
        )

    @classmethod
    def create(
        cls,
        *,
        document_name: str,
        text: str,
        char_start: int,
        char_end: int,
        page_numbers: list[int],
    ) -> Chunk:
        """Build a chunk with a deterministic id derived from its span."""
        return cls(
            chunk_id=make_chunk_id(document_name, char_start, char_end),
            document_name=document_name,
            text=text,
            char_start=char_start,
            char_end=char_end,
            page_numbers=page_numbers,
        )


class ScoredChunk(BaseModel):
    """A chunk together with the retriever score that surfaced it."""

    chunk: Chunk
    score: float
