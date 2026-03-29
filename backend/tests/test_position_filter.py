"""Unit tests for reading-position-aware retrieval logic.

These tests cover the pure-Python helpers in retriever.py and the source
tagging in tutor.py. No database, ChromaDB, or LLM calls are made.
"""

import pytest

from app.rag.retriever import POSITION_FILTER_MIN_CHUNKS, _chunk_is_within_range, search_chunks_positioned
from app.agents.tutor import _format_sources


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_chunk(chunk_id: str, page_numbers: list[int], score: float = 0.8) -> dict:
    return {
        "id": chunk_id,
        "content": f"Content of {chunk_id}",
        "metadata": {
            "chapter": "Chapter 1",
            "section": "Section 1",
            "page_numbers": page_numbers,
            "chunk_index": 0,
            "content_type": "text",
        },
        "score": score,
    }


# ---------------------------------------------------------------------------
# _chunk_is_within_range
# ---------------------------------------------------------------------------

def test_chunk_within_range_all_pages_within() -> None:
    chunk = _make_chunk("c1", [10, 11, 12])
    assert _chunk_is_within_range(chunk, max_page=15) is True


def test_chunk_within_range_one_page_exceeds() -> None:
    chunk = _make_chunk("c1", [10, 11, 16])
    assert _chunk_is_within_range(chunk, max_page=15) is False


def test_chunk_within_range_exactly_at_boundary() -> None:
    chunk = _make_chunk("c1", [15])
    assert _chunk_is_within_range(chunk, max_page=15) is True


def test_chunk_within_range_empty_pages_passes_through() -> None:
    chunk = _make_chunk("c1", [])
    # No page info → treated as within range
    assert _chunk_is_within_range(chunk, max_page=5) is True


# ---------------------------------------------------------------------------
# search_chunks_positioned
# ---------------------------------------------------------------------------

def test_search_chunks_positioned_no_page_returns_same_as_search_chunks(monkeypatch) -> None:
    chunks = [_make_chunk("c1", [1]), _make_chunk("c2", [2])]

    def fake_search(*, book_id, query, k):
        return chunks[:k]

    monkeypatch.setattr("app.rag.retriever.search_chunks", fake_search)

    result, used_fallback = search_chunks_positioned(
        book_id="b1", query="test", k=2, current_page=None
    )
    assert result == chunks[:2]
    assert used_fallback is False


def test_search_chunks_positioned_filters_out_ahead_chunks(monkeypatch) -> None:
    in_range = [_make_chunk(f"c{i}", [i]) for i in range(1, 4)]   # pages 1–3
    ahead = [_make_chunk("c10", [20]), _make_chunk("c11", [25])]

    def fake_search(*, book_id, query, k):
        return (in_range + ahead)[:k]

    monkeypatch.setattr("app.rag.retriever.search_chunks", fake_search)

    result, used_fallback = search_chunks_positioned(
        book_id="b1", query="test", k=5, current_page=5
    )
    # All 3 in-range chunks pass; ahead ones are filtered
    assert all(c["id"] in {"c1", "c2", "c3"} for c in result)
    assert used_fallback is False


def test_search_chunks_positioned_triggers_fallback_when_too_few_in_range(monkeypatch) -> None:
    # Only 1 in-range chunk — below POSITION_FILTER_MIN_CHUNKS
    in_range = [_make_chunk("c1", [1])]
    ahead = [_make_chunk(f"a{i}", [50 + i]) for i in range(5)]

    def fake_search(*, book_id, query, k):
        return (in_range + ahead)[:k]

    monkeypatch.setattr("app.rag.retriever.search_chunks", fake_search)

    result, used_fallback = search_chunks_positioned(
        book_id="b1", query="test", k=4, current_page=5
    )
    assert used_fallback is True
    # In-range chunk should come first
    assert result[0]["id"] == "c1"


def test_search_chunks_positioned_exactly_at_min_threshold_no_fallback(monkeypatch) -> None:
    in_range = [_make_chunk(f"c{i}", [i]) for i in range(1, POSITION_FILTER_MIN_CHUNKS + 1)]

    def fake_search(*, book_id, query, k):
        return in_range[:k]

    monkeypatch.setattr("app.rag.retriever.search_chunks", fake_search)

    _, used_fallback = search_chunks_positioned(
        book_id="b1", query="test", k=5, current_page=10
    )
    assert used_fallback is False


# ---------------------------------------------------------------------------
# _format_sources — is_ahead_of_position tagging
# ---------------------------------------------------------------------------

def test_format_sources_no_current_page_no_ahead_tags() -> None:
    chunks = [_make_chunk("c1", [50])]
    sources = _format_sources(chunks, current_page=None)
    assert sources[0]["is_ahead_of_position"] is False


def test_format_sources_chunk_within_range_not_tagged() -> None:
    chunks = [_make_chunk("c1", [10, 11])]
    sources = _format_sources(chunks, current_page=15)
    assert sources[0]["is_ahead_of_position"] is False


def test_format_sources_chunk_beyond_current_page_tagged() -> None:
    chunks = [_make_chunk("c1", [20])]
    sources = _format_sources(chunks, current_page=10)
    assert sources[0]["is_ahead_of_position"] is True


def test_format_sources_chunk_spanning_boundary_tagged_by_any() -> None:
    # Chunk spans pages 8–12; reader is on page 10.
    # all(p <= 10) is False → filter would exclude it.
    # any(p > 10) is True → tag fires.
    chunks = [_make_chunk("c1", [8, 9, 10, 11, 12])]
    sources = _format_sources(chunks, current_page=10)
    assert sources[0]["is_ahead_of_position"] is True


def test_format_sources_empty_page_numbers_not_tagged() -> None:
    chunks = [_make_chunk("c1", [])]
    sources = _format_sources(chunks, current_page=5)
    assert sources[0]["is_ahead_of_position"] is False


def test_format_sources_includes_is_ahead_key_always() -> None:
    chunks = [_make_chunk("c1", [3])]
    sources = _format_sources(chunks, current_page=10)
    assert "is_ahead_of_position" in sources[0]
