from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditEvent, SeatAssignment


def _canonical_json(value: dict[str, Any] | None) -> str:
    if not isinstance(value, dict):
        value = {}
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash_event_v2(
    *,
    prev_hash: str,
    event_index: int,
    event_type: str,
    actor_json: str,
    payload_json: str,
    resource_json: str,
    context_json: str,
    source: str,
    classification: str,
    severity: str,
    trace_id: str,
    run_id: str,
    session_id: str,
    hash_timestamp: str,
) -> str:
    seed = "|".join(
        [
            "v2",
            prev_hash,
            str(event_index),
            event_type,
            actor_json,
            payload_json,
            resource_json,
            context_json,
            source,
            classification,
            severity,
            trace_id,
            run_id,
            session_id,
            hash_timestamp,
        ]
    )
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def build_actor_snapshot(db: Session, principal: Any, project_id: str | None = None) -> dict[str, Any]:
    roles = [str(role) for role in getattr(principal, "roles", [])]
    actor: dict[str, Any] = {
        "actor_type": "user",
        "actor_id": str(getattr(principal, "user_id", "")),
        "tenant_id": str(getattr(principal, "tenant_id", "")),
        "roles": roles,
        "clearance_tier": str(getattr(principal, "clearance_tier", "")),
        "compartments": [str(x) for x in getattr(principal, "compartments", [])],
    }

    if project_id:
        seat = db.scalar(
            select(SeatAssignment)
            .where(
                SeatAssignment.project_id == project_id,
                SeatAssignment.user_id == actor["actor_id"],
                SeatAssignment.status == "active",
            )
            .order_by(SeatAssignment.created_at.desc())
            .limit(1)
        )
        if seat is not None:
            actor["seat"] = {
                "seat_id": seat.id,
                "role": seat.role,
                "rank": seat.rank,
                "position": seat.position,
                "group_name": seat.group_name,
            }

    return actor


def append_audit_event(
    db: Session,
    *,
    tenant_id: str,
    project_id: str,
    event_type: str,
    payload: dict[str, Any],
    actor: dict[str, Any] | None = None,
    resource: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
    source: str = "api",
    classification: str = "operational",
    severity: str = "info",
    trace_id: str = "",
    run_id: str = "",
    session_id: str = "",
) -> AuditEvent:
    latest = db.scalar(
        select(AuditEvent)
        .where(AuditEvent.tenant_id == tenant_id, AuditEvent.project_id == project_id)
        .order_by(AuditEvent.event_index.desc(), AuditEvent.created_at.desc())
        .limit(1)
    )
    prev_hash = latest.event_hash if latest else ""
    event_index = (latest.event_index + 1) if latest else 1
    created_at = datetime.now(timezone.utc)
    hash_timestamp = created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    actor_data = actor if isinstance(actor, dict) else {}
    resource_data = resource if isinstance(resource, dict) else {}
    context_data = context if isinstance(context, dict) else {}

    actor_json = _canonical_json(actor_data)
    payload_json = _canonical_json(payload)
    resource_json = _canonical_json(resource_data)
    context_json = _canonical_json(context_data)

    event_hash = _hash_event_v2(
        prev_hash=prev_hash,
        event_index=event_index,
        event_type=event_type,
        actor_json=actor_json,
        payload_json=payload_json,
        resource_json=resource_json,
        context_json=context_json,
        source=source,
        classification=classification,
        severity=severity,
        trace_id=trace_id,
        run_id=run_id,
        session_id=session_id,
        hash_timestamp=hash_timestamp,
    )

    seat = actor_data.get("seat", {}) if isinstance(actor_data.get("seat"), dict) else {}
    event = AuditEvent(
        tenant_id=tenant_id,
        project_id=project_id,
        event_index=event_index,
        event_type=event_type,
        actor_type=str(actor_data.get("actor_type", "")),
        actor_id=str(actor_data.get("actor_id", "")),
        actor_role=str(seat.get("role", "")),
        actor_rank=str(seat.get("rank", "")),
        actor_position=str(seat.get("position", "")),
        source=source,
        classification=classification,
        severity=severity,
        trace_id=trace_id,
        run_id=run_id,
        session_id=session_id,
        actor_json=actor_json,
        payload_json=payload_json,
        resource_json=resource_json,
        context_json=context_json,
        prev_hash=prev_hash,
        event_hash=event_hash,
        hash_version="v2",
        hash_timestamp=hash_timestamp,
        created_at=created_at,
    )
    db.add(event)
    db.flush()
    return event


def verify_audit_chain(
    db: Session,
    *,
    tenant_id: str,
    project_id: str,
    limit: int = 2000,
) -> dict[str, Any]:
    rows = db.scalars(
        select(AuditEvent)
        .where(AuditEvent.tenant_id == tenant_id, AuditEvent.project_id == project_id)
        .order_by(AuditEvent.event_index.asc(), AuditEvent.created_at.asc())
        .limit(max(1, min(limit, 10000)))
    ).all()

    prev_hash = ""
    failures: list[dict[str, Any]] = []
    verified = 0

    for row in rows:
        chain_ok = row.prev_hash == prev_hash
        hash_ok = False
        expected_hash = ""
        if row.hash_version == "v2":
            expected_hash = _hash_event_v2(
                prev_hash=row.prev_hash,
                event_index=row.event_index,
                event_type=row.event_type,
                actor_json=row.actor_json or "{}",
                payload_json=row.payload_json or "{}",
                resource_json=row.resource_json or "{}",
                context_json=row.context_json or "{}",
                source=row.source or "",
                classification=row.classification or "",
                severity=row.severity or "",
                trace_id=row.trace_id or "",
                run_id=row.run_id or "",
                session_id=row.session_id or "",
                hash_timestamp=row.hash_timestamp or row.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            )
            hash_ok = expected_hash == row.event_hash

        if not chain_ok or not hash_ok:
            failures.append(
                {
                    "event_id": row.id,
                    "event_index": row.event_index,
                    "event_type": row.event_type,
                    "chain_ok": chain_ok,
                    "hash_ok": hash_ok,
                    "expected_hash": expected_hash,
                    "actual_hash": row.event_hash,
                }
            )
        else:
            verified += 1
        prev_hash = row.event_hash

    return {
        "ok": len(failures) == 0,
        "project_id": project_id,
        "tenant_id": tenant_id,
        "events_examined": len(rows),
        "events_verified": verified,
        "failures": failures,
    }
