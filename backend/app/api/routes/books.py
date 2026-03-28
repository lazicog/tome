import aiofiles
from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile

from app.config import settings
from app.rag.ingest import ingest_book
from app.schemas import BookListResponse, BookResponse, ProcessingStatus
from app.services.storage_provider import create_book, get_book, list_books, update_book_status

router = APIRouter(prefix="/books", tags=["books"])


async def _process_book(book_id: str, file_path: str) -> None:
    try:
        await update_book_status(book_id, ProcessingStatus.processing)
        chunks = ingest_book(book_id=book_id, file_path=file_path)
        await update_book_status(book_id, ProcessingStatus.ready, chunks=chunks)
    except Exception:
        await update_book_status(book_id, ProcessingStatus.failed)


async def _read_upload_with_limit(file: UploadFile) -> bytes:
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    total = 0
    chunks: list[bytes] = []

    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File exceeds max size of {settings.max_upload_size_mb}MB",
            )
        chunks.append(chunk)

    if total == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    return b"".join(chunks)


@router.get("", response_model=BookListResponse, summary="List uploaded books")
async def get_books(page: int = 1, limit: int = 100) -> BookListResponse:
    items = await list_books(page=page, limit=limit)
    return BookListResponse(items=items, total=len(items), page=page, limit=limit)


@router.post("", response_model=BookResponse, status_code=201, summary="Upload a PDF book")
async def upload_book(background_tasks: BackgroundTasks, file: UploadFile = File(...)) -> BookResponse:
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    data = await _read_upload_with_limit(file)
    book, file_path = await create_book(file.filename or "book.pdf")
    async with aiofiles.open(file_path, "wb") as out:
        await out.write(data)

    background_tasks.add_task(_process_book, book.id, str(file_path))
    return book


@router.get("/{book_id}", response_model=BookResponse, summary="Get one book")
async def get_book_by_id(book_id: str) -> BookResponse:
    item = await get_book(book_id)
    if not item:
        raise HTTPException(status_code=404, detail="Book not found")
    return item
