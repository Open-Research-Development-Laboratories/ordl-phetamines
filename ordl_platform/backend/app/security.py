from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache
import json

import jwt
from jwt import PyJWKClient
from fastapi import Depends, Header, HTTPException, status

from app.config import Settings, get_settings


@dataclass
class Principal:
    user_id: str
    tenant_id: str
    roles: list[str]
    clearance_tier: str
    compartments: list[str]


def _claim_get(payload: dict, claim_path: str, default=None):
    if not claim_path:
        return default
    current = payload
    for token in claim_path.split("."):
        if isinstance(current, dict) and token in current:
            current = current[token]
            continue
        return default
    return current


@lru_cache(maxsize=8)
def _jwks_client(jwks_url: str) -> PyJWKClient:
    return PyJWKClient(jwks_url)


def create_access_token(
    user_id: str,
    tenant_id: str,
    roles: list[str],
    clearance_tier: str,
    compartments: list[str],
    settings: Settings,
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "roles": roles,
        "clearance_tier": clearance_tier,
        "compartments": compartments,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=settings.access_token_ttl_seconds)).timestamp()),
    }
    return jwt.encode(payload, settings.auth_secret, algorithm="HS256")


def _decode_local_access_token(token: str, settings: Settings) -> Principal:
    try:
        payload = jwt.decode(token, settings.auth_secret, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token") from exc

    return Principal(
        user_id=str(payload.get("sub", "")),
        tenant_id=str(payload.get("tenant_id", "")),
        roles=list(payload.get("roles", [])),
        clearance_tier=str(payload.get("clearance_tier", "internal")),
        compartments=list(payload.get("compartments", [])),
    )


def _decode_oidc_access_token(token: str, settings: Settings) -> Principal:
    if not settings.oidc_enabled:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="oidc disabled")
    if not settings.oidc_jwks_url:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="oidc jwks url not configured")

    try:
        signing_key = _jwks_client(settings.oidc_jwks_url).get_signing_key_from_jwt(token)
        options = {
            "verify_aud": bool(settings.oidc_audience),
            "verify_iss": bool(settings.oidc_issuer),
        }
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256", "ES256", "PS256"],
            audience=settings.oidc_audience if settings.oidc_audience else None,
            issuer=settings.oidc_issuer if settings.oidc_issuer else None,
            options=options,
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid oidc token") from exc

    roles_claim = _claim_get(payload, settings.oidc_roles_claim, [])
    if isinstance(roles_claim, str):
        roles = [roles_claim]
    elif isinstance(roles_claim, list):
        roles = [str(x) for x in roles_claim]
    else:
        roles = []

    compartments_claim = _claim_get(payload, settings.oidc_compartments_claim, [])
    if isinstance(compartments_claim, str):
        compartments = [compartments_claim]
    elif isinstance(compartments_claim, list):
        compartments = [str(x) for x in compartments_claim]
    else:
        compartments = []

    tenant_id = str(_claim_get(payload, settings.oidc_tenant_claim, "") or "")
    if not tenant_id:
        tenant_id = settings.oidc_issuer or "oidc-tenant"

    user_id = str(_claim_get(payload, settings.oidc_subject_claim, "") or "")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid oidc subject claim")

    clearance_tier = str(_claim_get(payload, settings.oidc_clearance_claim, "internal"))
    return Principal(
        user_id=user_id,
        tenant_id=tenant_id,
        roles=roles,
        clearance_tier=clearance_tier,
        compartments=compartments,
    )


def decode_access_token(token: str, settings: Settings) -> Principal:
    # OIDC-first path for production federation, fallback to local issuer when enabled.
    if settings.oidc_enabled:
        try:
            return _decode_oidc_access_token(token, settings)
        except HTTPException as oidc_exc:
            if settings.oidc_required or not settings.allow_local_token_issuer:
                raise oidc_exc
            return _decode_local_access_token(token, settings)
    return _decode_local_access_token(token, settings)


def _decode_principal_from_header(
    authorization: str | None = Header(default=None),
    x_principal_json: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> Principal | None:
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        return decode_access_token(token, settings)

    if x_principal_json:
        try:
            payload = json.loads(x_principal_json)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=401, detail="invalid principal header") from exc
        return Principal(
            user_id=str(payload.get("user_id", "")),
            tenant_id=str(payload.get("tenant_id", "")),
            roles=list(payload.get("roles", [])),
            clearance_tier=str(payload.get("clearance_tier", "internal")),
            compartments=list(payload.get("compartments", [])),
        )
    return None


def get_optional_principal(
    principal: Principal | None = Depends(_decode_principal_from_header),
) -> Principal | None:
    return principal


def get_current_principal(
    principal: Principal | None = Depends(get_optional_principal),
    settings: Settings = Depends(get_settings),
) -> Principal:
    if principal is not None:
        return principal

    if settings.oidc_required:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="oidc token required")
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing authentication")
