"""Integration tests for CognitoValidator and AcceptAnyTokenValidator."""

from __future__ import annotations

import json
import time
from typing import Any
from unittest.mock import MagicMock, patch

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from src.infrastructure.cognito.cognito_validator import (
    AcceptAnyTokenValidator,
    CognitoValidator,
)
from src.infrastructure.cognito.exceptions import InvalidTokenError

pytestmark = pytest.mark.integration

# ---------------------------------------------------------------------------
# RSA key pair for signing test tokens
# ---------------------------------------------------------------------------

_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_PUBLIC_KEY = _PRIVATE_KEY.public_key()
_KID = "test-key-id-1"

_USER_POOL_ID = "eu-central-1_TestPool"
_APP_CLIENT_ID = "test-client-id"
_REGION = "eu-central-1"
_ISSUER = f"https://cognito-idp.{_REGION}.amazonaws.com/{_USER_POOL_ID}"


def _make_token(
    sub: str = "user-123",
    audience: str = _APP_CLIENT_ID,
    issuer: str = _ISSUER,
    exp_offset: int = 3600,
    kid: str = _KID,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    now = int(time.time())
    payload: dict[str, Any] = {
        "sub": sub,
        "aud": audience,
        "iss": issuer,
        "iat": now,
        "exp": now + exp_offset,
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(
        payload,
        _PRIVATE_KEY,
        algorithm="RS256",
        headers={"kid": kid},
    )


def _make_jwks() -> dict[str, Any]:
    pub_numbers = _PUBLIC_KEY.public_numbers()
    import base64

    def int_to_base64url(n: int) -> str:
        length = (n.bit_length() + 7) // 8
        return base64.urlsafe_b64encode(n.to_bytes(length, "big")).rstrip(b"=").decode()

    return {
        "keys": [
            {
                "kty": "RSA",
                "kid": _KID,
                "use": "sig",
                "alg": "RS256",
                "n": int_to_base64url(pub_numbers.n),
                "e": int_to_base64url(pub_numbers.e),
            }
        ]
    }


@pytest.fixture
def validator() -> CognitoValidator:
    return CognitoValidator(
        user_pool_id=_USER_POOL_ID,
        app_client_id=_APP_CLIENT_ID,
        region=_REGION,
    )


def _patch_jwks(validator: CognitoValidator) -> None:
    mock_resp = MagicMock()
    mock_resp.json.return_value = _make_jwks()
    mock_resp.raise_for_status = MagicMock()
    with patch("src.infrastructure.cognito.cognito_validator.requests.get", return_value=mock_resp):
        validator._fetch_jwks()


# ---------------------------------------------------------------------------
# AcceptAnyTokenValidator
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_accept_any_returns_dev_identity() -> None:
    v = AcceptAnyTokenValidator()
    result = await v.validate("any-token")
    assert result["sub"] == "dev-user"
    assert result["email"] == "dev@local"


@pytest.mark.asyncio
async def test_accept_any_ignores_token_content() -> None:
    v = AcceptAnyTokenValidator()
    result1 = await v.validate("token-a")
    result2 = await v.validate("token-b")
    assert result1 == result2


# ---------------------------------------------------------------------------
# CognitoValidator — valid token
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_valid_token(validator: CognitoValidator) -> None:
    token = _make_token()
    mock_resp = MagicMock()
    mock_resp.json.return_value = _make_jwks()
    mock_resp.raise_for_status = MagicMock()

    with patch("src.infrastructure.cognito.cognito_validator.requests.get", return_value=mock_resp):
        payload = await validator.validate(token)

    assert payload["sub"] == "user-123"
    assert payload["aud"] == _APP_CLIENT_ID


# ---------------------------------------------------------------------------
# CognitoValidator — expired token
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_expired_token_raises(validator: CognitoValidator) -> None:
    token = _make_token(exp_offset=-1)
    mock_resp = MagicMock()
    mock_resp.json.return_value = _make_jwks()
    mock_resp.raise_for_status = MagicMock()

    with patch("src.infrastructure.cognito.cognito_validator.requests.get", return_value=mock_resp):
        with pytest.raises(InvalidTokenError, match="expired"):
            await validator.validate(token)


# ---------------------------------------------------------------------------
# CognitoValidator — wrong audience
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_wrong_audience_raises(validator: CognitoValidator) -> None:
    token = _make_token(audience="wrong-client")
    mock_resp = MagicMock()
    mock_resp.json.return_value = _make_jwks()
    mock_resp.raise_for_status = MagicMock()

    with patch("src.infrastructure.cognito.cognito_validator.requests.get", return_value=mock_resp):
        with pytest.raises(InvalidTokenError, match="audience"):
            await validator.validate(token)


# ---------------------------------------------------------------------------
# CognitoValidator — wrong issuer
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_wrong_issuer_raises(validator: CognitoValidator) -> None:
    token = _make_token(issuer="https://evil.com/pool")
    mock_resp = MagicMock()
    mock_resp.json.return_value = _make_jwks()
    mock_resp.raise_for_status = MagicMock()

    with patch("src.infrastructure.cognito.cognito_validator.requests.get", return_value=mock_resp):
        with pytest.raises(InvalidTokenError, match="issuer"):
            await validator.validate(token)


# ---------------------------------------------------------------------------
# CognitoValidator — malformed token
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_malformed_token_raises(validator: CognitoValidator) -> None:
    with pytest.raises(InvalidTokenError):
        await validator.validate("not.a.valid.jwt.at.all")


# ---------------------------------------------------------------------------
# CognitoValidator — unknown kid
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_unknown_kid_raises(validator: CognitoValidator) -> None:
    token = _make_token(kid="unknown-kid")
    mock_resp = MagicMock()
    mock_resp.json.return_value = _make_jwks()
    mock_resp.raise_for_status = MagicMock()

    with patch("src.infrastructure.cognito.cognito_validator.requests.get", return_value=mock_resp):
        with pytest.raises(InvalidTokenError, match="kid"):
            await validator.validate(token)


# ---------------------------------------------------------------------------
# CognitoValidator — missing kid in header
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_token_without_kid_raises(validator: CognitoValidator) -> None:
    # Encode without kid header
    token = jwt.encode(
        {"sub": "x", "aud": _APP_CLIENT_ID, "iss": _ISSUER, "exp": int(time.time()) + 3600},
        _PRIVATE_KEY,
        algorithm="RS256",
    )
    with pytest.raises(InvalidTokenError, match="kid"):
        await validator.validate(token)


# ---------------------------------------------------------------------------
# CognitoValidator — JWKS fetch failure
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_raises_when_jwks_fetch_fails(validator: CognitoValidator) -> None:
    token = _make_token()
    with patch(
        "src.infrastructure.cognito.cognito_validator.requests.get",
        side_effect=Exception("network error"),
    ):
        with pytest.raises(InvalidTokenError, match="JWKS"):
            await validator.validate(token)


# ---------------------------------------------------------------------------
# CognitoValidator — JWKS cache reuse
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_jwks_cache_is_reused(validator: CognitoValidator) -> None:
    token = _make_token()
    mock_resp = MagicMock()
    mock_resp.json.return_value = _make_jwks()
    mock_resp.raise_for_status = MagicMock()

    with patch(
        "src.infrastructure.cognito.cognito_validator.requests.get",
        return_value=mock_resp,
    ) as mock_get:
        await validator.validate(token)
        await validator.validate(token)

    # JWKS fetched only once; second call used cache
    mock_get.assert_called_once()


# ---------------------------------------------------------------------------
# CognitoValidator — extra claims preserved
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_preserves_extra_claims(validator: CognitoValidator) -> None:
    token = _make_token(extra_claims={"email": "user@example.com", "custom:role": "admin"})
    mock_resp = MagicMock()
    mock_resp.json.return_value = _make_jwks()
    mock_resp.raise_for_status = MagicMock()

    with patch("src.infrastructure.cognito.cognito_validator.requests.get", return_value=mock_resp):
        payload = await validator.validate(token)

    assert payload["email"] == "user@example.com"
    assert payload["custom:role"] == "admin"
