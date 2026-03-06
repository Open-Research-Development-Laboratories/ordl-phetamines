from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import verify_audit_chain
from app.common import ensure_project_scope, json_list
from app.db import get_db
from app.models import AuditEvent, PolicyDecision
from app.security import Principal, get_current_principal

router = APIRouter(prefix='/audit', tags=['audit'])


def _json_obj(value: str | None) -> dict:
    try:
        loaded = json.loads(value or '{}')
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


@router.get('')
def list_policy_decisions(
    project_id: str,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> list[dict]:
    ensure_project_scope(db, principal, project_id)
    rows = db.scalars(
        select(PolicyDecision)
        .where(PolicyDecision.project_id == project_id)
        .order_by(PolicyDecision.created_at.desc())
        .limit(200)
    ).all()
    return [
        {
            'id': row.id,
            'action': row.action,
            'resource_type': row.resource_type,
            'resource_id': row.resource_id,
            'decision': row.decision,
            'reason_codes': json_list(row.reason_codes_json),
            'request_hash': row.request_hash,
            'token_nonce': row.token_nonce,
            'created_at': row.created_at.isoformat(),
        }
        for row in rows
    ]


@router.get('/events')
def list_audit_events(
    project_id: str,
    limit: int = Query(default=200, ge=1, le=2000),
    actor_id: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> list[dict]:
    ensure_project_scope(db, principal, project_id)
    stmt = (
        select(AuditEvent)
        .where(AuditEvent.project_id == project_id)
        .order_by(AuditEvent.event_index.desc(), AuditEvent.created_at.desc())
        .limit(limit)
    )
    if actor_id:
        stmt = stmt.where(AuditEvent.actor_id == actor_id)
    if event_type:
        stmt = stmt.where(AuditEvent.event_type == event_type)

    rows = db.scalars(stmt).all()
    return [
        {
            'id': row.id,
            'event_index': row.event_index,
            'event_type': row.event_type,
            'actor_type': row.actor_type,
            'actor_id': row.actor_id,
            'actor_role': row.actor_role,
            'actor_rank': row.actor_rank,
            'actor_position': row.actor_position,
            'source': row.source,
            'classification': row.classification,
            'severity': row.severity,
            'trace_id': row.trace_id,
            'run_id': row.run_id,
            'session_id': row.session_id,
            'actor': _json_obj(row.actor_json),
            'payload': _json_obj(row.payload_json),
            'resource': _json_obj(row.resource_json),
            'context': _json_obj(row.context_json),
            'prev_hash': row.prev_hash,
            'event_hash': row.event_hash,
            'hash_version': row.hash_version,
            'hash_timestamp': row.hash_timestamp,
            'created_at': row.created_at.isoformat(),
        }
        for row in rows
    ]


@router.get('/verify')
def verify_project_audit(
    project_id: str,
    limit: int = Query(default=2000, ge=1, le=10000),
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> dict:
    ensure_project_scope(db, principal, project_id)
    return verify_audit_chain(
        db,
        tenant_id=principal.tenant_id,
        project_id=project_id,
        limit=limit,
    )
