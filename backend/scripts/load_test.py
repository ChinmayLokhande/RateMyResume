"""Simulate N users logging in, uploading a resume at the same time, and timing the pipeline.

Per user it measures:  login -> upload -> text extraction -> analysis -> JD match
(extraction/analysis are measured from the moment the upload request is sent).

Run from anywhere (needs:  pip install httpx):
    python load_test.py --resume ./sample.pdf
"""
import argparse
import asyncio
import getpass
import json
import os
import statistics
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

import httpx

FINAL = {"completed", "failed"}


@dataclass
class UserRun:
    username: str
    login_s: float | None = None
    upload_s: float | None = None
    extraction_s: float | None = None  # upload sent -> extraction finished
    analysis_s: float | None = None    # upload sent -> analysis finished
    jd_match_s: float | None = None    # duration of the job-matches request
    score: int | None = None
    top_match: str | None = None
    resume_id: str | None = None
    error: str | None = None
    notes: list[str] = field(default_factory=list)
    http_errors: dict = field(default_factory=dict)  # status code -> count (retried)


def make_payload(path: Path, unique: bool) -> bytes:
    """Duplicate uploads are rejected per user, so make each upload byte-different (PDF only)."""
    data = path.read_bytes()
    if unique and path.suffix.lower() == ".pdf":
        data += f"\n%load-test-{uuid.uuid4()}\n".encode()  # trailing PDF comment; harmless
    return data


async def login(client: httpx.AsyncClient, args, username: str, password: str) -> str:
    r = await client.post(
        args.token_url,
        data={"grant_type": "password", "client_id": args.client_id,
              "username": username, "password": password},
    )
    r.raise_for_status()
    return r.json()["access_token"]


async def call(client, method, url, run, args, creds, **kw):
    """HTTP call that retries transient failures and records what the API returned.
    401 -> log in again; 429/502/503/504 -> wait and retry; anything else -> fail with the real message."""
    r = None
    for attempt in range(4):
        r = await client.request(method, url, headers={"Authorization": f"Bearer {creds['token']}"}, **kw)
        if r.status_code < 400:
            return r
        run.http_errors[str(r.status_code)] = run.http_errors.get(str(r.status_code), 0) + 1
        if r.status_code == 401:
            creds["token"] = await login(client, args, creds["username"], creds["password"])
        elif r.status_code not in (429, 502, 503, 504):
            break
        await asyncio.sleep(1 + attempt)
    raise RuntimeError(f"{method} {url.split('/api/v1')[-1]} -> HTTP {r.status_code}: {r.text[:150]}")


async def run_user(args, username: str, password: str, tokens: dict, start_gate: asyncio.Event,
                   path: Path) -> UserRun:
    run = UserRun(username)
    api = args.base_url.rstrip("/") + "/api/v1"
    creds = {"username": username, "password": password, "token": None}
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            # Step 1: login (before the gate, so all users are logged in first)
            t0 = time.perf_counter()
            creds["token"] = await login(client, args, username, password)
            run.login_s = time.perf_counter() - t0
            tokens[username] = creds["token"]

            await start_gate.wait()  # Step 2: everyone uploads at the same instant
            payload = make_payload(path, args.unique)
            t_upload = time.perf_counter()
            r = await call(client, "POST", f"{api}/resumes", run, args, creds,
                           files={"file": (path.name, payload, "application/octet-stream")})
            run.upload_s = time.perf_counter() - t_upload
            body = r.json()
            if body.get("status") != "accepted" or not body.get("resume_id"):
                raise RuntimeError(f"upload not accepted: {body.get('status')} {body.get('detail')}")
            run.resume_id = body["resume_id"]

            # Step 3: poll until extraction, then analysis, reach a final state
            deadline = t_upload + args.timeout
            ext_done = False
            while True:
                s = (await call(client, "GET", f"{api}/resumes/{run.resume_id}/status", run, args, creds)).json()
                now = time.perf_counter() - t_upload
                if not ext_done and s.get("extraction_status") in FINAL:
                    ext_done, run.extraction_s = True, now
                    if s["extraction_status"] == "failed":
                        raise RuntimeError(f"extraction failed: {s.get('error_message')}")
                if ext_done and s.get("analysis_status") in FINAL:
                    run.analysis_s = now
                    if s["analysis_status"] == "failed":
                        run.notes.append(f"analysis failed: {s.get('error_message')}")
                    break
                if time.perf_counter() > deadline:
                    raise TimeoutError(f"not finished after {args.timeout}s "
                                       f"(extraction={s.get('extraction_status')}, analysis={s.get('analysis_status')})")
                await asyncio.sleep(args.poll)

            # Step 4: score, then the JD match (calculated synchronously by the API)
            try:
                a = await call(client, "GET", f"{api}/resumes/{run.resume_id}/analysis", run, args, creds)
                run.score = a.json().get("score")
            except Exception as exc:
                run.notes.append(f"no score: {exc}")
            t_jd = time.perf_counter()
            m = await call(client, "POST", f"{api}/resumes/{run.resume_id}/job-matches", run, args, creds)
            run.jd_match_s = time.perf_counter() - t_jd
            results = m.json().get("results", [])
            if results:
                best = max(results, key=lambda x: x["fit_percentage"])
                run.top_match = f'{best["job_title"]} ({best["fit_percentage"]}%)'
    except Exception as exc:  # one user failing must not stop the others
        run.error = f"{type(exc).__name__}: {exc}"
    return run


async def health_monitor(args, samples: list, stop: asyncio.Event):
    """Step 5 (background): sample GET /health the whole time to see if the app stays responsive."""
    async with httpx.AsyncClient(timeout=10) as client:
        while not stop.is_set():
            t = time.perf_counter()
            try:
                r = await client.get(args.base_url.rstrip("/") + "/health")
                samples.append((r.status_code, time.perf_counter() - t))
            except Exception:
                samples.append((0, time.perf_counter() - t))
            try:
                await asyncio.wait_for(stop.wait(), timeout=2)
            except asyncio.TimeoutError:
                pass


def fmt(v):
    return "-" if v is None else f"{v:6.2f}s"


def summarize(runs: list[UserRun], health: list, wall: float):
    print("\n" + "=" * 100)
    print(f'{"user":<14}{"login":>8}{"upload":>9}{"extract":>10}{"analysis":>10}{"JD match":>10}  {"score":>5}  top match / error')
    print("-" * 100)
    for r in runs:
        tail = r.error or r.top_match or ""
        print(f"{r.username:<14}{fmt(r.login_s):>8}{fmt(r.upload_s):>9}{fmt(r.extraction_s):>10}"
              f'{fmt(r.analysis_s):>10}{fmt(r.jd_match_s):>10}  {str(r.score or "-"):>5}  {tail}')
    print("=" * 100)
    ok = [r for r in runs if not r.error]
    print(f"Succeeded: {len(ok)}/{len(runs)}   Total wall time: {wall:.1f}s")
    for label, attr in (("extraction", "extraction_s"), ("analysis", "analysis_s"), ("JD match", "jd_match_s")):
        vals = sorted(getattr(r, attr) for r in ok if getattr(r, attr) is not None)
        if vals:
            p95 = vals[min(len(vals) - 1, int(round(0.95 * (len(vals) - 1))))]
            print(f"  {label:<11} min {vals[0]:.2f}s  avg {statistics.mean(vals):.2f}s  "
                  f"max {vals[-1]:.2f}s  p95 {p95:.2f}s")
    if health:
        good = [d for c, d in health if c == 200]
        print(f"/health: {len(good)}/{len(health)} OK"
              + (f", slowest {max(good):.2f}s" if good else "") + " (sampled during the run)")
    errs = {}
    for r in runs:
        for k, v in r.http_errors.items():
            errs[k] = errs.get(k, 0) + v
    if errs:
        print(f"HTTP errors seen (retried automatically): {errs}   <- shows what the API was returning")
    print("Tip: if analysis times climb user by user, the worker is processing jobs one at a time (--pool=solo).")


async def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--resume", required=True, help="PDF or DOCX file to upload")
    p.add_argument("--users", type=int, default=5)
    p.add_argument("--prefix", default="loadtest", help="usernames are <prefix>1..<prefix>N")
    p.add_argument("--usernames", help="comma-separated list; overrides --prefix/--users")
    p.add_argument("--base-url", default="http://localhost:8000")
    p.add_argument("--token-url", default="http://localhost:8080/realms/ratemyresume/protocol/openid-connect/token")
    p.add_argument("--client-id", default="ratemyresume-frontend")
    p.add_argument("--poll", type=float, default=2.0, help="seconds between status checks")
    p.add_argument("--timeout", type=float, default=300, help="max seconds to wait per user")
    p.add_argument("--no-unique", dest="unique", action="store_false",
                   help="upload identical bytes (second runs will be rejected as duplicates)")
    p.add_argument("--out", help="also save results to this JSON file")
    args = p.parse_args()

    path = Path(args.resume)
    if not path.is_file():
        raise SystemExit(f"File not found: {path}")
    names = args.usernames.split(",") if args.usernames else [f"{args.prefix}{i}" for i in range(1, args.users + 1)]
    password = os.environ.get("LOAD_TEST_PASSWORD") or getpass.getpass("Password for the test users: ")

    # Step 0: is the app up at all?
    async with httpx.AsyncClient(timeout=10) as c:
        try:
            h = await c.get(args.base_url.rstrip("/") + "/health")
            print(f"/health before run: {h.status_code} {h.text[:120]}")
        except Exception as exc:
            raise SystemExit(f"Backend not reachable at {args.base_url}: {exc}")

    gate, stop, tokens, health = asyncio.Event(), asyncio.Event(), {}, []
    monitor = asyncio.create_task(health_monitor(args, health, stop))
    tasks = [asyncio.create_task(run_user(args, n, password, tokens, gate, path)) for n in names]

    # Release the gate only once every user has logged in (or failed to)
    while len(tokens) + sum(t.done() for t in tasks) < len(names):
        await asyncio.sleep(0.1)
    print(f"{len(tokens)}/{len(names)} users logged in. Uploading all at once...")
    t_start = time.perf_counter()
    gate.set()
    runs = await asyncio.gather(*tasks)
    wall = time.perf_counter() - t_start
    stop.set()
    await monitor

    summarize(runs, health, wall)
    if args.out:
        Path(args.out).write_text(json.dumps([asdict(r) for r in runs], indent=2))
        print(f"Saved {args.out}")


if __name__ == "__main__":
    asyncio.run(main())