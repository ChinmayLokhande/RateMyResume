import uuid
from typing import Literal

from pydantic import BaseModel


class UploadItemResult(BaseModel):
    filename: str
    status: Literal["accepted", "rejected", "duplicate"]
    resume_id: uuid.UUID | None = None
    detail: str | None = None


class BulkUploadResponse(BaseModel):
    accepted: int
    rejected: int  # includes duplicates; see each result's status
    results: list[UploadItemResult]