from typing import TypedDict

import structlog

from app.rag.processor import PageContent, PageText

log = structlog.get_logger()


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
    return max(1, len(text.split()))


def _detect_headings(pages: list[PageContent]) -> dict[float, str]:
    """Analyze font sizes across all pages to classify heading levels."""
    size_counts: dict[float, int] = {}
    for page in pages:
        for block in page.blocks:
            size = block.font_size
            size_counts[size] = size_counts.get(size, 0) + 1

    if not size_counts:
        return {}

    sorted_sizes = sorted(size_counts.keys(), reverse=True)
    body_size = max(size_counts, key=size_counts.get)

    heading_map: dict[float, str] = {}
    chapter_assigned = False
    section_assigned = False

    for size in sorted_sizes:
        if size <= body_size:
            break
        if not chapter_assigned and size >= body_size * 1.4:
            heading_map[size] = "chapter"
            chapter_assigned = True
        elif not section_assigned and size >= body_size * 1.1:
            heading_map[size] = "section"
            section_assigned = True

    return heading_map


def chunk_pages_rich(
    book_id: str,
    pages: list[PageContent],
    max_tokens: int = 900,
    overlap_tokens: int = 128,
) -> list[Chunk]:
    """Heading-aware chunking using font metadata."""
    heading_map = _detect_headings(pages)
    chunks: list[Chunk] = []
    chunk_index = 0
    current_chapter = "Introduction"
    current_section = ""
    current_parts: list[str] = []
    current_tokens = 0
    current_pages: set[int] = set()

    def _flush():
        nonlocal chunk_index, current_parts, current_tokens, current_pages
        if not current_parts:
            return
        body = "\n\n".join(current_parts).strip()
        if not body:
            return
        sorted_pages = sorted(current_pages) if current_pages else [1]
        section_label = current_section or f"Pages {sorted_pages[0]}-{sorted_pages[-1]}"

        context_header = f"[Chapter: {current_chapter} | Section: {section_label}]"
        content = f"{context_header}\n\n{body}"

        chunks.append(
            Chunk(
                id=f"{book_id}-{chunk_index}",
                content=content,
                metadata=ChunkMetadata(
                    book_id=book_id,
                    chapter=current_chapter,
                    section=section_label,
                    page_numbers=sorted_pages,
                    chunk_index=chunk_index,
                    content_type="text",
                ),
            )
        )
        chunk_index += 1

        words = content.split()
        overlap = " ".join(words[-overlap_tokens:]) if len(words) > overlap_tokens else ""
        current_parts = [overlap] if overlap else []
        current_tokens = _estimate_tokens(overlap) if overlap else 0
        current_pages = set()

    for page in pages:
        current_pages.add(page.page_number)
        for block in page.blocks:
            heading_level = heading_map.get(block.font_size)

            if heading_level == "chapter":
                _flush()
                current_chapter = block.text
                current_section = ""
                continue

            if heading_level == "section":
                _flush()
                current_section = block.text
                continue

            para_tokens = _estimate_tokens(block.text)
            if current_tokens + para_tokens > max_tokens and current_parts:
                _flush()
                current_pages.add(page.page_number)

            current_parts.append(block.text)
            current_tokens += para_tokens

    _flush()

    log.info("chunker.result", book_id=book_id, total_chunks=len(chunks), chapters_found=len({c["metadata"]["chapter"] for c in chunks}))
    return chunks


def chunk_pages(
    book_id: str,
    pages: list[PageText],
    max_tokens: int = 900,
    overlap_tokens: int = 128,
) -> list[Chunk]:
    """Legacy chunker for backward compat with PageText input."""
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
