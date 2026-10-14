import uuid

import redis

from app.core import cache


class FakeRedis:
    def __init__(self):
        self.data: dict[str, str] = {}
        self.ttls: dict[str, int | None] = {}

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value, ex=None):
        self.data[key] = value
        self.ttls[key] = ex

    def delete(self, *keys):
        for key in keys:
            self.data.pop(key, None)


class BrokenRedis:
    def get(self, key):
        raise redis.exceptions.ConnectionError("down")

    def set(self, key, value, ex=None):
        raise redis.exceptions.ConnectionError("down")

    def delete(self, *keys):
        raise redis.exceptions.ConnectionError("down")


def test_roundtrip_and_delete(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(cache, "_client", lambda: fake)
    cache.cache_set("k", {"total": 3}, 30)
    assert cache.cache_get("k") == {"total": 3}
    cache.cache_delete("k")
    assert cache.cache_get("k") is None


def test_ttl_is_applied(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(cache, "_client", lambda: fake)
    cache.cache_set("k", {"a": 1}, 45)
    assert fake.ttls["k"] == 45


def test_keys_are_scoped_to_the_owner():
    owner_a, owner_b, resume = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    assert cache.dashboard_key(owner_a) != cache.dashboard_key(owner_b)
    assert cache.analysis_key(owner_a, resume) != cache.analysis_key(owner_b, resume)
    assert str(owner_a) in cache.analysis_key(owner_a, resume)


def test_redis_outage_never_raises(monkeypatch):
    monkeypatch.setattr(cache, "_client", lambda: BrokenRedis())
    assert cache.cache_get("k") is None
    cache.cache_set("k", {"a": 1}, 30)
    cache.cache_delete("k")


def test_disabled_cache_is_a_no_op(monkeypatch):
    monkeypatch.setattr(cache, "_client", lambda: None)
    assert cache.cache_get("k") is None
    cache.cache_set("k", {"a": 1}, 30)
    cache.cache_delete("k")