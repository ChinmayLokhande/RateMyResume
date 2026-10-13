import sys
from pathlib import Path

from app.ai.candidate_extraction import extract_candidate
from app.ai.llm import get_llm_provider
from app.ai.ocr import get_ocr_engine
from app.services.extraction import extract_resume_text
from app.services.resume_service import detect_mime

data = Path(sys.argv[1]).read_bytes()
result = extract_resume_text(data, detect_mime(data), get_ocr_engine())
print(extract_candidate(result.text, get_llm_provider()))