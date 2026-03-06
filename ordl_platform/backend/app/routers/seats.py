from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import append_audit_event, build_actor_snapshot
from app.authz import evaluate_authorization
from app.common import ensure_project_scope, json_list, upsert_config_state
from app.db import get_db
from app.models import SeatAssignment
from app.schemas import (
    SeatAssignRequest,
    SeatBulkAssignRequest,
    SeatCreate,
    SeatMatrixUpdate,
    SeatOut,
    SeatUpdate,
    SeatVacateRequest,
)
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


@router.post('/{seat_id}/assign', response_model=SeatOut)
def assign_seat(
    seat_id: str,
    payload: SeatAssignRequest,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> SeatOut:
    seat = db.get(SeatAssignment, seat_id)
    if seat is None:
        raise HTTPException(status_code=404, detail='seat not found')
    ensure_project_scope(db, principal, seat.project_id)
    seat.user_id = payload.user_id
    if payload.role is not None:
        seat.role = payload.role
    if payload.rank is not None:
        seat.rank = payload.rank
    if payload.position is not None:
        seat.position = payload.position
    if payload.group_name is not None:
        seat.group_name = payload.group_name
    if payload.clearance_tier is not None:
        seat.clearance_tier = payload.clearance_tier
    seat.compartments_json = json.dumps(payload.compartments, sort_keys=True)
    seat.status = 'active'
    append_audit_event(
        db,
        tenant_id=principal.tenant_id,
        project_id=seat.project_id,
        event_type='seat.assigned',
        payload={'seat_id': seat.id, 'user_id': payload.user_id},
        actor=build_actor_snapshot(db, principal, seat.project_id),
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


@router.post('/{seat_id}/vacate', response_model=SeatOut)
def vacate_seat(
    seat_id: str,
    payload: SeatVacateRequest,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> SeatOut:
    seat = db.get(SeatAssignment, seat_id)
    if seat is None:
        raise HTTPException(status_code=404, detail='seat not found')
    ensure_project_scope(db, principal, seat.project_id)
    seat.status = 'vacant'
    append_audit_event(
        db,
        tenant_id=principal.tenant_id,
        project_id=seat.project_id,
        event_type='seat.vacated',
        payload={'seat_id': seat.id, 'reason': payload.reason},
        actor=build_actor_snapshot(db, principal, seat.project_id),
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


@router.post('/bulk')
def bulk_assign_seats(
    payload: SeatBulkAssignRequest,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> dict:
    ensure_project_scope(db, principal, payload.project_id)
    processed: list[str] = []
    for item in payload.assignments:
        if item.seat_id:
            seat = db.get(SeatAssignment, item.seat_id)
            if seat is None:
                continue
            if seat.project_id != payload.project_id:
                continue
            seat.user_id = item.user_id
            seat.role = item.role
            seat.rank = item.rank
            seat.position = item.position
            seat.group_name = item.group_name
            seat.clearance_tier = item.clearance_tier
            seat.compartments_json = json.dumps(item.compartments, sort_keys=True)
            seat.status = item.status
            processed.append(seat.id)
        else:
            seat = SeatAssignment(
                project_id=payload.project_id,
                user_id=item.user_id,
                role=item.role,
                rank=item.rank,
                position=item.position,
                group_name=item.group_name,
                clearance_tier=item.clearance_tier,
                compartments_json=json.dumps(item.compartments, sort_keys=True),
                status=item.status,
            )
            db.add(seat)
            db.flush()
            processed.append(seat.id)
    append_audit_event(
        db,
        tenant_id=principal.tenant_id,
        project_id=payload.project_id,
        event_type='seat.bulk_assigned',
        payload={'processed_count': len(processed), 'seat_ids': processed},
        actor=build_actor_snapshot(db, principal, payload.project_id),
        resource={'resource_type': 'seat_assignment_batch', 'resource_id': payload.project_id},
    )
    db.commit()
    return {'project_id': payload.project_id, 'processed_count': len(processed), 'seat_ids': processed}


@router.put('/matrix')
def update_seat_matrix(
    payload: SeatMatrixUpdate,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> dict:
    ensure_project_scope(db, principal, payload.project_id)
    upsert_config_state(
        db,
        tenant_id=principal.tenant_id,
        scope_type='project',
        scope_id=payload.project_id,
        config_key='seat_matrix',
        value=payload.matrix,
        updated_by_user_id=principal.user_id,
    )
    append_audit_event(
        db,
        tenant_id=principal.tenant_id,
        project_id=payload.project_id,
        event_type='seat.matrix_updated',
        payload={'keys': sorted(payload.matrix.keys())},
        actor=build_actor_snapshot(db, principal, payload.project_id),
        resource={'resource_type': 'seat_matrix', 'resource_id': payload.project_id},
    )
    db.commit()
    return payload.matrix


@router.put('/{seat_id}', response_model=SeatOut)
def update_seat(
    seat_id: str,
    payload: SeatUpdate,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> SeatOut:
    seat = db.get(SeatAssignment, seat_id)
    if seat is None:
        raise HTTPException(status_code=404, detail='seat not found')
    ensure_project_scope(db, principal, seat.project_id)
    auth = evaluate_authorization(principal, action='manage_seats', high_risk=True)
    if auth.decision != 'allow':
        raise HTTPException(status_code=403, detail=f'seat update denied: {auth.reason_codes}')

    patch = payload.model_dump(exclude_none=True)
    if 'compartments' in patch:
        seat.compartments_json = json.dumps(patch.pop('compartments'), sort_keys=True)
    for key, value in patch.items():
        setattr(seat, key, value)
    append_audit_event(
        db,
        tenant_id=principal.tenant_id,
        project_id=seat.project_id,
        event_type='seat.updated',
        payload={'seat_id': seat.id, 'patch': payload.model_dump(exclude_none=True)},
        actor=build_actor_snapshot(db, principal, seat.project_id),
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
