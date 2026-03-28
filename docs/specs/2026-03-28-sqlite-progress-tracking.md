# SQLite Progress-Tracking Foundation

## Problem

Book metadata is currently stored in a flat JSON file (`data/books.json`). Chat history is ephemeral (lives only in frontend state). There is no persistence layer for learning progress, chat sessions, or message history. This blocks future features like session resume, study planning, and progress dashboards.

## Scope

- In scope:
  - SQLite database with schema for books, chat sessions, and chat messages
  - Database initialization and migration utility
  - Service layer (async CRUD operations) for all three tables
  - Unit tests for service layer
  - Migrate book storage from JSON to SQLite behind the same service interface

- Out of scope:
  - API route changes (existing routes keep working, storage swap is internal)
  - Frontend changes
  - Learning analytics or quiz score tables (future phase)
  - User authentication or multi-user support

## Goals

- Provide a durable, query-friendly storage layer that replaces JSON file I/O.
- Persist chat sessions and messages so conversations can be resumed.
- Keep the migration reversible: JSON storage code remains available but unused.

## Non-goals

- Building a full ORM or migration framework.
- Adding new API endpoints for sessions or messages.
- Supporting concurrent multi-process writes (single-server local-first for now).

## Proposed Design

### Database location

`data/tome.db` (alongside existing `data/` directory).

### Schema

```sql
CREATE TABLE IF NOT EXISTS books (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    file_name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    chunks INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chat_sessions (
    id TEXT PRIMARY KEY,
    book_id TEXT NOT NULL REFERENCES books(id),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES chat_sessions(id),
    role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    agent_type TEXT,
    created_at TEXT NOT NULL
);
```

### Module layout

- `backend/app/services/database.py` - connection management, schema init
- `backend/app/services/storage_db.py` - book CRUD (SQLite replacement for `storage.py`)
- `backend/app/services/sessions.py` - chat session and message CRUD

### Service interfaces

```python
# storage_db.py
async def create_book(file_name: str) -> tuple[BookResponse, Path]
async def list_books(page: int, limit: int) -> list[BookResponse]
async def get_book(book_id: str) -> BookResponse | None
async def update_book_status(book_id: str, status: ProcessingStatus, chunks: int) -> None

# sessions.py
async def create_session(book_id: str) -> str  # returns session_id
async def get_session(session_id: str) -> dict | None
async def list_sessions(book_id: str) -> list[dict]
async def add_message(session_id: str, role: str, content: str, agent_type: str | None) -> int
async def get_messages(session_id: str) -> list[dict]
```

### Wiring strategy

- `storage.py` (JSON-based) remains untouched as fallback.
- New `storage_db.py` exposes the same interface but backed by SQLite.
- Swap happens in import sites (`books.py`, `chat.py`) once validated.
- Config flag `use_sqlite_storage: bool = False` gates the switch.

## API and Data Changes

- No endpoint signature changes.
- No response schema changes.
- Internal storage backend changes from JSON to SQLite (transparent to callers).

## Risks and Mitigations

- Risk: aiosqlite async context adds complexity.
  - Mitigation: Thin wrapper with connection-per-request pattern, no connection pooling needed at this scale.

- Risk: Existing JSON data not migrated automatically.
  - Mitigation: Provide a one-shot migration helper that reads `books.json` and inserts into SQLite. Not required for fresh starts.

- Risk: WAL mode or file locking issues on Windows.
  - Mitigation: Use WAL mode explicitly and test on Windows. Single-server model avoids multi-process contention.

## Test Plan

- Unit tests:
  - Book CRUD: create, list, get, update status
  - Session CRUD: create session, add messages, retrieve messages
  - Schema initialization on fresh database
  - Edge cases: get nonexistent book, empty session messages

- Integration tests:
  - Create book -> create session -> add messages -> retrieve full session

- Manual checks:
  - Verify `data/tome.db` is created on startup
  - Verify existing API behavior unchanged after storage swap

## Rollout Plan

1. Add `aiosqlite` dependency to `requirements.txt`.
2. Implement `database.py` with schema init.
3. Implement `storage_db.py` with book CRUD.
4. Implement `sessions.py` with session/message CRUD.
5. Add unit tests for all service operations.
6. Add config flag `use_sqlite_storage` (default `False`).
7. Validate tests pass, then flip flag in dev to `True`.
8. Remove JSON storage code in a future cleanup pass.

## Implementation Checklist

- [ ] Add `aiosqlite` to `backend/requirements.txt`.
- [ ] Create `backend/app/services/database.py` with connection helper and schema init.
- [ ] Create `backend/app/services/storage_db.py` with book CRUD matching `storage.py` interface.
- [ ] Create `backend/app/services/sessions.py` with session and message CRUD.
- [ ] Add `use_sqlite_storage` config flag in `backend/app/config.py`.
- [ ] Add unit tests in `backend/tests/test_storage_db.py`.
- [ ] Add unit tests in `backend/tests/test_sessions.py`.
- [ ] Validate all existing tests still pass (no regressions).
- [ ] Update devlog and changelog.
