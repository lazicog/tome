"""LangChain tools for the orchestrator agent.

Each tool is created via build_tools() which binds book_id, current_page,
and shared mutable state lists via closure.
"""

import structlog
from langchain_core.tools import tool

from app.agents.tutor import build_context

log = structlog.get_logger()


def _add_unique_chunks(retrieved_chunks: list, new_chunks: list) -> None:
    """Append chunks from new_chunks that aren't already in retrieved_chunks."""
    existing_ids = {c["id"] for c in retrieved_chunks}
    for c in new_chunks:
        if c["id"] not in existing_ids:
            retrieved_chunks.append(c)
            existing_ids.add(c["id"])
from app.config import settings
from app.rag.retriever import search_chunks_positioned
from app.services.llm import get_chat_model_with_fallback

QUIZ_PROMPT = """You are Tome Quiz Master.
Generate 3-5 questions based solely on the retrieved context to test the user's understanding.

Requirements:
- Mix question types: at least one multiple-choice, one true/false, one short-answer
- Each question must be directly grounded in the context
- For multiple-choice, provide 4 options labeled A-D with exactly one correct answer
- After all questions, include an answer key with brief explanations
- Format as a numbered list for readability
- Keep questions focused on the user's topic

Context:
{context}
"""

THINKING_LABELS: dict[str, str] = {
    "search_book": "Searching book…",
    "get_page_text": "Reading page…",
    "save_note": "Saving note…",
    "update_note": "Updating note…",
    "list_notes": "Checking notes…",
    "generate_quiz": "Building quiz…",
    "web_search": "Searching web…",
}


def thinking_label(tool_name: str) -> str:
    return THINKING_LABELS.get(tool_name, f"Using {tool_name}…")


def build_tools(
    book_id: str,
    current_page: int | None,
    retrieved_chunks: list,
    pending_notes: list,
    web_sources: list,
    *,
    force_web_search: bool = False,
) -> list:
    """Return a list of LangChain tools bound to this request's context."""

    @tool
    async def search_book(query: str, whole_book: bool = False) -> str:
        """Search the book semantically for content related to the query.
        Set whole_book=True to search the entire book regardless of current page."""
        page = None if whole_book else current_page
        chunks, _ = search_chunks_positioned(
            book_id=book_id,
            query=query,
            k=settings.top_k_chunks,
            current_page=page,
        )
        _add_unique_chunks(retrieved_chunks, chunks)

        if not chunks:
            return "No relevant content found for that query."

        parts = []
        for c in chunks[:6]:
            meta = c["metadata"]
            page_nums = meta.get("page_numbers", [])
            loc = f"p.{page_nums[0]}" if page_nums else "unknown page"
            chapter = meta.get("chapter", "")
            header = f"[{loc} — {chapter}]" if chapter else f"[{loc}]"
            parts.append(f"{header}\n{c['content'][:700]}")
        return "\n\n---\n\n".join(parts)

    @tool
    async def get_page_text(page_number: int) -> str:
        """Get the verbatim text of a specific page from the PDF.
        Use this to verify exact wording, code samples, or figures on a page."""
        from app.rag.page_extractor import get_page_text as _extract
        text = await _extract(book_id, page_number)
        if not text:
            return f"No extractable text found on page {page_number}."
        return f"[Page {page_number} verbatim text]:\n{text}"

    @tool
    async def save_note(title: str, content: str, tags: str = "") -> str:
        """Save a structured note to the user's notes panel.
        Use this when the user asks to save/remember something, or after a substantive explanation."""
        from app.services.notes import create_note as _create
        note = await _create(
            book_id=book_id,
            content=content,
            title=title,
            page_number=current_page,
            note_type="agent_insight",
            tags=tags,
        )
        pending_notes.append({"title": title, "id": note.get("id", "")})
        return f"Note saved: {title}"

    @tool
    async def list_notes(query: str = "", page_number: int | None = None) -> str:
        """List existing notes for this book. Call this before saving a new note to check if
        a relevant note already exists — prefer updating over creating a duplicate.
        Optionally filter by a search query or page number.
        Returns up to 10 notes with their IDs, titles, and a content preview."""
        from app.services.notes import list_notes as _list
        notes = await _list(book_id, page_number=page_number, search=query or None)
        if not notes:
            return "No notes found."
        lines = [
            f"[ID: {n['id']}] {n['title'] or '(untitled)'} — {n['content'][:200]}"
            for n in notes[:10]
        ]
        return "\n".join(lines)

    @tool
    async def update_note(note_id: str, title: str | None = None, content: str | None = None, tags: str | None = None) -> str:
        """Update an existing note by ID (obtained from list_notes).
        Choose the update strategy based on context:
        - Append new findings to a running summary
        - Rewrite if the existing content is incomplete or outdated
        - Add a clearly labelled new section if the topic is adjacent but distinct
        At least one of title, content, or tags must be provided."""
        from app.services.notes import update_note as _update
        updated = await _update(note_id, title=title, content=content, tags=tags)
        if not updated:
            return f"Note {note_id} not found."
        pending_notes.append({"title": updated["title"], "id": note_id, "action": "updated"})
        return f"Note updated: {updated['title']}"

    @tool
    async def generate_quiz(topic: str) -> str:
        """Generate quiz questions on a topic using content from the book.
        Returns formatted questions with answer key."""
        chunks, _ = search_chunks_positioned(
            book_id=book_id,
            query=topic,
            k=6,
            current_page=current_page,
        )
        if not chunks:
            return "Not enough book content found to generate a quiz on that topic."

        _add_unique_chunks(retrieved_chunks, chunks)

        context = build_context(chunks)
        llm = get_chat_model_with_fallback()
        from langchain_core.messages import HumanMessage, SystemMessage
        response = await llm.ainvoke([
            SystemMessage(content=QUIZ_PROMPT.format(context=context)),
            HumanMessage(content=f"Generate a quiz on: {topic}"),
        ])
        content = response.content
        if isinstance(content, list):
            content = "".join(
                p.get("text", "") if isinstance(p, dict) else str(p)
                for p in content
            )
        return str(content)

    tools: list = [search_book, get_page_text, save_note, list_notes, update_note, generate_quiz]

    if settings.web_search_enabled or force_web_search:
        @tool
        async def web_search(query: str) -> str:
            """Search the web for latest documentation, API references, or current information.
            Use when: user asks about a specific library/API, book content may be outdated,
            or user says 'look up', 'find docs', 'latest version'."""
            results = await _do_web_search(query)
            web_sources.extend(results)
            if not results:
                return "No web results found."
            return "\n\n".join(
                f"[Source: {r['url']}]\n{r['snippet']}" for r in results[:3]
            )

        tools.append(web_search)

    return tools


async def _do_web_search(query: str) -> list[dict]:
    """Try Tavily first, fall back to DuckDuckGo."""
    if settings.tavily_api_key:
        try:
            from tavily import AsyncTavilyClient
            client = AsyncTavilyClient(api_key=settings.tavily_api_key)
            resp = await client.search(query, max_results=3)
            return [
                {"url": r.get("url", ""), "snippet": r.get("content", r.get("snippet", ""))}
                for r in resp.get("results", [])
            ]
        except Exception as exc:
            log.warning("web_search.tavily_failed", error=str(exc))

    # Fallback: DuckDuckGo (sync wrapper run in thread)
    try:
        import asyncio
        from langchain_community.tools import DuckDuckGoSearchRun
        ddg = DuckDuckGoSearchRun()
        raw = await asyncio.to_thread(ddg.run, query)
        return [{"url": "", "snippet": raw[:1200]}]
    except Exception as exc:
        log.warning("web_search.duckduckgo_failed", error=str(exc))
        return []
