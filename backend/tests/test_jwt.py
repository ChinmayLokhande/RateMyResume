import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.auth import security
from app.core.config import get_settings

KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
OTHER_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


class FakeJwks:
    def __init__(self, key=None, error=None):
        self._key, self._error = key, error

    def get_signing_key_from_jwt(self, token):
        if self._error:
            raise self._error

        class SigningKey:
            key = self._key.public_key()

        return SigningKey()


@pytest.fixture(autouse=True)
def _jwks(monkeypatch):
    monkeypatch.setattr(security, "_jwks_client", lambda: FakeJwks(KEY))


def claims(**overrides):
    s = get_settings()
    base = {"sub": "user-1", "iss": s.keycloak_issuer, "aud": s.keycloak_api_audience,
            "exp": int(time.time()) + 300, "preferred_username": "alice",
            "realm_access": {"roles": ["user"]}}
    base.update(overrides)
    return base


def call(token):
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token) if token else None
    return security.get_current_user(credentials)


def expect_401(token):
    with pytest.raises(HTTPException) as error:
        call(token)
    assert error.value.status_code == 401


def test_valid_token_is_accepted():
    user = call(jwt.encode(claims(), KEY, algorithm="RS256"))
    assert user.sub == "user-1" and user.roles == frozenset({"user"})


def test_expired_token_is_rejected():
    expect_401(jwt.encode(claims(exp=int(time.time()) - 10), KEY, algorithm="RS256"))


def test_wrong_audience_is_rejected():
    expect_401(jwt.encode(claims(aud="account"), KEY, algorithm="RS256"))


def test_wrong_issuer_is_rejected():
    expect_401(jwt.encode(claims(iss="http://evil.example/realms/x"), KEY, algorithm="RS256"))


def test_token_signed_with_another_key_is_rejected():
    expect_401(jwt.encode(claims(), OTHER_KEY, algorithm="RS256"))


def test_token_without_expiry_is_rejected():
    payload = claims()
    del payload["exp"]
    expect_401(jwt.encode(payload, KEY, algorithm="RS256"))


def test_symmetric_algorithm_tokens_are_rejected():
    expect_401(jwt.encode(claims(), "x" * 40, algorithm="HS256"))


def test_garbage_token_is_rejected():
    expect_401("not-a-token")


def test_missing_credentials_are_rejected():
    expect_401(None)


def test_unreachable_key_server_gives_503(monkeypatch):
    error = jwt.PyJWKClientConnectionError("down")
    monkeypatch.setattr(security, "_jwks_client", lambda: FakeJwks(error=error))
    with pytest.raises(HTTPException) as caught:
        call(jwt.encode(claims(), KEY, algorithm="RS256"))
    assert caught.value.status_code == 503


def test_token_without_roles_has_none():
    assert call(jwt.encode(claims(realm_access={}), KEY, algorithm="RS256")).roles == frozenset()