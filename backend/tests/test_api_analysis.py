import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from app.models import ProcessingJob, ResumeAnalysis
from tests.helpers import pdf_bytes, set_fields, upload

API = "/api/v1"


def _completed(client, headers, db):
    rid = upload(client, headers, pdf_bytes()).json()["resume_id"]
    set_fields(db, rid, extraction_status="completed", extracted_text="Test Person")
    return rid


def _add_analysis(db, rid, score, year):
    db.add(ResumeAnalysis(
        resume_id=uuid.UUID(rid), score=score, summary="s", detailed_result={"x": 1},
        rubric_version="rubric-v1", prompt_version="analysis-v1", model_name="m",
        created_at=datetime(year, 1, 1, tzinfo=timezone.utc),
    ))
    db.commit()


def test_analysis_needs_completed_extraction(client, alice):
    rid = upload(client, alice, pdf_bytes()).json()["resume_id"]
    assert client.post(f"{API}/resumes/{rid}/analyze", headers=alice).status_code == 409


def test_analyze_queues_one_job_and_blocks_a_second(client, alice, db, queued):
    rid = _completed(client, alice, db)
    response = client.post(f"{API}/resumes/{rid}/analyze", headers=alice)
    assert response.status_code == 202 and response.json()["analysis_status"] == "queued"
    assert len(queued["analysis"]) == 1
    assert client.post(f"{API}/resumes/{rid}/analyze", headers=alice).status_code == 409
    assert db.scalar(select(ProcessingJob).where(ProcessingJob.job_type == "analysis")).status == "queued"


def test_no_analysis_is_404_then_newest_is_returned(client, alice, db):
    rid = _completed(client, alice, db)
    assert client.get(f"{API}/resumes/{rid}/analysis", headers=alice).status_code == 404
    _add_analysis(db, rid, 50, 2025)
    _add_analysis(db, rid, 80, 2026)
    assert client.get(f"{API}/resumes/{rid}/analysis", headers=alice).json()["score"] == 80


def test_a_failed_rerun_keeps_the_previous_result(client, alice, db):
    rid = _completed(client, alice, db)
    _add_analysis(db, rid, 70, 2026)
    set_fields(db, rid, analysis_status="failed")
    body = client.get(f"{API}/resumes/{rid}/analysis", headers=alice).json()
    assert body["score"] == 70 and body["analysis_status"] == "failed"


def test_other_users_cannot_read_or_run_analysis(client, alice, bob, db):
    rid = _completed(client, alice, db)
    _add_analysis(db, rid, 70, 2026)
    assert client.get(f"{API}/resumes/{rid}/analysis", headers=bob).status_code == 404
    assert client.post(f"{API}/resumes/{rid}/analyze", headers=bob).status_code == 404


def test_admin_cannot_read_or_run_analysis(client, alice, carol, db):
    rid = _completed(client, alice, db)
    assert client.get(f"{API}/resumes/{rid}/analysis", headers=carol).status_code == 403
    assert client.post(f"{API}/resumes/{rid}/analyze", headers=carol).status_code == 403