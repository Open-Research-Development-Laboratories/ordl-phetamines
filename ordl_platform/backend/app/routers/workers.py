from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import append_audit_event, build_actor_snapshot
from app.authz import evaluate_authorization
from app.common import ensure_project_scope, json_list
from app.config import get_settings
from app.db import get_db
from app.models import (
    WorkerAction,
    WorkerDiscoveryScan,
    WorkerInstance,
    WorkerUpdateBundle,
    WorkerUpdateCampaign,
    WorkerUpdateExecution,
)
from app.policy import hash_request, validate_policy_token
from app.schemas import (
    WorkerActionRequest,
    WorkerConnectivityOut,
    WorkerDiscoveryScanCreate,
    WorkerDiscoveryScanOut,
    WorkerHeartbeatRequest,
    WorkerOut,
    WorkerProbeRequest,
    WorkerRegister,
    WorkerUpdateCampaignCreate,
    WorkerUpdateCampaignOut,
    WorkerUpdateCampaignRollback,
    WorkerUpdateCampaignStart,
    WorkerUpdateBundleCreate,
    WorkerUpdateBundleOut,
    WorkerUpdateExecutionOut,
)
from app.security import Principal, get_current_principal

router = APIRouter(prefix='/workers', tags=['workers'])


def _iso_or_none(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _reconnect_required(row: WorkerInstance, stale_after_seconds: int) -> bool:
    now = datetime.now(timezone.utc)
    if row.connectivity_state == 'down':
        return True
    keepalive_at = _as_utc(row.last_keepalive_at)
    if keepalive_at is None:
        return True
    age = (now - keepalive_at).total_seconds()
    return age > stale_after_seconds


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
    return normalized


def _dump_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def _authorize_worker_action(principal: Principal) -> None:
    auth = evaluate_authorization(principal, action='worker_action')
    if auth.decision != 'allow':
        raise HTTPException(status_code=403, detail=f'worker action denied: {auth.reason_codes}')


def _authorize_worker_read(principal: Principal) -> None:
    auth = evaluate_authorization(principal, action='read_project')
    if auth.decision == 'deny':
        raise HTTPException(status_code=403, detail=f'worker read denied: {auth.reason_codes}')


def _campaign_out(row: WorkerUpdateCampaign) -> WorkerUpdateCampaignOut:
    return WorkerUpdateCampaignOut(
        id=row.id,
        project_id=row.project_id,
        name=row.name,
        bundle_id=row.bundle_id,
        target_selector=_json_obj(row.target_selector_json),
        desired_version=row.desired_version,
        rollout_strategy=row.rollout_strategy,
        preflight_required=bool(row.preflight_required),
        backup_required=bool(row.backup_required),
        canary_batch_size=row.canary_batch_size,
        max_allowed_failures=row.max_allowed_failures,
        auto_rollback_on_halt=bool(row.auto_rollback_on_halt),
        halt_reason=row.halt_reason,
        state=row.state,
        created_by_user_id=row.created_by_user_id,
        started_at=_iso_or_none(row.started_at),
        completed_at=_iso_or_none(row.completed_at),
        rolled_back_at=_iso_or_none(row.rolled_back_at),
    )


def _execution_out(row: WorkerUpdateExecution) -> WorkerUpdateExecutionOut:
    return WorkerUpdateExecutionOut(
        id=row.id,
        campaign_id=row.campaign_id,
        worker_id=row.worker_id,
        state=row.state,
        preflight_ok=bool(row.preflight_ok),
        backup_ref=row.backup_ref,
        applied_version=row.applied_version,
        failure_reason=row.failure_reason,
        rollback_state=row.rollback_state,
        started_at=_iso_or_none(row.started_at),
        completed_at=_iso_or_none(row.completed_at),
    )


def _bundle_out(row: WorkerUpdateBundle) -> WorkerUpdateBundleOut:
    return WorkerUpdateBundleOut(
        id=row.id,
        project_id=row.project_id,
        name=row.name,
        version=row.version,
        digest=row.digest,
        signature=row.signature,
        signer=row.signer,
        artifact_uri=row.artifact_uri,
        metadata=_json_obj(row.metadata_json),
        status=row.status,
        created_by_user_id=row.created_by_user_id,
    )


def _scan_out(row: WorkerDiscoveryScan) -> WorkerDiscoveryScanOut:
    return WorkerDiscoveryScanOut(
        id=row.id,
        project_id=row.project_id,
        initiated_by_user_id=row.initiated_by_user_id,
        network_scope=row.network_scope,
        status=row.status,
        findings=_json_obj_list(row.findings_json),
        notes=row.notes,
        started_at=_iso_or_none(row.started_at),
        completed_at=_iso_or_none(row.completed_at),
    )


def _connectivity_out(row: WorkerInstance, stale_after_seconds: int) -> WorkerConnectivityOut:
    reconnect_targets = json_list(row.gateway_candidates_json)
    if row.last_gateway_url and row.last_gateway_url not in reconnect_targets:
        reconnect_targets.insert(0, row.last_gateway_url)
    return WorkerConnectivityOut(
        worker_id=row.id,
        worker_name=row.name,
        role=row.role,
        status=row.status,
        connectivity_state=row.connectivity_state,
        last_seen_at=_iso_or_none(row.last_seen_at),
        last_keepalive_at=_iso_or_none(row.last_keepalive_at),
        last_probe_at=_iso_or_none(row.last_probe_at),
        last_gateway_url=row.last_gateway_url,
        gateway_rtt_ms=row.gateway_rtt_ms,
        reconnect_required=_reconnect_required(row, stale_after_seconds=stale_after_seconds),
        reconnect_targets=reconnect_targets,
    )


def _select_workers_for_campaign(
    campaign: WorkerUpdateCampaign,
    workers: list[WorkerInstance],
    explicit_worker_ids: list[str],
) -> list[WorkerInstance]:
    selector = _json_obj(campaign.target_selector_json)
    selector_ids = [str(x) for x in selector.get('worker_ids', [])] if isinstance(selector.get('worker_ids'), list) else []
    selector_role = str(selector.get('role', '')).strip()
    selector_host_contains = str(selector.get('host_contains', '')).strip().lower()
    selector_capability = str(selector.get('capability', '')).strip()
    explicit = set(explicit_worker_ids)

    selected: list[WorkerInstance] = []
    for row in workers:
        if explicit and row.id not in explicit:
            continue
        if selector_ids and row.id not in selector_ids and row.device_id not in selector_ids:
            continue
        if selector_role and row.role != selector_role:
            continue
        if selector_host_contains and selector_host_contains not in (row.host or '').lower():
            continue
        if selector_capability:
            capabilities = set(json_list(row.capabilities_json))
            if selector_capability not in capabilities:
                continue
        selected.append(row)
    return selected


def _bundle_signature_payload(*, project_id: str, name: str, version: str, digest: str, signer: str, artifact_uri: str) -> str:
    canonical = {
        'project_id': project_id,
        'name': name,
        'version': version,
        'digest': digest,
        'signer': signer,
        'artifact_uri': artifact_uri,
    }
    return _dump_json(canonical)


def _expected_bundle_signature(*, payload: str) -> str:
    secret = get_settings().extension_signing_secret
    mac = hmac.new(secret.encode('utf-8'), payload.encode('utf-8'), hashlib.sha256)
    return mac.hexdigest()


def _verify_bundle_signature(
    *,
    project_id: str,
    name: str,
    version: str,
    digest: str,
    signer: str,
    artifact_uri: str,
    signature: str,
) -> bool:
    payload = _bundle_signature_payload(
        project_id=project_id,
        name=name,
        version=version,
        digest=digest,
        signer=signer,
        artifact_uri=artifact_uri,
    )
    expected = _expected_bundle_signature(payload=payload)
    return hmac.compare_digest(expected, signature)


@router.post('/register', response_model=WorkerOut)
def register_worker(
    payload: WorkerRegister,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> WorkerOut:
    ensure_project_scope(db, principal, payload.project_id)
    row = db.scalar(
        select(WorkerInstance).where(
            WorkerInstance.project_id == payload.project_id,
            WorkerInstance.device_id == payload.device_id,
        )
    )
    if row is None:
        row = WorkerInstance(
            project_id=payload.project_id,
            name=payload.name,
            role=payload.role,
            host=payload.host,
            device_id=payload.device_id,
            capabilities_json=json.dumps(payload.capabilities, sort_keys=True),
            status='online',
            connectivity_state='online',
            gateway_candidates_json='[]',
            last_seen_at=datetime.now(timezone.utc),
        )
        db.add(row)
    else:
        row.name = payload.name
        row.role = payload.role
        row.host = payload.host
        row.capabilities_json = json.dumps(payload.capabilities, sort_keys=True)
        row.status = 'online'
        row.connectivity_state = 'online'
        row.last_seen_at = datetime.now(timezone.utc)

    db.commit()
    return WorkerOut(
        id=row.id,
        project_id=row.project_id,
        name=row.name,
        role=row.role,
        host=row.host,
        device_id=row.device_id,
        status=row.status,
        capabilities=json_list(row.capabilities_json),
    )


@router.get('', response_model=list[WorkerOut])
def list_workers(
    project_id: str,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> list[WorkerOut]:
    ensure_project_scope(db, principal, project_id)
    _authorize_worker_read(principal)
    rows = db.scalars(select(WorkerInstance).where(WorkerInstance.project_id == project_id)).all()
    return [
        WorkerOut(
            id=row.id,
            project_id=row.project_id,
            name=row.name,
            role=row.role,
            host=row.host,
            device_id=row.device_id,
            status=row.status,
            capabilities=json_list(row.capabilities_json),
        )
        for row in rows
    ]


@router.post('/{worker_id}/action')
def queue_worker_action(
    worker_id: str,
    payload: WorkerActionRequest,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> dict:
    worker = db.get(WorkerInstance, worker_id)
    if worker is None:
        raise HTTPException(status_code=404, detail='worker not found')
    ensure_project_scope(db, principal, worker.project_id)
    _authorize_worker_action(principal)

    action = WorkerAction(
        worker_id=worker_id,
        action=payload.action,
        requested_by_user_id=principal.user_id,
        status='queued',
        notes=payload.notes,
    )
    db.add(action)
    db.commit()
    return {'worker_action_id': action.id, 'status': action.status}


@router.post('/{worker_id}/heartbeat')
def worker_heartbeat(
    worker_id: str,
    payload: WorkerHeartbeatRequest,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    worker = db.get(WorkerInstance, worker_id)
    if worker is None:
        raise HTTPException(status_code=404, detail='worker not found')
    ensure_project_scope(db, principal, worker.project_id)
    _authorize_worker_action(principal)

    now = datetime.now(timezone.utc)
    worker.status = 'online'
    worker.connectivity_state = payload.connectivity_state
    worker.last_gateway_url = payload.gateway_url
    worker.gateway_candidates_json = json.dumps(payload.gateway_candidates, sort_keys=True)
    worker.gateway_rtt_ms = payload.gateway_rtt_ms
    worker.keepalive_interval_seconds = payload.keepalive_interval_seconds
    worker.keepalive_miss_threshold = payload.keepalive_miss_threshold
    worker.last_keepalive_at = now
    worker.last_seen_at = now
    db.commit()
    return {
        'worker_id': worker.id,
        'status': worker.status,
        'connectivity_state': worker.connectivity_state,
        'last_keepalive_at': worker.last_keepalive_at.isoformat() if worker.last_keepalive_at else None,
    }


@router.post('/{worker_id}/probe')
def worker_probe(
    worker_id: str,
    payload: WorkerProbeRequest,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    worker = db.get(WorkerInstance, worker_id)
    if worker is None:
        raise HTTPException(status_code=404, detail='worker not found')
    ensure_project_scope(db, principal, worker.project_id)
    _authorize_worker_action(principal)

    now = datetime.now(timezone.utc)
    worker.last_probe_at = now
    worker.last_seen_at = now
    worker.last_gateway_url = payload.gateway_url or worker.last_gateway_url
    worker.gateway_rtt_ms = payload.gateway_rtt_ms
    if payload.reachable:
        worker.status = 'online'
        worker.connectivity_state = 'online'
    else:
        worker.status = 'degraded'
        worker.connectivity_state = 'down'
        if payload.reason:
            action = WorkerAction(
                worker_id=worker.id,
                action='gateway_probe_failed',
                requested_by_user_id=principal.user_id,
                status='recorded',
                notes=payload.reason,
            )
            db.add(action)
    db.commit()
    return {
        'worker_id': worker.id,
        'status': worker.status,
        'connectivity_state': worker.connectivity_state,
        'last_probe_at': worker.last_probe_at.isoformat() if worker.last_probe_at else None,
    }


@router.get('/connectivity', response_model=list[WorkerConnectivityOut])
def list_worker_connectivity(
    project_id: str,
    stale_after_seconds: int = 90,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> list[WorkerConnectivityOut]:
    ensure_project_scope(db, principal, project_id)
    _authorize_worker_read(principal)
    rows = db.scalars(select(WorkerInstance).where(WorkerInstance.project_id == project_id)).all()
    return [_connectivity_out(row, stale_after_seconds=stale_after_seconds) for row in rows]


@router.post('/update-bundles', response_model=WorkerUpdateBundleOut)
def create_update_bundle(
    payload: WorkerUpdateBundleCreate,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> WorkerUpdateBundleOut:
    ensure_project_scope(db, principal, payload.project_id)
    _authorize_worker_action(principal)
    if not _verify_bundle_signature(
        project_id=payload.project_id,
        name=payload.name,
        version=payload.version,
        digest=payload.digest,
        signer=payload.signer,
        artifact_uri=payload.artifact_uri,
        signature=payload.signature,
    ):
        raise HTTPException(status_code=400, detail='update bundle signature validation failed')

    row = WorkerUpdateBundle(
        project_id=payload.project_id,
        name=payload.name,
        version=payload.version,
        digest=payload.digest,
        signature=payload.signature,
        signer=payload.signer,
        artifact_uri=payload.artifact_uri,
        metadata_json=_dump_json(payload.metadata),
        status='active',
        created_by_user_id=principal.user_id,
    )
    db.add(row)
    db.flush()

    append_audit_event(
        db,
        tenant_id=principal.tenant_id,
        project_id=payload.project_id,
        event_type='worker_update_bundle.created',
        payload={
            'bundle_id': row.id,
            'name': row.name,
            'version': row.version,
            'digest': row.digest,
        },
        actor=build_actor_snapshot(db, principal, payload.project_id),
        resource={'resource_type': 'worker_update_bundle', 'resource_id': row.id},
    )
    db.commit()
    return _bundle_out(row)


@router.get('/update-bundles', response_model=list[WorkerUpdateBundleOut])
def list_update_bundles(
    project_id: str,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> list[WorkerUpdateBundleOut]:
    ensure_project_scope(db, principal, project_id)
    _authorize_worker_read(principal)
    rows = db.scalars(
        select(WorkerUpdateBundle)
        .where(WorkerUpdateBundle.project_id == project_id)
        .order_by(WorkerUpdateBundle.created_at.desc())
    ).all()
    return [_bundle_out(row) for row in rows]


@router.get('/update-bundles/{bundle_id}', response_model=WorkerUpdateBundleOut)
def get_update_bundle(
    bundle_id: str,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> WorkerUpdateBundleOut:
    row = db.get(WorkerUpdateBundle, bundle_id)
    if row is None:
        raise HTTPException(status_code=404, detail='update bundle not found')
    ensure_project_scope(db, principal, row.project_id)
    _authorize_worker_read(principal)
    return _bundle_out(row)


@router.post('/update-campaigns', response_model=WorkerUpdateCampaignOut)
def create_update_campaign(
    payload: WorkerUpdateCampaignCreate,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> WorkerUpdateCampaignOut:
    ensure_project_scope(db, principal, payload.project_id)
    _authorize_worker_action(principal)

    bundle: WorkerUpdateBundle | None = None
    if payload.bundle_id:
        bundle = db.get(WorkerUpdateBundle, payload.bundle_id)
        if bundle is None:
            raise HTTPException(status_code=404, detail='update bundle not found')
        if bundle.project_id != payload.project_id:
            raise HTTPException(status_code=400, detail='bundle must belong to the same project')
        if bundle.status != 'active':
            raise HTTPException(status_code=400, detail='bundle is not active')
        if bundle.version != payload.desired_version:
            raise HTTPException(status_code=400, detail='bundle version must match desired_version')
        if not _verify_bundle_signature(
            project_id=bundle.project_id,
            name=bundle.name,
            version=bundle.version,
            digest=bundle.digest,
            signer=bundle.signer,
            artifact_uri=bundle.artifact_uri,
            signature=bundle.signature,
        ):
            raise HTTPException(status_code=400, detail='bundle signature no longer valid')

    row = WorkerUpdateCampaign(
        project_id=payload.project_id,
        name=payload.name,
        bundle_id=payload.bundle_id,
        target_selector_json=_dump_json(payload.target_selector),
        desired_version=payload.desired_version,
        rollout_strategy=payload.rollout_strategy,
        preflight_required=1 if payload.preflight_required else 0,
        backup_required=1 if payload.backup_required else 0,
        canary_batch_size=payload.canary_batch_size,
        max_allowed_failures=payload.max_allowed_failures,
        auto_rollback_on_halt=1 if payload.auto_rollback_on_halt else 0,
        halt_reason='',
        state='draft',
        created_by_user_id=principal.user_id,
    )
    db.add(row)
    db.flush()

    append_audit_event(
        db,
        tenant_id=principal.tenant_id,
        project_id=payload.project_id,
        event_type='worker_update_campaign.created',
        payload={
            'campaign_id': row.id,
            'name': row.name,
            'rollout_strategy': row.rollout_strategy,
            'desired_version': row.desired_version,
            'bundle_id': row.bundle_id,
        },
        actor=build_actor_snapshot(db, principal, payload.project_id),
        resource={'resource_type': 'worker_update_campaign', 'resource_id': row.id},
    )
    db.commit()
    return _campaign_out(row)


@router.get('/update-campaigns', response_model=list[WorkerUpdateCampaignOut])
def list_update_campaigns(
    project_id: str,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> list[WorkerUpdateCampaignOut]:
    ensure_project_scope(db, principal, project_id)
    _authorize_worker_read(principal)
    rows = db.scalars(
        select(WorkerUpdateCampaign)
        .where(WorkerUpdateCampaign.project_id == project_id)
        .order_by(WorkerUpdateCampaign.created_at.asc())
    ).all()
    return [_campaign_out(row) for row in rows]


@router.post('/update-campaigns/{campaign_id}/start')
def start_update_campaign(
    campaign_id: str,
    payload: WorkerUpdateCampaignStart,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    campaign = db.get(WorkerUpdateCampaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail='update campaign not found')
    ensure_project_scope(db, principal, campaign.project_id)
    _authorize_worker_action(principal)
    if campaign.state == 'running':
        raise HTTPException(status_code=400, detail='campaign already running')
    if campaign.state in {'completed', 'rolled_back'}:
        raise HTTPException(status_code=400, detail='campaign has already completed')

    policy_payload = {
        'campaign_id': campaign.id,
        'project_id': campaign.project_id,
        'desired_version': campaign.desired_version,
        'requested_worker_ids': sorted([str(x) for x in payload.worker_ids]),
    }
    policy_hash = hash_request(policy_payload)
    validate_policy_token(
        token=payload.policy_token,
        expected_request_hash=policy_hash,
        expected_destination_scope='project',
        settings=get_settings(),
    )

    workers = db.scalars(select(WorkerInstance).where(WorkerInstance.project_id == campaign.project_id)).all()
    selected_workers = _select_workers_for_campaign(campaign, workers, payload.worker_ids)
    now = datetime.now(timezone.utc)

    if not selected_workers:
        campaign.state = 'failed'
        campaign.started_at = now
        campaign.completed_at = now
        append_audit_event(
            db,
            tenant_id=principal.tenant_id,
            project_id=campaign.project_id,
            event_type='worker_update_campaign.failed_no_targets',
            payload={'campaign_id': campaign.id},
            actor=build_actor_snapshot(db, principal, campaign.project_id),
            resource={'resource_type': 'worker_update_campaign', 'resource_id': campaign.id},
            severity='warn',
        )
        db.commit()
        return {'campaign': _campaign_out(campaign).model_dump(), 'selected_workers': 0}

    campaign.state = 'running'
    campaign.started_at = now
    campaign.halt_reason = ''

    batch_size = max(1, campaign.canary_batch_size)
    failures = 0
    successes = 0
    halted = False

    for idx, worker in enumerate(selected_workers):
        execution = db.scalar(
            select(WorkerUpdateExecution).where(
                WorkerUpdateExecution.campaign_id == campaign.id,
                WorkerUpdateExecution.worker_id == worker.id,
            )
        )
        if execution is None:
            execution = WorkerUpdateExecution(campaign_id=campaign.id, worker_id=worker.id)
            db.add(execution)
            db.flush()
        execution.started_at = now
        execution.rollback_state = 'not_requested'

        preflight_ok = worker.connectivity_state != 'down' and worker.status != 'degraded'
        if campaign.preflight_required and not preflight_ok:
            execution.state = 'failed'
            execution.preflight_ok = 0
            execution.backup_ref = ''
            execution.applied_version = ''
            execution.failure_reason = 'preflight_connectivity_down'
            execution.completed_at = now
            failures += 1
        else:
            execution.state = 'updated'
            execution.preflight_ok = 1
            execution.backup_ref = (
                f"snapshot:{worker.id}:{campaign.desired_version}:{int(now.timestamp())}"
                if campaign.backup_required
                else ''
            )
            execution.applied_version = campaign.desired_version
            execution.failure_reason = ''
            execution.completed_at = now
            successes += 1

        # Canary or rolling checkpoints evaluate failure thresholds at batch boundaries.
        if campaign.rollout_strategy in {'canary', 'rolling'}:
            boundary_reached = ((idx + 1) % batch_size == 0) or (idx + 1 == len(selected_workers))
            if boundary_reached and failures > campaign.max_allowed_failures:
                halted = True
                campaign.halt_reason = (
                    f'failure threshold exceeded: {failures} > {campaign.max_allowed_failures}'
                )
                break

    if halted:
        campaign.state = 'halted'
        campaign.completed_at = now
        campaign.rolled_back_at = None
        if campaign.auto_rollback_on_halt:
            executions = db.scalars(
                select(WorkerUpdateExecution).where(WorkerUpdateExecution.campaign_id == campaign.id)
            ).all()
            for execution in executions:
                if execution.state == 'updated':
                    execution.rollback_state = 'rolled_back'
                    execution.state = 'rolled_back'
                    execution.failure_reason = execution.failure_reason or 'automatic rollback after halt'
            campaign.state = 'halted_rolled_back'
            campaign.rolled_back_at = now
    else:
        campaign.state = 'completed'
        campaign.completed_at = now
        campaign.rolled_back_at = None

    append_audit_event(
        db,
        tenant_id=principal.tenant_id,
        project_id=campaign.project_id,
        event_type='worker_update_campaign.started',
        payload={
            'campaign_id': campaign.id,
            'selected_workers': len(selected_workers),
            'desired_version': campaign.desired_version,
            'policy_request_hash': policy_hash,
            'successes': successes,
            'failures': failures,
            'halted': halted,
            'halt_reason': campaign.halt_reason,
        },
        actor=build_actor_snapshot(db, principal, campaign.project_id),
        resource={'resource_type': 'worker_update_campaign', 'resource_id': campaign.id},
    )
    db.commit()
    return {
        'campaign': _campaign_out(campaign).model_dump(),
        'selected_workers': len(selected_workers),
        'successes': successes,
        'failures': failures,
        'halted': halted,
    }


@router.get('/update-campaigns/{campaign_id}/executions', response_model=list[WorkerUpdateExecutionOut])
def list_update_campaign_executions(
    campaign_id: str,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> list[WorkerUpdateExecutionOut]:
    campaign = db.get(WorkerUpdateCampaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail='update campaign not found')
    ensure_project_scope(db, principal, campaign.project_id)
    _authorize_worker_read(principal)
    rows = db.scalars(
        select(WorkerUpdateExecution)
        .where(WorkerUpdateExecution.campaign_id == campaign_id)
        .order_by(WorkerUpdateExecution.created_at.asc())
    ).all()
    return [_execution_out(row) for row in rows]


@router.post('/update-campaigns/{campaign_id}/rollback', response_model=WorkerUpdateCampaignOut)
def rollback_update_campaign(
    campaign_id: str,
    payload: WorkerUpdateCampaignRollback,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> WorkerUpdateCampaignOut:
    campaign = db.get(WorkerUpdateCampaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail='update campaign not found')
    ensure_project_scope(db, principal, campaign.project_id)
    _authorize_worker_action(principal)
    if campaign.state not in {'completed', 'running', 'failed', 'halted', 'halted_rolled_back'}:
        raise HTTPException(status_code=400, detail='campaign is not rollback eligible')

    now = datetime.now(timezone.utc)
    executions = db.scalars(select(WorkerUpdateExecution).where(WorkerUpdateExecution.campaign_id == campaign.id)).all()
    for execution in executions:
        execution.rollback_state = 'rolled_back'
        execution.state = 'rolled_back'
        if payload.reason and not execution.failure_reason:
            execution.failure_reason = payload.reason
        execution.updated_at = now

    campaign.state = 'rolled_back'
    campaign.rolled_back_at = now
    campaign.updated_at = now

    append_audit_event(
        db,
        tenant_id=principal.tenant_id,
        project_id=campaign.project_id,
        event_type='worker_update_campaign.rolled_back',
        payload={'campaign_id': campaign.id, 'reason': payload.reason},
        actor=build_actor_snapshot(db, principal, campaign.project_id),
        resource={'resource_type': 'worker_update_campaign', 'resource_id': campaign.id},
        severity='warn',
    )
    db.commit()
    return _campaign_out(campaign)


@router.post('/discovery/scans', response_model=WorkerDiscoveryScanOut)
def create_discovery_scan(
    payload: WorkerDiscoveryScanCreate,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> WorkerDiscoveryScanOut:
    ensure_project_scope(db, principal, payload.project_id)
    _authorize_worker_action(principal)

    now = datetime.now(timezone.utc)
    existing_workers = db.scalars(select(WorkerInstance).where(WorkerInstance.project_id == payload.project_id)).all()
    existing_by_host = {row.host: row for row in existing_workers if row.host}
    findings: list[dict[str, Any]] = []

    for host in payload.candidate_hosts:
        host_value = str(host).strip()
        if not host_value:
            continue
        existing = existing_by_host.get(host_value)
        if existing is not None:
            findings.append(
                {
                    'host': host_value,
                    'status': 'already_registered',
                    'worker_id': existing.id,
                    'role': existing.role,
                    'action': 'monitor_only',
                }
            )
            continue
        findings.append(
            {
                'host': host_value,
                'status': 'candidate',
                'recommended_role': 'builder',
                'auto_enroll': payload.auto_enroll,
                'action': 'evaluate_and_stage',
            }
        )

    if not payload.candidate_hosts:
        for row in existing_workers:
            findings.append(
                {
                    'host': row.host or row.device_id,
                    'status': 'existing',
                    'worker_id': row.id,
                    'role': row.role,
                    'connectivity_state': row.connectivity_state,
                }
            )

    row = WorkerDiscoveryScan(
        project_id=payload.project_id,
        initiated_by_user_id=principal.user_id,
        network_scope=payload.network_scope,
        status='completed',
        findings_json=_dump_json(findings),
        notes=payload.notes,
        started_at=now,
        completed_at=now,
    )
    db.add(row)
    db.flush()

    append_audit_event(
        db,
        tenant_id=principal.tenant_id,
        project_id=payload.project_id,
        event_type='worker.discovery_scan.completed',
        payload={
            'scan_id': row.id,
            'network_scope': row.network_scope,
            'finding_count': len(findings),
        },
        actor=build_actor_snapshot(db, principal, payload.project_id),
        resource={'resource_type': 'worker_discovery_scan', 'resource_id': row.id},
    )
    db.commit()
    return _scan_out(row)


@router.get('/discovery/scans', response_model=list[WorkerDiscoveryScanOut])
def list_discovery_scans(
    project_id: str,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> list[WorkerDiscoveryScanOut]:
    ensure_project_scope(db, principal, project_id)
    _authorize_worker_read(principal)
    rows = db.scalars(
        select(WorkerDiscoveryScan)
        .where(WorkerDiscoveryScan.project_id == project_id)
        .order_by(WorkerDiscoveryScan.created_at.desc())
    ).all()
    return [_scan_out(row) for row in rows]


@router.get('/discovery/scans/{scan_id}', response_model=WorkerDiscoveryScanOut)
def get_discovery_scan(
    scan_id: str,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> WorkerDiscoveryScanOut:
    row = db.get(WorkerDiscoveryScan, scan_id)
    if row is None:
        raise HTTPException(status_code=404, detail='discovery scan not found')
    ensure_project_scope(db, principal, row.project_id)
    _authorize_worker_read(principal)
    return _scan_out(row)
