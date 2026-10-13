import getpass
import sys
from pathlib import Path

import httpx

TOKEN_URL = "http://localhost:8080/realms/ratemyresume/protocol/openid-connect/token"
path = Path(sys.argv[1])
if not path.is_file():
    raise SystemExit(f"File not found: {path}")
token = httpx.post(
    TOKEN_URL,
    data={"grant_type": "password", "client_id": "ratemyresume-frontend",
          "username": "testuser", "password": getpass.getpass("Password for testuser: ")},
).raise_for_status().json()["access_token"]
response = httpx.post(
    "http://localhost:8000/api/v1/resumes",
    files={"file": (path.name, path.read_bytes(), "application/octet-stream")},
    headers={"Authorization": f"Bearer {token}"},
    timeout=60,
)
print(response.status_code, response.json())