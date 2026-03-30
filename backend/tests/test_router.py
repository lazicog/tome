"""Tests for the orchestrator tools module."""


def test_thinking_labels_defined() -> None:
    from app.agents.tools import THINKING_LABELS
    assert "search_book" in THINKING_LABELS
    assert "get_page_text" in THINKING_LABELS
    assert "save_note" in THINKING_LABELS
    assert "generate_quiz" in THINKING_LABELS
    assert "web_search" in THINKING_LABELS


def test_thinking_label_known() -> None:
    from app.agents.tools import thinking_label
    assert thinking_label("search_book") == "Searching book…"
    assert thinking_label("get_page_text") == "Reading page…"
    assert thinking_label("save_note") == "Saving note…"
    assert thinking_label("generate_quiz") == "Building quiz…"
    assert thinking_label("web_search") == "Searching web…"


def test_thinking_label_unknown() -> None:
    from app.agents.tools import thinking_label
    result = thinking_label("mystery_tool")
    assert "mystery_tool" in result


def test_build_tools_returns_base_four(monkeypatch) -> None:
    """build_tools returns 4 tools when web_search is disabled."""
    import app.agents.tools as tools_module
    monkeypatch.setattr(tools_module.settings, "web_search_enabled", False)

    tools = tools_module.build_tools(
        book_id="book-1",
        current_page=3,
        retrieved_chunks=[],
        pending_notes=[],
        web_sources=[],
    )
    names = {t.name for t in tools}
    assert names == {"search_book", "get_page_text", "save_note", "generate_quiz"}


def test_build_tools_adds_web_search_when_enabled(monkeypatch) -> None:
    import app.agents.tools as tools_module
    monkeypatch.setattr(tools_module.settings, "web_search_enabled", True)

    tools = tools_module.build_tools(
        book_id="book-1",
        current_page=None,
        retrieved_chunks=[],
        pending_notes=[],
        web_sources=[],
    )
    names = {t.name for t in tools}
    assert "web_search" in names
    assert len(names) == 5
