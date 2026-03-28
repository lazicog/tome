import structlog

from app.rag.chunker import chunk_pages, chunk_pages_rich
from app.rag.embeddings import embed_texts
from app.rag.processor import extract_pdf_pages, extract_pdf_text
from app.rag.retriever import add_chunks, delete_collection

log = structlog.get_logger()


def ingest_book(book_id: str, file_path: str) -> int:
    """Ingest a PDF using the improved heading-aware pipeline."""
    pages = extract_pdf_pages(file_path)
    chunks = chunk_pages_rich(book_id=book_id, pages=pages)
    vectors = embed_texts([c["content"] for c in chunks])
    add_chunks(book_id=book_id, chunks=chunks, embeddings=vectors)
    log.info("ingest.complete", book_id=book_id, chunks=len(chunks))
    return len(chunks)


def reingest_book(book_id: str, file_path: str) -> int:
    """Delete existing embeddings and re-ingest with current pipeline."""
    log.info("reingest.start", book_id=book_id)
    delete_collection(book_id)
    return ingest_book(book_id, file_path)
