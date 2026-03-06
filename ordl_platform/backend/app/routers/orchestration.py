from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import append_audit_event, build_actor_snapshot
from app.authz import evaluate_authorization
from app.common import ensure_project_scope, json_list
from app.db import get_db
from app.models import (
    JobDeliveryReceipt,
    JobRun,
    JobTemplate,
    OrchestrationProfile,
    WorkerGroup,
)
from app.schemas import (
    JobDeliveryCreate,
    JobDeliveryOut,
    JobRunCreate,
    JobRunOut,
    JobRunStateTransition,
    JobTemplateCreate,
    JobTemplateOut,
    OrchestrationProfileCreate,
    OrchestrationProfileOut,
    WorkerGroupCreate,
    WorkerGroupOut,
)
from app.security import Principal, get_current_principal

router = APIRouter(tags=['orchestration'])


JOB_TRANSITIONS: dict[str, set[str]] = {
    'created': {'queued'},
    'queued': {'dispatching', 'canceled'},
    'dispatching': {'running', 'retrying', 'failed', 'canceled'},
    'running': {'postback_pending', 'retrying', 'failed', 'canceled'},
    'postback_pending': {'delivered', 'failed_visibility'},
    'retrying': {'running', 'failed'},
    'failed': {'escalated'},
    'failed_visibility': {'escalated'},
    'delivered': {'closed'},
    'escalated': {'closed'},
    'closed': set(),
    'canceled': set(),
}


def _json_obj(value: str | None) -> dict[str, Any]:
    try:
        parsed = json.loads(value or '{}')
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _json_obj_list(value: str | None) -> list[dict[str, Any]]:
    try:
        parsed = json.loads(value or '[]')
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    normalized: list[dict[str, Any]] = []
    for item in parsed:
        if isinstance(item, dict):
            normalized.append(item)
        else:
            normalized.append({'value': str(item)})
    return normalized


def _dump_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def _worker_group_out(row: WorkerGroup) -> WorkerGroupOut:
    return WorkerGroupOut(
        id=row.id,
        project_id=row.project_id,
        name=row.name,
        routing_strategy=row.routing_strategy,
        selection_mode=row.selection_mode,
        target_role=row.target_role,
        capability_tags=json_list(row.capability_tags_json),
        worker_ids=json_list(row.worker_ids_json),
        failover_group_id=row.failover_group_id,
    )


def _profile_out(row: OrchestrationProfile) -> OrchestrationProfileOut:
    return OrchestrationProfileOut(
        id=row.id,
        project_id=row.project_id,
        name=row.name,
        routing_mode=row.routing_mode,
        target_group_id=row.target_group_id,
        failover_group_id=row.failover_group_id,
        quality_bar=row.quality_bar,
        max_parallel=row.max_parallel,
        retry_max_attempts=row.retry_max_attempts,
        retry_backoff_seconds=row.retry_backoff_seconds,
        postback_required=bool(row.postback_required),
        visible_body_required=bool(row.visible_body_required),
        max_chunk_chars=row.max_chunk_chars,
        owner_principal_id=row.owner_principal_id,
        report_to=json_list(row.report_to_json),
        escalation_to=json_list(row.escalation_to_json),
        visibility_mode=row.visibility_mode,
        status=row.status,
    )


def _template_out(row: JobTemplate) -> JobTemplateOut:
    return JobTemplateOut(
        id=row.id,
        project_id=row.project_id,
        name=row.name,
        version=row.version,
        objective=row.objective,
        required_inputs=json_list(row.required_inputs_json),
        constraints=_json_obj(row.constraints_json),
        output_schema=_json_obj(row.output_schema_json),
        default_profile_id=row.default_profile_id,
        report_to=json_list(row.report_to_json),
        escalation_to=json_list(row.escalation_to_json),
        visibility_mode=row.visibility_mode,
        status=row.status,
    )


def _job_run_out(row: JobRun) -> JobRunOut:
    return JobRunOut(
        id=row.id,
        project_id=row.project_id,
        template_id=row.template_id,
        profile_id=row.profile_id,
        owner_principal_id=row.owner_principal_id,
        report_to=json_list(row.report_to_json),
        escalation_to=json_list(row.escalation_to_json),
        visibility_mode=row.visibility_mode,
        routing_mode=row.routing_mode,
        target_group_id=row.target_group_id,
        target_worker_id=row.target_worker_id,
        target_role=row.target_role,
        objective=row.objective,
        input_payload=_json_obj(row.input_payload_json),
        state=row.state,
        attempt_count=row.attempt_count,
        artifact_summary=_json_obj_list(row.artifact_summary_json),
        last_error=row.last_error,
        state_reason=row.state_reason,
    )


def _delivery_out(row: JobDeliveryReceipt) -> JobDeliveryOut:
    return JobDeliveryOut(
        id=row.id,
        job_run_id=row.job_run_id,
        project_id=row.project_id,
        recipient=row.recipient,
        channel=row.channel,
        status=row.status,
        detail=_json_obj(row.detail_json),
        delivered_at=row.delivered_at.isoformat() if row.delivered_at else None,
    )


def _authorize_orchestration(principal: Principal, manage: bool = False) -> None:
    action = 'manage_seats' if manage else 'dispatch'
    auth = evaluate_authorization(principal, action=action)
    if auth.decision != 'allow':
        raise HTTPException(status_code=403, detail=f'orchestration denied: {auth.reason_codes}')


@router.post('/worker-groups', response_model=WorkerGroupOut)
def create_worker_group(
    payload: WorkerGroupCreate,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> WorkerGroupOut:
    _authorize_orchestration(principal, manage=True)
    ensure_project_scope(db, principal, payload.project_id)

    if payload.failover_group_id:
        failover = db.get(WorkerGroup, payload.failover_group_id)
        if failover is None or failover.project_id != payload.project_id:
            raise HTTPException(status_code=400, detail='failover group must be in the same project')

    row = WorkerGroup(
        project_id=payload.project_id,
        name=payload.name,
        routing_strategy=payload.routing_strategy,
        selection_mode=payload.selection_mode,
        target_role=payload.target_role,
        capability_tags_json=_dump_json(payload.capability_tags),
        worker_ids_json=_dump_json(payload.worker_ids),
        failover_group_id=payload.failover_group_id,
        created_by_user_id=principal.user_id,
    )
    db.add(row)
    db.flush()

    append_audit_event(
        db,
        tenant_id=principal.tenant_id,
        project_id=payload.project_id,
        event_type='worker_group.created',
        payload={
            'worker_group_id': row.id,
            'name': row.name,
            'routing_strategy': row.routing_strategy,
            'selection_mode': row.selection_mode,
        },
        actor=build_actor_snapshot(db, principal, payload.project_id),
        resource={'resource_type': 'worker_group', 'resource_id': row.id},
    )
    db.commit()
    return _worker_group_out(row)


@router.get('/worker-groups', response_model=list[WorkerGroupOut])
def list_worker_groups(
    project_id: str,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> list[WorkerGroupOut]:
    ensure_project_scope(db, principal, project_id)
    rows = db.scalars(select(WorkerGroup).where(WorkerGroup.project_id == project_id).order_by(WorkerGroup.created_at.asc())).all()
    return [_worker_group_out(row) for row in rows]


@router.post('/orchestration/profiles', response_model=OrchestrationProfileOut)
def create_orchestration_profile(
    payload: OrchestrationProfileCreate,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> OrchestrationProfileOut:
    _authorize_orchestration(principal, manage=True)
    ensure_project_scope(db, principal, payload.project_id)

    if not payload.report_to:
        raise HTTPException(status_code=400, detail='report_to recipients are required')

    for group_id in [payload.target_group_id, payload.failover_group_id]:
        if not group_id:
            continue
        group = db.get(WorkerGroup, group_id)
        if group is None or group.project_id != payload.project_id:
            raise HTTPException(status_code=400, detail='profile groups must exist in the same project')

    row = OrchestrationProfile(
        project_id=payload.project_id,
        name=payload.name,
        routing_mode=payload.routing_mode,
        target_group_id=payload.target_group_id,
        failover_group_id=payload.failover_group_id,
        quality_bar=payload.quality_bar,
        max_parallel=payload.max_parallel,
        retry_max_attempts=payload.retry_max_attempts,
        retry_backoff_seconds=payload.retry_backoff_seconds,
        postback_required=1 if payload.postback_required else 0,
        visible_body_required=1 if payload.visible_body_required else 0,
        max_chunk_chars=payload.max_chunk_chars,
        owner_principal_id=payload.owner_principal_id,
        report_to_json=_dump_json(payload.report_to),
        escalation_to_json=_dump_json(payload.escalation_to),
        visibility_mode=payload.visibility_mode,
        status=payload.status,
        created_by_user_id=principal.user_id,
    )
    db.add(row)
    db.flush()

    append_audit_event(
        db,
        tenant_id=principal.tenant_id,
        project_id=payload.project_id,
        event_type='orchestration_profile.created',
        payload={
            'profile_id': row.id,
            'name': row.name,
            'routing_mode': row.routing_mode,
            'owner_principal_id': row.owner_principal_id,
        },
        actor=build_actor_snapshot(db, principal, payload.project_id),
        resource={'resource_type': 'orchestration_profile', 'resource_id': row.id},
    )
    db.commit()
    return _profile_out(row)


@router.get('/orchestration/profiles', response_model=list[OrchestrationProfileOut])
def list_orchestration_profiles(
    project_id: str,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> list[OrchestrationProfileOut]:
    ensure_project_scope(db, principal, project_id)
    rows = db.scalars(
        select(OrchestrationProfile)
        .where(OrchestrationProfile.project_id == project_id)
        .order_by(OrchestrationProfile.created_at.asc())
    ).all()
    return [_profile_out(row) for row in rows]


@router.post('/jobs/templates', response_model=JobTemplateOut)
def create_job_template(
    payload: JobTemplateCreate,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> JobTemplateOut:
    _authorize_orchestration(principal, manage=True)
    ensure_project_scope(db, principal, payload.project_id)

    if payload.default_profile_id:
        profile = db.get(OrchestrationProfile, payload.default_profile_id)
        if profile is None or profile.project_id != payload.project_id:
            raise HTTPException(status_code=400, detail='default_profile_id must exist in the same project')

    row = JobTemplate(
        project_id=payload.project_id,
        name=payload.name,
        version=payload.version,
        objective=payload.objective,
        required_inputs_json=_dump_json(payload.required_inputs),
        constraints_json=_dump_json(payload.constraints),
        output_schema_json=_dump_json(payload.output_schema),
        default_profile_id=payload.default_profile_id,
        report_to_json=_dump_json(payload.report_to),
        escalation_to_json=_dump_json(payload.escalation_to),
        visibility_mode=payload.visibility_mode,
        status=payload.status,
        created_by_user_id=principal.user_id,
    )
    db.add(row)
    db.flush()

    append_audit_event(
        db,
        tenant_id=principal.tenant_id,
        project_id=payload.project_id,
        event_type='job_template.created',
        payload={
            'template_id': row.id,
            'name': row.name,
            'version': row.version,
        },
        actor=build_actor_snapshot(db, principal, payload.project_id),
        resource={'resource_type': 'job_template', 'resource_id': row.id},
    )
    db.commit()
    return _template_out(row)


@router.get('/jobs/templates', response_model=list[JobTemplateOut])
def list_job_templates(
    project_id: str,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> list[JobTemplateOut]:
    ensure_project_scope(db, principal, project_id)
    rows = db.scalars(
        select(JobTemplate)
        .where(JobTemplate.project_id == project_id)
        .order_by(JobTemplate.created_at.asc())
    ).all()
    return [_template_out(row) for row in rows]


@router.post('/jobs/runs', response_model=JobRunOut)
def create_job_run(
    payload: JobRunCreate,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> JobRunOut:
    _authorize_orchestration(principal, manage=False)
    ensure_project_scope(db, principal, payload.project_id)

    template: JobTemplate | None = None
    if payload.template_id:
        template = db.get(JobTemplate, payload.template_id)
        if template is None or template.project_id != payload.project_id:
            raise HTTPException(status_code=404, detail='template not found')

    profile_id = payload.profile_id or (template.default_profile_id if template else None)
    profile: OrchestrationProfile | None = None
    if profile_id:
        profile = db.get(OrchestrationProfile, profile_id)
        if profile is None or profile.project_id != payload.project_id:
            raise HTTPException(status_code=404, detail='profile not found')

    objective = payload.objective.strip() or (template.objective if template else '')
    report_to = list(payload.report_to)
    escalation_to = list(payload.escalation_to)

    if not report_to and template:
        report_to = json_list(template.report_to_json)
    if not escalation_to and template:
        escalation_to = json_list(template.escalation_to_json)
    if not report_to and profile:
        report_to = json_list(profile.report_to_json)
    if not escalation_to and profile:
        escalation_to = json_list(profile.escalation_to_json)

    if not report_to:
        raise HTTPException(status_code=400, detail='job run requires explicit report_to recipients')

    target_group_id = payload.target_group_id or (profile.target_group_id if profile else None)
    if target_group_id:
        group = db.get(WorkerGroup, target_group_id)
        if group is None or group.project_id != payload.project_id:
            raise HTTPException(status_code=400, detail='target_group_id must exist in the same project')

    run = JobRun(
        project_id=payload.project_id,
        template_id=payload.template_id,
        profile_id=profile_id,
        owner_principal_id=payload.owner_principal_id,
        report_to_json=_dump_json(report_to),
        escalation_to_json=_dump_json(escalation_to),
        visibility_mode=payload.visibility_mode,
        routing_mode=payload.routing_mode,
        target_group_id=target_group_id,
        target_worker_id=payload.target_worker_id,
        target_role=payload.target_role,
        objective=objective,
        input_payload_json=_dump_json(payload.input_payload),
        state='created',
        created_by_user_id=principal.user_id,
    )
    db.add(run)
    db.flush()

    append_audit_event(
        db,
        tenant_id=principal.tenant_id,
        project_id=payload.project_id,
        event_type='job_run.created',
        payload={
            'job_run_id': run.id,
            'template_id': run.template_id,
            'profile_id': run.profile_id,
            'routing_mode': run.routing_mode,
            'report_to': report_to,
        },
        actor=build_actor_snapshot(db, principal, payload.project_id),
        resource={'resource_type': 'job_run', 'resource_id': run.id},
        trace_id=run.id,
        run_id=run.id,
    )
    db.commit()
    return _job_run_out(run)


@router.get('/jobs/runs', response_model=list[JobRunOut])
def list_job_runs(
    project_id: str,
    state: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=2000),
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> list[JobRunOut]:
    ensure_project_scope(db, principal, project_id)
    stmt = (
        select(JobRun)
        .where(JobRun.project_id == project_id)
        .order_by(JobRun.created_at.desc())
        .limit(limit)
    )
    if state:
        stmt = stmt.where(JobRun.state == state)
    rows = db.scalars(stmt).all()
    return [_job_run_out(row) for row in rows]


@router.post('/jobs/runs/{job_run_id}/state', response_model=JobRunOut)
def transition_job_run_state(
    job_run_id: str,
    payload: JobRunStateTransition,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> JobRunOut:
    _authorize_orchestration(principal, manage=False)
    row = db.get(JobRun, job_run_id)
    if row is None:
        raise HTTPException(status_code=404, detail='job run not found')
    ensure_project_scope(db, principal, row.project_id)

    allowed = JOB_TRANSITIONS.get(row.state, set())
    if payload.target_state not in allowed:
        raise HTTPException(status_code=400, detail=f'invalid transition: {row.state} -> {payload.target_state}')

    previous = row.state
    row.state = payload.target_state
    row.state_reason = payload.state_reason

    now = datetime.now(timezone.utc)
    if payload.target_state == 'retrying':
        row.attempt_count += 1
    if payload.target_state == 'running' and row.started_at is None:
        row.started_at = now
    if payload.target_state in {'delivered', 'closed'} and row.completed_at is None:
        row.completed_at = now
    if payload.target_state == 'canceled' and row.canceled_at is None:
        row.canceled_at = now
    if payload.target_state in {'failed', 'failed_visibility'} and payload.state_reason:
        row.last_error = payload.state_reason

    append_audit_event(
        db,
        tenant_id=principal.tenant_id,
        project_id=row.project_id,
        event_type='job_run.state_transitioned',
        payload={
            'job_run_id': row.id,
            'from_state': previous,
            'to_state': payload.target_state,
            'state_reason': payload.state_reason,
        },
        actor=build_actor_snapshot(db, principal, row.project_id),
        resource={'resource_type': 'job_run', 'resource_id': row.id},
        trace_id=row.id,
        run_id=row.id,
    )
    db.commit()
    return _job_run_out(row)


@router.post('/jobs/runs/{job_run_id}/cancel', response_model=JobRunOut)
def cancel_job_run(
    job_run_id: str,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> JobRunOut:
    _authorize_orchestration(principal, manage=False)
    row = db.get(JobRun, job_run_id)
    if row is None:
        raise HTTPException(status_code=404, detail='job run not found')
    ensure_project_scope(db, principal, row.project_id)

    if 'canceled' not in JOB_TRANSITIONS.get(row.state, set()):
        raise HTTPException(status_code=400, detail=f'job run cannot be canceled from state={row.state}')

    previous = row.state
    row.state = 'canceled'
    row.state_reason = 'canceled_by_request'
    row.canceled_at = datetime.now(timezone.utc)

    append_audit_event(
        db,
        tenant_id=principal.tenant_id,
        project_id=row.project_id,
        event_type='job_run.canceled',
        payload={
            'job_run_id': row.id,
            'from_state': previous,
            'to_state': 'canceled',
        },
        actor=build_actor_snapshot(db, principal, row.project_id),
        resource={'resource_type': 'job_run', 'resource_id': row.id},
        trace_id=row.id,
        run_id=row.id,
    )
    db.commit()
    return _job_run_out(row)


@router.get('/jobs/runs/{job_run_id}/artifacts')
def get_job_run_artifacts(
    job_run_id: str,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    row = db.get(JobRun, job_run_id)
    if row is None:
        raise HTTPException(status_code=404, detail='job run not found')
    ensure_project_scope(db, principal, row.project_id)
    artifacts = _json_obj_list(row.artifact_summary_json)
    return {
        'job_run_id': row.id,
        'project_id': row.project_id,
        'artifact_count': len(artifacts),
        'artifacts': artifacts,
    }


@router.post('/jobs/runs/{job_run_id}/delivery', response_model=JobDeliveryOut)
def record_job_delivery(
    job_run_id: str,
    payload: JobDeliveryCreate,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> JobDeliveryOut:
    _authorize_orchestration(principal, manage=False)
    run = db.get(JobRun, job_run_id)
    if run is None:
        raise HTTPException(status_code=404, detail='job run not found')
    ensure_project_scope(db, principal, run.project_id)

    expected_recipients = set(json_list(run.report_to_json))
    if expected_recipients and payload.recipient not in expected_recipients:
        raise HTTPException(status_code=400, detail='recipient is not in job run report_to route')

    now = datetime.now(timezone.utc)
    receipt = JobDeliveryReceipt(
        job_run_id=run.id,
        project_id=run.project_id,
        recipient=payload.recipient,
        channel=payload.channel,
        status=payload.status,
        detail_json=_dump_json(payload.detail),
        delivered_at=now if payload.status == 'delivered' else None,
    )
    db.add(receipt)
    db.flush()

    artifacts = _json_obj_list(run.artifact_summary_json)
    artifacts.append(
        {
            'delivery_receipt_id': receipt.id,
            'recipient': payload.recipient,
            'channel': payload.channel,
            'status': payload.status,
            'delivered_at': receipt.delivered_at.isoformat() if receipt.delivered_at else None,
        }
    )
    run.artifact_summary_json = _dump_json(artifacts)

    if payload.status == 'delivered' and run.state not in {'delivered', 'closed'}:
        run.state = 'delivered'
        run.completed_at = now
        run.state_reason = 'delivery_recorded'
    elif payload.status == 'failed':
        run.state = 'failed_visibility'
        run.last_error = str(payload.detail.get('error', 'delivery failed'))
        run.state_reason = 'delivery_failed'

    append_audit_event(
        db,
        tenant_id=principal.tenant_id,
        project_id=run.project_id,
        event_type='job_run.delivery_recorded',
        payload={
            'job_run_id': run.id,
            'delivery_receipt_id': receipt.id,
            'recipient': payload.recipient,
            'channel': payload.channel,
            'status': payload.status,
        },
        actor=build_actor_snapshot(db, principal, run.project_id),
        resource={'resource_type': 'job_delivery_receipt', 'resource_id': receipt.id},
        trace_id=run.id,
        run_id=run.id,
    )
    db.commit()
    return _delivery_out(receipt)


@router.get('/jobs/runs/{job_run_id}/delivery', response_model=list[JobDeliveryOut])
def list_job_delivery_receipts(
    job_run_id: str,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> list[JobDeliveryOut]:
    run = db.get(JobRun, job_run_id)
    if run is None:
        raise HTTPException(status_code=404, detail='job run not found')
    ensure_project_scope(db, principal, run.project_id)
    rows = db.scalars(
        select(JobDeliveryReceipt)
        .where(JobDeliveryReceipt.job_run_id == job_run_id)
        .order_by(JobDeliveryReceipt.created_at.asc())
    ).all()
    return [_delivery_out(row) for row in rows]
