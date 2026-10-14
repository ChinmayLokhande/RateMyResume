import getpass
import time
import uuid

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


def wait_for(rid: str, field: str, done: tuple[str, ...], timeout: int = 300) -> str:
    deadline = time.time() + timeout
    while time.time() < deadline:
        value = client.get(f"/resumes/{rid}/status", headers=H["testuser"]).json()[field]
        if value in done:
            return value
        time.sleep(3)
    return "timeout"


items = client.get("/resumes", params={"status": "completed"}, headers=H["testuser"]).json()["items"]
check("a completed resume exists", bool(items))
rid = items[0]["id"]

wait_for(rid, "analysis_status", ("not_started", "completed", "failed"))  # let any auto-run finish
check("analyze -> 202", client.post(f"/resumes/{rid}/analyze", headers=H["testuser"]).status_code == 202)
final = wait_for(rid, "analysis_status", ("completed", "failed"))
check("analysis completes", final == "completed", f"(got {final})")

response = client.get(f"/resumes/{rid}/analysis", headers=H["testuser"])
check("get analysis -> 200", response.status_code == 200)
if response.status_code == 200:
    body = response.json()
    detail = body["detailed_result"]
    criteria = detail["rubric"]["criteria"]
    check("score within 0-100", 0 <= body["score"] <= 100, f"score={body['score']}")
    check("score equals sum of criteria", body["score"] == sum(c["points"] for c in criteria))
    check("rubric version recorded", body["rubric_version"] == "rubric-v1")
    check("advisory notice present", bool(detail["advisory_notice"]))
    check("summary not empty", bool(body["summary"]))
    print("      model:", body["model_name"], "| prompt:", body["prompt_version"],
          "| narrative:", detail["narrative_available"])
    for c in criteria:
        print(f"      {c['label']}: {c['points']}/{c['max_points']}")
    print("      missing/unclear items:", len(detail["missing_or_unclear"]))
    if detail["narrative"]:
        n = detail["narrative"]
        print("      narrative lengths:", len(n["professional_summary"]),
              "chars; strengths:", len(n["strengths"]), "improvements:", len(n["improvements"]))

check("other user: analysis -> 404", client.get(f"/resumes/{rid}/analysis", headers=H["testuser2"]).status_code == 404)
check("other user: analyze -> 404", client.post(f"/resumes/{rid}/analyze", headers=H["testuser2"]).status_code == 404)
check("admin: analysis -> 403", client.get(f"/resumes/{rid}/analysis", headers=H["testadmin"]).status_code == 403)
check("admin: analyze -> 403", client.post(f"/resumes/{rid}/analyze", headers=H["testadmin"]).status_code == 403)
check("no token -> 401", client.get(f"/resumes/{rid}/analysis").status_code == 401)

junk = b"%PDF-1.4\n% fixture " + uuid.uuid4().hex.encode() + b"\n%%EOF"
jid = client.post("/resumes", files={"file": ("junk.pdf", junk)}, headers=H["testuser"]).json()["resume_id"]
check("junk extraction fails", wait_for(jid, "extraction_status", ("completed", "failed")) == "failed")
check("junk: no analysis yet -> 404", client.get(f"/resumes/{jid}/analysis", headers=H["testuser"]).status_code == 404)
check("junk: analyze -> 409", client.post(f"/resumes/{jid}/analyze", headers=H["testuser"]).status_code == 409)
client.delete(f"/resumes/{jid}", headers=H["testuser"])
print(f"\n{failures} failure(s)")