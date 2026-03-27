# Tome Session Handoff

Use this file as the startup context when resuming work with the agent.

## How to resume

At the start of the next session, say:

`Read docs/SESSION-HANDOFF.md and continue from there.`

## Current project status

- Project: `tome` (`https://github.com/lazicog/tome`)
- Branch: `master`
- Last local commit: `df41d41`
- Working tree was clean at session end
- Local branch was ahead of `origin/master` by 1 commit (not pushed yet at session end)

## What is completed

### Foundation

- Cursor rules and skills are in place
- Documentation system is in place:
  - ADRs in `docs/adr/`
  - Devlog in `docs/devlog/`
  - Changelog in `CHANGELOG.md`

### Phase 1 implementation (scaffolded)

- Backend created under `backend/app/`
  - FastAPI app in `backend/app/main.py`
  - Routes:
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
  - LLM provider abstraction (LangChain):
    - `backend/app/services/llm.py`

- Frontend created under `frontend/`
  - Book library/upload page: `frontend/src/app/page.tsx`
  - Chat page: `frontend/src/app/chat/[bookId]/page.tsx`
  - API client: `frontend/src/lib/api.ts`

- Runtime/config:
  - `docker-compose.yml`
  - `.env.example`
  - `backend/requirements.txt`
  - `README.md`

## Important decisions already made

- Do not use LiteLLM
- Use LangChain chat models (`ChatOpenAI`, `ChatAnthropic`, `ChatOllama`)
- Solo workflow for now: direct commits to `master` allowed
- Branch/PR workflow only when contributors join

See ADRs:
- `docs/adr/0001-langchain-over-litellm.md`
- `docs/adr/0002-langgraph-for-orchestration.md`
- `docs/adr/0003-phase1-local-storage-and-sse.md`

## First checks on next session

1. `git status`
2. If ahead by 1 commit and you want backup: `git push`
3. Create `.env` from `.env.example`
4. Start app:
   - `docker compose up`
5. Verify:
   - Frontend: `http://localhost:3000`
   - Backend docs: `http://localhost:8000/docs`

## Suggested next work (Phase 1 hardening)

1. Add strict upload size validation on backend
2. Improve SSE framing robustness for multiline payloads
3. Add frontend polling for processing status refresh
4. Add basic integration test for upload -> ready -> chat path
5. Then move to Phase 2 (router + specialized agents)
