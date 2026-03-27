from typing import TypedDict

from app.rag.processor import PageText


class ChunkMetadata(TypedDict):
    book_id: str
    chapter: str
    section: str
    page_numbers: list[int]
    chunk_index: int
    content_type: str


class Chunk(TypedDict):
    id: str
    content: str
    metadata: ChunkMetadata


def _estimate_tokens(text: str) -> int:
    # A fast approximation good enough for chunking.
    return max(1, len(text.split()))


def chunk_pages(book_id: str, pages: list[PageText], max_tokens: int = 900, overlap_tokens: int = 128) -> list[Chunk]:
    chunks: list[Chunk] = []
    chunk_index = 0

    for page in pages:
        paragraphs = [p.strip() for p in page.text.split("\n\n") if p.strip()]
        current_parts: list[str] = []
        current_tokens = 0

        for para in paragraphs:
            para_tokens = _estimate_tokens(para)
            if current_tokens + para_tokens > max_tokens and current_parts:
                content = "\n\n".join(current_parts).strip()
                chunks.append(
                    Chunk(
                        id=f"{book_id}-{chunk_index}",
                        content=content,
                        metadata=ChunkMetadata(
                            book_id=book_id,
                            chapter="Unknown",
                            section=f"Page {page.page_number}",
                            page_numbers=[page.page_number],
                            chunk_index=chunk_index,
                            content_type="text",
                        ),
                    )
                )
                chunk_index += 1

                words = content.split()
                overlap = " ".join(words[-overlap_tokens:]) if len(words) > overlap_tokens else content
                current_parts = [overlap, para]
                current_tokens = _estimate_tokens(overlap) + para_tokens
            else:
                current_parts.append(para)
                current_tokens += para_tokens

        if current_parts:
            content = "\n\n".join(current_parts).strip()
            chunks.append(
                Chunk(
                    id=f"{book_id}-{chunk_index}",
                    content=content,
                    metadata=ChunkMetadata(
                        book_id=book_id,
                        chapter="Unknown",
                        section=f"Page {page.page_number}",
                        page_numbers=[page.page_number],
                        chunk_index=chunk_index,
                        content_type="text",
                    ),
                )
            )
            chunk_index += 1

    return chunks
