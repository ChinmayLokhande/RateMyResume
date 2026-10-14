from pydantic import BaseModel

from app.schemas.resume import ResumeSummary


class DashboardStats(BaseModel):
    total: int
    completed: int
    in_progress: int  # queued or processing
    failed: int
    recent: list[ResumeSummary]