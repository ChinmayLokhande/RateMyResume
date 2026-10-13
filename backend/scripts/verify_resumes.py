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


tokens = {name: token(name) for name in ("testuser", "testuser2", "testadmin")}
H = {name: {"Authorization": f"Bearer {t}"} for name, t in tokens.items()}
client = httpx.Client(base_url=API, timeout=30)
failures = 0


def check(label: str, ok: bool, extra: str = "") -> None:
    global failures
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  {label} {extra}")


def get(path: str, who: str | None = "testuser", **params) -> httpx.Response:
    return client.get(path, params=params, headers=H.get(who, {}))


def wait_failed(resume_id: str, timeout: int = 60) -> str:
    deadline = time.time() + timeout
    while time.time() < deadline:
        state = get(f"/resumes/{resume_id}/status").json()["extraction_status"]
        if state in ("completed", "failed"):
            return state
        time.sleep(2)
    return "timeout"


# Listing
listing = get("/resumes")
body = listing.json()
check("list", listing.status_code == 200 and body["total"] >= 1, f"total={body['total']}")
check("list hides extracted_text", all("extracted_text" not in i for i in body["items"]))
check("pagination", get("/resumes", page_size=1).json()["items"].__len__() == 1)
check("search no match", get("/resumes", q="zzzz-no-match").json()["total"] == 0)
check("search treats % literally", get("/resumes", q="%").json()["total"] == 0)
done = get("/resumes", status="completed").json()
check("status filter", all(i["extraction_status"] == "completed" for i in done["items"]), f"n={done['total']}")
asc = [i["uploaded_at"] for i in get("/resumes", sort="uploaded_at", direction="asc").json()["items"]]
check("sort ascending", asc == sorted(asc))
check("bad sort rejected", get("/resumes", sort="password").status_code == 422)
check("page_size cap", get("/resumes", page_size=1000).status_code == 422)

# Detail and access control
first = body["items"][0]["id"]
detail = get(f"/resumes/{first}")
check("detail", detail.status_code == 200 and "extracted_text" in detail.json())
check("other user: list empty", get("/resumes", "testuser2").json()["total"] == 0)
for label, response in (
    ("other user: detail", get(f"/resumes/{first}", "testuser2")),
    ("other user: status", get(f"/resumes/{first}/status", "testuser2")),
    ("other user: retry", client.post(f"/resumes/{first}/retry", headers=H["testuser2"])),
    ("other user: delete", client.delete(f"/resumes/{first}", headers=H["testuser2"])),
):
    check(label + " -> 404", response.status_code == 404)
check("admin list -> 403", get("/resumes", "testadmin").status_code == 403)
check("admin detail -> 403", get(f"/resumes/{first}", "testadmin").status_code == 403)
check("no token -> 401", get("/resumes", None).status_code == 401)
check("unknown id -> 404", get(f"/resumes/{uuid.uuid4()}").status_code == 404)
if done["items"]:
    retry = client.post(f"/resumes/{done['items'][0]['id']}/retry", headers=H["testuser"])
    check("retry on completed -> 409", retry.status_code == 409)

# Lifecycle: upload junk -> fails -> retry -> fails -> delete
junk = b"%PDF-1.4\n% fixture " + uuid.uuid4().hex.encode() + b"\n%%EOF"
upload = client.post("/resumes", files={"file": ("junk.pdf", junk)}, headers=H["testuser"])
check("upload junk", upload.status_code == 202)
rid = upload.json()["resume_id"]
state = wait_failed(rid)
check("junk ends failed", state == "failed", f"(got {state})")
if state == "failed":
    check("retry failed -> 202", client.post(f"/resumes/{rid}/retry", headers=H["testuser"]).status_code == 202)
    check("junk fails again", wait_failed(rid) == "failed")
check("delete -> 204", client.delete(f"/resumes/{rid}", headers=H["testuser"]).status_code == 204)
check("deleted -> 404", get(f"/resumes/{rid}").status_code == 404)
print(f"\n{failures} failure(s)")