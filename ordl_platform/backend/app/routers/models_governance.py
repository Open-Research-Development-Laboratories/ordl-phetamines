from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import append_audit_event, build_actor_snapshot
from app.authz import evaluate_authorization
from app.common import default_project_policy_profiles, ensure_project_scope, get_config_state
from app.db import get_db
from app.models import ModelEvalRun, ModelFineTuneRun, ModelPromotion
from app.schemas import (
    ModelEvalRunCreate,
    ModelEvalRunOut,
    ModelFineTuneRunCreate,
    ModelFineTuneRunOut,
    ModelFineTuneRunStateUpdate,
    ModelPromotionCreate,
    ModelPromotionOut,
)
from app.security import Principal, get_current_principal

router = APIRouter(prefix="/models", tags=["models"])


def _json_obj(value: str | None, default: dict | None = None) -> dict:
    fallback = default or {}
    try:
        parsed = json.loads(value or "{}")
    except json.JSONDecodeError:
        return dict(fallback)
    return parsed if isinstance(parsed, dict) else dict(fallback)


def _json_list(value: str | None) -> list:
    try:
        parsed = json.loads(value or "[]")
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def _eval_out(row: ModelEvalRun) -> ModelEvalRunOut:
    return ModelEvalRunOut(
        id=row.id,
        project_id=row.project_id,
        provider=row.provider,
        model=row.model,
        suite_name=row.suite_name,
        score_bp=row.score_bp,
        threshold_bp=row.threshold_bp,
        status=row.status,
        metrics=_json_obj(row.metrics_json),
        findings=_json_list(row.findings_json),
        executed_by_user_id=row.executed_by_user_id,
        created_at=row.created_at.isoformat() if row.created_at else None,
    )


def _fine_tune_out(row: ModelFineTuneRun) -> ModelFineTuneRunOut:
    return ModelFineTuneRunOut(
        id=row.id,
        project_id=row.project_id,
        provider=row.provider,
        base_model=row.base_model,
        target_model=row.target_model,
        status=row.status,
        dataset_uri=row.dataset_uri,
        dataset_digest=row.dataset_digest,
        dataset_provenance=_json_obj(row.dataset_provenance_json),
        training_params=_json_obj(row.training_params_json),
        latest_eval_run_id=row.latest_eval_run_id,
        promotion_state=row.promotion_state,
        created_by_user_id=row.created_by_user_id,
        created_at=row.created_at.isoformat() if row.created_at else None,
        updated_at=row.updated_at.isoformat() if row.updated_at else None,
    )


def _promotion_out(row: ModelPromotion) -> ModelPromotionOut:
    return ModelPromotionOut(
        id=row.id,
        project_id=row.project_id,
        provider=row.provider,
        model=row.model,
        environment=row.environment,
        mode=row.mode,
        fine_tune_run_id=row.fine_tune_run_id,
        required_eval_run_id=row.required_eval_run_id,
        status=row.status,
        reason_codes=_json_list(row.reason_codes_json),
        approved_by_user_id=row.approved_by_user_id,
        created_at=row.created_at.isoformat() if row.created_at else None,
        updated_at=row.updated_at.isoformat() if row.updated_at else None,
    )


def _authorize(principal: Principal, action: str, *, high_risk: bool = False) -> None:
    auth = evaluate_authorization(principal, action=action, high_risk=high_risk)
    if auth.decision != "allow":
        raise HTTPException(status_code=403, detail=f"{action} denied: {auth.reason_codes}")


def _resolve_eval_for_gate(
    *,
    db: Session,
    project_id: str,
    provider: str,
    model: str,
    requested_eval_run_id: str | None,
) -> ModelEvalRun | None:
    if requested_eval_run_id:
        return db.scalar(
            select(ModelEvalRun).where(
                ModelEvalRun.id == requested_eval_run_id,
                ModelEvalRun.project_id == project_id,
                ModelEvalRun.provider == provider,
                ModelEvalRun.model == model,
            )
        )
    return db.scalar(
        select(ModelEvalRun)
        .where(
            ModelEvalRun.project_id == project_id,
            ModelEvalRun.provider == provider,
            ModelEvalRun.model == model,
        )
        .order_by(ModelEvalRun.created_at.desc(), ModelEvalRun.id.desc())
        .limit(1)
    )


def _enforce_eval_gate(
    *,
    db: Session,
    principal: Principal,
    project_id: str,
    provider: str,
    model: str,
    eval_run_id: str | None,
) -> tuple[ModelEvalRun | None, list[str]]:
    profiles = get_config_state(
        db,
        tenant_id=principal.tenant_id,
        scope_type="project",
        scope_id=project_id,
        config_key="policy_profiles",
        default=default_project_policy_profiles(),
    )
    model_policy = profiles.get("model", {}) if isinstance(profiles, dict) else {}
    if not isinstance(model_policy, dict):
        model_policy = {}
    require_eval = bool(model_policy.get("require_eval_for_promotion", True))
    min_score = int(model_policy.get("min_eval_score_bp", 8000))

    eval_row = _resolve_eval_for_gate(
        db=db,
        project_id=project_id,
        provider=provider,
        model=model,
        requested_eval_run_id=eval_run_id,
    )
    reasons: list[str] = []
    if require_eval and eval_row is None:
        reasons.append("missing_eval_run")
        return None, reasons
    if eval_row is None:
        return None, reasons
    if eval_row.status != "pass":
        reasons.append("eval_not_passed")
    if eval_row.score_bp < min_score:
        reasons.append("eval_score_below_policy_threshold")
    return eval_row, reasons


@router.post("/evals/runs", response_model=ModelEvalRunOut)
def create_eval_run(
    payload: ModelEvalRunCreate,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> ModelEvalRunOut:
    ensure_project_scope(db, principal, payload.project_id)
    _authorize(principal, "dispatch")

    row = ModelEvalRun(
        project_id=payload.project_id,
        provider=payload.provider,
        model=payload.model,
        suite_name=payload.suite_name,
        score_bp=payload.score_bp,
        threshold_bp=payload.threshold_bp,
        status=payload.status,
        metrics_json=json.dumps(payload.metrics, sort_keys=True),
        findings_json=json.dumps(payload.findings, sort_keys=True),
        executed_by_user_id=principal.user_id,
    )
    db.add(row)
    append_audit_event(
        db,
        tenant_id=principal.tenant_id,
        project_id=payload.project_id,
        event_type="model.eval_run.created",
        payload={"eval_run_id": row.id, "model": payload.model, "status": payload.status, "score_bp": payload.score_bp},
        actor=build_actor_snapshot(db, principal, payload.project_id),
        resource={"resource_type": "model_eval_run", "resource_id": row.id},
    )
    db.commit()
    return _eval_out(row)


@router.get("/evals/runs", response_model=list[ModelEvalRunOut])
def list_eval_runs(
    project_id: str = Query(...),
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> list[ModelEvalRunOut]:
    ensure_project_scope(db, principal, project_id)
    rows = db.scalars(
        select(ModelEvalRun)
        .where(ModelEvalRun.project_id == project_id)
        .order_by(ModelEvalRun.created_at.desc(), ModelEvalRun.id.desc())
    ).all()
    return [_eval_out(row) for row in rows]


@router.get("/evals/runs/{eval_run_id}", response_model=ModelEvalRunOut)
def get_eval_run(
    eval_run_id: str,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> ModelEvalRunOut:
    row = db.get(ModelEvalRun, eval_run_id)
    if row is None:
        raise HTTPException(status_code=404, detail="eval run not found")
    ensure_project_scope(db, principal, row.project_id)
    return _eval_out(row)


@router.post("/fine-tunes", response_model=ModelFineTuneRunOut)
def create_fine_tune_run(
    payload: ModelFineTuneRunCreate,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> ModelFineTuneRunOut:
    ensure_project_scope(db, principal, payload.project_id)
    _authorize(principal, "dispatch", high_risk=True)

    required_provenance = {"source", "collection_method", "rights_basis"}
    missing = [key for key in sorted(required_provenance) if not str(payload.dataset_provenance.get(key, "")).strip()]
    if missing:
        raise HTTPException(status_code=422, detail=f"dataset_provenance missing required fields: {', '.join(missing)}")

    row = ModelFineTuneRun(
        project_id=payload.project_id,
        provider=payload.provider,
        base_model=payload.base_model,
        target_model=payload.target_model,
        status="queued",
        dataset_uri=payload.dataset_uri,
        dataset_digest=payload.dataset_digest,
        dataset_provenance_json=json.dumps(payload.dataset_provenance, sort_keys=True),
        training_params_json=json.dumps(payload.training_params, sort_keys=True),
        created_by_user_id=principal.user_id,
    )
    db.add(row)
    append_audit_event(
        db,
        tenant_id=principal.tenant_id,
        project_id=payload.project_id,
        event_type="model.fine_tune_run.created",
        payload={
            "fine_tune_run_id": row.id,
            "provider": payload.provider,
            "base_model": payload.base_model,
            "target_model": payload.target_model,
            "dataset_digest": payload.dataset_digest,
        },
        actor=build_actor_snapshot(db, principal, payload.project_id),
        resource={"resource_type": "model_fine_tune_run", "resource_id": row.id},
    )
    db.commit()
    return _fine_tune_out(row)


@router.get("/fine-tunes", response_model=list[ModelFineTuneRunOut])
def list_fine_tune_runs(
    project_id: str = Query(...),
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> list[ModelFineTuneRunOut]:
    ensure_project_scope(db, principal, project_id)
    rows = db.scalars(
        select(ModelFineTuneRun)
        .where(ModelFineTuneRun.project_id == project_id)
        .order_by(ModelFineTuneRun.created_at.desc(), ModelFineTuneRun.id.desc())
    ).all()
    return [_fine_tune_out(row) for row in rows]


@router.get("/fine-tunes/{fine_tune_run_id}", response_model=ModelFineTuneRunOut)
def get_fine_tune_run(
    fine_tune_run_id: str,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> ModelFineTuneRunOut:
    row = db.get(ModelFineTuneRun, fine_tune_run_id)
    if row is None:
        raise HTTPException(status_code=404, detail="fine-tune run not found")
    ensure_project_scope(db, principal, row.project_id)
    return _fine_tune_out(row)


@router.post("/fine-tunes/{fine_tune_run_id}/state", response_model=ModelFineTuneRunOut)
def update_fine_tune_state(
    fine_tune_run_id: str,
    payload: ModelFineTuneRunStateUpdate,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> ModelFineTuneRunOut:
    row = db.get(ModelFineTuneRun, fine_tune_run_id)
    if row is None:
        raise HTTPException(status_code=404, detail="fine-tune run not found")
    ensure_project_scope(db, principal, row.project_id)
    _authorize(principal, "dispatch", high_risk=True)

    row.status = payload.status
    if payload.latest_eval_run_id:
        eval_row = db.get(ModelEvalRun, payload.latest_eval_run_id)
        if eval_row is None:
            raise HTTPException(status_code=404, detail="latest_eval_run_id not found")
        if eval_row.project_id != row.project_id:
            raise HTTPException(status_code=403, detail="eval run scope denied")
        row.latest_eval_run_id = eval_row.id

    append_audit_event(
        db,
        tenant_id=principal.tenant_id,
        project_id=row.project_id,
        event_type="model.fine_tune_run.state_updated",
        payload={"fine_tune_run_id": row.id, "status": row.status, "notes": payload.notes},
        actor=build_actor_snapshot(db, principal, row.project_id),
        resource={"resource_type": "model_fine_tune_run", "resource_id": row.id},
    )
    db.commit()
    return _fine_tune_out(row)


def _create_promotion_row(
    *,
    db: Session,
    principal: Principal,
    payload: ModelPromotionCreate,
    eval_run: ModelEvalRun | None,
    reason_codes: list[str],
) -> ModelPromotion:
    status = "approved" if not reason_codes and payload.mode == "promote" else "deployed" if not reason_codes else "blocked"
    row = ModelPromotion(
        project_id=payload.project_id,
        provider=payload.provider,
        model=payload.model,
        environment=payload.environment,
        mode=payload.mode,
        fine_tune_run_id=payload.fine_tune_run_id,
        required_eval_run_id=eval_run.id if eval_run else payload.eval_run_id,
        status=status,
        reason_codes_json=json.dumps(reason_codes, sort_keys=True),
        approved_by_user_id=principal.user_id,
    )
    db.add(row)
    return row


@router.post("/promotions", response_model=ModelPromotionOut)
def create_model_promotion(
    payload: ModelPromotionCreate,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> ModelPromotionOut:
    ensure_project_scope(db, principal, payload.project_id)
    _authorize(principal, "dispatch", high_risk=True)
    eval_row, reasons = _enforce_eval_gate(
        db=db,
        principal=principal,
        project_id=payload.project_id,
        provider=payload.provider,
        model=payload.model,
        eval_run_id=payload.eval_run_id,
    )
    row = _create_promotion_row(
        db=db,
        principal=principal,
        payload=payload,
        eval_run=eval_row,
        reason_codes=reasons,
    )
    append_audit_event(
        db,
        tenant_id=principal.tenant_id,
        project_id=payload.project_id,
        event_type="model.promotion.requested" if not reasons else "model.promotion.blocked",
        payload={
            "promotion_id": row.id,
            "mode": payload.mode,
            "environment": payload.environment,
            "provider": payload.provider,
            "model": payload.model,
            "reason_codes": reasons,
        },
        actor=build_actor_snapshot(db, principal, payload.project_id),
        resource={"resource_type": "model_promotion", "resource_id": row.id},
    )
    db.commit()
    if reasons:
        raise HTTPException(status_code=409, detail={"reason": "eval_gate_failed", "reason_codes": reasons, "promotion_id": row.id})
    return _promotion_out(row)


@router.post("/deployments", response_model=ModelPromotionOut)
def create_model_deployment(
    payload: ModelPromotionCreate,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> ModelPromotionOut:
    deploy_payload = ModelPromotionCreate(
        project_id=payload.project_id,
        provider=payload.provider,
        model=payload.model,
        environment=payload.environment,
        fine_tune_run_id=payload.fine_tune_run_id,
        eval_run_id=payload.eval_run_id,
        mode="deploy",
    )
    return create_model_promotion(payload=deploy_payload, principal=principal, db=db)


@router.get("/promotions", response_model=list[ModelPromotionOut])
def list_model_promotions(
    project_id: str = Query(...),
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> list[ModelPromotionOut]:
    ensure_project_scope(db, principal, project_id)
    rows = db.scalars(
        select(ModelPromotion)
        .where(ModelPromotion.project_id == project_id)
        .order_by(ModelPromotion.created_at.desc(), ModelPromotion.id.desc())
    ).all()
    return [_promotion_out(row) for row in rows]
