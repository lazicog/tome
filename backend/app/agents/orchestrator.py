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
- **list_notes**: List existing notes for this book (with optional search/page filter). Always call this before saving a new note.
- **save_note**: Persist a new structured note. Only use this if list_notes confirms no relevant note exists.
- **update_note**: Update an existing note by ID. Prefer this over creating a duplicate.
- **generate_quiz**: Create quiz questions from book content on a topic.
{web_search_line}

Note management rules:
- Before saving a new note, call list_notes to check for an existing note on the same topic.
- If a relevant note exists, call update_note instead of save_note — choose the best strategy:
  - Append new findings to a running summary
  - Rewrite if the content is incomplete or outdated
  - Add a clearly labelled new section if the topic is adjacent but distinct
- Only call save_note when no existing note covers this topic.

Note format — use exactly this structure with blank lines between every section:

## {{Title}}

**p.{{page}}** · {{#tag1 #tag2}}

{{One crisp sentence summarising the core idea.}}

**Key points**
- **{{Term}}**: {{explanation}}
- **{{Term}}**: {{explanation}}
- **{{Term}}**: {{explanation}}

**Example**
{{Concrete example, analogy, or code snippet.}}

**Connects to**
{{Related concept or chapter from the book.}}

Important: each section must be separated by a blank line. Never run sections together in one paragraph.

Response style:
- Be direct and conversational. Don't open with filler like "Of course!", "Great question!", or "Certainly!".
- After saving or updating a note, give a one-sentence confirmation then move on naturally — don't list what you could add next unless the user asked.
- When explaining, lead with the point, then support it. Keep answers tight.
- Offer to save a note after a substantive explanation, but only once.

Rules:
- Always call search_book before answering unless the current page text already answers the question.
- When user says "note this", "remember this", or "save this" → check list_notes first, then save or update.{web_rules}
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
        event_name = "note_updated" if note.get("action") == "updated" else "note_saved"
        yield _sse_event(event_name, {"title": note.get("title", ""), "id": note.get("id", "")})

    if web_sources_list:
        yield _sse_event("web_sources", web_sources_list)

    yield _sse_event("done", "")

    # Yield eval metadata last (not an SSE string — consumed by chat.py only)
    yield EvalMetadata(
        retrieved_chunks=list(retrieved_chunks),
        tools_called=tools_called,
        tool_iterations=tool_iterations,
    )
