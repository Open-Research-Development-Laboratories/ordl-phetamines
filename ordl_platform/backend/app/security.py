from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json

import jwt
from fastapi import Depends, Header, HTTPException, status

from app.config import Settings, get_settings


@dataclass
class Principal:
    user_id: str
    tenant_id: str
    roles: list[str]
    clearance_tier: str
    compartments: list[str]


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


def decode_access_token(token: str, settings: Settings) -> Principal:
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


def get_current_principal(
    authorization: str | None = Header(default=None),
    x_principal_json: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> Principal:
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

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing authentication")

