from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import append_audit_event, build_actor_snapshot
from app.authz import evaluate_authorization
from app.common import ensure_project_scope, json_list
from app.db import get_db
from app.models import SeatAssignment
from app.schemas import SeatCreate, SeatOut
from app.security import Principal, get_current_principal

router = APIRouter(prefix='/seats', tags=['seats'])


@router.post('', response_model=SeatOut)
def create_seat(
    payload: SeatCreate,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> SeatOut:
    ensure_project_scope(db, principal, payload.project_id)
    auth = evaluate_authorization(principal, action='manage_seats', high_risk=True)
    if auth.decision != 'allow':
        raise HTTPException(status_code=403, detail=f'seat assignment denied: {auth.reason_codes}')

    seat = SeatAssignment(
        project_id=payload.project_id,
        user_id=payload.user_id,
        role=payload.role,
        rank=payload.rank,
        position=payload.position,
        group_name=payload.group_name,
        clearance_tier=payload.clearance_tier,
        compartments_json=json.dumps(payload.compartments, sort_keys=True),
        status=payload.status,
    )
    db.add(seat)
    append_audit_event(
        db,
        tenant_id=principal.tenant_id,
        project_id=payload.project_id,
        event_type='seat.created',
        payload={'user_id': payload.user_id, 'role': payload.role, 'rank': payload.rank},
        actor=build_actor_snapshot(db, principal, payload.project_id),
        resource={'resource_type': 'seat', 'resource_id': seat.id},
    )
    db.commit()
    return SeatOut(
        id=seat.id,
        project_id=seat.project_id,
        user_id=seat.user_id,
        role=seat.role,
        rank=seat.rank,
        position=seat.position,
        group_name=seat.group_name,
        clearance_tier=seat.clearance_tier,
        compartments=json_list(seat.compartments_json),
        status=seat.status,
    )


@router.get('', response_model=list[SeatOut])
def list_seats(
    project_id: str,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> list[SeatOut]:
    ensure_project_scope(db, principal, project_id)
    rows = db.scalars(select(SeatAssignment).where(SeatAssignment.project_id == project_id)).all()
    return [
        SeatOut(
            id=row.id,
            project_id=row.project_id,
            user_id=row.user_id,
            role=row.role,
            rank=row.rank,
            position=row.position,
            group_name=row.group_name,
            clearance_tier=row.clearance_tier,
            compartments=json_list(row.compartments_json),
            status=row.status,
        )
        for row in rows
    ]
