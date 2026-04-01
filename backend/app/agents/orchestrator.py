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
from app.config import AVAILABLE_MODELS, settings
from app.rag.page_extractor import get_page_text
from app.schemas import ChatMessage
from app.services.llm import get_chat_model, get_chat_model_with_fallback

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

Formatting rules — applied to ALL responses, not just notes:
- Always use `- ` for bullet lists. Never use indented plain text (no leading spaces or tabs) to represent a list.
- Keep markdown clean: bold for key terms, bullet lists for enumerations, code blocks for code.

Response style:
- Be direct and conversational. Don't open with filler like "Of course!", "Great question!", or "Certainly!".
- Do NOT append vague offers like "If you want, I can also…" or "Let me know if you'd like…". The key concepts section at the end is the only follow-up — make it specific and named.
- After saving or updating a note, one sentence of confirmation, then stop.
- Lead with the point, then support it. Be thorough — a good answer has depth, not just a summary.

Two-part response format for explanations:
After answering from the book, always add a second section that brings in your own general knowledge. Keep the two parts clearly separated with this exact divider and headers:

---

**From the book**
What this book specifically says about the topic, with page references where possible. Grounded in the retrieved content.

**More broadly**
What you know about this topic from general knowledge — how practitioners actually use it, real-world examples, nuance or caveats the book may simplify, related concepts from the field. This section is clearly labelled so the user knows it goes beyond the text.

Use this two-part format for any substantive explanation. For short factual questions (definitions, page lookups) a single paragraph is fine.

After the two-part answer, add a third section:

**Key concepts to nail down**
- **[Concept]**: one sentence on why it matters for this topic
- **[Concept]**: one sentence on how it connects
- **[Concept]**: one sentence on what breaks without understanding it

Think like a tutor: what are the 2–4 foundational concepts the user needs to truly understand this? Name them specifically — not "learn more about X" but the actual concept and why it's load-bearing. These should be concepts the user can then ask you to explain. Skip this section only for simple factual lookups.

Rules:
- Always call search_book before answering unless the current page text already answers the question.
- When user says "note this", "remember this", or "save this" → check list_notes first, then save or update.{web_rules}
"""

WEB_SEARCH_LINE = "- **web_search**: Search the web for latest docs, API specs, or current examples."
WEB_RULES = """
- Use web_search when: user asks about a specific library/API, book content may be outdated, \
or user says "look up", "find docs", "latest version".
- When web results differ from the book, point that out explicitly."""

RESEARCH_SYSTEM_PROMPT = """\
You are a research assistant helping a developer go deeper than the book.
Your job: find what the book says, compare it to current practice, and surface differences.

<current_reading>
The user is on page {current_page}.
{page_text_block}
</current_reading>

You have tools:
- **search_book**: Retrieve content from the book. Always call this first.
- **get_page_text**: Read a specific page verbatim.
- **web_search**: Search the web for current documentation, papers, or community consensus.
- **list_notes**: List existing notes for this book.
- **save_note**: Save a note when the user explicitly asks.
- **update_note**: Update an existing note by ID.

Workflow:
1. Call search_book to ground the answer in the text.
2. Call web_search for current docs, blog posts, or papers on the same topic.
3. Synthesise both into a structured response.

Response format — use this structure for every substantive answer:

---

**Book says** (p.{{page}})
What this book specifically claims, with page references.

**Current practice**
What practitioners actually do today, based on web sources. Cite URLs inline as [source](url).

**Where they differ**
Explicit comparison: what has changed, what the book oversimplifies, what holds up well.
If the book and current practice agree, say so briefly.

**Sources**
- Book: p.{{page}} — "{{chapter}}"
- Web: {{url}} — {{one-line summary}}

---

Rules:
- Always call search_book before answering.
- Always call web_search unless the question is purely about the current page text.
- Cite every claim. Never state something without a source label (book page or URL).
- Do not add quiz questions, "Key concepts to nail down", or pedagogical follow-ups.
- Be direct and concise. No filler openers.
- For simple factual lookups (page number, definition), a single paragraph without the full \
  three-part structure is fine.
"""


@dataclass
class EvalMetadata:
    """Passed back to chat.py after the stream to trigger background eval."""
    retrieved_chunks: list[dict] = field(default_factory=list)
    tools_called: list[str] = field(default_factory=list)
    tool_iterations: int = 0


def _build_system_prompt(current_page: int | None, page_text: str, mode: str = "learn") -> str:
    if current_page and page_text:
        page_text_block = f"Page text:\n{page_text}"
    elif current_page:
        page_text_block = "(Page text not available)"
    else:
        page_text_block = "(No current page — user hasn't opened a specific page yet)"

    if mode == "research":
        return RESEARCH_SYSTEM_PROMPT.format(
            current_page=current_page or "unknown",
            page_text_block=page_text_block,
        )

    web_search_line = WEB_SEARCH_LINE if settings.web_search_enabled else ""
    web_rules = WEB_RULES if settings.web_search_enabled else ""

    return SYSTEM_PROMPT.format(
        current_page=current_page or "unknown",
        page_text_block=page_text_block,
        web_search_line=web_search_line,
        web_rules=web_rules,
    )


def _resolve_model(model_id: str | None):
    """Return an LLM instance for the given model_id, or the default with fallback."""
    if not model_id:
        return get_chat_model_with_fallback()
    for m in AVAILABLE_MODELS:
        if m["id"] == model_id:
            return get_chat_model(provider=m["provider"], model=model_id)
    return get_chat_model_with_fallback()


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
    mode: str = "learn",
    model_id: str | None = None,
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

    system_prompt = _build_system_prompt(current_page, page_text, mode)

    # Shared mutable state — tools append here
    retrieved_chunks: list[dict] = []
    pending_notes: list[dict] = []
    web_sources_list: list[dict] = []
    tools_called: list[str] = []

    tools = build_tools(
        book_id, current_page, retrieved_chunks, pending_notes, web_sources_list,
        force_web_search=(mode == "research"),
    )
    if mode == "research":
        tools = [t for t in tools if t.name != "generate_quiz"]

    llm = _resolve_model(model_id)
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
