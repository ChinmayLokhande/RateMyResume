import os
import shutil
import tempfile
from pathlib import Path

# These must be set BEFORE any app module is imported: point everything at throwaway resources.
os.environ["POSTGRES_DB"] = "ratemyresume_test"
os.environ["CACHE_ENABLED"] = "false"
os.environ["LLM_ENABLED"] = "false"
os.environ["STORAGE_DIR"] = tempfile.mkdtemp(prefix="rmr-test-storage-")

import pytest  # noqa: E402
from fastapi import HTTPException, Request  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app import models  # noqa: E402,F401  (registers the tables)
from app.auth.security import CurrentUser, get_current_user  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.main import app as fastapi_app  # noqa: E402

assert get_settings().postgres_db.endswith("_test"), "Refusing to run against a non-test database"

USERS = {
    "alice": CurrentUser("sub-alice", "alice", "alice@example.com", "Alice", frozenset({"user"})),
    "bob": CurrentUser("sub-bob", "bob", "bob@example.com", "Bob", frozenset({"user"})),
    "carol": CurrentUser("sub-carol", "carol", "carol@example.com", "Carol", frozenset({"admin"})),
}


def _fake_current_user(request: Request) -> CurrentUser:
    name = request.headers.get("x-test-user")
    if name not in USERS:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return USERS[name]


@pytest.fixture(scope="session")
def _database():
    try:
        engine.connect().close()
    except Exception:
        pytest.exit("Create the test database first: createdb -O ratemyresume_user ratemyresume_test")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    engine.dispose()


@pytest.fixture
def clean_db(_database):
    yield
    with engine.begin() as connection:
        connection.execute(
            text("TRUNCATE resume_analyses, processing_jobs, resumes, user_profiles CASCADE")
        )
    for child in Path(os.environ["STORAGE_DIR"]).iterdir():
        shutil.rmtree(child) if child.is_dir() else child.unlink()


@pytest.fixture
def db(clean_db):
    with SessionLocal() as session:
        yield session


@pytest.fixture
def queued(monkeypatch):
    """Records background jobs instead of sending them to Celery."""
    calls = {"extraction": [], "analysis": []}
    monkeypatch.setattr(
        "app.api.v1.resume.enqueue_extraction", lambda job_id: calls["extraction"].append(job_id) or True
    )
    monkeypatch.setattr(
        "app.api.v1.analysis.enqueue_analysis", lambda job_id: calls["analysis"].append(job_id) or True
    )
    return calls


@pytest.fixture
def client(clean_db, queued):
    fastapi_app.dependency_overrides[get_current_user] = _fake_current_user
    with TestClient(fastapi_app) as test_client:
        yield test_client
    fastapi_app.dependency_overrides.clear()


@pytest.fixture
def alice():
    return {"x-test-user": "alice"}


@pytest.fixture
def bob():
    return {"x-test-user": "bob"}


@pytest.fixture
def carol():
    return {"x-test-user": "carol"}