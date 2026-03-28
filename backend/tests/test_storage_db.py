import pytest
import pytest_asyncio

from app.schemas import ProcessingStatus
from app.services import database


@pytest_asyncio.fixture
async def _fresh_db(tmp_path, monkeypatch):
    """Point database module at a temp directory so each test gets a fresh DB."""
    monkeypatch.setattr(database, "_data_dir_override", tmp_path)
    await database.init_db()


@pytest.mark.asyncio
@pytest.mark.usefixtures("_fresh_db")
async def test_create_and_get_book():
    from app.services.storage_db import create_book, get_book

    book, file_path = await create_book("test-book.pdf")
    assert book.title == "test-book"
    assert book.file_name == "test-book.pdf"
    assert book.status == ProcessingStatus.queued
    assert book.chunks == 0
    assert file_path.name.endswith(".pdf")

    fetched = await get_book(book.id)
    assert fetched is not None
    assert fetched.id == book.id
    assert fetched.title == book.title


@pytest.mark.asyncio
@pytest.mark.usefixtures("_fresh_db")
async def test_get_nonexistent_book():
    from app.services.storage_db import get_book

    result = await get_book("does-not-exist")
    assert result is None


@pytest.mark.asyncio
@pytest.mark.usefixtures("_fresh_db")
async def test_list_books_pagination():
    from app.services.storage_db import create_book, list_books

    for i in range(5):
        await create_book(f"book-{i}.pdf")

    page1 = await list_books(page=1, limit=3)
    assert len(page1) == 3

    page2 = await list_books(page=2, limit=3)
    assert len(page2) == 2

    all_books = await list_books(page=1, limit=100)
    assert len(all_books) == 5


@pytest.mark.asyncio
@pytest.mark.usefixtures("_fresh_db")
async def test_update_book_status():
    from app.services.storage_db import create_book, get_book, update_book_status

    book, _ = await create_book("status-test.pdf")
    assert book.status == ProcessingStatus.queued

    await update_book_status(book.id, ProcessingStatus.processing)
    updated = await get_book(book.id)
    assert updated is not None
    assert updated.status == ProcessingStatus.processing

    await update_book_status(book.id, ProcessingStatus.ready, chunks=42)
    ready = await get_book(book.id)
    assert ready is not None
    assert ready.status == ProcessingStatus.ready
    assert ready.chunks == 42


@pytest.mark.asyncio
@pytest.mark.usefixtures("_fresh_db")
async def test_update_nonexistent_book_is_noop():
    from app.services.storage_db import update_book_status

    await update_book_status("ghost-id", ProcessingStatus.ready, chunks=10)
