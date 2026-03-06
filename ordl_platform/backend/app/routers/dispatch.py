from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.authz import evaluate_authorization
from app.common import ensure_project_scope
from app.config import get_settings
from app.db import get_db
from app.dispatch import create_dispatch
from app.models import CollabMessage, DispatchRequest, DispatchResult
from app.providers import PROVIDER_REGISTRY
from app.schemas import DispatchCreate, DispatchOut, DispatchResultOut
from app.security import Principal, get_current_principal

router = APIRouter(prefix='/dispatch', tags=['dispatch'])


def _dispatch_out(row: DispatchRequest) -> DispatchOut:
    return DispatchOut(
        id=row.id,
        project_id=row.project_id,
        message_id=row.message_id,
        target_scope=row.target_scope,
        target_value=row.target_value,
        provider=row.provider,
        model=row.model,
        request_hash=row.request_hash,
        state=row.state,
    )


@router.post('', response_model=DispatchOut)
def dispatch_work(
    payload: DispatchCreate,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> DispatchOut:
    ensure_project_scope(db, principal, payload.project_id)
    if payload.provider not in PROVIDER_REGISTRY:
        raise HTTPException(status_code=422, detail=f"unsupported provider: {payload.provider}")

    auth = evaluate_authorization(principal, action='dispatch', high_risk=True)
    if auth.decision != 'allow':
        raise HTTPException(status_code=403, detail=f'dispatch denied: {auth.reason_codes}')

    if payload.message_id:
        msg = db.get(CollabMessage, payload.message_id)
        if msg is None or msg.project_id != payload.project_id:
            raise HTTPException(status_code=404, detail='linked message not found')
        if msg.state != 'approved':
            raise HTTPException(status_code=400, detail='linked message must be approved before dispatch')

    request_row, _, _ = create_dispatch(
        db,
        tenant_id=principal.tenant_id,
        project_id=payload.project_id,
        requested_by_user_id=principal.user_id,
        message_id=payload.message_id,
        target_scope=payload.target_scope,
        target_value=payload.target_value,
        provider=payload.provider,
        model=payload.model,
        payload=payload.payload,
        policy_reason_codes=auth.reason_codes,
        settings=get_settings(),
    )
    db.commit()
    return _dispatch_out(request_row)


@router.get('', response_model=list[DispatchOut])
def list_dispatch(
    project_id: str,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> list[DispatchOut]:
    ensure_project_scope(db, principal, project_id)
    rows = db.scalars(
        select(DispatchRequest)
        .where(DispatchRequest.project_id == project_id)
        .order_by(DispatchRequest.created_at.asc(), DispatchRequest.id.asc())
    ).all()
    return [_dispatch_out(row) for row in rows]


@router.get('/results', response_model=list[DispatchResultOut])
def list_dispatch_results(
    dispatch_request_id: str,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> list[DispatchResultOut]:
    dispatch = db.get(DispatchRequest, dispatch_request_id)
    if dispatch is None:
        return []
    ensure_project_scope(db, principal, dispatch.project_id)
    rows = db.scalars(
        select(DispatchResult)
        .where(DispatchResult.dispatch_request_id == dispatch_request_id)
        .order_by(DispatchResult.created_at.asc(), DispatchResult.id.asc())
    ).all()
    return [
        DispatchResultOut(
            id=row.id,
            dispatch_request_id=row.dispatch_request_id,
            worker_id=row.worker_id,
            status=row.status,
            provider_reference=row.provider_reference,
            output=row.output,
            error=row.error,
        )
        for row in rows
    ]
