from dataclasses import dataclass

import fitz


@dataclass
class PageText:
    page_number: int
    text: str


def extract_pdf_text(file_path: str) -> list[PageText]:
    doc = fitz.open(file_path)
    pages: list[PageText] = []
    for i, page in enumerate(doc, start=1):
        pages.append(PageText(page_number=i, text=page.get_text("text") or ""))
    doc.close()
    return pages
