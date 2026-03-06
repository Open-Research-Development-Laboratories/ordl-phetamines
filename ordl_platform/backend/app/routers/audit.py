from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from io import StringIO
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import verify_audit_chain
from app.common import ensure_project_scope, json_list
from app.db import get_db
from app.models import AuditEvent, PolicyDecision
from app.security import Principal, get_current_principal

router = APIRouter(prefix='/audit', tags=['audit'])


def _json_obj(value: str | None) -> dict[str, Any]:
    try:
        loaded = json.loads(value or '{}')
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _parse_time(value: str | None, field_name: str) -> datetime | None:
    if not value:
        return None
    normalized = value.strip().replace('Z', '+00:00')
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f'invalid {field_name} format') from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _event_row(row: AuditEvent) -> dict[str, Any]:
    return {
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


def _query_events(
    db: Session,
    *,
    project_id: str,
    limit: int,
    actor_id: str | None = None,
    event_type: str | None = None,
    trace_id: str | None = None,
    run_id: str | None = None,
    severity: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> list[AuditEvent]:
    stmt = select(AuditEvent).where(AuditEvent.project_id == project_id)
    if actor_id:
        stmt = stmt.where(AuditEvent.actor_id == actor_id)
    if event_type:
        stmt = stmt.where(AuditEvent.event_type == event_type)
    if trace_id:
        stmt = stmt.where(AuditEvent.trace_id == trace_id)
    if run_id:
        stmt = stmt.where(AuditEvent.run_id == run_id)
    if severity:
        stmt = stmt.where(AuditEvent.severity == severity)
    if start_time:
        stmt = stmt.where(AuditEvent.created_at >= start_time)
    if end_time:
        stmt = stmt.where(AuditEvent.created_at <= end_time)
    stmt = stmt.order_by(AuditEvent.event_index.desc(), AuditEvent.created_at.desc()).limit(limit)
    return db.scalars(stmt).all()


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
    trace_id: str | None = Query(default=None),
    run_id: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    start_time: str | None = Query(default=None),
    end_time: str | None = Query(default=None),
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> list[dict]:
    ensure_project_scope(db, principal, project_id)
    start_dt = _parse_time(start_time, 'start_time')
    end_dt = _parse_time(end_time, 'end_time')
    rows = _query_events(
        db,
        project_id=project_id,
        limit=limit,
        actor_id=actor_id,
        event_type=event_type,
        trace_id=trace_id,
        run_id=run_id,
        severity=severity,
        start_time=start_dt,
        end_time=end_dt,
    )
    return [_event_row(row) for row in rows]


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


@router.get('/export')
def export_audit(
    project_id: str,
    format: str = Query(default='json', pattern='^(json|csv)$'),
    limit: int = Query(default=2000, ge=1, le=10000),
    actor_id: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
    trace_id: str | None = Query(default=None),
    run_id: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    start_time: str | None = Query(default=None),
    end_time: str | None = Query(default=None),
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> Any:
    ensure_project_scope(db, principal, project_id)
    start_dt = _parse_time(start_time, 'start_time')
    end_dt = _parse_time(end_time, 'end_time')
    rows = _query_events(
        db,
        project_id=project_id,
        limit=limit,
        actor_id=actor_id,
        event_type=event_type,
        trace_id=trace_id,
        run_id=run_id,
        severity=severity,
        start_time=start_dt,
        end_time=end_dt,
    )
    events = [_event_row(row) for row in rows]

    if format == 'json':
        return {
            'project_id': project_id,
            'format': 'json',
            'count': len(events),
            'events': events,
        }

    buffer = StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=[
            'id',
            'event_index',
            'event_type',
            'actor_type',
            'actor_id',
            'actor_role',
            'actor_rank',
            'actor_position',
            'source',
            'classification',
            'severity',
            'trace_id',
            'run_id',
            'session_id',
            'created_at',
            'event_hash',
            'prev_hash',
        ],
    )
    writer.writeheader()
    for event in events:
        writer.writerow(
            {
                'id': event['id'],
                'event_index': event['event_index'],
                'event_type': event['event_type'],
                'actor_type': event['actor_type'],
                'actor_id': event['actor_id'],
                'actor_role': event['actor_role'],
                'actor_rank': event['actor_rank'],
                'actor_position': event['actor_position'],
                'source': event['source'],
                'classification': event['classification'],
                'severity': event['severity'],
                'trace_id': event['trace_id'],
                'run_id': event['run_id'],
                'session_id': event['session_id'],
                'created_at': event['created_at'],
                'event_hash': event['event_hash'],
                'prev_hash': event['prev_hash'],
            }
        )

    return Response(
        content=buffer.getvalue(),
        media_type='text/csv',
        headers={'Content-Disposition': f'attachment; filename="audit-{project_id}.csv"'},
    )


@router.post('/evidence')
def create_evidence_package(
    payload: dict,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> dict:
    project_id = str(payload.get('project_id') or '').strip()
    if not project_id:
        raise HTTPException(status_code=400, detail='project_id is required')
    ensure_project_scope(db, principal, project_id)

    event_ids = payload.get('event_ids', [])
    if not isinstance(event_ids, list):
        raise HTTPException(status_code=400, detail='event_ids must be a list')

    if event_ids:
        rows = db.scalars(
            select(AuditEvent)
            .where(
                AuditEvent.project_id == project_id,
                AuditEvent.id.in_([str(x) for x in event_ids]),
            )
            .order_by(AuditEvent.event_index.asc(), AuditEvent.created_at.asc())
        ).all()
    else:
        rows = db.scalars(
            select(AuditEvent)
            .where(AuditEvent.project_id == project_id)
            .order_by(AuditEvent.event_index.asc(), AuditEvent.created_at.asc())
            .limit(500)
        ).all()

    chain = verify_audit_chain(db, tenant_id=principal.tenant_id, project_id=project_id, limit=5000)
    package = {
        'project_id': project_id,
        'event_count': len(rows),
        'events': [_event_row(row) for row in rows],
        'chain_verified': bool(chain.get('ok', False)),
        'chain': chain,
        'generated_at': datetime.now(timezone.utc).isoformat(),
    }
    canonical = json.dumps(package, sort_keys=True, separators=(',', ':'))
    evidence_hash = hashlib.sha256(canonical.encode('utf-8')).hexdigest()
    evidence_id = f"evidence-{evidence_hash[:16]}"
    return {
        'evidence_id': evidence_id,
        'project_id': project_id,
        'event_count': len(rows),
        'chain_verified': bool(chain.get('ok', False)),
        'evidence_hash': evidence_hash,
        'format': str(payload.get('format') or 'json'),
        'description': str(payload.get('description') or ''),
    }
