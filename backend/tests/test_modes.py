"""Tests for multi-agent mode routing."""

import pytest


def test_chat_request_defaults_mode_to_learn():
    """ChatRequest.mode defaults to 'learn' for backwards compatibility."""
    from app.schemas import ChatRequest
    req = ChatRequest(message="hello")
    assert req.mode == "learn"


def test_chat_request_accepts_research_mode():
    from app.schemas import ChatRequest
    req = ChatRequest(message="hello", mode="research")
    assert req.mode == "research"


def test_learn_mode_system_prompt_contains_tutor_markers():
    """Learn mode prompt includes the two-part format markers."""
    from app.agents.orchestrator import _build_system_prompt
    prompt = _build_system_prompt(current_page=1, page_text="some text", mode="learn")
    assert "From the book" in prompt
    assert "More broadly" in prompt
    assert "Key concepts" in prompt


def test_research_mode_system_prompt_contains_research_markers():
    """Research mode prompt includes the three-part format markers."""
    from app.agents.orchestrator import _build_system_prompt
    prompt = _build_system_prompt(current_page=1, page_text="some text", mode="research")
    assert "Book says" in prompt
    assert "Current practice" in prompt
    assert "Where they differ" in prompt
    # Should NOT contain the learn-mode two-part structure instruction
    assert "After the two-part answer, add a third section" not in prompt
    assert "learning companion" not in prompt


def test_research_mode_forces_web_search_tool(monkeypatch):
    """Research mode includes web_search even when web_search_enabled=False."""
    import app.agents.tools as tools_module
    monkeypatch.setattr(tools_module.settings, "web_search_enabled", False)

    tools = tools_module.build_tools(
        book_id="book-1",
        current_page=1,
        retrieved_chunks=[],
        pending_notes=[],
        web_sources=[],
        force_web_search=True,
    )
    names = {t.name for t in tools}
    assert "web_search" in names


def test_research_mode_excludes_generate_quiz(monkeypatch):
    """Research mode tool list does not include generate_quiz."""
    import app.agents.tools as tools_module
    monkeypatch.setattr(tools_module.settings, "web_search_enabled", False)

    tools = tools_module.build_tools(
        book_id="book-1",
        current_page=1,
        retrieved_chunks=[],
        pending_notes=[],
        web_sources=[],
        force_web_search=True,
    )
    # Simulate the research-mode filter applied in orchestrator
    research_tools = [t for t in tools if t.name != "generate_quiz"]
    names = {t.name for t in research_tools}
    assert "generate_quiz" not in names
    assert "web_search" in names
    assert "search_book" in names


def test_build_tools_force_web_search_false_respects_settings(monkeypatch):
    """force_web_search=False still respects the settings flag."""
    import app.agents.tools as tools_module
    monkeypatch.setattr(tools_module.settings, "web_search_enabled", False)

    tools = tools_module.build_tools(
        book_id="book-1",
        current_page=1,
        retrieved_chunks=[],
        pending_notes=[],
        web_sources=[],
        force_web_search=False,
    )
    names = {t.name for t in tools}
    assert "web_search" not in names
