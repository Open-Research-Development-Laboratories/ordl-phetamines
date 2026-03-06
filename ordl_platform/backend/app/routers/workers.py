from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.authz import evaluate_authorization
from app.common import ensure_project_scope, json_list
from app.db import get_db
from app.models import WorkerAction, WorkerInstance
from app.schemas import (
    WorkerActionRequest,
    WorkerConnectivityOut,
    WorkerHeartbeatRequest,
    WorkerOut,
    WorkerProbeRequest,
    WorkerRegister,
)
from app.security import Principal, get_current_principal

router = APIRouter(prefix='/workers', tags=['workers'])


def _iso_or_none(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _reconnect_required(row: WorkerInstance, stale_after_seconds: int) -> bool:
    now = datetime.now(timezone.utc)
    if row.connectivity_state == 'down':
        return True
    keepalive_at = _as_utc(row.last_keepalive_at)
    if keepalive_at is None:
        return True
    age = (now - keepalive_at).total_seconds()
    return age > stale_after_seconds


def _connectivity_out(row: WorkerInstance, stale_after_seconds: int) -> WorkerConnectivityOut:
    reconnect_targets = json_list(row.gateway_candidates_json)
    if row.last_gateway_url and row.last_gateway_url not in reconnect_targets:
        reconnect_targets.insert(0, row.last_gateway_url)
    return WorkerConnectivityOut(
        worker_id=row.id,
        worker_name=row.name,
        role=row.role,
        status=row.status,
        connectivity_state=row.connectivity_state,
        last_seen_at=_iso_or_none(row.last_seen_at),
        last_keepalive_at=_iso_or_none(row.last_keepalive_at),
        last_probe_at=_iso_or_none(row.last_probe_at),
        last_gateway_url=row.last_gateway_url,
        gateway_rtt_ms=row.gateway_rtt_ms,
        reconnect_required=_reconnect_required(row, stale_after_seconds=stale_after_seconds),
        reconnect_targets=reconnect_targets,
    )


@router.post('/register', response_model=WorkerOut)
def register_worker(
    payload: WorkerRegister,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> WorkerOut:
    ensure_project_scope(db, principal, payload.project_id)
    row = db.scalar(
        select(WorkerInstance).where(
            WorkerInstance.project_id == payload.project_id,
            WorkerInstance.device_id == payload.device_id,
        )
    )
    if row is None:
        row = WorkerInstance(
            project_id=payload.project_id,
            name=payload.name,
            role=payload.role,
            host=payload.host,
            device_id=payload.device_id,
            capabilities_json=json.dumps(payload.capabilities, sort_keys=True),
            status='online',
            connectivity_state='online',
            gateway_candidates_json='[]',
            last_seen_at=datetime.now(timezone.utc),
        )
        db.add(row)
    else:
        row.name = payload.name
        row.role = payload.role
        row.host = payload.host
        row.capabilities_json = json.dumps(payload.capabilities, sort_keys=True)
        row.status = 'online'
        row.connectivity_state = 'online'
        row.last_seen_at = datetime.now(timezone.utc)

    db.commit()
    return WorkerOut(
        id=row.id,
        project_id=row.project_id,
        name=row.name,
        role=row.role,
        host=row.host,
        device_id=row.device_id,
        status=row.status,
        capabilities=json_list(row.capabilities_json),
    )


@router.get('', response_model=list[WorkerOut])
def list_workers(
    project_id: str,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> list[WorkerOut]:
    ensure_project_scope(db, principal, project_id)
    rows = db.scalars(select(WorkerInstance).where(WorkerInstance.project_id == project_id)).all()
    return [
        WorkerOut(
            id=row.id,
            project_id=row.project_id,
            name=row.name,
            role=row.role,
            host=row.host,
            device_id=row.device_id,
            status=row.status,
            capabilities=json_list(row.capabilities_json),
        )
        for row in rows
    ]


@router.post('/{worker_id}/action')
def queue_worker_action(
    worker_id: str,
    payload: WorkerActionRequest,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> dict:
    worker = db.get(WorkerInstance, worker_id)
    if worker is None:
        raise HTTPException(status_code=404, detail='worker not found')
    ensure_project_scope(db, principal, worker.project_id)
    auth = evaluate_authorization(principal, action='worker_action')
    if auth.decision != 'allow':
        raise HTTPException(status_code=403, detail=f'worker action denied: {auth.reason_codes}')

    action = WorkerAction(
        worker_id=worker_id,
        action=payload.action,
        requested_by_user_id=principal.user_id,
        status='queued',
        notes=payload.notes,
    )
    db.add(action)
    db.commit()
    return {'worker_action_id': action.id, 'status': action.status}


@router.post('/{worker_id}/heartbeat')
def worker_heartbeat(
    worker_id: str,
    payload: WorkerHeartbeatRequest,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    worker = db.get(WorkerInstance, worker_id)
    if worker is None:
        raise HTTPException(status_code=404, detail='worker not found')
    ensure_project_scope(db, principal, worker.project_id)
    auth = evaluate_authorization(principal, action='worker_action')
    if auth.decision != 'allow':
        raise HTTPException(status_code=403, detail=f'worker heartbeat denied: {auth.reason_codes}')

    now = datetime.now(timezone.utc)
    worker.status = 'online'
    worker.connectivity_state = payload.connectivity_state
    worker.last_gateway_url = payload.gateway_url
    worker.gateway_candidates_json = json.dumps(payload.gateway_candidates, sort_keys=True)
    worker.gateway_rtt_ms = payload.gateway_rtt_ms
    worker.keepalive_interval_seconds = payload.keepalive_interval_seconds
    worker.keepalive_miss_threshold = payload.keepalive_miss_threshold
    worker.last_keepalive_at = now
    worker.last_seen_at = now
    db.commit()
    return {
        'worker_id': worker.id,
        'status': worker.status,
        'connectivity_state': worker.connectivity_state,
        'last_keepalive_at': worker.last_keepalive_at.isoformat() if worker.last_keepalive_at else None,
    }


@router.post('/{worker_id}/probe')
def worker_probe(
    worker_id: str,
    payload: WorkerProbeRequest,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    worker = db.get(WorkerInstance, worker_id)
    if worker is None:
        raise HTTPException(status_code=404, detail='worker not found')
    ensure_project_scope(db, principal, worker.project_id)
    auth = evaluate_authorization(principal, action='worker_action')
    if auth.decision != 'allow':
        raise HTTPException(status_code=403, detail=f'worker probe denied: {auth.reason_codes}')

    now = datetime.now(timezone.utc)
    worker.last_probe_at = now
    worker.last_seen_at = now
    worker.last_gateway_url = payload.gateway_url or worker.last_gateway_url
    worker.gateway_rtt_ms = payload.gateway_rtt_ms
    if payload.reachable:
        worker.status = 'online'
        worker.connectivity_state = 'online'
    else:
        worker.status = 'degraded'
        worker.connectivity_state = 'down'
        if payload.reason:
            action = WorkerAction(
                worker_id=worker.id,
                action='gateway_probe_failed',
                requested_by_user_id=principal.user_id,
                status='recorded',
                notes=payload.reason,
            )
            db.add(action)
    db.commit()
    return {
        'worker_id': worker.id,
        'status': worker.status,
        'connectivity_state': worker.connectivity_state,
        'last_probe_at': worker.last_probe_at.isoformat() if worker.last_probe_at else None,
    }


@router.get('/connectivity', response_model=list[WorkerConnectivityOut])
def list_worker_connectivity(
    project_id: str,
    stale_after_seconds: int = 90,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> list[WorkerConnectivityOut]:
    ensure_project_scope(db, principal, project_id)
    rows = db.scalars(select(WorkerInstance).where(WorkerInstance.project_id == project_id)).all()
    return [_connectivity_out(row, stale_after_seconds=stale_after_seconds) for row in rows]
