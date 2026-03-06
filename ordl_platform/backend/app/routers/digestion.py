from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.audit import append_audit_event, build_actor_snapshot
from app.authz import evaluate_authorization
from app.common import ensure_project_scope
from app.db import get_db
from app.ingestion import get_project_digestion_status, run_code_digestion
from app.schemas import DigestionRunRequest
from app.security import Principal, get_current_principal
from app.storage import get_storage_adapter

router = APIRouter(prefix='/digestion', tags=['digestion'])


@router.post('/run')
def run_digestion(
    payload: DigestionRunRequest,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> dict:
    ensure_project_scope(db, principal, payload.project_id)
    auth = evaluate_authorization(principal, action='read_project', high_risk=True)
    if auth.decision == 'deny':
        raise HTTPException(status_code=403, detail=f'digestion denied: {auth.reason_codes}')

    try:
        summary = run_code_digestion(
            db,
            project_id=payload.project_id,
            repo_root=payload.repo_root,
            chunk_size=payload.chunk_size,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    append_audit_event(
        db,
        tenant_id=principal.tenant_id,
        project_id=payload.project_id,
        event_type='digestion.completed',
        payload={
            'run_id': summary.run_id,
            'total_files': summary.total_files,
            'total_lines': summary.total_lines,
            'reviewed_lines': summary.reviewed_lines,
        },
        actor=build_actor_snapshot(db, principal, payload.project_id),
        resource={'resource_type': 'digestion_run', 'resource_id': summary.run_id},
        run_id=summary.run_id,
    )
    db.commit()
    return {
        'run_id': summary.run_id,
        'total_files': summary.total_files,
        'total_lines': summary.total_lines,
        'reviewed_lines': summary.reviewed_lines,
    }


@router.get('/status/{project_id}')
def digestion_status(
    project_id: str,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> dict:
    ensure_project_scope(db, principal, project_id)
    return get_project_digestion_status(db, project_id=project_id)


@router.get('/gate/{project_id}')
def digestion_gate(
    project_id: str,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> dict:
    ensure_project_scope(db, principal, project_id)
    status_payload = get_project_digestion_status(db, project_id=project_id)
    return {
        'project_id': project_id,
        'gate': 'pass' if status_payload.get('full_coverage') else 'fail',
        'coverage_percent': status_payload.get('coverage_percent', 0.0),
    }


@router.post('/export/{project_id}')
def export_digestion_report(
    project_id: str,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> dict:
    ensure_project_scope(db, principal, project_id)
    status_payload = get_project_digestion_status(db, project_id=project_id)
    report = {
        'project_id': project_id,
        'tenant_id': principal.tenant_id,
        'status': status_payload,
    }
    adapter = get_storage_adapter()
    key = f'digestion/{project_id}/status.json'
    uri = adapter.put_text(key=key, content=json.dumps(report, sort_keys=True))
    return {'artifact_uri': uri, 'key': key}
