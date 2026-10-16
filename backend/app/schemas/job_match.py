import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class JobMatchItem(BaseModel):
    job_id: uuid.UUID
    job_title: str
    fit_percentage: int = Field(ge=0, le=100)
    matching_skills: list[str]
    missing_required_skills: list[str]
    relevant_evidence: list[str]
    match_summary: str
    calculated_at: datetime | None = None


class JobMatchesResponse(BaseModel):
    resume_id: uuid.UUID
    scoring_version: str
    results: list[JobMatchItem]