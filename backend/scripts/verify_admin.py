import getpass
import secrets

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


H = {name: {"Authorization": f"Bearer {token(name)}"} for name in ("testadmin", "testuser")}
client = httpx.Client(base_url=API, timeout=30)
failures = 0


def check(label: str, ok: bool, extra: str = "") -> None:
    global failures
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  {label} {extra}")


suffix = secrets.token_hex(3)
payload = {
    "username": f"smoke-{suffix}", "email": f"smoke-{suffix}@example.com",
    "first_name": "Smoke", "last_name": "Test", "role": "user",
    "temporary_password": secrets.token_urlsafe(18),
}

listing = client.get("/admin/users", headers=H["testadmin"])
check("admin lists users", listing.status_code == 200, f"total={listing.json().get('total')}")
names = {u["username"]: u["roles"] for u in listing.json().get("items", [])}
check("roles are shown", names.get("testadmin") == ["admin"] and names.get("testuser") == ["user"])
check("search works", client.get("/admin/users", params={"q": "testadmin"}, headers=H["testadmin"]).json()["total"] >= 1)
check("regular user -> 403", client.get("/admin/users", headers=H["testuser"]).status_code == 403)
check("no token -> 401", client.get("/admin/users").status_code == 401)
check("regular user create -> 403", client.post("/admin/users", json=payload, headers=H["testuser"]).status_code == 403)

created = client.post("/admin/users", json=payload, headers=H["testadmin"])
check("create user -> 201", created.status_code == 201, str(created.json().get("roles")))
check("password not in response", payload["temporary_password"] not in created.text)
check("duplicate -> 409", client.post("/admin/users", json=payload, headers=H["testadmin"]).status_code == 409)
check("short password -> 422", client.post("/admin/users", json=dict(payload, username="x-" + suffix, temporary_password="short"), headers=H["testadmin"]).status_code == 422)
check("bad email -> 422", client.post("/admin/users", json=dict(payload, email="nope"), headers=H["testadmin"]).status_code == 422)
check("bad role -> 422", client.post("/admin/users", json=dict(payload, role="owner"), headers=H["testadmin"]).status_code == 422)
check("bad username -> 422", client.post("/admin/users", json=dict(payload, username="a b!"), headers=H["testadmin"]).status_code == 422)
check("new user appears in list", client.get("/admin/users", params={"q": payload["username"]}, headers=H["testadmin"]).json()["total"] == 1)

# Admins must not reach resume content
check("admin cannot list resumes -> 403", client.get("/resumes", headers=H["testadmin"]).status_code == 403)
print(f"\n{failures} failure(s). Delete the user '{payload['username']}' in the Keycloak console to clean up.")