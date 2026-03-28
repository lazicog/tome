"""One-shot migration: books.json -> SQLite.

Usage:
    cd backend
    .venv/Scripts/python -m app.services.migrate
"""

import asyncio
import json
import sys

from app.config import settings
from app.services.database import get_connection, init_db


async def migrate_books_json_to_sqlite() -> int:
    books_path = settings.books_index_path
    if not books_path.exists():
        print(f"No books.json found at {books_path}, nothing to migrate.")
        return 0

    with open(books_path, encoding="utf-8") as f:
        books: dict[str, dict] = json.loads(f.read() or "{}")

    if not books:
        print("books.json is empty, nothing to migrate.")
        return 0

    await init_db()

    migrated = 0
    async with get_connection() as conn:
        for book_id, payload in books.items():
            existing = await conn.execute("SELECT id FROM books WHERE id = ?", (book_id,))
            if await existing.fetchone():
                print(f"  skip {book_id} ({payload.get('title', '?')}) - already exists")
                continue

            await conn.execute(
                "INSERT INTO books (id, title, file_name, status, chunks, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    payload["id"],
                    payload.get("title", "Untitled"),
                    payload.get("file_name", "unknown.pdf"),
                    payload.get("status", "queued"),
                    payload.get("chunks", 0),
                    payload.get("created_at", ""),
                ),
            )
            migrated += 1
            print(f"  migrated {book_id} ({payload.get('title', '?')})")

        await conn.commit()

    print(f"\nMigration complete: {migrated} books migrated, {len(books) - migrated} skipped.")
    return migrated


def main() -> None:
    count = asyncio.run(migrate_books_json_to_sqlite())
    sys.exit(0 if count >= 0 else 1)


if __name__ == "__main__":
    main()
