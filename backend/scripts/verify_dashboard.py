import getpass

import httpx

TOKEN_URL = "http://localhost:8080/realms/ratemyresume/protocol/openid-connect/token"
API = "http://localhost:8000/api/v1"


def token(username: str) -> str:
    response = httpx.post(
        TOKEN_URL,
        data={"grant_type": "password", "client_id": "ratemyresume-frontend",
              "username": username, "password": getpass.getpass(f"Password for {username}: ")},
    )
    response.raise_for_status()
    return response.json()["access_token"]


H = {name: {"Authorization": f"Bearer {token(name)}"} for name in ("testuser", "testuser2", "testadmin")}
client = httpx.Client(base_url=API, timeout=30)
failures = 0


def check(label: str, ok: bool, extra: str = "") -> None:
    global failures
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  {label} {extra}")


def count(status: str | None = None) -> int:
    params = {"page_size": 1}
    if status:
        params["status"] = status
    return client.get("/resumes", params=params, headers=H["testuser"]).json()["total"]


stats = client.get("/dashboard/stats", headers=H["testuser"])
check("stats -> 200", stats.status_code == 200)
body = stats.json()
print(f"      total={body['total']} completed={body['completed']} "
      f"in_progress={body['in_progress']} failed={body['failed']} recent={len(body['recent'])}")
check("total matches the list", body["total"] == count())
check("completed matches", body["completed"] == count("completed"))
check("failed matches", body["failed"] == count("failed"))
check("in progress matches", body["in_progress"] == count("queued") + count("processing"))
check("parts add up", body["completed"] + body["in_progress"] + body["failed"] == body["total"])
check("recent is capped at 5", len(body["recent"]) <= 5)
dates = [r["uploaded_at"] for r in body["recent"]]
check("recent is newest first", dates == sorted(dates, reverse=True))
check("recent hides extracted text", all("extracted_text" not in r for r in body["recent"]))
other = client.get("/dashboard/stats", headers=H["testuser2"]).json()
check("other user sees only their own", other["total"] == 0 and other["recent"] == [])
check("admin -> 403", client.get("/dashboard/stats", headers=H["testadmin"]).status_code == 403)
check("no token -> 401", client.get("/dashboard/stats").status_code == 401)
print(f"\n{failures} failure(s)")