import pytest
import pytest_asyncio

from app.services.notes import create_note, delete_note, get_note, list_notes, update_note


@pytest_asyncio.fixture(autouse=True)
async def _db(isolated_db):
    """Use the shared isolated_db fixture for all tests in this module."""


@pytest.mark.asyncio
async def test_create_note():
    note = await create_note("book1", "Test content", title="My Note", note_type="manual")
    assert note["book_id"] == "book1"
    assert note["title"] == "My Note"
    assert note["content"] == "Test content"
    assert note["type"] == "manual"


@pytest.mark.asyncio
async def test_get_note():
    created = await create_note("book1", "Content here")
    fetched = await get_note(created["id"])
    assert fetched is not None
    assert fetched["content"] == "Content here"


@pytest.mark.asyncio
async def test_get_note_not_found():
    result = await get_note("nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_list_notes():
    await create_note("book1", "Note A", note_type="manual")
    await create_note("book1", "Note B", note_type="ai_summary")
    await create_note("book2", "Note C", note_type="manual")

    all_book1 = await list_notes("book1")
    assert len(all_book1) == 2

    summaries = await list_notes("book1", note_type="ai_summary")
    assert len(summaries) == 1
    assert summaries[0]["type"] == "ai_summary"


@pytest.mark.asyncio
async def test_list_notes_filter_by_page():
    await create_note("book1", "Page 5 note", page_number=5)
    await create_note("book1", "Page 10 note", page_number=10)

    page5 = await list_notes("book1", page_number=5)
    assert len(page5) == 1
    assert page5[0]["page_number"] == 5


@pytest.mark.asyncio
async def test_list_notes_search():
    await create_note("book1", "About embeddings and vectors", title="Embeddings")
    await create_note("book1", "About chunking strategies", title="Chunking")

    results = await list_notes("book1", search="embeddings")
    assert len(results) == 1
    assert "embeddings" in results[0]["content"].lower()


@pytest.mark.asyncio
async def test_update_note():
    note = await create_note("book1", "Original")
    updated = await update_note(note["id"], title="Updated Title", content="Updated Content")
    assert updated["title"] == "Updated Title"
    assert updated["content"] == "Updated Content"
    assert updated["updated_at"] != note["created_at"]


@pytest.mark.asyncio
async def test_delete_note():
    note = await create_note("book1", "To be deleted")
    assert await delete_note(note["id"]) is True
    assert await get_note(note["id"]) is None


@pytest.mark.asyncio
async def test_delete_note_not_found():
    assert await delete_note("nonexistent") is False


@pytest.mark.asyncio
async def test_create_note_with_all_fields():
    note = await create_note(
        "book1",
        "Full note",
        page_number=42,
        chapter="Chapter 3",
        title="Full",
        note_type="highlight",
        tags="important,review",
    )
    assert note["page_number"] == 42
    assert note["chapter"] == "Chapter 3"
    assert note["type"] == "highlight"
    assert note["tags"] == "important,review"
