import getpass
import time
import uuid

import httpx
import redis

TOKEN_URL = "http://localhost:8080/realms/ratemyresume/protocol/openid-connect/token"
API = "http://localhost:8000/api/v1"
cache_db = redis.Redis(host="localhost", port=6379, db=1, decode_responses=True)


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


def stats() -> dict:
    return client.get("/dashboard/stats", headers=H["testuser"]).json()


owner = client.get("/me", headers=H["testuser"]).json()["id"]
dash_key = f"v1:dashboard:{owner}"

# Dashboard counts
cache_db.delete(dash_key)
first = stats()
cached = cache_db.get(dash_key)
check("counts are cached after a read", cached is not None)
ttl = cache_db.ttl(dash_key)
check("TTL is set (<= 30 s)", 0 < ttl <= 30, f"ttl={ttl}")
import json
check("only counts are cached", set(json.loads(cached)) == {"total", "completed", "in_progress", "failed"})
check("no personal data in the cached value", "@" not in cached and "name" not in cached)
check("second read matches", stats()["total"] == first["total"])

# Invalidation on upload, worker completion and delete
junk = b"%PDF-1.4\n% cache fixture " + uuid.uuid4().hex.encode() + b"\n%%EOF"
upload = client.post("/resumes", files={"file": ("cache-test.pdf", junk)}, headers=H["testuser"])
check("upload", upload.status_code == 202)
rid = upload.json()["resume_id"]
check("total updates immediately after upload", stats()["total"] == first["total"] + 1)

state = "timeout"
deadline = time.time() + 90
while time.time() < deadline:
    state = client.get(f"/resumes/{rid}/status", headers=H["testuser"]).json()["extraction_status"]
    if state in ("completed", "failed"):
        break
    time.sleep(2)
check("junk file ends failed", state == "failed", f"(got {state})")
time.sleep(1.5)
check("failed count updates without waiting for the TTL", stats()["failed"] == first["failed"] + 1)

check("delete", client.delete(f"/resumes/{rid}", headers=H["testuser"]).status_code == 204)
check("total returns to the original after delete", stats()["total"] == first["total"])

# Analysis cache
listing = client.get("/resumes", params={"page_size": 100}, headers=H["testuser"]).json()["items"]
analyzed = [r for r in listing if r["analysis_status"] == "completed"]
if not analyzed:
    print("SKIP  no analyzed resume found; run an analysis in the UI and re-run this script")
else:
    rid = analyzed[0]["id"]
    a_key = f"v1:analysis:{owner}:{rid}"
    cache_db.delete(a_key)
    one = client.get(f"/resumes/{rid}/analysis", headers=H["testuser"])
    check("analysis -> 200", one.status_code == 200)
    check("analysis is cached", cache_db.get(a_key) is not None)
    ttl = cache_db.ttl(a_key)
    check("analysis TTL is set (<= 600 s)", 0 < ttl <= 600, f"ttl={ttl}")
    check("status is not cached", "analysis_status" not in json.loads(cache_db.get(a_key)))
    two = client.get(f"/resumes/{rid}/analysis", headers=H["testuser"])
    check("cached read is identical", two.json() == one.json())
    check("other user still gets 404", client.get(f"/resumes/{rid}/analysis", headers=H["testuser2"]).status_code == 404)
    check("admin still gets 403", client.get(f"/resumes/{rid}/analysis", headers=H["testadmin"]).status_code == 403)
    check("no token still 401", client.get(f"/resumes/{rid}/analysis").status_code == 401)

check("cache keys all live in Redis DB 1", len(redis.Redis(db=0).keys("v1:*")) == 0)
print(f"\n{failures} failure(s)")