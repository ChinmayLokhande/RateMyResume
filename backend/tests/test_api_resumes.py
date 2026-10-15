import uuid

from sqlalchemy import func, select

from app.core.config import get_settings
from app.models import ProcessingJob, Resume
from tests.helpers import docx_bytes, pdf_bytes, set_fields, upload

API = "/api/v1"


def test_upload_pdf_creates_record_job_and_stored_file(client, alice, db, queued):
    response = upload(client, alice, pdf_bytes(), "my resume.pdf")
    assert response.status_code == 202 and response.json()["status"] == "accepted"
    resume = db.scalar(select(Resume))
    job = db.scalar(select(ProcessingJob))
    assert resume.extraction_status == "queued" and resume.mime_type == "application/pdf"
    assert job.job_type == "extraction" and queued["extraction"] == [job.id]
    stored = get_settings().storage_dir / resume.storage_key
    assert stored.is_file() and "my resume" not in resume.storage_key


def test_upload_docx_is_accepted(client, alice, db):
    assert upload(client, alice, docx_bytes(), "cv.docx").status_code == 202
    assert db.scalar(select(Resume.mime_type)).endswith("wordprocessingml.document")


def test_hostile_filename_is_sanitized(client, alice, db):
    response = upload(client, alice, pdf_bytes(), "../../etc/passwd.pdf")
    assert response.status_code == 202 and response.json()["filename"] == "passwd.pdf"
    key = db.scalar(select(Resume.storage_key))
    assert ".." not in key and "passwd" not in key


def test_text_file_named_pdf_is_rejected(client, alice):
    assert upload(client, alice, b"hello world", "fake.pdf").status_code == 415


def test_empty_file_is_rejected(client, alice):
    assert upload(client, alice, b"", "empty.pdf").status_code == 400


def test_oversize_file_is_rejected(client, alice):
    assert upload(client, alice, b"%PDF-" + b"0" * (10 * 1024 * 1024), "big.pdf").status_code == 413


def test_duplicate_upload_is_a_409_pointing_at_the_original(client, alice, db):
    data = pdf_bytes()
    first = upload(client, alice, data).json()["resume_id"]
    second = upload(client, alice, data)
    assert second.status_code == 409
    assert second.json()["detail"]["existing_resume_id"] == first
    assert db.scalar(select(func.count()).select_from(Resume)) == 1


def test_same_file_from_another_user_is_allowed(client, alice, bob):
    data = pdf_bytes()
    assert upload(client, alice, data).status_code == 202
    assert upload(client, bob, data).status_code == 202


def test_bulk_upload_reports_each_file(client, alice, queued):
    dup = pdf_bytes()
    upload(client, alice, dup)
    response = client.post(
        f"{API}/resumes/bulk",
        files=[("files", ("new.pdf", pdf_bytes(), "application/pdf")),
               ("files", ("dup.pdf", dup, "application/pdf")),
               ("files", ("bad.txt", b"nope", "text/plain"))],
        headers=alice,
    )
    body = response.json()
    assert response.status_code == 202
    assert [r["status"] for r in body["results"]] == ["accepted", "duplicate", "rejected"]
    assert body["accepted"] == 1 and body["rejected"] == 2
    assert len(queued["extraction"]) == 2  # the first single upload plus the one accepted file


def test_bulk_upload_limits_the_file_count(client, alice):
    files = [("files", (f"f{i}.pdf", pdf_bytes(), "application/pdf")) for i in range(21)]
    assert client.post(f"{API}/resumes/bulk", files=files, headers=alice).status_code == 400


def test_upload_needs_the_user_role_and_a_token(client, carol):
    assert upload(client, carol, pdf_bytes()).status_code == 403
    assert client.post(f"{API}/resumes", files={"file": ("a.pdf", pdf_bytes())}).status_code == 401


def test_each_user_only_lists_their_own_resumes(client, alice, bob):
    upload(client, alice, pdf_bytes())
    upload(client, alice, pdf_bytes())
    upload(client, bob, pdf_bytes())
    assert client.get(f"{API}/resumes", headers=alice).json()["total"] == 2
    assert client.get(f"{API}/resumes", headers=bob).json()["total"] == 1


def _three(client, alice, db):
    ids = [upload(client, alice, pdf_bytes(), f"r{i}.pdf").json()["resume_id"] for i in range(3)]
    set_fields(db, ids[0], candidate_name="Ada Lovelace", email="ada@example.com",
               extraction_status="completed")
    set_fields(db, ids[1], candidate_name="Grace Hopper", email="grace@example.com",
               extraction_status="failed")
    return ids


def test_search_and_status_filter(client, alice, db):
    _three(client, alice, db)

    def total(**params):
        return client.get(f"{API}/resumes", params=params, headers=alice).json()["total"]

    assert total(q="LOVELACE") == 1
    assert total(q="grace@") == 1
    assert total(q="%") == 0 and total(q="_") == 0  # wildcards are matched literally
    assert total(status="failed") == 1 and total(status="completed") == 1


def test_sorting_and_pagination(client, alice, db):
    _three(client, alice, db)
    items = client.get(f"{API}/resumes", params={"sort": "candidate_name", "direction": "asc"},
                       headers=alice).json()["items"]
    assert [i["candidate_name"] for i in items] == ["Ada Lovelace", "Grace Hopper", None]
    page1 = client.get(f"{API}/resumes", params={"page_size": 2}, headers=alice).json()
    page2 = client.get(f"{API}/resumes", params={"page_size": 2, "page": 2}, headers=alice).json()
    assert page1["total_pages"] == 2 and len(page1["items"]) == 2 and len(page2["items"]) == 1
    assert all("extracted_text" not in item for item in page1["items"])


def test_list_validation_rejects_bad_parameters(client, alice):
    for params in ({"sort": "password"}, {"page_size": 1000}, {"page": 0}, {"status": "bogus"}):
        assert client.get(f"{API}/resumes", params=params, headers=alice).status_code == 422, params


def test_another_users_resume_is_invisible_and_untouched(client, alice, bob, db):
    rid = upload(client, alice, pdf_bytes()).json()["resume_id"]
    for method, path in (("GET", ""), ("GET", "/status"), ("POST", "/retry"), ("DELETE", "")):
        assert client.request(method, f"{API}/resumes/{rid}{path}", headers=bob).status_code == 404
    assert client.get(f"{API}/resumes/{rid}", headers=alice).status_code == 200


def test_unknown_and_malformed_ids(client, alice):
    assert client.get(f"{API}/resumes/{uuid.uuid4()}", headers=alice).status_code == 404
    assert client.get(f"{API}/resumes/not-a-uuid", headers=alice).status_code == 422


def test_retry_only_works_on_failed_resumes(client, alice, db, queued):
    rid = upload(client, alice, pdf_bytes()).json()["resume_id"]
    assert client.post(f"{API}/resumes/{rid}/retry", headers=alice).status_code == 409
    set_fields(db, rid, extraction_status="failed", error_message="boom")
    response = client.post(f"{API}/resumes/{rid}/retry", headers=alice)
    assert response.status_code == 202 and response.json()["extraction_status"] == "queued"
    assert response.json()["error_message"] is None
    assert db.scalar(select(func.count()).select_from(ProcessingJob)) == 2
    assert len(queued["extraction"]) == 2


def test_delete_removes_row_jobs_and_file(client, alice, db):
    rid = upload(client, alice, pdf_bytes()).json()["resume_id"]
    path = get_settings().storage_dir / db.scalar(select(Resume.storage_key))
    assert path.exists()
    assert client.delete(f"{API}/resumes/{rid}", headers=alice).status_code == 204
    db.expire_all()
    assert db.scalar(select(func.count()).select_from(Resume)) == 0
    assert db.scalar(select(func.count()).select_from(ProcessingJob)) == 0
    assert not path.exists()
    assert client.get(f"{API}/resumes/{rid}", headers=alice).status_code == 404


def test_dashboard_counts_are_per_user(client, alice, bob, carol, db):
    ids = [upload(client, alice, pdf_bytes()).json()["resume_id"] for _ in range(3)]
    set_fields(db, ids[0], extraction_status="completed")
    set_fields(db, ids[1], extraction_status="failed")
    stats = client.get(f"{API}/dashboard/stats", headers=alice).json()
    assert (stats["total"], stats["completed"], stats["failed"], stats["in_progress"]) == (3, 1, 1, 1)
    assert len(stats["recent"]) == 3
    assert client.get(f"{API}/dashboard/stats", headers=bob).json()["total"] == 0
    assert client.get(f"{API}/dashboard/stats", headers=carol).status_code == 403