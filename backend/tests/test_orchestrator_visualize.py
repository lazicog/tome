"""Tests for Visualize mode system prompt dispatch and tool filtering."""

import pytest

from app.agents.orchestrator import (
    RESEARCH_SYSTEM_PROMPT,
    SYSTEM_PROMPT,
    VISUALIZE_SYSTEM_PROMPT,
    _build_system_prompt,
)


def test_visualize_system_prompt_used():
    prompt = _build_system_prompt(current_page=5, page_text="some text", mode="visualize")
    assert "mermaid" in prompt.lower()
    assert "diagram" in prompt.lower()
    assert "Key concepts to nail down" not in prompt


def test_visualize_prompt_excludes_quiz_tool_mention():
    prompt = _build_system_prompt(current_page=5, page_text="some text", mode="visualize")
    # generate_quiz should not be listed as an available tool
    assert "generate_quiz" not in prompt
    # web_search should not appear as an available tool (it appears only in rules: "Do not use web_search")
    assert "**web_search**" not in prompt


@pytest.mark.asyncio
async def test_visualize_tool_filter():
    """stream_orchestrated_answer should bind only search_book and get_page_text in visualize mode."""
    from unittest.mock import AsyncMock, MagicMock, patch

    import app.agents.orchestrator as orch

    captured_tools = []

    async def empty_astream(*args, **kwargs):
        return
        yield  # make it an async generator

    fake_llm_with_tools = MagicMock()
    fake_llm_with_tools.astream = empty_astream

    fake_llm = MagicMock()
    fake_llm.bind_tools = MagicMock(
        side_effect=lambda tools: captured_tools.extend([t.name for t in tools]) or fake_llm_with_tools
    )

    with patch.object(orch, "_resolve_model", return_value=fake_llm), \
         patch.object(orch, "get_page_text", AsyncMock(return_value="")):

        async for _ in orch.stream_orchestrated_answer(
            book_id="test-book",
            message="visualize this",
            history=[],
            current_page=1,
            mode="visualize",
        ):
            pass

    assert set(captured_tools) == {"search_book", "get_page_text"}


def test_learn_not_regressed():
    prompt = _build_system_prompt(current_page=1, page_text="text", mode="learn")
    assert "learning companion" in prompt.lower() or "Key concepts to nail down" in prompt


def test_research_not_regressed():
    prompt = _build_system_prompt(current_page=1, page_text="text", mode="research")
    assert "Book says" in prompt or "current practice" in prompt.lower()
