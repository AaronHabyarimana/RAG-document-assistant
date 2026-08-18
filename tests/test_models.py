"""Tests for the core schemas.

These guard the invariants in CLAUDE.md. They are cheap now and expensive to
add back after phase 5 has already produced numbers from a broken eval set.
"""

import pytest
from pydantic import ValidationError

from app.models import Chunk, DocumentSpan, make_chunk_id


def make_span(start: int, end: int, document: str = "handbook.pdf") -> DocumentSpan:
    return DocumentSpan(document_name=document, char_start=start, char_end=end)


class TestChunkId:
    def test_is_deterministic(self) -> None:
        assert make_chunk_id("a.pdf", 0, 100) == make_chunk_id("a.pdf", 0, 100)

    def test_differs_by_document(self) -> None:
        assert make_chunk_id("a.pdf", 0, 100) != make_chunk_id("b.pdf", 0, 100)

    def test_differs_by_span(self) -> None:
        assert make_chunk_id("a.pdf", 0, 100) != make_chunk_id("a.pdf", 0, 101)

    def test_span_boundary_is_unambiguous(self) -> None:
        """The separator must prevent (1, 23) from colliding with (12, 3)."""
        assert make_chunk_id("a.pdf", 1, 23) != make_chunk_id("a.pdf", 12, 3)


class TestDocumentSpanOverlap:
    def test_overlapping_spans(self) -> None:
        assert make_span(0, 100).overlaps(make_span(50, 150))

    def test_containment_counts_as_overlap(self) -> None:
        assert make_span(0, 100).overlaps(make_span(40, 60))
        assert make_span(40, 60).overlaps(make_span(0, 100))

    def test_disjoint_spans(self) -> None:
        assert not make_span(0, 100).overlaps(make_span(100, 200))

    def test_adjacent_spans_do_not_overlap(self) -> None:
        """Ranges are half-open, so touching endpoints are not a hit."""
        assert not make_span(0, 50).overlaps(make_span(50, 100))

    def test_different_documents_never_overlap(self) -> None:
        assert not make_span(0, 100, "a.pdf").overlaps(make_span(0, 100, "b.pdf"))

    def test_is_symmetric(self) -> None:
        a, b = make_span(0, 100), make_span(99, 200)
        assert a.overlaps(b) == b.overlaps(a)

    def test_rejects_inverted_range(self) -> None:
        with pytest.raises(ValidationError):
            DocumentSpan(document_name="a.pdf", char_start=100, char_end=50)


class TestChunk:
    def test_create_derives_deterministic_id(self) -> None:
        kwargs = {
            "document_name": "handbook.pdf",
            "text": "Die Anlage ist vor Wartung spannungsfrei zu schalten.",
            "char_start": 1200,
            "char_end": 1252,
            "page_numbers": [4],
        }
        assert Chunk.create(**kwargs).chunk_id == Chunk.create(**kwargs).chunk_id  # type: ignore[arg-type]

    def test_span_property_round_trips(self) -> None:
        chunk = Chunk.create(
            document_name="handbook.pdf",
            text="text",
            char_start=10,
            char_end=20,
            page_numbers=[1],
        )
        assert chunk.span == make_span(10, 20, "handbook.pdf")

    def test_accepts_multiple_pages(self) -> None:
        """Chunks straddle page boundaries; that must survive the model."""
        chunk = Chunk.create(
            document_name="report.pdf",
            text="text spanning a page break",
            char_start=0,
            char_end=26,
            page_numbers=[7, 8],
        )
        assert chunk.page_numbers == [7, 8]

    def test_rejects_empty_page_numbers(self) -> None:
        with pytest.raises(ValidationError):
            Chunk.create(
                document_name="a.pdf",
                text="text",
                char_start=0,
                char_end=4,
                page_numbers=[],
            )

    def test_rejects_zero_indexed_pages(self) -> None:
        with pytest.raises(ValidationError):
            Chunk.create(
                document_name="a.pdf",
                text="text",
                char_start=0,
                char_end=4,
                page_numbers=[0, 1],
            )

    def test_rejects_unsorted_pages(self) -> None:
        with pytest.raises(ValidationError):
            Chunk.create(
                document_name="a.pdf",
                text="text",
                char_start=0,
                char_end=4,
                page_numbers=[3, 2],
            )

    def test_rejects_duplicate_pages(self) -> None:
        with pytest.raises(ValidationError):
            Chunk.create(
                document_name="a.pdf",
                text="text",
                char_start=0,
                char_end=4,
                page_numbers=[2, 2],
            )

    def test_rejects_empty_text(self) -> None:
        with pytest.raises(ValidationError):
            Chunk.create(
                document_name="a.pdf",
                text="",
                char_start=0,
                char_end=1,
                page_numbers=[1],
            )
