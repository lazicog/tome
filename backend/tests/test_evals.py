"""Tests for the eval persistence service and LLM-as-judge evaluator."""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import app.services.database as db_mod
from app.services.evals import create_eval, eval_stats, get_eval, list_evals


@pytest_asyncio.fixture(autouse=True)
async def _isolated_db(tmp_path):
    db_mod._data_dir_override = tmp_path
    await db_mod.init_db()
    async with db_mod.get_connection() as conn:
        await conn.execute(
            "INSERT INTO books (id, title, file_name, status, chunks, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("book1", "Test Book", "test.pdf", "ready", 10, "2026-01-01T00:00:00Z"),
        )
        await conn.commit()
    yield
    db_mod._data_dir_override = None


# ── create_eval ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_eval_minimal():
    record = await create_eval(
        book_id="book1",
        user_message="What is ownership?",
        assistant_response="Ownership is...",
    )
    assert record["book_id"] == "book1"
    assert record["user_message"] == "What is ownership?"
    assert record["id"] is not None
    assert record["faithfulness_score"] is None
    assert record["helpfulness_score"] is None


@pytest.mark.asyncio
async def test_create_eval_full():
    record = await create_eval(
        book_id="book1",
        user_message="Explain borrowing",
        assistant_response="Borrowing allows...",
        session_id="sess-abc",
        retrieved_context=["chunk1 text", "chunk2 text"],
        tool_iterations=2,
        tools_called=["search_book", "get_page_text"],
        used_retrieval=True,
        used_page_text=True,
        used_web_search=False,
        faithfulness_score=4.0,
        faithfulness_reason="Most claims grounded",
        helpfulness_score=5.0,
        helpfulness_reason="Excellent explanation",
        eval_model="gpt-4o-mini",
        eval_duration_ms=1234,
    )
    assert record["session_id"] == "sess-abc"
    assert record["faithfulness_score"] == 4.0
    assert record["helpfulness_score"] == 5.0
    assert record["used_retrieval"] is True
    assert record["used_web_search"] is False
    assert record["tools_called"] == ["search_book", "get_page_text"]
    assert record["retrieved_context"] == ["chunk1 text", "chunk2 text"]
    assert record["tool_iterations"] == 2
    assert record["eval_duration_ms"] == 1234


# ── list_evals ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_evals_empty():
    results = await list_evals("book1")
    assert results == []


@pytest.mark.asyncio
async def test_list_evals_returns_newest_first():
    await create_eval(book_id="book1", user_message="q1", assistant_response="a1")
    await create_eval(book_id="book1", user_message="q2", assistant_response="a2")

    results = await list_evals("book1")
    assert len(results) == 2
    # newest first (ORDER BY created_at DESC)
    assert results[0]["user_message"] == "q2"
    assert results[1]["user_message"] == "q1"


@pytest.mark.asyncio
async def test_list_evals_limit():
    for i in range(5):
        await create_eval(book_id="book1", user_message=f"q{i}", assistant_response=f"a{i}")

    results = await list_evals("book1", limit=3)
    assert len(results) == 3


# ── get_eval ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_eval_found():
    record = await create_eval(
        book_id="book1",
        user_message="What is a trait?",
        assistant_response="A trait is an interface-like...",
        faithfulness_score=3.5,
    )
    fetched = await get_eval(record["id"])
    assert fetched is not None
    assert fetched["id"] == record["id"]
    assert fetched["faithfulness_score"] == 3.5


@pytest.mark.asyncio
async def test_get_eval_not_found():
    result = await get_eval("nonexistent-id")
    assert result is None


# ── eval_stats ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_eval_stats_empty():
    stats = await eval_stats("book1")
    assert stats["total"] == 0


@pytest.mark.asyncio
async def test_eval_stats_aggregates():
    await create_eval(
        book_id="book1",
        user_message="q1",
        assistant_response="a1",
        faithfulness_score=4.0,
        helpfulness_score=5.0,
        used_retrieval=True,
        tool_iterations=2,
    )
    await create_eval(
        book_id="book1",
        user_message="q2",
        assistant_response="a2",
        faithfulness_score=2.0,
        helpfulness_score=3.0,
        used_retrieval=False,
        tool_iterations=1,
    )

    stats = await eval_stats("book1")
    assert stats["total"] == 2
    assert stats["avg_faithfulness"] == 3.0
    assert stats["avg_helpfulness"] == 4.0
    assert stats["avg_tool_iterations"] == 1.5
    assert stats["retrieval_rate"] == 0.5


# ── evaluator (fire-and-forget) ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_run_eval_disabled(monkeypatch):
    """When eval_enabled=False, run_eval returns immediately without calling LLM."""
    import app.config as cfg_mod
    monkeypatch.setattr(cfg_mod.settings, "eval_enabled", False)

    from app.agents.evaluator import run_eval

    with patch("app.agents.evaluator._get_eval_llm") as mock_llm:
        await run_eval(
            book_id="book1",
            user_message="q",
            assistant_response="a",
            retrieved_chunks=[],
            tools_called=[],
            tool_iterations=0,
        )
        mock_llm.assert_not_called()


@pytest.mark.asyncio
async def test_run_eval_empty_response(monkeypatch):
    """When assistant_response is blank, run_eval skips eval."""
    import app.config as cfg_mod
    monkeypatch.setattr(cfg_mod.settings, "eval_enabled", True)

    from app.agents.evaluator import run_eval

    with patch("app.agents.evaluator._get_eval_llm") as mock_llm:
        await run_eval(
            book_id="book1",
            user_message="q",
            assistant_response="   ",
            retrieved_chunks=[],
            tools_called=[],
            tool_iterations=0,
        )
        mock_llm.assert_not_called()


@pytest.mark.asyncio
async def test_run_eval_persists_scores(monkeypatch):
    """Happy path: LLM returns valid scores, eval is persisted."""
    import app.config as cfg_mod
    monkeypatch.setattr(cfg_mod.settings, "eval_enabled", True)
    monkeypatch.setattr(cfg_mod.settings, "eval_model", "")
    monkeypatch.setattr(cfg_mod.settings, "llm_model", "gpt-4o-mini")

    faith_response = MagicMock()
    faith_response.content = '{"score": 4, "reason": "Grounded in sources"}'
    help_response = MagicMock()
    help_response.content = '{"score": 5, "reason": "Very clear explanation"}'

    mock_llm = AsyncMock()
    mock_llm.ainvoke = AsyncMock(side_effect=[faith_response, help_response])

    from app.agents.evaluator import run_eval

    with patch("app.agents.evaluator._get_eval_llm", return_value=mock_llm):
        await run_eval(
            book_id="book1",
            user_message="What is ownership?",
            assistant_response="Ownership means one owner at a time.",
            retrieved_chunks=[{"content": "Rust ownership rules..."}],
            tools_called=["search_book"],
            tool_iterations=1,
            session_id="sess-xyz",
        )

    records = await list_evals("book1")
    assert len(records) == 1
    rec = records[0]
    assert rec["faithfulness_score"] == 4.0
    assert rec["helpfulness_score"] == 5.0
    assert rec["used_retrieval"] is True
    assert rec["tools_called"] == ["search_book"]
    assert rec["session_id"] == "sess-xyz"
