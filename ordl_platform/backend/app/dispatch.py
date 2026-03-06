from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import append_audit_event
from app.config import Settings
from app.models import DispatchEvent, DispatchExecution, DispatchRequest, DispatchResult, PolicyDecision, ProviderCredential
from app.policy import hash_request, issue_policy_token
from app.providers import get_provider_adapter


def _json_obj(value: str | None) -> dict[str, Any]:
    try:
        parsed = json.loads(value or "{}")
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _provider_metadata(db: Session, *, tenant_id: str, provider: str) -> dict[str, Any]:
    row = db.scalar(
        select(ProviderCredential).where(
            ProviderCredential.tenant_id == tenant_id,
            ProviderCredential.provider == provider,
        )
    )
    if row is None:
        return {}
    data = _json_obj(row.metadata_json)
    data["auth_mode"] = row.auth_mode
    data["configured"] = (row.configured == "true")
    return data


def _append_dispatch_event(
    db: Session,
    *,
    execution_id: str,
    dispatch_request_id: str,
    sequence: int,
    event_type: str,
    payload: dict[str, Any],
) -> DispatchEvent:
    row = DispatchEvent(
        execution_id=execution_id,
        dispatch_request_id=dispatch_request_id,
        sequence=sequence,
        event_type=event_type,
        event_payload_json=json.dumps(payload, sort_keys=True, ensure_ascii=False),
    )
    db.add(row)
    db.flush()
    return row


def execute_dispatch_request(
    db: Session,
    *,
    tenant_id: str,
    dispatch_request: DispatchRequest,
    requested_by_user_id: str,
    settings: Settings,
    policy_reason_codes: list[str] | None = None,
) -> tuple[DispatchExecution, DispatchResult, PolicyDecision]:
    token, nonce = issue_policy_token(
        request_hash_value=dispatch_request.request_hash,
        destination_scope=dispatch_request.target_scope,
        decision="allow",
        policy_version="v1",
        settings=settings,
    )

    policy_decision = PolicyDecision(
        project_id=dispatch_request.project_id,
        user_id=requested_by_user_id,
        action="dispatch",
        resource_type="dispatch_request",
        resource_id=dispatch_request.id,
        decision="allow",
        reason_codes_json=json.dumps(policy_reason_codes or ["policy_allow"], sort_keys=True),
        request_hash=dispatch_request.request_hash,
        token_nonce=nonce,
    )
    db.add(policy_decision)
    db.flush()

    execution = DispatchExecution(
        dispatch_request_id=dispatch_request.id,
        started_by_user_id=requested_by_user_id,
        status="running",
        started_at=datetime.now(timezone.utc),
    )
    db.add(execution)
    db.flush()

    payload = _json_obj(dispatch_request.payload_json)
    provider_meta = _provider_metadata(db, tenant_id=tenant_id, provider=dispatch_request.provider)

    status = "failed"
    provider_reference = ""
    output_text = ""
    error_text = ""
    event_rows: list[dict[str, Any]]

    try:
        adapter = get_provider_adapter(dispatch_request.provider)
        adapter_result = adapter.execute(
            policy_token=token,
            request_hash=dispatch_request.request_hash,
            destination_scope=dispatch_request.target_scope,
            payload=payload,
            model=dispatch_request.model,
            settings=settings,
            provider_metadata=provider_meta,
        )
        status = adapter_result.status
        provider_reference = adapter_result.provider_reference
        output_text = adapter_result.output_text
        error_text = adapter_result.error_text
        event_rows = adapter_result.events or []
    except Exception as exc:
        error_text = str(exc)
        event_rows = [
            {"event_type": "execution.started", "payload": {"provider": dispatch_request.provider, "model": dispatch_request.model}},
            {"event_type": "provider.error", "payload": {"error": error_text}},
            {"event_type": "execution.failed", "payload": {"status": "failed"}},
        ]

    sequence = 1
    for event in event_rows:
        event_type = str(event.get("event_type", "info"))
        payload_obj = event.get("payload", {})
        if not isinstance(payload_obj, dict):
            payload_obj = {"value": str(payload_obj)}
        _append_dispatch_event(
            db,
            execution_id=execution.id,
            dispatch_request_id=dispatch_request.id,
            sequence=sequence,
            event_type=event_type,
            payload=payload_obj,
        )
        sequence += 1

    execution.provider_reference = provider_reference
    execution.output_text = output_text
    execution.error_text = error_text
    execution.status = "completed" if status in {"accepted", "completed"} else "failed"
    execution.completed_at = datetime.now(timezone.utc)
    execution.updated_at = execution.completed_at

    dispatch_result = DispatchResult(
        dispatch_request_id=dispatch_request.id,
        worker_id=dispatch_request.target_value,
        status=status,
        provider_reference=provider_reference,
        output=output_text,
        error=error_text,
    )
    db.add(dispatch_result)

    dispatch_request.state = "dispatched" if status in {"accepted", "completed"} else "failed"
    db.flush()

    append_audit_event(
        db,
        tenant_id=tenant_id,
        project_id=dispatch_request.project_id,
        event_type="dispatch.executed" if dispatch_request.state == "dispatched" else "dispatch.failed",
        payload={
            "dispatch_request_id": dispatch_request.id,
            "dispatch_execution_id": execution.id,
            "provider": dispatch_request.provider,
            "model": dispatch_request.model,
            "target_scope": dispatch_request.target_scope,
            "target_value": dispatch_request.target_value,
            "status": status,
            "error": error_text,
        },
        actor={"actor_type": "user", "actor_id": requested_by_user_id},
        resource={"resource_type": "dispatch_request", "resource_id": dispatch_request.id},
        run_id=execution.id,
        classification="dispatch",
        severity="error" if dispatch_request.state == "failed" else "info",
    )
    db.flush()
    return execution, dispatch_result, policy_decision


def create_dispatch(
    db: Session,
    *,
    tenant_id: str,
    project_id: str,
    requested_by_user_id: str,
    message_id: str | None,
    target_scope: str,
    target_value: str,
    provider: str,
    model: str,
    payload: dict[str, Any],
    policy_reason_codes: list[str],
    settings: Settings,
) -> tuple[DispatchRequest, DispatchResult, PolicyDecision]:
    request_hash_value = hash_request(
        {
            "project_id": project_id,
            "target_scope": target_scope,
            "target_value": target_value,
            "provider": provider,
            "model": model,
            "payload": payload,
        }
    )

    dispatch_request = DispatchRequest(
        project_id=project_id,
        requested_by_user_id=requested_by_user_id,
        message_id=message_id,
        target_scope=target_scope,
        target_value=target_value,
        provider=provider,
        model=model,
        payload_json=json.dumps(payload, sort_keys=True),
        request_hash=request_hash_value,
        state="queued",
    )
    db.add(dispatch_request)
    db.flush()

    _, dispatch_result, policy_decision = execute_dispatch_request(
        db,
        tenant_id=tenant_id,
        dispatch_request=dispatch_request,
        requested_by_user_id=requested_by_user_id,
        settings=settings,
        policy_reason_codes=policy_reason_codes,
    )
    return dispatch_request, dispatch_result, policy_decision

