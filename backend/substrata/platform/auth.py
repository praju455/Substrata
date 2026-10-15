"""Verified OIDC claims; development signing is explicitly restricted to local mode."""

import os
import threading
import time
from collections import OrderedDict
from pathlib import Path
from typing import Literal

import jwt
from fastapi import HTTPException, Request
from jwt import PyJWKClient
from pydantic import BaseModel, Field

from substrata.platform.domain import Identifier


class Principal(BaseModel):
    subject: str = Field(min_length=1, max_length=256)
    tenant_id: Identifier
    roles: set[Literal["viewer", "analyst", "approver", "admin"]]

    def require(self, role: str):
        allowed = {
            "viewer": {"viewer", "analyst", "approver", "admin"},
            "analyst": {"analyst", "admin"},
            "approver": {"approver", "admin"},
            "admin": {"admin"},
        }[role]
        if not self.roles & allowed:
            raise HTTPException(403, "Your role does not permit this operation.")


class TokenVerifier:
    def __init__(
        self,
        *,
        issuer: str,
        audience: str,
        key=None,
        jwks_url: str | None = None,
        algorithm: str = "RS256",
    ):
        if not issuer or not audience or algorithm not in {"RS256", "ES256", "EdDSA", "HS256"}:
            raise ValueError("Configure an issuer, audience and supported signing algorithm.")
        if jwks_url and (not jwks_url.startswith("https://") or algorithm == "HS256"):
            raise ValueError("OIDC key discovery requires HTTPS and asymmetric signing.")
        self.issuer, self.audience, self.key, self.algorithm = issuer, audience, key, algorithm
        self.jwks = PyJWKClient(jwks_url, timeout=5, cache_jwk_set=True) if jwks_url else None
        if key is None and self.jwks is None:
            raise ValueError("Configure a verification key or OIDC JWKS URL.")

    def verify(self, token: str) -> Principal:
        try:
            key = self.jwks.get_signing_key_from_jwt(token).key if self.jwks else self.key
            claims = jwt.decode(
                token,
                key,
                algorithms=[self.algorithm],
                issuer=self.issuer,
                audience=self.audience,
                leeway=15,
                options={
                    "require": ["exp", "iat", "nbf", "sub", "iss", "aud", "tenant_id", "roles"]
                },
            )
            return Principal(
                subject=claims["sub"], tenant_id=claims["tenant_id"], roles=claims["roles"]
            )
        except (jwt.PyJWTError, ValueError, TypeError, KeyError):
            raise HTTPException(
                401, "Access token is invalid or expired.", headers={"WWW-Authenticate": "Bearer"}
            ) from None


def configured_verifier():
    mode = os.environ.get("SUBSTRATA_ENV", "development")
    algorithm = os.environ.get("SUBSTRATA_AUTH_ALGORITHM", "RS256")
    key_file = os.environ.get("SUBSTRATA_AUTH_KEY_FILE")
    key = Path(key_file).read_text(encoding="utf-8").strip() if key_file else None
    if algorithm == "HS256":
        if mode != "development" or key is None or len(key.encode()) < 32:
            raise ValueError("HS256 is local development only and requires a 32-byte secret file.")
    elif mode != "development" and not os.environ.get("SUBSTRATA_OIDC_ISSUER", "").startswith(
        "https://"
    ):
        raise ValueError("Production requires an HTTPS OIDC issuer.")
    return TokenVerifier(
        issuer=os.environ.get("SUBSTRATA_OIDC_ISSUER", ""),
        audience=os.environ.get("SUBSTRATA_OIDC_AUDIENCE", "substrata"),
        algorithm=algorithm,
        key=key,
        jwks_url=os.environ.get("SUBSTRATA_OIDC_JWKS_URL"),
    )


class RateLimiter:
    """Bounded per-process guard; shared tenant job budgets add durable enforcement."""

    def __init__(self, limit: int = 120, window: float = 60, capacity: int = 10000):
        self.limit, self.window, self.capacity = limit, window, capacity
        self.entries = OrderedDict()
        self.lock = threading.Lock()

    def check(self, key: tuple):
        now = time.monotonic()
        with self.lock:
            start, count = self.entries.pop(key, (now, 0))
            if now - start >= self.window:
                start, count = now, 0
            self.entries[key] = (start, count + 1)
            while len(self.entries) > self.capacity:
                self.entries.popitem(last=False)
            if count >= self.limit:
                raise HTTPException(
                    429,
                    "Request budget exceeded; retry later.",
                    headers={"Retry-After": str(int(self.window))},
                )


def principal(request: Request) -> Principal:
    header = request.headers.get("authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token or len(token) > 16384:
        raise HTTPException(
            401, "A verified access token is required.", headers={"WWW-Authenticate": "Bearer"}
        )
    actor = request.app.state.auth_verifier.verify(token)
    request.app.state.platform_rate_limiter.check((actor.tenant_id, actor.subject))
    return actor


def public_request(request: Request) -> None:
    """Bound public credential work by transport peer and the fixed endpoint name.

    Caller-supplied forwarding headers, tokens and request bodies never form keys.
    The separate limiter leaves authenticated tenant budgets unchanged.
    """
    peer = request.client.host if request.client else "unknown"
    route = request.scope["route"]
    request.app.state.platform_public_rate_limiter.check((route.name, peer))
