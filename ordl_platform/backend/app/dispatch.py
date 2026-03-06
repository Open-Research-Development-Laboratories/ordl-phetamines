from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.audit import append_audit_event
from app.config import Settings
from app.models import DispatchRequest, DispatchResult, PolicyDecision
from app.policy import hash_request, issue_policy_token
from app.providers import get_provider_adapter


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
    payload: dict,
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

    token, nonce = issue_policy_token(
        request_hash_value=request_hash_value,
        destination_scope=target_scope,
        decision="allow",
        policy_version="v1",
        settings=settings,
    )

    policy_decision = PolicyDecision(
        project_id=project_id,
        user_id=requested_by_user_id,
        action="dispatch",
        resource_type="dispatch_request",
        resource_id=dispatch_request.id,
        decision="allow",
        reason_codes_json=json.dumps(policy_reason_codes, sort_keys=True),
        request_hash=request_hash_value,
        token_nonce=nonce,
    )
    db.add(policy_decision)
    db.flush()

    status = "accepted"
    provider_reference = ""
    error_text = ""
    dispatch_state = "dispatched"
    try:
        adapter = get_provider_adapter(provider)
        adapter_result = adapter.send(
            policy_token=token,
            request_hash=request_hash_value,
            destination_scope=target_scope,
            payload=payload,
            settings=settings,
        )
        status = adapter_result.status
        provider_reference = adapter_result.provider_reference
    except Exception as exc:
        # Keep a durable trail of provider failures instead of dropping the request.
        status = "failed"
        provider_reference = ""
        error_text = str(exc)
        dispatch_state = "failed"

    dispatch_result = DispatchResult(
        dispatch_request_id=dispatch_request.id,
        worker_id=target_value,
        status=status,
        provider_reference=provider_reference,
        output="",
        error=error_text,
    )
    db.add(dispatch_result)
    dispatch_request.state = dispatch_state

    append_audit_event(
        db,
        tenant_id=tenant_id,
        project_id=project_id,
        event_type="dispatch.created" if dispatch_state == "dispatched" else "dispatch.failed",
        payload={
            "dispatch_request_id": dispatch_request.id,
            "provider": provider,
            "model": model,
            "target_scope": target_scope,
            "target_value": target_value,
            "status": status,
            "error": error_text,
        },
        actor={"actor_type": "user", "actor_id": requested_by_user_id},
        resource={"resource_type": "dispatch_request", "resource_id": dispatch_request.id},
        run_id=dispatch_request.id,
        classification="dispatch",
        severity="error" if dispatch_state == "failed" else "info",
    )
    db.flush()
    return dispatch_request, dispatch_result, policy_decision
