"""OIDC authorization-code/PKCE configuration and bounded server-side exchange."""

import json
import os
import urllib.parse
import urllib.request
from functools import lru_cache

from fastapi import HTTPException
from pydantic import Field

from substrata.platform.connectors import NoRedirect, read_json
from substrata.platform.domain import Contract


class CodeExchange(Contract):
    code: str = Field(min_length=1, max_length=4096)
    verifier: str = Field(pattern=r"^[A-Za-z0-9._~-]{43,128}$")
    redirect_uri: str = Field(min_length=1, max_length=2048)


@lru_cache(maxsize=1)
def login_config():
    development = os.environ.get("SUBSTRATA_ENV", "development") == "development"
    issuer = os.environ.get("SUBSTRATA_OIDC_ISSUER", "")
    client_id = os.environ.get("SUBSTRATA_OIDC_CLIENT_ID")
    if not client_id:
        return {"enabled": False, "development": development}
    if not issuer.startswith("https://"):
        raise ValueError("Interactive OIDC login requires an HTTPS issuer.")
    discovery = read_json(issuer.rstrip("/") + "/.well-known/openid-configuration")
    if discovery.get("issuer") != issuer:
        raise ValueError("OIDC discovery issuer does not match configured issuer.")
    for field in ("authorization_endpoint", "token_endpoint"):
        endpoint = discovery.get(field, "")
        if not endpoint.startswith("https://"):
            raise ValueError("OIDC endpoints must use HTTPS.")
    return {
        "enabled": True,
        "development": development,
        "client_id": client_id,
        "authorization_endpoint": discovery["authorization_endpoint"],
        "token_endpoint": discovery["token_endpoint"],
        "scope": os.environ.get("SUBSTRATA_OIDC_SCOPE", "openid profile"),
        "redirect_uris": os.environ.get("SUBSTRATA_OIDC_REDIRECT_URIS", "").split(","),
    }


def exchange(body: CodeExchange, verifier):
    config = login_config()
    if not config["enabled"] or body.redirect_uri not in config["redirect_uris"]:
        raise HTTPException(400, "Login redirect URI is not configured.")
    data = urllib.parse.urlencode(
        {
            "grant_type": "authorization_code",
            "client_id": config["client_id"],
            "code": body.code,
            "code_verifier": body.verifier,
            "redirect_uri": body.redirect_uri,
        }
    ).encode()
    request = urllib.request.Request(
        config["token_endpoint"],
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.build_opener(NoRedirect()).open(request, timeout=10) as response:
            encoded = response.read(65537)
        if len(encoded) > 65536:
            raise ValueError("Token response is too large.")
        result = json.loads(encoded)
        token = result["access_token"]
        verifier.verify(token)
        return {"access_token": token, "token_type": "Bearer"}
    except (OSError, ValueError, KeyError, HTTPException):
        raise HTTPException(
            401, "Login could not be completed; check identity-provider configuration."
        ) from None
