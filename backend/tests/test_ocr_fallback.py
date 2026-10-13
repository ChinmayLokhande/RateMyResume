import numpy as np
import pytest

from app.services.extraction import ExtractionError, extract_resume_text
from app.services.resume_service import PDF_MIME
from tests.test_extraction import LONG_LINE, make_pdf


class FakeOcr:
    name = "fake"

    def __init__(self, text: str = "Scanned Person\nscan@example.com") -> None:
        self.text = text
        self.calls = 0

    def recognize(self, image: np.ndarray) -> str:
        assert image.ndim == 3 and image.shape[2] == 3
        self.calls += 1
        return self.text


class BrokenOcr:
    name = "broken"

    def recognize(self, image: np.ndarray) -> str:
        raise RuntimeError("engine crashed")


def test_text_pdf_does_not_use_ocr():
    engine = FakeOcr()
    result = extract_resume_text(make_pdf(LONG_LINE), PDF_MIME, engine)
    assert engine.calls == 0
    assert result.method == "native_text"


def test_scanned_pdf_falls_back_to_ocr():
    engine = FakeOcr()
    result = extract_resume_text(make_pdf(None), PDF_MIME, engine)
    assert engine.calls == 1
    assert result.method == "ocr"
    assert "scan@example.com" in result.text


def test_ocr_with_no_text_is_an_error():
    with pytest.raises(ExtractionError, match="No readable text"):
        extract_resume_text(make_pdf(None), PDF_MIME, FakeOcr(text=""))


def test_ocr_engine_crash_becomes_safe_error():
    with pytest.raises(ExtractionError, match="OCR could not read"):
        extract_resume_text(make_pdf(None), PDF_MIME, BrokenOcr())