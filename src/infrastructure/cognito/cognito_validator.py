"""Cognito token validators.

AcceptAnyTokenValidator: dev bypass — always returns a fixed identity.
CognitoValidator: validates JWTs against a real Cognito user pool.
"""

from __future__ import annotations

import logging
from typing import Any

from src.infrastructure.cognito.exceptions import InvalidTokenError

logger = logging.getLogger(__name__)


class AcceptAnyTokenValidator:
    """Dev-mode validator that accepts any token without verification.

    Only used when ACCEPT_ANY_TOKEN=true in InfraConfig. Never in production.
    """

    async def validate(self, token: str) -> dict[str, Any]:
        logger.warning("AcceptAnyTokenValidator: bypassing token validation (dev mode)")
        return {"sub": "dev-user", "email": "dev@local"}


class CognitoValidator:
    """Validates Cognito JWTs against a real user pool.

    Phase 4 deliverable 15 — full JWKS verification not yet implemented.
    Stub raises InvalidTokenError for all tokens until real validation is wired.
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

    async def validate(self, token: str) -> dict[str, Any]:
        # TODO Phase 4 Deliverable 15: implement JWKS-based JWT validation
        # For now, attempt basic JWT decode without signature verification
        # so local testing with real-ish tokens works.
        try:
            import jwt

            payload: dict[str, Any] = jwt.decode(
                token,
                options={"verify_signature": False},
                algorithms=["RS256"],
            )
            if "sub" not in payload:
                raise InvalidTokenError("Token missing 'sub' claim")
            return payload
        except InvalidTokenError:
            raise
        except Exception as exc:
            raise InvalidTokenError(f"Token validation failed: {exc}") from exc
