# 2026-03-28: SQLite Progress-Tracking Foundation

## What was done

- Spec written: `docs/specs/2026-03-28-sqlite-progress-tracking.md`
- Added `aiosqlite` dependency for async SQLite access
- Created database module (`backend/app/services/database.py`):
  - Schema with three tables: `books`, `chat_sessions`, `chat_messages`
  - Async context manager for connections with WAL mode and foreign keys
  - `init_db()` for schema initialization
  - `_data_dir_override` for test-time path redirection
- Created SQLite-backed book storage (`backend/app/services/storage_db.py`):
  - Same interface as `storage.py` (JSON-based): `create_book`, `list_books`, `get_book`, `update_book_status`
  - Transparent swap candidate for existing routes
- Created session/message persistence (`backend/app/services/sessions.py`):
  - `create_session`, `get_session`, `list_sessions`
  - `add_message`, `get_messages`
  - Messages track `agent_type` for routed agent attribution
- Added `use_sqlite_storage` config flag (default `False`) for gated rollout
- Added 11 unit tests across `test_storage_db.py` (5 tests) and `test_sessions.py` (6 tests)
- All 35 tests pass (24 existing + 11 new)

## Key decisions made

- Used `aiosqlite` async context manager pattern (not raw `await connect()`) to avoid thread reuse bugs
- Exposed `_data_dir_override` module variable for clean test isolation without fighting Pydantic property setters
- Left JSON storage (`storage.py`) untouched as fallback; swap happens at import site when flag is flipped

## Issues / Gotchas

- `aiosqlite.connect()` returns a Connection that doubles as a context manager; calling `await` on it starts an internal thread. Using `async with await get_connection()` caused `RuntimeError: threads can only be started once`. Fixed by wrapping in `@asynccontextmanager`.
- `pytest-asyncio` 0.26.0 requires `pytest<9`, so pytest was downgraded from 9.0.2 to 8.4.2.

## Next steps

- Wire `use_sqlite_storage` flag to swap `storage.py` → `storage_db.py` in route imports
- Add session persistence to chat route (create session on first message, persist messages)
- Plan Quiz Master and Study Planner agents for future phases
