# Tome Session Handoff

Use this file as the startup context when resuming work with the agent.

## How to resume

At the start of the next session, say:

`Read docs/SESSION-HANDOFF.md and continue from there.`

## Current project status

- Project: `tome` ([https://github.com/lazicog/tome](https://github.com/lazicog/tome))
- Branch: `master`
- Latest pushed commit at handoff start: `856fec6`
- Workflow: solo mode direct commits to `master`

## What is completed

### Foundation and conventions

- Cursor rules and skills are set up
- Documentation system is active:
  - ADRs in `docs/adr/`
  - Devlog in `docs/devlog/`
  - Changelog in `CHANGELOG.md`

### Phase 1 (scaffold + hardening)

- Backend created under `backend/app/`
  - FastAPI app in `backend/app/main.py`
  - Endpoints:
    - `GET /api/health`
    - `GET /api/books`
    - `POST /api/books` (PDF upload + background processing)
    - `GET /api/books/{book_id}`
    - `POST /api/books/{book_id}/chat` (SSE stream)
  - RAG pipeline:
    - PDF extraction: `backend/app/rag/processor.py`
    - Chunking: `backend/app/rag/chunker.py`
    - Embeddings: `backend/app/rag/embeddings.py`
    - Storage/retrieval: `backend/app/rag/retriever.py`
    - Ingestion orchestrator: `backend/app/rag/ingest.py`
  - Tutor streaming:
    - `backend/app/agents/tutor.py`
  - LLM abstraction (LangChain):
    - `backend/app/services/llm.py`

- Frontend created under `frontend/`
  - Book library/upload page: `frontend/src/app/page.tsx`
  - Chat page: `frontend/src/app/chat/[bookId]/page.tsx`
  - API client: `frontend/src/lib/api.ts`

- Hardening completed:
  - Upload size/empty-file validation
  - CORS for both `localhost` and `127.0.0.1`
  - Chroma metadata scalar serialization fix
  - SSE framing/parsing robustness improvements
  - Polling while books are processing

## Important decisions already made

- Do not use LiteLLM
- Use LangChain chat models (`ChatOpenAI`, `ChatAnthropic`, `ChatOllama`)
- Solo workflow for now: direct commits to `master`
- Branch/PR workflow only when contributors join

See ADRs:
- `docs/adr/0001-langchain-over-litellm.md`
- `docs/adr/0002-langgraph-for-orchestration.md`
- `docs/adr/0003-phase1-local-storage-and-sse.md`

## Run without Docker (preferred on this machine)

1. Backend:

```powershell
cd C:\Users\Celavi\Documents\HelpMeLearn\backend
.\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

2. Frontend:

```powershell
cd C:\Users\Celavi\Documents\HelpMeLearn\frontend
npm run dev -- --hostname 127.0.0.1 --port 3000
```

3. Verify:
- Frontend: `http://127.0.0.1:3000`
- Backend docs: `http://127.0.0.1:8000/docs`
- Health: `http://127.0.0.1:8000/api/health`

## Known gotchas

- Port conflict on backend startup (`WinError 10048`) means another process is using `8000`
  - find: `netstat -ano | findstr :8000`
  - kill: `taskkill /PID <PID> /F`
- Browser origin mismatch (`localhost` vs `127.0.0.1`) can trigger CORS issues

## Suggested next work

1. Add integration test for upload -> ready -> chat stream path
2. Start Phase 2: router + specialized agent nodes
3. Introduce persistent progress tracking (SQLite) once Phase 2 flow is stable
