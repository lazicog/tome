import aiofiles
import structlog
from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.config import settings
from app.rag.ingest import ingest_book, reingest_book
from app.schemas import BookListResponse, BookResponse, ProcessingStatus
from app.services.storage_provider import create_book, get_book, list_books, update_book_status

log = structlog.get_logger()
router = APIRouter(prefix="/books", tags=["books"])


def _find_pdf_on_disk(book_id: str, file_name: str):
    """Resolve the actual PDF path -- files are stored as {book_id}.pdf on disk."""
    by_id = settings.uploads_dir / f"{book_id}.pdf"
    if by_id.exists():
        return by_id
    by_name = settings.uploads_dir / file_name
    if by_name.exists():
        return by_name
    return None


async def _process_book(book_id: str, file_path: str) -> None:
    try:
        await update_book_status(book_id, ProcessingStatus.processing)
        chunks = ingest_book(book_id=book_id, file_path=file_path)
        await update_book_status(book_id, ProcessingStatus.ready, chunks=chunks)
    except Exception as exc:
        log.error("books.process_failed", book_id=book_id, error=str(exc))
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


@router.post("/{book_id}/reingest", response_model=BookResponse, summary="Re-ingest a book with the latest pipeline")
async def reingest_book_endpoint(book_id: str, background_tasks: BackgroundTasks) -> BookResponse:
    item = await get_book(book_id)
    if not item:
        raise HTTPException(status_code=404, detail="Book not found")

    file_path = _find_pdf_on_disk(book_id, item.file_name)
    if not file_path:
        raise HTTPException(status_code=404, detail="Original PDF file not found on disk")

    async def _do_reingest(bid: str, fp: str) -> None:
        try:
            await update_book_status(bid, ProcessingStatus.processing)
            chunks = reingest_book(book_id=bid, file_path=fp)
            await update_book_status(bid, ProcessingStatus.ready, chunks=chunks)
        except Exception as exc:
            log.error("books.reingest_failed", book_id=bid, error=str(exc))
            await update_book_status(bid, ProcessingStatus.failed)

    background_tasks.add_task(_do_reingest, book_id, str(file_path))
    return item


@router.get("/{book_id}/pdf", summary="Serve the uploaded PDF file")
async def serve_book_pdf(book_id: str):
    item = await get_book(book_id)
    if not item:
        raise HTTPException(status_code=404, detail="Book not found")

    file_path = _find_pdf_on_disk(book_id, item.file_name)
    if not file_path:
        raise HTTPException(status_code=404, detail="PDF file not found on disk")

    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=item.file_name,
        content_disposition_type="inline",
    )
