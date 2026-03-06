from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.authz import evaluate_authorization
from app.common import ensure_project_scope, json_list
from app.db import get_db
from app.models import WorkerAction, WorkerInstance
from app.schemas import WorkerActionRequest, WorkerOut, WorkerRegister
from app.security import Principal, get_current_principal

router = APIRouter(prefix='/workers', tags=['workers'])


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
            last_seen_at=datetime.now(timezone.utc),
        )
        db.add(row)
    else:
        row.name = payload.name
        row.role = payload.role
        row.host = payload.host
        row.capabilities_json = json.dumps(payload.capabilities, sort_keys=True)
        row.status = 'online'
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
