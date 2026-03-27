# 2026-03-27: Phase 1 Hardening (Local Dev + Reliability)

## What was done

- Hardened upload handling in `POST /api/books`:
  - Added strict max-size enforcement using `MAX_UPLOAD_SIZE_MB`
  - Added explicit empty-upload rejection
  - Kept MIME validation for PDF-only uploads
- Hardened SSE transport:
  - Backend now emits SSE frames through a dedicated event formatter
  - Frontend parser now handles multi-line `data:` payloads correctly
- Improved frontend UX for ingestion lifecycle:
  - Auto-polls book list while any book is `queued` or `processing`
  - Disables chat links until a book is `ready`
  - Shows clearer chat request errors
- Fixed Chroma metadata compatibility:
  - Serialize metadata to scalar-safe values for Chroma storage
  - Rehydrate `page_numbers` back to numeric arrays on retrieval
- Verified local non-Docker run path:
  - Backend and frontend run natively on Windows
  - End-to-end upload -> processing -> ready flow works

## Key decisions made

- Keep Docker as optional convenience; ensure first-class local dev workflow without virtualization
- Keep hybrid retrieval baseline, but prioritize reliability and debuggability before adding Phase 2 agent routing

## Issues / Gotchas

- Localhost origin mismatch (`localhost` vs `127.0.0.1`) causes browser `Failed to fetch` due to CORS
- Port `8000` conflicts can happen from stale uvicorn processes; must free port before restart
- Chroma metadata only supports scalar values; nested/list metadata must be transformed

## Next steps

- Add a lightweight integration test for upload -> ready -> chat stream path
- Start Phase 2: router node + specialized agent nodes behind intent routing
