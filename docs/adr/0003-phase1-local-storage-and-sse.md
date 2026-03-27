# ADR-0003: Phase 1 uses local metadata storage and SSE chat streaming

**Status**: Accepted
**Date**: 2026-03-27

## Context

For Phase 1 we needed a usable end-to-end product quickly:

- upload PDF
- ingest/chunk/embed/store
- ask questions against retrieved chunks
- stream answers in the UI

Adding SQLAlchemy/Alembic and a full persistent chat schema in the first pass would have slowed delivery.

## Decision

Use a lightweight local-first implementation for Phase 1:

- book metadata stored in `backend/data/books.json`
- vectors stored in ChromaDB (`backend/data/chroma`)
- uploaded PDFs stored in `backend/data/uploads`
- chat delivery via Server-Sent Events (`text/event-stream`)
- background ingestion using FastAPI `BackgroundTasks`

## Consequences

- **Positive**: Fast to implement and easy for users to run locally
- **Positive**: No external services required to test end-to-end flow
- **Positive**: Streaming UX works immediately with simple SSE parsing
- **Negative**: Metadata storage is file-based and not ideal for concurrent writes
- **Negative**: No durable chat session persistence yet
- **Negative**: Background task processing is basic (no worker queue/retries)
