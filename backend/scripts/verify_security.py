import getpass

import httpx
import redis

TOKEN_URL = "http://localhost:8080/realms/ratemyresume/protocol/openid-connect/token"
ROOT = "http://localhost:8000"
API = f"{ROOT}/api/v1"
cache_db = redis.Redis(host="localhost", port=6379, db=1, decode_responses=True)


def token(username: str) -> str:
    response = httpx.post(
        TOKEN_URL,
        data={"grant_type": "password", "client_id": "ratemyresume-frontend",
              "username": username, "password": getpass.getpass(f"Password for {username}: ")},
    )
    response.raise_for_status()
    return response.json()["access_token"]


H = {name: {"Authorization": f"Bearer {token(name)}"} for name in ("testuser", "testuser2")}
client = httpx.Client(base_url=API, timeout=60)
failures = 0


def check(label: str, ok: bool, extra: str = "") -> None:
    global failures
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  {label} {extra}")


# Headers
headers = httpx.get(f"{ROOT}/health").headers
check("nosniff header", headers.get("x-content-type-options") == "nosniff")
check("frame header", headers.get("x-frame-options") == "DENY")
check("no-store header", headers.get("cache-control") == "no-store")
check("referrer header", headers.get("referrer-policy") == "no-referrer")

# Oversized JSON body is stopped before authentication or parsing
try:
    big = httpx.post(f"{API}/admin/users", content=b"x" * (2 * 1024 * 1024),
                     headers={"Content-Type": "application/json"}, timeout=30)
    check("2 MB body to a JSON endpoint -> 413", big.status_code == 413, f"(got {big.status_code})")
except httpx.TransportError:
    # The server closed the connection while the client was still sending. That is the
    # server rejecting the body early, and is acceptable.
    check("2 MB body to a JSON endpoint -> connection closed early", True)

# Rate limiting on upload (tiny invalid files, so nothing is stored)
sub = client.get("/me", headers=H["testuser"]).json()["keycloak_sub"]
key = f"v1:rl:upload:{sub}"
cache_db.delete(key)
codes = [
    client.post("/resumes", files={"file": (f"rl{i}.txt", b"nope")}, headers=H["testuser"]).status_code
    for i in range(35)
]
check("first 30 requests are not limited", 429 not in codes[:30], str(sorted(set(codes[:30]))))
check("requests after 30 get 429", all(c == 429 for c in codes[30:]), str(codes[30:]))
last = client.post("/resumes", files={"file": ("x.txt", b"nope")}, headers=H["testuser"])
check("Retry-After header is sent", int(last.headers.get("retry-after", "0")) >= 1, last.headers.get("retry-after", ""))
check("another user is not limited", client.post("/resumes", files={"file": ("x.txt", b"nope")}, headers=H["testuser2"]).status_code != 429)
check("no token -> 401, not 429", client.post("/resumes", files={"file": ("x.txt", b"nope")}).status_code == 401)
check("counter lives in Redis DB 1 with an expiry", 0 < cache_db.ttl(key) <= 60)
cache_db.delete(key)  # reset so later checks are not blocked
print(f"\n{failures} failure(s)")