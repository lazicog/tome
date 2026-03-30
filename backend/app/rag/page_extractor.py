"""Extract verbatim text from a specific PDF page using pdfplumber."""

import structlog

from app.config import settings

log = structlog.get_logger()


def _find_pdf_path(book_id: str, file_name: str):
    by_id = settings.uploads_dir / f"{book_id}.pdf"
    if by_id.exists():
        return by_id
    by_name = settings.uploads_dir / file_name
    if by_name.exists():
        return by_name
    return None


async def get_page_text(book_id: str, page_number: int) -> str:
    """Return verbatim text of a PDF page (1-indexed). Returns '' on any error."""
    try:
        from app.services.storage_provider import get_book
        book = await get_book(book_id)
        if not book:
            return ""

        pdf_path = _find_pdf_path(book_id, book.file_name)
        if not pdf_path:
            return ""

        import pdfplumber
        with pdfplumber.open(str(pdf_path)) as pdf:
            if page_number < 1 or page_number > len(pdf.pages):
                return ""
            text = pdf.pages[page_number - 1].extract_text() or ""

        # Strip excessive blank lines and cap length
        lines = [ln for ln in text.splitlines() if ln.strip()]
        cleaned = "\n".join(lines)
        return cleaned[:3000]

    except Exception as exc:
        log.warning("page_extractor.error", book_id=book_id, page=page_number, error=str(exc))
        return ""
