from collections.abc import Iterator
from functools import lru_cache
from typing import Protocol

import numpy as np
import pymupdf

OCR_DPI = 200  # higher is more accurate but slower and heavier on memory


class OcrEngine(Protocol):
    name: str

    def recognize(self, image: np.ndarray) -> str:
        """Takes a BGR image array, returns the text found, one line per row."""
        ...


class PaddleOcrEngine:
    name = "paddleocr"

    def __init__(self, lang: str = "en") -> None:
        self._lang = lang
        self._engine = None  # loaded on first use; model loading is slow

    def _load(self):
        if self._engine is None:
            from paddleocr import PaddleOCR  # imported lazily: it is a heavy import

            self._engine = PaddleOCR(
                lang=self._lang,
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=False,
            )
        return self._engine

    def recognize(self, image: np.ndarray) -> str:
        lines: list[str] = []
        for page in self._load().predict(image):
            lines.extend(page["rec_texts"])
        return "\n".join(lines)


@lru_cache
def get_ocr_engine() -> OcrEngine:
    return PaddleOcrEngine()


def render_pdf_pages(data: bytes, max_pages: int, dpi: int = OCR_DPI) -> Iterator[np.ndarray]:
    """Yields one page at a time, so we never hold every page image in memory."""
    with pymupdf.open(stream=data, filetype="pdf") as doc:
        for page in doc.pages(0, min(doc.page_count, max_pages)):
            pix = page.get_pixmap(dpi=dpi, colorspace=pymupdf.csRGB, alpha=False)
            rgb = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
            yield rgb[:, :, ::-1].copy()  # RGB -> BGR, which is what Paddle expects