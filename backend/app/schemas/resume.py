import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class UploadItemResult(BaseModel):
    filename: str
    status: Literal["accepted", "rejected", "duplicate"]
    resume_id: uuid.UUID | None = None
    detail: str | None = None


class BulkUploadResponse(BaseModel):
    accepted: int
    rejected: int  # includes duplicates; see each result's status
    results: list[UploadItemResult]


class ResumeSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    original_filename: str
    candidate_name: str | None
    email: str | None
    mobile: str | None
    location: str | None
    skills: list[str]
    uploaded_at: datetime
    extraction_status: str
    analysis_status: str
    error_message: str | None


class ResumeDetail(ResumeSummary):
    mime_type: str
    file_size: int
    extraction_method: str | None
    extracted_at: datetime | None
    extracted_text: str | None


class ResumeListResponse(BaseModel):
    items: list[ResumeSummary]
    total: int
    page: int
    page_size: int
    total_pages: int


class ResumeStatus(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    extraction_status: str
    analysis_status: str
    error_message: str | None
    extracted_at: datetime | None