from app.rag.chunker import chunk_pages
from app.rag.embeddings import embed_texts
from app.rag.processor import extract_pdf_text
from app.rag.retriever import add_chunks


def ingest_book(book_id: str, file_path: str) -> int:
    pages = extract_pdf_text(file_path)
    chunks = chunk_pages(book_id=book_id, pages=pages)
    vectors = embed_texts([c["content"] for c in chunks])
    add_chunks(book_id=book_id, chunks=chunks, embeddings=vectors)
    return len(chunks)
