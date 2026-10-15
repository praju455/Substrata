"""Asymmetric OIDC signature, audience and algorithm-confusion regression."""

from datetime import UTC, datetime, timedelta

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException

from substrata.platform.auth import TokenVerifier


def test_asymmetric_signature_and_algorithm_are_pinned():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    verifier = TokenVerifier(issuer="https://identity.example", audience="substrata", key=public)
    now = datetime.now(UTC)
    claims = {
        "iss": "https://identity.example",
        "aud": "substrata",
        "sub": "analyst",
        "tenant_id": "tenant-a",
        "roles": ["analyst"],
        "iat": now,
        "nbf": now,
        "exp": now + timedelta(minutes=5),
    }
    signed = jwt.encode(claims, key, algorithm="RS256")
    assert verifier.verify(signed).tenant_id == "tenant-a"
    for invalid in (
        jwt.encode(claims, "test-secret-with-at-least-32-bytes", algorithm="HS256"),
        jwt.encode({**claims, "aud": "wrong"}, key, algorithm="RS256"),
        jwt.encode({k: v for k, v in claims.items() if k != "exp"}, key, algorithm="RS256"),
    ):
        with pytest.raises(HTTPException) as exc:
            verifier.verify(invalid)
        assert exc.value.status_code == 401
