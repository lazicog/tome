# Spec: Phoenix Observability + LLM Evaluation Pipeline

**Date:** 2026-03-30
**Status:** Approved — implementing
**Scope:** Backend instrumentation + eval pipeline; no frontend changes

---

## Problem

The orchestrator agent is a black box. We have no visibility into:
- Which tools were called per request and how long they took
- How many tool-call iterations the agent needed
- Whether the final answer is grounded in the retrieved chunks (faithfulness)
- Whether the answer is actually helpful for the user's question (relevance)
- Whether the agent is over-calling tools or skipping retrieval it should do

Without this, tuning the system prompt, tool descriptions, and RAG parameters is guesswork.

---

## Goals

1. **Trace every chat request** end-to-end: tool calls, LLM calls, latencies, token counts
2. **Score every response automatically** for faithfulness and helpfulness using LLM-as-judge
3. **Store eval scores** in SQLite alongside sessions for trend analysis
4. **Expose eval scores** via API for debugging
5. **No Docker, no cloud** — everything runs locally as Python processes

---

## Non-Goals

- User-facing eval UI (internal/debug only)
- Real-time eval scores shown in chat (adds latency)
- RAGAS golden dataset pipeline (future work, needs curated Q&A pairs)
- Streaming eval scores over SSE

---

## Architecture

```
Chat request
    │
    ▼
orchestrator.stream_orchestrated_answer()
    │  ← wrapped by OpenInference LangChain instrumentation (auto)
    │  ← manual spans added for: tool calls, page extraction, iteration count
    │
    ▼
Phoenix collector (localhost:6006)
    │
    ├── Trace viewer: full tool-call tree, LLM call details, latencies
    └── Span attributes: book_id, current_page, tool_name, chunk_count, score

    │
    ▼ (after stream completes)
EvalJob (background asyncio task, not blocking the stream)
    │
    ├── Collect: user_message + retrieved_chunks + assistant_response
    ├── Call LLM with judge prompt → faithfulness score (1-5) + reason
    ├── Call LLM with judge prompt → helpfulness score (1-5) + reason
    ├── Compute: tool_iteration_count, used_search (bool), used_web_search (bool)
    └── INSERT INTO evals table in SQLite

GET /api/debug/evals?book_id=...&limit=20
    └── Returns recent eval scores with trend data
```

---

## Implementation Plan

### 1. Phoenix Setup

**Package:** `arize-phoenix`, `openinference-instrumentation-langchain`, `opentelemetry-sdk`, `opentelemetry-exporter-otlp-proto-grpc`

**How to run Phoenix:**
```bash
python -m phoenix.server.main
# UI at http://localhost:6006
```

**Integration in `backend/app/main.py`:**
```python
from openinference.instrumentation.langchain import LangChainInstrumentor
from opentelemetry import trace as otel_trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

def _setup_phoenix():
    """Wire OTel → Phoenix if PHOENIX_ENABLED=true."""
    if not settings.phoenix_enabled:
        return
    provider = TracerProvider()
    provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.phoenix_endpoint))
    )
    otel_trace.set_tracer_provider(provider)
    LangChainInstrumentor().instrument()
```

This auto-traces every LangChain call (LLM invocations, tool calls) without touching the orchestrator code.

**New config fields (`config.py`):**
```python
phoenix_enabled: bool = False
phoenix_endpoint: str = "http://localhost:4317"
```

**New `.env` variables:**
```
PHOENIX_ENABLED=true
PHOENIX_ENDPOINT=http://localhost:4317
```

---

### 2. SQLite Evals Table

**New migration in `database.py`:**
```sql
CREATE TABLE IF NOT EXISTS evals (
    id          TEXT PRIMARY KEY,
    session_id  TEXT,
    book_id     TEXT NOT NULL,
    created_at  TEXT NOT NULL,

    -- Input snapshot
    user_message        TEXT NOT NULL,
    assistant_response  TEXT NOT NULL,
    retrieved_context   TEXT,        -- JSON: list of chunk contents used

    -- Tool use metrics
    tool_iterations     INTEGER DEFAULT 0,
    tools_called        TEXT,        -- JSON: list of tool names called e.g. ["search_book","save_note"]
    used_retrieval      INTEGER DEFAULT 0,   -- bool: search_book was called
    used_page_text      INTEGER DEFAULT 0,   -- bool: get_page_text was called
    used_web_search     INTEGER DEFAULT 0,   -- bool: web_search was called

    -- LLM-as-judge scores (1-5, null if eval failed)
    faithfulness_score  REAL,
    faithfulness_reason TEXT,
    helpfulness_score   REAL,
    helpfulness_reason  TEXT,

    -- Aggregate
    eval_model          TEXT,        -- which model was used for judging
    eval_duration_ms    INTEGER      -- time to run the eval
)
```

---

### 3. Eval Service (`backend/app/services/evals.py`)

**Responsibilities:**
- `create_eval(...)` — INSERT row into evals table
- `list_evals(book_id, limit)` — SELECT recent evals with scores
- `eval_stats(book_id)` — AVG scores, trend over time

---

### 4. Eval Job (`backend/app/agents/evaluator.py`)

Runs as a fire-and-forget `asyncio.create_task()` after the SSE stream finishes.

**Judge prompt — Faithfulness:**
```
You are evaluating whether an AI assistant's response is grounded in the provided context.

Context retrieved from the book:
{context}

User question:
{question}

Assistant response:
{response}

Rate the faithfulness of the response on a scale of 1-5:
1 = The response contradicts or ignores the context entirely
2 = The response is mostly not grounded in the context
3 = The response is partially grounded
4 = The response is mostly grounded with minor additions
5 = The response is fully grounded in the provided context

Reply with JSON only: {{"score": <1-5>, "reason": "<one sentence>"}}
```

**Judge prompt — Helpfulness:**
```
You are evaluating whether an AI assistant's response is helpful for a student learning from a technical book.

User question:
{question}

Assistant response:
{response}

Rate the helpfulness on a scale of 1-5:
1 = Not helpful at all — wrong, confusing, or completely off-topic
2 = Slightly helpful — addresses the topic but misses the point
3 = Moderately helpful — answers the question but lacks depth or clarity
4 = Very helpful — clear, accurate, well-explained
5 = Excellent — precise, well-structured, deepens understanding

Reply with JSON only: {{"score": <1-5>, "reason": "<one sentence>"}}
```

**Tool efficiency metric** (computed, no LLM needed):
- `tool_iterations`: count of tool-call rounds before final answer
- `used_retrieval`: True if `search_book` was called (should almost always be True)
- Flag if `tool_iterations > 3` — likely agent is over-calling

---

### 5. Orchestrator Integration

Pass eval metadata out of the orchestrator to `chat.py` which fires the eval job:

```python
# orchestrator.py — return eval metadata alongside the stream
class OrchestrationMetadata(TypedDict):
    retrieved_chunks: list[dict]
    pending_notes: list[dict]
    tool_calls_made: list[str]
    tool_iterations: int

# chat.py — after stream completes
asyncio.create_task(
    run_eval(
        book_id=book_id,
        session_id=session_id,
        user_message=message,
        assistant_response=collected_text,
        metadata=metadata,
    )
)
```

The stream itself is not slowed down — eval runs independently after `done` is emitted.

---

### 6. Eval API (`backend/app/api/routes/debug.py` extension)

**New endpoints:**

`GET /api/debug/evals?book_id=<id>&limit=20`

Response:
```json
{
  "evals": [
    {
      "id": "...",
      "created_at": "...",
      "user_message": "Explain ownership in Rust",
      "faithfulness_score": 4.0,
      "helpfulness_score": 4.5,
      "tool_iterations": 2,
      "tools_called": ["search_book", "get_page_text"],
      "used_retrieval": true
    }
  ],
  "stats": {
    "avg_faithfulness": 3.8,
    "avg_helpfulness": 4.1,
    "avg_tool_iterations": 1.7,
    "retrieval_rate": 0.94,
    "total": 47
  }
}
```

`GET /api/debug/evals/{eval_id}` — full detail including judge reasons and context snapshot

---

## File Plan

| File | Change |
|---|---|
| `backend/app/config.py` | Add `phoenix_enabled`, `phoenix_endpoint` |
| `backend/app/main.py` | Add `_setup_phoenix()` in lifespan |
| `backend/app/services/database.py` | Add `evals` table migration |
| `backend/app/services/evals.py` | NEW — eval CRUD service |
| `backend/app/agents/evaluator.py` | NEW — LLM-as-judge eval job |
| `backend/app/agents/orchestrator.py` | Return eval metadata after stream |
| `backend/app/api/routes/chat.py` | Fire eval background task after stream |
| `backend/app/api/routes/debug.py` | Add `/api/debug/evals` endpoints |
| `backend/tests/test_evals.py` | NEW — eval service + evaluator unit tests |
| `backend/requirements.txt` | Add phoenix + openinference packages |
| `.env.example` | Add `PHOENIX_ENABLED`, `PHOENIX_ENDPOINT` |

---

## Packages to Add

```
arize-phoenix>=8.0.0
openinference-instrumentation-langchain>=0.1.0
opentelemetry-sdk>=1.20.0
opentelemetry-exporter-otlp-proto-grpc>=1.20.0
```

---

## Running Phoenix Locally

```bash
# Install (already in requirements after this change)
pip install arize-phoenix

# Start Phoenix server (separate terminal)
python -m phoenix.server.main

# UI available at
http://localhost:6006
```

Set `PHOENIX_ENABLED=true` in `.env` to start sending traces.

---

## Verification Steps

1. Start Phoenix: `python -m phoenix.server.main`
2. Set `PHOENIX_ENABLED=true` in `.env`, restart backend
3. Send a chat message → Phoenix UI shows trace with tool spans
4. Check `GET /api/debug/evals` → returns eval row with scores
5. Check scores: faithfulness ≥ 3 means retrieval is working
6. Artificially ask a question that bypasses retrieval → faithfulness should drop to 1-2
7. `pytest tests/test_evals.py` → all pass

---

## Success Metrics

- Every chat request produces a Phoenix trace with at least one span
- Eval scores appear within 5 seconds of response completion
- Faithfulness score ≥ 3.5 average across 20 real questions means RAG is grounded
- Tool iteration count ≤ 2 average means orchestrator is efficient
- All new tests pass, existing 58 tests unaffected
