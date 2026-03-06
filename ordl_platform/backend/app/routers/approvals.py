from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.authz import evaluate_authorization
from app.common import ensure_project_scope
from app.db import get_db
from app.models import Approval, CollabMessage
from app.schemas import ApprovalCreate, ApprovalOut
from app.security import Principal, get_current_principal

router = APIRouter(prefix='/approvals', tags=['approvals'])


@router.post('', response_model=ApprovalOut)
def create_approval(
    payload: ApprovalCreate,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> ApprovalOut:
    ensure_project_scope(db, principal, payload.project_id)
    auth = evaluate_authorization(principal, action='approve_message')
    if auth.decision != 'allow':
        raise HTTPException(status_code=403, detail=f'approval denied: {auth.reason_codes}')

    msg = db.get(CollabMessage, payload.message_id)
    if msg is None or msg.project_id != payload.project_id:
        raise HTTPException(status_code=404, detail='message not found')

    row = Approval(
        project_id=payload.project_id,
        message_id=payload.message_id,
        reviewer_user_id=principal.user_id,
        decision=payload.decision,
        rationale=payload.rationale,
    )
    db.add(row)
    if payload.decision == 'approved':
        msg.state = 'approved'
        msg.updated_at = datetime.now(timezone.utc)
    db.commit()
    return ApprovalOut(
        id=row.id,
        project_id=row.project_id,
        message_id=row.message_id,
        reviewer_user_id=row.reviewer_user_id,
        decision=row.decision,
        rationale=row.rationale,
    )
