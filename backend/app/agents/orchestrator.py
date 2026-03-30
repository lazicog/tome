"""Single orchestrator agent that replaces the multi-agent routing graph.

Streams SSE events: thinking → token → sources → note_saved → web_sources → done

Also yields an EvalMetadata dict as the final item (not an SSE string) so that
chat.py can fire the background eval task without re-parsing the stream.
"""

import operator
from dataclasses import dataclass, field
from functools import reduce
from typing import AsyncGenerator

import structlog
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from app.agents.tools import build_tools, thinking_label
from app.agents.tutor import _format_sources, _history_to_messages, _sse_event
from app.config import settings
from app.rag.page_extractor import get_page_text
from app.schemas import ChatMessage
from app.services.llm import get_chat_model_with_fallback

log = structlog.get_logger()

MAX_TOOL_ITERATIONS = 6

SYSTEM_PROMPT = """\
You are an expert learning companion for technical books. \
Help the user understand the material deeply — explain concepts clearly, \
give concrete examples, quiz them when asked, and save notes when requested.

<current_reading>
The user is on page {current_page}.
{page_text_block}
</current_reading>

You have tools:
- **search_book**: Search semantically across the book. Use this first for most questions.
- **get_page_text**: Retrieve any specific page verbatim. Use to verify exact wording or code.
- **save_note**: Persist a structured note. Use when the user says "save", "note this", "remember this".
- **generate_quiz**: Create quiz questions from book content on a topic.
{web_search_line}

When creating notes, use this structure:
## {{Title}} — p.{{page}}
**Summary**: one sentence.
**Key Points**: 3-5 bullets with bold terms.
**Example**: concrete example or code snippet.
**Connects to**: related concept if relevant.
Tags: #tag1 #tag2

Rules:
- Always call search_book before answering unless the current page text already answers the question.
- Proactively offer to save a note after a substantive explanation.
- When user says "note this", "remember this", or "save this" → call save_note immediately.
- Be concise and precise. Teach, don't lecture.{web_rules}
"""

WEB_SEARCH_LINE = "- **web_search**: Search the web for latest docs, API specs, or current examples."
WEB_RULES = """
- Use web_search when: user asks about a specific library/API, book content may be outdated, \
or user says "look up", "find docs", "latest version".
- When web results differ from the book, point that out explicitly."""


@dataclass
class EvalMetadata:
    """Passed back to chat.py after the stream to trigger background eval."""
    retrieved_chunks: list[dict] = field(default_factory=list)
    tools_called: list[str] = field(default_factory=list)
    tool_iterations: int = 0


def _build_system_prompt(current_page: int | None, page_text: str) -> str:
    if current_page and page_text:
        page_text_block = f"Page text:\n{page_text}"
    elif current_page:
        page_text_block = "(Page text not available)"
    else:
        page_text_block = "(No current page — user hasn't opened a specific page yet)"

    web_search_line = WEB_SEARCH_LINE if settings.web_search_enabled else ""
    web_rules = WEB_RULES if settings.web_search_enabled else ""

    return SYSTEM_PROMPT.format(
        current_page=current_page or "unknown",
        page_text_block=page_text_block,
        web_search_line=web_search_line,
        web_rules=web_rules,
    )


def _extract_text(content) -> str:
    """Extract text from LLM response content (str or list of blocks)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            p.get("text", "") if isinstance(p, dict) else str(p) for p in content
        )
    return str(content) if content else ""


async def stream_orchestrated_answer(
    book_id: str,
    message: str,
    history: list[ChatMessage],
    current_page: int | None = None,
) -> AsyncGenerator[str | EvalMetadata, None]:
    """
    Yields SSE strings (str) followed by a single EvalMetadata object.
    Consumers must handle both types: SSE strings are forwarded to clients,
    EvalMetadata is used to trigger the background eval task.
    """
    # Fetch current page text upfront
    page_text = ""
    if current_page:
        page_text = await get_page_text(book_id, current_page)

    system_prompt = _build_system_prompt(current_page, page_text)

    # Shared mutable state — tools append here
    retrieved_chunks: list[dict] = []
    pending_notes: list[dict] = []
    web_sources_list: list[dict] = []
    tools_called: list[str] = []

    tools = build_tools(book_id, current_page, retrieved_chunks, pending_notes, web_sources_list)

    llm = get_chat_model_with_fallback()
    llm_with_tools = llm.bind_tools(tools)
    tool_map = {t.name: t for t in tools}

    messages: list = [
        SystemMessage(content=system_prompt),
        *_history_to_messages(history),
        HumanMessage(content=message),
    ]

    tool_iterations = 0

    # Agentic streaming loop
    for iteration in range(MAX_TOOL_ITERATIONS):
        chunk_buffer = []

        async for chunk in llm_with_tools.astream(messages):
            chunk_buffer.append(chunk)
            text = _extract_text(chunk.content)
            if text:
                yield _sse_event("token", text)

        if not chunk_buffer:
            break

        full_response: AIMessage = reduce(operator.add, chunk_buffer)
        messages.append(full_response)

        if not full_response.tool_calls:
            break

        tool_iterations += 1

        for tc in full_response.tool_calls:
            tool_name = tc["name"]
            tools_called.append(tool_name)
            yield _sse_event("thinking", thinking_label(tool_name))

            tool_fn = tool_map.get(tool_name)
            if tool_fn is None:
                tool_result = f"Unknown tool: {tool_name}"
            else:
                try:
                    tool_result = await tool_fn.ainvoke(tc["args"])
                except Exception as exc:
                    log.warning("tool.error", tool=tool_name, error=str(exc))
                    tool_result = f"Tool error: {exc}"

            messages.append(
                ToolMessage(content=str(tool_result), tool_call_id=tc["id"])
            )

    # ── Post-stream SSE events ──
    if retrieved_chunks:
        yield _sse_event("sources", _format_sources(retrieved_chunks, current_page))

    for note in pending_notes:
        yield _sse_event("note_saved", {"title": note.get("title", "")})

    if web_sources_list:
        yield _sse_event("web_sources", web_sources_list)

    yield _sse_event("done", "")

    # Yield eval metadata last (not an SSE string — consumed by chat.py only)
    yield EvalMetadata(
        retrieved_chunks=list(retrieved_chunks),
        tools_called=tools_called,
        tool_iterations=tool_iterations,
    )
