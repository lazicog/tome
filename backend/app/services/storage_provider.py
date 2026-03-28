"""Thin re-export layer that delegates to JSON or SQLite storage based on config."""

from app.config import settings

if settings.use_sqlite_storage:
    from app.services.storage_db import create_book, delete_book, get_book, list_books, update_book_status
else:
    from app.services.storage import create_book, delete_book, get_book, list_books, update_book_status

__all__ = ["create_book", "delete_book", "get_book", "list_books", "update_book_status"]
