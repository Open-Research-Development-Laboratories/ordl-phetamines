from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.authz import evaluate_authorization
from app.common import get_config_state, upsert_config_state
from app.db import get_db
from app.schemas import (
    AuthorizationDecisionOut,
    ClearanceCompartmentCreate,
    ClearanceCompartmentUpdate,
    ClearanceEvaluateRequest,
    ClearanceMatrixUpdate,
    ClearanceTierUpdate,
    ClearanceTiersUpdate,
)
from app.security import Principal, get_current_principal

router = APIRouter(prefix='/clearance', tags=['clearance'])


@router.post('/evaluate', response_model=AuthorizationDecisionOut)
def evaluate_clearance(
    payload: ClearanceEvaluateRequest,
    principal: Principal = Depends(get_current_principal),
) -> AuthorizationDecisionOut:
    result = evaluate_authorization(
        principal,
        action=payload.action,
        required_clearance=payload.required_clearance,
        required_compartments=payload.required_compartments,
        high_risk=payload.high_risk,
    )
    return AuthorizationDecisionOut(decision=result.decision, reason_codes=result.reason_codes)


def _default_tiers() -> list[dict]:
    return [
        {"level": "public", "name": "Public", "description": "Open visibility", "color": "#7f8c8d"},
        {"level": "internal", "name": "Internal", "description": "Employee scoped", "color": "#2d7ff9"},
        {"level": "restricted", "name": "Restricted", "description": "Need-to-know", "color": "#f39c12"},
        {"level": "confidential", "name": "Confidential", "description": "Leadership approved", "color": "#e74c3c"},
        {"level": "secret", "name": "Secret", "description": "Executive clearance", "color": "#8e44ad"},
    ]


@router.get('/tiers')
def list_tiers(
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> list[dict]:
    return get_config_state(
        db,
        tenant_id=principal.tenant_id,
        scope_type='clearance',
        scope_id='tenant',
        config_key='tiers',
        default=_default_tiers(),
    )


@router.put('/tiers')
def put_tiers(
    payload: ClearanceTiersUpdate,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> list[dict]:
    upsert_config_state(
        db,
        tenant_id=principal.tenant_id,
        scope_type='clearance',
        scope_id='tenant',
        config_key='tiers',
        value=[item.model_dump() for item in payload.tiers],
        updated_by_user_id=principal.user_id,
    )
    db.commit()
    return [item.model_dump() for item in payload.tiers]


@router.get('/tiers/{tier_id}')
def get_tier(
    tier_id: str,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> dict:
    tiers = get_config_state(
        db,
        tenant_id=principal.tenant_id,
        scope_type='clearance',
        scope_id='tenant',
        config_key='tiers',
        default=_default_tiers(),
    )
    row = next((item for item in tiers if str(item.get('level')) == tier_id), None)
    if row is None:
        raise HTTPException(status_code=404, detail='tier not found')
    return row


@router.put('/tiers/{tier_id}')
def patch_tier(
    tier_id: str,
    payload: ClearanceTierUpdate,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> dict:
    tiers = get_config_state(
        db,
        tenant_id=principal.tenant_id,
        scope_type='clearance',
        scope_id='tenant',
        config_key='tiers',
        default=_default_tiers(),
    )
    row = next((item for item in tiers if str(item.get('level')) == tier_id), None)
    if row is None:
        raise HTTPException(status_code=404, detail='tier not found')
    row.update(payload.model_dump(exclude_none=True))
    upsert_config_state(
        db,
        tenant_id=principal.tenant_id,
        scope_type='clearance',
        scope_id='tenant',
        config_key='tiers',
        value=tiers,
        updated_by_user_id=principal.user_id,
    )
    db.commit()
    return row


@router.get('/compartments')
def list_compartments(
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> list[dict]:
    return get_config_state(
        db,
        tenant_id=principal.tenant_id,
        scope_type='clearance',
        scope_id='tenant',
        config_key='compartments',
        default=[],
    )


@router.post('/compartments')
def create_compartment(
    payload: ClearanceCompartmentCreate,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> dict:
    rows = get_config_state(
        db,
        tenant_id=principal.tenant_id,
        scope_type='clearance',
        scope_id='tenant',
        config_key='compartments',
        default=[],
    )
    if any(str(item.get('id')) == payload.id for item in rows):
        raise HTTPException(status_code=409, detail='compartment already exists')
    record = payload.model_dump()
    rows.append(record)
    upsert_config_state(
        db,
        tenant_id=principal.tenant_id,
        scope_type='clearance',
        scope_id='tenant',
        config_key='compartments',
        value=rows,
        updated_by_user_id=principal.user_id,
    )
    db.commit()
    return record


@router.get('/compartments/{comp_id}')
def get_compartment(
    comp_id: str,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> dict:
    rows = get_config_state(
        db,
        tenant_id=principal.tenant_id,
        scope_type='clearance',
        scope_id='tenant',
        config_key='compartments',
        default=[],
    )
    item = next((row for row in rows if str(row.get('id')) == comp_id), None)
    if item is None:
        raise HTTPException(status_code=404, detail='compartment not found')
    return item


@router.put('/compartments/{comp_id}')
def patch_compartment(
    comp_id: str,
    payload: ClearanceCompartmentUpdate,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> dict:
    rows = get_config_state(
        db,
        tenant_id=principal.tenant_id,
        scope_type='clearance',
        scope_id='tenant',
        config_key='compartments',
        default=[],
    )
    item = next((row for row in rows if str(row.get('id')) == comp_id), None)
    if item is None:
        raise HTTPException(status_code=404, detail='compartment not found')
    item.update(payload.model_dump(exclude_none=True))
    upsert_config_state(
        db,
        tenant_id=principal.tenant_id,
        scope_type='clearance',
        scope_id='tenant',
        config_key='compartments',
        value=rows,
        updated_by_user_id=principal.user_id,
    )
    db.commit()
    return item


@router.put('/matrix')
def put_ntk_matrix(
    payload: ClearanceMatrixUpdate,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> dict:
    upsert_config_state(
        db,
        tenant_id=principal.tenant_id,
        scope_type='clearance',
        scope_id='tenant',
        config_key='ntk_matrix',
        value=payload.matrix,
        updated_by_user_id=principal.user_id,
    )
    db.commit()
    return payload.matrix


@router.put('/ntk-matrix')
def put_ntk_matrix_alias(
    payload: ClearanceMatrixUpdate,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> dict:
    return put_ntk_matrix(payload=payload, principal=principal, db=db)


@router.get('/matrix/export')
def export_clearance_matrix(
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> dict:
    tiers = get_config_state(
        db,
        tenant_id=principal.tenant_id,
        scope_type='clearance',
        scope_id='tenant',
        config_key='tiers',
        default=_default_tiers(),
    )
    compartments = get_config_state(
        db,
        tenant_id=principal.tenant_id,
        scope_type='clearance',
        scope_id='tenant',
        config_key='compartments',
        default=[],
    )
    matrix = get_config_state(
        db,
        tenant_id=principal.tenant_id,
        scope_type='clearance',
        scope_id='tenant',
        config_key='ntk_matrix',
        default={},
    )
    return {'tiers': tiers, 'compartments': compartments, 'matrix': matrix}
