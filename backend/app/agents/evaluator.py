"""LLM-as-judge evaluation job.

Runs as a fire-and-forget asyncio task after the SSE stream completes.
Does NOT block the chat response.
"""

import json
import time

import structlog
from langchain_core.messages import HumanMessage, SystemMessage

from app.config import settings
from app.services.evals import create_eval

log = structlog.get_logger()

_FAITHFULNESS_PROMPT = """\
You are evaluating whether an AI assistant's response is grounded in the provided source material.

Source material retrieved from the book:
{context}

User question:
{question}

Assistant response:
{response}

Rate the faithfulness of the response on a scale of 1-5:
1 = Contradicts or completely ignores the source material
2 = Mostly not grounded — significant unsupported claims
3 = Partially grounded — some claims supported, others not
4 = Mostly grounded — minor additions or inferences beyond the source
5 = Fully grounded — every claim is supported by the source material

Reply with JSON only, no markdown: {{"score": <1-5>, "reason": "<one concise sentence>"}}"""

_HELPFULNESS_PROMPT = """\
You are evaluating whether an AI assistant's response is helpful for a student learning from a technical book.

User question:
{question}

Assistant response:
{response}

Rate the helpfulness on a scale of 1-5:
1 = Not helpful — wrong, confusing, or completely off-topic
2 = Slightly helpful — touches the topic but misses the point
3 = Moderately helpful — answers the question but lacks depth or clarity
4 = Very helpful — clear, accurate, well-explained
5 = Excellent — precise, well-structured, deepens understanding

Reply with JSON only, no markdown: {{"score": <1-5>, "reason": "<one concise sentence>"}}"""


def _get_eval_llm():
    """Return LLM configured for eval — uses eval_model if set, else primary model."""
    from app.services.llm import get_chat_model
    model = settings.eval_model or settings.llm_model
    return get_chat_model(model=model, temperature=0, max_tokens=256)


async def _score(llm, prompt: str) -> tuple[float | None, str | None]:
    """Call the judge LLM and parse the JSON score response."""
    try:
        response = await llm.ainvoke([
            SystemMessage(content="You are a precise AI evaluator. Always reply with valid JSON only."),
            HumanMessage(content=prompt),
        ])
        content = response.content
        if isinstance(content, list):
            content = "".join(p.get("text", "") if isinstance(p, dict) else str(p) for p in content)
        # Strip markdown fences if present
        content = content.strip().strip("```json").strip("```").strip()
        parsed = json.loads(content)
        score = float(parsed.get("score", 0))
        reason = str(parsed.get("reason", ""))
        if not (1.0 <= score <= 5.0):
            return None, None
        return score, reason
    except Exception as exc:
        log.warning("evaluator.score_failed", error=str(exc))
        return None, None


async def run_eval(
    book_id: str,
    user_message: str,
    assistant_response: str,
    retrieved_chunks: list[dict],
    tools_called: list[str],
    tool_iterations: int,
    session_id: str | None = None,
) -> None:
    """Fire-and-forget eval job. Call with asyncio.create_task()."""
    if not settings.eval_enabled:
        return
    if not assistant_response.strip():
        return

    t0 = time.monotonic()

    # Build context string from retrieved chunks (cap at 2000 chars to keep prompt short)
    context_parts = [c.get("content", "")[:400] for c in retrieved_chunks[:5]]
    context = "\n\n---\n\n".join(context_parts) if context_parts else "(no book content retrieved)"

    used_retrieval = "search_book" in tools_called
    used_page_text = "get_page_text" in tools_called
    used_web_search = "web_search" in tools_called

    try:
        llm = _get_eval_llm()

        faith_score, faith_reason = await _score(
            llm,
            _FAITHFULNESS_PROMPT.format(
                context=context,
                question=user_message,
                response=assistant_response[:1500],
            ),
        )

        help_score, help_reason = await _score(
            llm,
            _HELPFULNESS_PROMPT.format(
                question=user_message,
                response=assistant_response[:1500],
            ),
        )

        duration_ms = int((time.monotonic() - t0) * 1000)
        eval_model = settings.eval_model or settings.llm_model

        await create_eval(
            book_id=book_id,
            user_message=user_message,
            assistant_response=assistant_response,
            session_id=session_id,
            retrieved_context=[c.get("content", "")[:300] for c in retrieved_chunks[:5]],
            tool_iterations=tool_iterations,
            tools_called=tools_called,
            used_retrieval=used_retrieval,
            used_page_text=used_page_text,
            used_web_search=used_web_search,
            faithfulness_score=faith_score,
            faithfulness_reason=faith_reason,
            helpfulness_score=help_score,
            helpfulness_reason=help_reason,
            eval_model=eval_model,
            eval_duration_ms=duration_ms,
        )

        log.info(
            "evaluator.done",
            book_id=book_id,
            faithfulness=faith_score,
            helpfulness=help_score,
            tools=tools_called,
            iterations=tool_iterations,
            duration_ms=duration_ms,
        )

    except Exception as exc:
        log.warning("evaluator.failed", book_id=book_id, error=str(exc))
