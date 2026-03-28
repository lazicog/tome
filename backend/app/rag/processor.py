from dataclasses import dataclass, field

import fitz


@dataclass
class TextBlock:
    text: str
    font_size: float
    is_bold: bool


@dataclass
class PageContent:
    page_number: int
    blocks: list[TextBlock] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n".join(b.text for b in self.blocks if b.text.strip())


@dataclass
class PageText:
    """Legacy compat — used by old chunker interface."""
    page_number: int
    text: str


def extract_pdf_pages(file_path: str) -> list[PageContent]:
    """Extract pages with font metadata for heading detection."""
    doc = fitz.open(file_path)
    pages: list[PageContent] = []

    for i, page in enumerate(doc, start=1):
        page_dict = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
        blocks: list[TextBlock] = []

        for block in page_dict.get("blocks", []):
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                line_text = ""
                max_size = 0.0
                has_bold = False
                for span in line.get("spans", []):
                    line_text += span.get("text", "")
                    size = span.get("size", 0.0)
                    if size > max_size:
                        max_size = size
                    font = span.get("font", "").lower()
                    if "bold" in font or "heavy" in font or "black" in font:
                        has_bold = True

                stripped = line_text.strip()
                if stripped:
                    blocks.append(TextBlock(text=stripped, font_size=round(max_size, 1), is_bold=has_bold))

        pages.append(PageContent(page_number=i, blocks=blocks))

    doc.close()
    return pages


def extract_pdf_text(file_path: str) -> list[PageText]:
    """Legacy interface for backward compat."""
    rich_pages = extract_pdf_pages(file_path)
    return [PageText(page_number=p.page_number, text=p.text) for p in rich_pages]
