import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AnalysisResponse(BaseModel):
    id: uuid.UUID
    resume_id: uuid.UUID
    analysis_status: str  # state of the newest run; this body is the newest successful one
    score: int | None
    summary: str
    detailed_result: dict[str, Any]
    rubric_version: str
    prompt_version: str
    model_name: str
    model_version: str | None
    created_at: datetime