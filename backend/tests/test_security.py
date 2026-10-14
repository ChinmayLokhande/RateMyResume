import pytest
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.testclient import TestClient

from app.auth.security import CurrentUser
from app.core import cache
from app.core import rate_limit as rate_limit_module
from app.core.middleware import BodySizeLimitMiddleware, SecurityHeadersMiddleware
from app.core.rate_limit import rate_limit


def make_app(upload_limit=1000, default_limit=10) -> FastAPI:
    app = FastAPI()
    app.add_middleware(
        BodySizeLimitMiddleware, upload_limit=upload_limit, default_limit=default_limit
    )
    app.add_middleware(SecurityHeadersMiddleware)

    @app.post("/echo")
    async def echo(request: Request):
        return {"size": len(await request.body())}

    @app.post("/api/v1/resumes")
    async def upload(request: Request):
        return {"size": len(await request.body())}

    @app.get("/plain")
    def plain():
        return {"ok": True}

    @app.get("/cached")
    def cached():
        return Response("x", headers={"Cache-Control": "max-age=60"})

    return app


def test_body_within_limit_passes():
    assert TestClient(make_app()).post("/echo", content=b"x" * 5).status_code == 200


def test_declared_oversize_body_is_rejected():
    response = TestClient(make_app()).post("/echo", content=b"x" * 100)
    assert response.status_code == 413
    assert response.json() == {"detail": "Request body too large"}


def test_streamed_oversize_body_is_rejected():
    chunks = (
        b"x" * 10 for _ in range(10)
    )  # no Content-Length, so it is sent in chunks
    assert TestClient(make_app()).post("/echo", content=chunks).status_code == 413


def test_upload_paths_get_the_larger_limit():
    client = TestClient(make_app(upload_limit=1000, default_limit=10))
    assert client.post("/api/v1/resumes", content=b"x" * 100).status_code == 200
    assert client.post("/echo", content=b"x" * 100).status_code == 413


def test_security_headers_are_added():
    headers = TestClient(make_app()).get("/plain").headers
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["x-frame-options"] == "DENY"
    assert headers["referrer-policy"] == "no-referrer"
    assert headers["cache-control"] == "no-store"


def test_existing_headers_are_not_overridden():
    assert (
        TestClient(make_app()).get("/cached").headers["cache-control"] == "max-age=60"
    )


class FakeRedis:
    def __init__(self):
        self.counts: dict[str, int] = {}
        self.ttls: dict[str, int] = {}

    def incr(self, key):
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]

    def ttl(self, key):
        return self.ttls.get(key, -1)

    def expire(self, key, seconds):
        self.ttls[key] = seconds


class BrokenRedis:
    def incr(self, key):
        raise cache.redis.exceptions.ConnectionError("down")


USER_A = CurrentUser(
    sub="user-a",
    username=None,
    email=None,
    display_name=None,
    roles=frozenset({"user"}),
)
USER_B = CurrentUser(
    sub="user-b",
    username=None,
    email=None,
    display_name=None,
    roles=frozenset({"user"}),
)


def test_rate_limit_counts_and_sets_expiry(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(cache, "_client", lambda: fake)
    assert cache.rate_limit_hit("k", 60) == (1, 60)
    assert cache.rate_limit_hit("k", 60)[0] == 2


def test_rate_limit_blocks_after_the_limit(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(cache, "_client", lambda: fake)
    check = rate_limit("test", 2, 60)
    check(USER_A)
    check(USER_A)
    with pytest.raises(HTTPException) as error:
        check(USER_A)
    assert error.value.status_code == 429
    assert int(error.value.headers["Retry-After"]) >= 1


def test_rate_limit_is_per_user(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(cache, "_client", lambda: fake)
    check = rate_limit("test", 1, 60)
    check(USER_A)
    with pytest.raises(HTTPException):
        check(USER_A)  # user A is now over the limit
    check(USER_B)  # user B has their own counter and is still allowed


def test_rate_limit_can_be_disabled(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(cache, "_client", lambda: fake)

    class Disabled:
        rate_limit_enabled = False

    monkeypatch.setattr(rate_limit_module, "get_settings", lambda: Disabled())
    check = rate_limit("test", 1, 60)
    for _ in range(5):
        check(USER_A)
    assert fake.counts == {}  # nothing was counted at all


def test_rate_limit_is_per_user(monkeypatch):
    monkeypatch.setattr(cache, "_client", lambda: FakeRedis())
    check = rate_limit("test", 1, 60)
    check(USER_A)
    check(USER_B)  # a different user has their own counter


def test_rate_limit_fails_open_when_redis_is_down(monkeypatch):
    monkeypatch.setattr(cache, "_client", lambda: BrokenRedis())
    check = rate_limit("test", 1, 60)
    for _ in range(5):
        check(USER_A)


def test_rate_limit_can_be_disabled(monkeypatch):
    monkeypatch.setattr(cache, "_client", lambda: FakeRedis())

    class Disabled:
        rate_limit_enabled = False

    monkeypatch.setattr(rate_limit_module, "get_settings", lambda: Disabled())
    check = rate_limit("test", 1, 60)
    for _ in range(5):
        check(USER_A)
