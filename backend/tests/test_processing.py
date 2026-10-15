from app.ai.llm import LlmError
from app.models import ProcessingJob, Resume
from app.services.processing import PARTIAL_NOTE, process_extraction
from app.services.storage import get_storage
from tests.helpers import make_resume, pdf_bytes
from tests.test_candidate_extraction import FakeLlm
from tests.test_extraction import LONG_LINE, make_pdf
from tests.test_ocr_fallback import FakeOcr

GOOD_LLM = {"full_name": "Test Person", "location": "", "skills": ["Python"]}


class CountingStorage:
    def __init__(self):
        self.inner, self.reads = get_storage(), 0

    def read(self, key):
        self.reads += 1
        return self.inner.read(key)


def test_successful_extraction_fills_the_record(db):
    rid, jid = make_resume(db, make_pdf(LONG_LINE))
    outcome = process_extraction(db, jid, get_storage(), FakeOcr(), FakeLlm(GOOD_LLM))
    assert outcome.status == "completed"
    db.expire_all()
    resume, job = db.get(Resume, rid), db.get(ProcessingJob, jid)
    assert resume.extraction_status == "completed" and resume.extraction_method == "native_text"
    assert resume.candidate_name == "Test Person" and resume.email == "test@example.com"
    assert resume.skills == ["Python"] and resume.error_message is None
    assert job.status == "completed" and job.attempt_count == 1


def test_duplicate_delivery_is_ignored(db):
    rid, jid = make_resume(db, make_pdf(LONG_LINE))
    llm = FakeLlm(GOOD_LLM)
    assert process_extraction(db, jid, get_storage(), FakeOcr(), llm).status == "completed"
    assert process_extraction(db, jid, get_storage(), FakeOcr(), llm).status == "skipped"
    db.expire_all()
    assert db.get(ProcessingJob, jid).attempt_count == 1


def test_unreadable_file_fails_permanently_with_a_safe_message(db):
    rid, jid = make_resume(db, pdf_bytes())  # looks like a PDF but is not a real one
    outcome = process_extraction(db, jid, get_storage(), FakeOcr(), FakeLlm(GOOD_LLM))
    assert outcome.status == "failed"
    db.expire_all()
    resume = db.get(Resume, rid)
    assert resume.extraction_status == "failed" and resume.error_message == "The PDF could not be read"
    assert db.get(ProcessingJob, jid).attempt_count == 1  # no pointless retries


def test_model_failure_retries_then_completes_partially_without_redoing_extraction(db):
    rid, jid = make_resume(db, make_pdf(LONG_LINE))
    storage, llm = CountingStorage(), FakeLlm(LlmError("down"))
    statuses = [process_extraction(db, jid, storage, FakeOcr(), llm).status for _ in range(3)]
    assert statuses == ["retry", "retry", "completed"]
    db.expire_all()
    resume = db.get(Resume, rid)
    assert resume.extraction_status == "completed" and resume.error_message == PARTIAL_NOTE
    assert resume.email == "test@example.com" and resume.candidate_name is None
    assert db.get(ProcessingJob, jid).attempt_count == 3
    assert storage.reads == 1  # the saved text was reused on every retry


def test_deleted_resume_is_skipped(db):
    rid, jid = make_resume(db, make_pdf(LONG_LINE))
    db.delete(db.get(Resume, rid))
    db.commit()
    assert process_extraction(db, jid, get_storage(), FakeOcr(), FakeLlm(GOOD_LLM)).status == "skipped"


def test_one_failing_resume_does_not_affect_another(db):
    _, bad_job = make_resume(db, pdf_bytes())
    good_id, good_job = make_resume(db, make_pdf(LONG_LINE))
    llm = FakeLlm(GOOD_LLM)
    assert process_extraction(db, bad_job, get_storage(), FakeOcr(), llm).status == "failed"
    assert process_extraction(db, good_job, get_storage(), FakeOcr(), llm).status == "completed"