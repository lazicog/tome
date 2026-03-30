# Tome

AI-powered learning companion for technical books (PDFs). Upload a PDF, chat with an intelligent agent that explains concepts, quizzes you, saves notes, and searches the web for up-to-date information.

## Features

- Upload any technical PDF and start chatting immediately
- Orchestrator agent with tool-calling — searches the book semantically, reads specific pages verbatim, saves structured notes, generates quizzes, and optionally searches the web
- Hybrid RAG retrieval: ChromaDB vector search + BM25 keyword scoring + cross-encoder reranking
- Streaming responses over SSE with live "thinking" indicators while tools execute
- Notes panel — create, edit, search, and highlight notes; agent can save notes automatically
- Session persistence — conversation history stored in SQLite across page reloads
- LLM-as-judge evaluation — every response is scored for faithfulness and helpfulness in the background
- Observability via Arize Phoenix — full LangChain traces with token counts and cost tracking

## Tech Stack

- **Backend**: FastAPI, LangChain, ChromaDB, sentence-transformers, pdfplumber, aiosqlite
- **Frontend**: Next.js 15 (App Router), TypeScript, Tailwind CSS v4, react-pdf
- **Observability**: Arize Phoenix (local), OpenTelemetry, openinference-instrumentation-langchain

## Quick Start (Manual)

### 1. Environment

```bash
cp .env.example .env
```

Edit `.env` and set at minimum:

```env
OPENAI_API_KEY=sk-...        # or ANTHROPIC_API_KEY
USE_SQLITE_STORAGE=true
```

### 2. Backend

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload
```

Backend runs at `http://localhost:8000`. API docs at `http://localhost:8000/docs`.

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:3000`.

### 4. Docker (alternative)

```bash
docker compose up --build
```

## Observability (optional)

Tome integrates with [Arize Phoenix](https://github.com/Arize-ai/phoenix) for local LLM tracing.

**Start Phoenix:**

```bash
pip install arize-phoenix
phoenix serve
```

Phoenix UI: `http://localhost:6006`

**Enable tracing** — add to `.env`:

```env
PHOENIX_ENABLED=true
PHOENIX_ENDPOINT=http://localhost:4317
```

Restart the backend. Every chat request will appear as a trace in Phoenix with token counts, latency, tool calls, and cost breakdown.

## Evaluation

Every chat response is automatically scored by an LLM judge (fire-and-forget, non-blocking):

- **Faithfulness** (1–5): Is the answer grounded in the retrieved book content?
- **Helpfulness** (1–5): Is the answer useful for a student learning from the book?

Results are stored in SQLite and accessible via:

```
GET /api/debug/evals?book_id=<id>        # list recent evals + aggregate stats
GET /api/debug/evals/<eval_id>           # single eval record
```

**Configure** in `.env`:

```env
EVAL_ENABLED=true           # default: true
EVAL_MODEL=gpt-4o-mini      # defaults to LLM_MODEL if not set
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `openai` | `openai`, `anthropic`, or `ollama` |
| `LLM_MODEL` | `gpt-4o-mini` | Model name for the provider |
| `LLM_FALLBACK_PROVIDER` | `ollama` | Provider to fall back to if primary fails |
| `LLM_FALLBACK_MODEL` | `llama3` | Model for the fallback provider |
| `OPENAI_API_KEY` | — | Required if using OpenAI |
| `ANTHROPIC_API_KEY` | — | Required if using Anthropic |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama endpoint |
| `USE_SQLITE_STORAGE` | `false` | Enable persistent sessions, notes, and evals |
| `WEB_SEARCH_ENABLED` | `false` | Enable web search tool (requires Tavily or DuckDuckGo) |
| `TAVILY_API_KEY` | — | Optional — falls back to DuckDuckGo if absent |
| `PHOENIX_ENABLED` | `false` | Enable OpenTelemetry tracing to Phoenix |
| `PHOENIX_ENDPOINT` | `http://localhost:4317` | Phoenix gRPC endpoint |
| `EVAL_ENABLED` | `true` | Enable LLM-as-judge scoring |
| `EVAL_MODEL` | — | Model for eval judge (defaults to `LLM_MODEL`) |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000/api` | Frontend → backend URL |

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/health` | Health check |
| `GET` | `/api/books` | List uploaded books |
| `POST` | `/api/books` | Upload a PDF |
| `GET` | `/api/books/{id}` | Get book status |
| `POST` | `/api/books/{id}/chat` | Chat (SSE stream) |
| `GET` | `/api/books/{id}/notes` | List notes for a book |
| `POST` | `/api/books/{id}/notes` | Create a note |
| `PUT` | `/api/notes/{id}` | Update a note |
| `DELETE` | `/api/notes/{id}` | Delete a note |
| `GET` | `/api/sessions/{id}/messages` | Get session history |
| `GET` | `/api/debug/retrieve` | Inspect raw retrieval results |
| `GET` | `/api/debug/evals` | List eval scores for a book |
| `GET` | `/api/debug/evals/{id}` | Single eval record |

## Running Tests

```bash
cd backend
source .venv/Scripts/activate   # Windows: .venv\Scripts\activate
pytest
```

70 tests covering chat streaming, RAG retrieval, sessions, notes, evals, and SSE contracts.
