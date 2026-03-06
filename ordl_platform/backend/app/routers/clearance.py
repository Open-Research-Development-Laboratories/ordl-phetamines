from __future__ import annotations

from fastapi import APIRouter, Depends

from app.authz import evaluate_authorization
from app.schemas import AuthorizationDecisionOut, ClearanceEvaluateRequest
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
