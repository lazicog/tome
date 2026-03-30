"""Eval score persistence — stores LLM-as-judge results in SQLite."""

import json
import uuid
from datetime import datetime, timezone

from app.services.database import get_connection, init_db


async def create_eval(
    book_id: str,
    user_message: str,
    assistant_response: str,
    *,
    session_id: str | None = None,
    retrieved_context: list[str] | None = None,
    tool_iterations: int = 0,
    tools_called: list[str] | None = None,
    used_retrieval: bool = False,
    used_page_text: bool = False,
    used_web_search: bool = False,
    faithfulness_score: float | None = None,
    faithfulness_reason: str | None = None,
    helpfulness_score: float | None = None,
    helpfulness_reason: str | None = None,
    eval_model: str | None = None,
    eval_duration_ms: int | None = None,
) -> dict:
    await init_db()
    eval_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc).isoformat()

    async with get_connection() as conn:
        await conn.execute(
            """INSERT INTO evals (
                id, session_id, book_id, created_at,
                user_message, assistant_response, retrieved_context,
                tool_iterations, tools_called,
                used_retrieval, used_page_text, used_web_search,
                faithfulness_score, faithfulness_reason,
                helpfulness_score, helpfulness_reason,
                eval_model, eval_duration_ms
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                eval_id, session_id, book_id, now,
                user_message, assistant_response,
                json.dumps(retrieved_context or []),
                tool_iterations,
                json.dumps(tools_called or []),
                int(used_retrieval), int(used_page_text), int(used_web_search),
                faithfulness_score, faithfulness_reason,
                helpfulness_score, helpfulness_reason,
                eval_model, eval_duration_ms,
            ),
        )
        await conn.commit()
        cursor = await conn.execute("SELECT * FROM evals WHERE id = ?", (eval_id,))
        row = await cursor.fetchone()
    return _row_to_dict(row)


async def list_evals(book_id: str, *, limit: int = 20) -> list[dict]:
    await init_db()
    async with get_connection() as conn:
        cursor = await conn.execute(
            "SELECT * FROM evals WHERE book_id = ? ORDER BY created_at DESC LIMIT ?",
            (book_id, limit),
        )
        rows = await cursor.fetchall()
    return [_row_to_dict(r) for r in rows]


async def get_eval(eval_id: str) -> dict | None:
    await init_db()
    async with get_connection() as conn:
        cursor = await conn.execute("SELECT * FROM evals WHERE id = ?", (eval_id,))
        row = await cursor.fetchone()
    return _row_to_dict(row) if row else None


async def eval_stats(book_id: str) -> dict:
    await init_db()
    async with get_connection() as conn:
        cursor = await conn.execute(
            """SELECT
                COUNT(*) as total,
                AVG(faithfulness_score) as avg_faithfulness,
                AVG(helpfulness_score) as avg_helpfulness,
                AVG(tool_iterations) as avg_tool_iterations,
                AVG(used_retrieval) as retrieval_rate
            FROM evals WHERE book_id = ?""",
            (book_id,),
        )
        row = await cursor.fetchone()
    if not row:
        return {"total": 0}
    return {
        "total": row["total"],
        "avg_faithfulness": round(row["avg_faithfulness"], 2) if row["avg_faithfulness"] else None,
        "avg_helpfulness": round(row["avg_helpfulness"], 2) if row["avg_helpfulness"] else None,
        "avg_tool_iterations": round(row["avg_tool_iterations"], 2) if row["avg_tool_iterations"] else None,
        "retrieval_rate": round(row["retrieval_rate"], 2) if row["retrieval_rate"] else None,
    }


def _row_to_dict(row) -> dict:
    d = dict(row)
    for key in ("tools_called", "retrieved_context"):
        if isinstance(d.get(key), str):
            try:
                d[key] = json.loads(d[key])
            except (json.JSONDecodeError, TypeError):
                d[key] = []
    for key in ("used_retrieval", "used_page_text", "used_web_search"):
        if key in d:
            d[key] = bool(d[key])
    return d
