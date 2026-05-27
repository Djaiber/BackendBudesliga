"""Cognito token validators.

AcceptAnyTokenValidator: dev bypass — always returns a fixed identity.
CognitoValidator: validates JWTs against a real Cognito user pool using JWKS.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import jwt
import requests
from jwt.algorithms import RSAAlgorithm

from src.infrastructure.cognito.exceptions import InvalidTokenError

logger = logging.getLogger(__name__)

_JWKS_CACHE_TTL_SECONDS = 3600


class AcceptAnyTokenValidator:
    """Dev-mode validator that accepts any token without verification.

    Only used when ACCEPT_ANY_TOKEN=true in InfraConfig. Never in production.
    """

    async def validate(self, token: str) -> dict[str, Any]:
        logger.warning("AcceptAnyTokenValidator: bypassing token validation (dev mode)")
        return {"sub": "dev-user", "email": "dev@local"}


class CognitoValidator:
    """Validates Cognito JWTs against a real user pool via JWKS.

    Fetches public keys from the Cognito JWKS endpoint and caches them for
    _JWKS_CACHE_TTL_SECONDS (1 hour) to avoid repeated network calls.
    """

    def __init__(
        self,
        user_pool_id: str,
        app_client_id: str,
        region: str,
    ) -> None:
        self._user_pool_id = user_pool_id
        self._app_client_id = app_client_id
        self._region = region
        self._jwks_url = (
            f"https://cognito-idp.{region}.amazonaws.com"
            f"/{user_pool_id}/.well-known/jwks.json"
        )
        self._issuer = (
            f"https://cognito-idp.{region}.amazonaws.com/{user_pool_id}"
        )
        self._jwks_cache: dict[str, Any] | None = None
        self._jwks_fetched_at: float = 0.0

    def _fetch_jwks(self) -> dict[str, Any]:
        now = time.monotonic()
        if self._jwks_cache and (now - self._jwks_fetched_at) < _JWKS_CACHE_TTL_SECONDS:
            return self._jwks_cache
        try:
            response = requests.get(self._jwks_url, timeout=5)
            response.raise_for_status()
            self._jwks_cache = response.json()
            self._jwks_fetched_at = now
            logger.info("JWKS refreshed from %s", self._jwks_url)
            return self._jwks_cache
        except Exception as exc:
            raise InvalidTokenError(f"Failed to fetch JWKS: {exc}") from exc

    def _get_public_key(self, kid: str) -> Any:
        jwks = self._fetch_jwks()
        for key_data in jwks.get("keys", []):
            if key_data.get("kid") == kid:
                return RSAAlgorithm.from_jwk(key_data)
        raise InvalidTokenError(f"Public key not found for kid={kid!r}")

    async def validate(self, token: str) -> dict[str, Any]:
        try:
            unverified_header = jwt.get_unverified_header(token)
        except jwt.DecodeError as exc:
            raise InvalidTokenError(f"Malformed token header: {exc}") from exc

        kid = unverified_header.get("kid")
        if not kid:
            raise InvalidTokenError("Token header missing 'kid'")

        public_key = self._get_public_key(kid)

        try:
            payload: dict[str, Any] = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                audience=self._app_client_id,
                issuer=self._issuer,
            )
        except jwt.ExpiredSignatureError as exc:
            raise InvalidTokenError("Token has expired") from exc
        except jwt.InvalidAudienceError as exc:
            raise InvalidTokenError("Token audience mismatch") from exc
        except jwt.InvalidIssuerError as exc:
            raise InvalidTokenError("Token issuer mismatch") from exc
        except jwt.PyJWTError as exc:
            raise InvalidTokenError(f"Token validation failed: {exc}") from exc

        if "sub" not in payload:
            raise InvalidTokenError("Token missing 'sub' claim")

        return payload
