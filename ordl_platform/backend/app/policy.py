from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
import secrets

import jwt
from fastapi import HTTPException, status

from app.config import Settings


def hash_request(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass
class PolicyTokenPayload:
    request_hash: str
    destination_scope: str
    decision: str
    policy_version: str
    nonce: str
    exp: int


def issue_policy_token(
    *,
    request_hash_value: str,
    destination_scope: str,
    decision: str,
    policy_version: str,
    settings: Settings,
    ttl_seconds: int | None = None,
) -> tuple[str, str]:
    ttl = ttl_seconds or settings.policy_token_ttl_seconds
    now = datetime.now(timezone.utc)
    nonce = secrets.token_hex(16)
    payload = {
        "request_hash": request_hash_value,
        "destination_scope": destination_scope,
        "decision": decision,
        "policy_version": policy_version,
        "nonce": nonce,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=ttl)).timestamp()),
    }
    token = jwt.encode(payload, settings.policy_secret, algorithm="HS256")
    return token, nonce


def decode_policy_token(token: str, settings: Settings) -> PolicyTokenPayload:
    try:
        payload = jwt.decode(token, settings.policy_secret, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="invalid policy token") from exc

    return PolicyTokenPayload(
        request_hash=str(payload.get("request_hash", "")),
        destination_scope=str(payload.get("destination_scope", "")),
        decision=str(payload.get("decision", "")),
        policy_version=str(payload.get("policy_version", "")),
        nonce=str(payload.get("nonce", "")),
        exp=int(payload.get("exp", 0)),
    )


def validate_policy_token(
    *,
    token: str,
    expected_request_hash: str,
    expected_destination_scope: str,
    settings: Settings,
) -> PolicyTokenPayload:
    payload = decode_policy_token(token, settings)
    if payload.decision != "allow":
        raise HTTPException(status_code=403, detail="policy decision is not allow")
    if payload.request_hash != expected_request_hash:
        raise HTTPException(status_code=403, detail="policy token request hash mismatch")
    if payload.destination_scope != expected_destination_scope:
        raise HTTPException(status_code=403, detail="policy token destination mismatch")
    return payload

