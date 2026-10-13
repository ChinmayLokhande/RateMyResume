import sys
from pathlib import Path

from app.ai.ocr import get_ocr_engine
from app.services.extraction import extract_resume_text
from app.services.resume_service import detect_mime

data = Path(sys.argv[1]).read_bytes()
result = extract_resume_text(data, detect_mime(data), get_ocr_engine())
print(f"method={result.method} chars={len(result.text)} pages={result.page_count}")
print(result.text if "--full" in sys.argv else result.text[:200])