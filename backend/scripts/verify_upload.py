import getpass
import io
import uuid
import zipfile

import httpx

TOKEN_URL = "http://localhost:8080/realms/ratemyresume/protocol/openid-connect/token"
API = "http://localhost:8000/api/v1"
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def get_token(username: str) -> str:
    password = getpass.getpass(f"Password for {username}: ")
    response = httpx.post(
        TOKEN_URL,
        data={"grant_type": "password", "client_id": "ratemyresume-frontend",
              "username": username, "password": password},
    )
    response.raise_for_status()
    return response.json()["access_token"]


def make_pdf() -> bytes:
    return b"%PDF-1.4\n% fixture " + uuid.uuid4().hex.encode() + b"\n%%EOF"


def make_docx() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", f"<doc>{uuid.uuid4().hex}</doc>")
    return buffer.getvalue()


user = {"Authorization": f"Bearer {get_token('testuser')}"}
admin = {"Authorization": f"Bearer {get_token('testadmin')}"}
client = httpx.Client(base_url=API, timeout=30)
failures = 0


def check(label: str, got: int, expected: int, extra: str = "") -> None:
    global failures
    ok = got == expected
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  {label}: got {got}, expected {expected} {extra}")


def single(name: str, data: bytes, headers=user) -> httpx.Response:
    return client.post("/resumes", files={"file": (name, data, "application/octet-stream")}, headers=headers)


pdf = make_pdf()
check("valid PDF", single("a.pdf", pdf).status_code, 202)
check("same PDF again (duplicate)", single("a.pdf", pdf).status_code, 409)
check("valid DOCX", single("b.docx", make_docx()).status_code, 202)
check("text file named .pdf", single("fake.pdf", b"hello world").status_code, 415)
check("empty file", single("empty.pdf", b"").status_code, 400)
check("oversize (11 MB)", single("big.pdf", b"%PDF-" + b"0" * (11 * 1024 * 1024)).status_code, 413)
check("admin upload", single("c.pdf", make_pdf(), admin).status_code, 403)
check("no token", client.post("/resumes", files={"file": ("d.pdf", make_pdf())}).status_code, 401)

bulk = client.post(
    "/resumes/bulk",
    files=[("files", ("new.pdf", make_pdf(), "application/pdf")),
           ("files", ("dup.pdf", pdf, "application/pdf")),
           ("files", ("bad.txt", b"nope", "text/plain"))],
    headers=user,
)
statuses = [r["status"] for r in bulk.json().get("results", [])]
check("bulk: mixed batch", bulk.status_code, 202, str(statuses))
print("PASS" if statuses == ["accepted", "duplicate", "rejected"] else "FAIL", " bulk statuses are per-file")

too_many = [("files", (f"f{i}.pdf", b"%PDF-" + str(i).encode(), "application/pdf")) for i in range(21)]
check("bulk: 21 files", client.post("/resumes/bulk", files=too_many, headers=user).status_code, 400)
print(f"\n{failures} failure(s)")