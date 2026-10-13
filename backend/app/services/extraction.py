import io
import re
from dataclasses import dataclass
from app.ai.ocr import OcrEngine, render_pdf_pages
import pymupdf
from docx import Document

from app.services.resume_service import DOCX_MIME, PDF_MIME

MAX_PDF_PAGES = 30  # resumes are short; this bounds work on hostile files
MAX_TEXT_CHARS = 200_000
MIN_CHARS_PER_PAGE = 50  # below this, a PDF is treated as a scan and needs OCR


class ExtractionError(Exception):
    """Carries a message that is safe to show to the user."""


@dataclass(frozen=True)
class ExtractionResult:
    text: str
    method: str  # "native_text"
    page_count: int | None
    needs_ocr: bool


def _clean(text: str) -> str:
    text = text.replace("\x00", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()[:MAX_TEXT_CHARS]


def extract_pdf(data: bytes) -> ExtractionResult:
    try:
        with pymupdf.open(stream=data, filetype="pdf") as doc:
            if doc.needs_pass:
                raise ExtractionError("The PDF is password protected")
            page_count = doc.page_count
            pages_read = min(page_count, MAX_PDF_PAGES)
            pages = [page.get_text("text") for page in doc.pages(0, pages_read)]
    except ExtractionError:
        raise
    except Exception as exc:
        raise ExtractionError("The PDF could not be read") from exc

    text = _clean("\n\n".join(pages))
    needs_ocr = len(text) < MIN_CHARS_PER_PAGE * max(pages_read, 1)
    return ExtractionResult(text, "native_text", page_count, needs_ocr)


def extract_docx(data: bytes) -> ExtractionResult:
    try:
        document = Document(io.BytesIO(data))
        parts = [paragraph.text for paragraph in document.paragraphs]
        for table in document.tables:
            for row in table.rows:
                parts.append(" | ".join(cell.text.strip() for cell in row.cells))
    except Exception as exc:
        raise ExtractionError("The DOCX could not be read") from exc

    return ExtractionResult(_clean("\n".join(parts)), "native_text", None, False)


def extract_text(data: bytes, mime_type: str) -> ExtractionResult:
    if mime_type == PDF_MIME:
        return extract_pdf(data)
    if mime_type == DOCX_MIME:
        return extract_docx(data)
    raise ExtractionError("Unsupported file type")

def ocr_pdf(data: bytes, engine: OcrEngine) -> ExtractionResult:
    try:
        pages = [engine.recognize(image) for image in render_pdf_pages(data, MAX_PDF_PAGES)]
    except Exception as exc:
        raise ExtractionError("OCR could not read the document") from exc

    text = _clean("\n\n".join(pages))
    if not text:
        raise ExtractionError("No readable text was found in the document")
    return ExtractionResult(text, "ocr", len(pages), needs_ocr=False)


def extract_resume_text(data: bytes, mime_type: str, ocr_engine: OcrEngine) -> ExtractionResult:
    """The main entry point: native extraction first, OCR only if the PDF looks scanned."""
    result = extract_text(data, mime_type)
    if mime_type == PDF_MIME and result.needs_ocr:
        return ocr_pdf(data, ocr_engine)
    return result