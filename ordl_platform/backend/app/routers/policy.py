from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.authz import evaluate_authorization
from app.common import ensure_project_scope
from app.config import get_settings
from app.db import get_db
from app.models import PolicyDecision
from app.policy import hash_request, issue_policy_token, validate_policy_token
from app.schemas import PolicyDecideRequest, PolicyDecideResponse, PolicyValidateRequest
from app.security import Principal, get_current_principal

router = APIRouter(prefix='/policy', tags=['policy'])


@router.post('/decide', response_model=PolicyDecideResponse)
def policy_decide(
    payload: PolicyDecideRequest,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> PolicyDecideResponse:
    ensure_project_scope(db, principal, payload.project_id)
    auth = evaluate_authorization(
        principal,
        action=payload.action,
        required_clearance=payload.required_clearance,
        required_compartments=payload.required_compartments,
        high_risk=payload.high_risk,
    )

    request_hash = hash_request(payload.payload)
    token = None
    nonce = ''
    if auth.decision == 'allow':
        token, nonce = issue_policy_token(
            request_hash_value=request_hash,
            destination_scope=payload.destination_scope,
            decision='allow',
            policy_version='v1',
            settings=get_settings(),
        )

    row = PolicyDecision(
        project_id=payload.project_id,
        user_id=principal.user_id,
        action=payload.action,
        resource_type=payload.resource_type,
        resource_id=payload.resource_id,
        decision=auth.decision,
        reason_codes_json=json.dumps(auth.reason_codes, sort_keys=True),
        request_hash=request_hash,
        token_nonce=nonce,
    )
    db.add(row)
    db.commit()

    return PolicyDecideResponse(
        decision=auth.decision,
        reason_codes=auth.reason_codes,
        request_hash=request_hash,
        policy_token=token,
    )


@router.post('/validate')
def policy_validate(
    payload: PolicyValidateRequest,
    principal: Principal = Depends(get_current_principal),
) -> dict:
    validate_policy_token(
        token=payload.token,
        expected_request_hash=payload.request_hash,
        expected_destination_scope=payload.destination_scope,
        settings=get_settings(),
    )
    return {'valid': True, 'tenant_id': principal.tenant_id}
