import uuid

from sqlalchemy import func, select

from app.models import UserProfile

API = "/api/v1"


def test_missing_token_is_401(client):
    assert client.get(f"{API}/resumes").status_code == 401
    assert client.get(f"{API}/me").status_code == 401


def test_admin_cannot_use_resume_endpoints(client, carol):
    rid = uuid.uuid4()
    for path in ("/resumes", "/dashboard/stats", f"/resumes/{rid}", f"/resumes/{rid}/analysis"):
        assert client.get(f"{API}{path}", headers=carol).status_code == 403, path
    assert client.post(f"{API}/resumes/{rid}/analyze", headers=carol).status_code == 403


def test_user_cannot_use_admin_endpoints(client, alice):
    assert client.get(f"{API}/admin/users", headers=alice).status_code == 403
    body = {"username": "new-user", "email": "n@example.com", "first_name": "N", "last_name": "U",
            "role": "user", "temporary_password": "a-long-temp-password"}
    assert client.post(f"{API}/admin/users", json=body, headers=alice).status_code == 403


def test_me_creates_the_profile_only_once(client, alice, db):
    for _ in range(2):
        response = client.get(f"{API}/me", headers=alice)
        assert response.status_code == 200 and response.json()["roles"] == ["user"]
    assert db.scalar(select(func.count()).select_from(UserProfile)) == 1


def test_me_reports_the_admin_role(client, carol):
    assert client.get(f"{API}/me", headers=carol).json()["roles"] == ["admin"]