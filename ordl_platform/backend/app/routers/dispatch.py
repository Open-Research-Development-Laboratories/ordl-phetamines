from __future__ import annotations

import json
import re

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.authz import evaluate_authorization
from app.common import default_project_policy_profiles, ensure_project_scope, get_config_state
from app.config import get_settings
from app.db import get_db
from app.dispatch import create_dispatch, execute_dispatch_request
from app.models import CollabMessage, DispatchEvent, DispatchExecution, DispatchRequest, DispatchResult
from app.providers import PROVIDER_REGISTRY
from app.schemas import (
    DispatchCreate,
    DispatchEventOut,
    DispatchExecuteRequest,
    DispatchExecutionOut,
    DispatchOut,
    DispatchResultOut,
)
from app.security import Principal, get_current_principal

router = APIRouter(prefix='/dispatch', tags=['dispatch'])


def _is_model_pinned(model: str, *, allowed_patterns: list[str], blocked_aliases: list[str]) -> bool:
    value = (model or "").strip()
    if not value:
        return False
    if value in set(str(x) for x in blocked_aliases):
        return False
    for pattern in allowed_patterns:
        try:
            if re.fullmatch(str(pattern), value):
                return True
        except re.error:
            continue
    return False


def _has_json_schema(payload: dict) -> bool:
    text = payload.get("text")
    if isinstance(text, dict):
        fmt = text.get("format")
        if isinstance(fmt, dict) and fmt.get("type") == "json_schema":
            return True
    response_format = payload.get("response_format")
    if isinstance(response_format, dict):
        if response_format.get("type") == "json_schema" and isinstance(response_format.get("json_schema"), dict):
            return True
    return False


def _validate_dispatch_policy(*, project_id: str, provider: str, model: str, request_payload: dict, db: Session, principal: Principal) -> None:
    settings = get_settings()
    profiles = get_config_state(
        db,
        tenant_id=principal.tenant_id,
        scope_type="project",
        scope_id=project_id,
        config_key="policy_profiles",
        default=default_project_policy_profiles(settings.environment),
    )
    if not isinstance(profiles, dict):
        profiles = default_project_policy_profiles(settings.environment)

    model_policy = profiles.get("model", {})
    if not isinstance(model_policy, dict):
        model_policy = {}
    enforce_pin = bool(model_policy.get("enforce_snapshot_pinning", True))
    allowed_patterns = model_policy.get("allowed_snapshot_patterns", [])
    blocked_aliases = model_policy.get("blocked_aliases", [])
    if not isinstance(allowed_patterns, list):
        allowed_patterns = []
    if not isinstance(blocked_aliases, list):
        blocked_aliases = []
    if enforce_pin and provider == "openai_codex":
        if not _is_model_pinned(model, allowed_patterns=[str(x) for x in allowed_patterns], blocked_aliases=[str(x) for x in blocked_aliases]):
            raise HTTPException(
                status_code=422,
                detail="model snapshot pinning policy violation: use pinned model snapshot for OpenAI dispatch",
            )

    instructions_policy = profiles.get("instructions", {})
    if not isinstance(instructions_policy, dict):
        instructions_policy = {}
    if provider == "openai_codex" and bool(instructions_policy.get("require_instructions_for_openai", False)):
        instructions = request_payload.get("instructions")
        min_len = int(instructions_policy.get("min_instruction_chars", 1))
        if not isinstance(instructions, str) or len(instructions.strip()) < min_len:
            raise HTTPException(
                status_code=422,
                detail="instructions policy violation: missing or too-short instructions for OpenAI request",
            )

    schema_policy = profiles.get("schema", {})
    if not isinstance(schema_policy, dict):
        schema_policy = {}
    if bool(schema_policy.get("require_json_schema_for_machine_consumed", False)):
        if bool(request_payload.get("machine_consumed", False)) and not _has_json_schema(request_payload):
            raise HTTPException(
                status_code=422,
                detail="schema policy violation: machine-consumed payload must provide JSON schema",
            )

    tooling_policy = profiles.get("tooling", {})
    if not isinstance(tooling_policy, dict):
        tooling_policy = {}
    if bool(tooling_policy.get("enforce_tool_allowlist", False)):
        allowed_tools = tooling_policy.get("allowed_tools", [])
        allowed_set = {str(t) for t in allowed_tools} if isinstance(allowed_tools, list) else set()
        tools = request_payload.get("tools", [])
        if isinstance(tools, list):
            for tool in tools:
                if isinstance(tool, dict):
                    name = str(tool.get("name") or tool.get("type") or "").strip()
                else:
                    name = str(tool).strip()
                if name and name not in allowed_set:
                    raise HTTPException(
                        status_code=422,
                        detail=f"tooling policy violation: tool '{name}' is not in project allowlist",
                    )


def _dispatch_out(row: DispatchRequest) -> DispatchOut:
    return DispatchOut(
        id=row.id,
        project_id=row.project_id,
        message_id=row.message_id,
        target_scope=row.target_scope,
        target_value=row.target_value,
        provider=row.provider,
        model=row.model,
        request_hash=row.request_hash,
        state=row.state,
    )


def _execution_out(row: DispatchExecution) -> DispatchExecutionOut:
    return DispatchExecutionOut(
        id=row.id,
        dispatch_request_id=row.dispatch_request_id,
        started_by_user_id=row.started_by_user_id,
        status=row.status,
        provider_reference=row.provider_reference,
        output_text=row.output_text,
        error_text=row.error_text,
        started_at=row.started_at.isoformat() if row.started_at else None,
        completed_at=row.completed_at.isoformat() if row.completed_at else None,
    )


def _event_out(row: DispatchEvent) -> DispatchEventOut:
    try:
        payload = json.loads(row.event_payload_json or "{}")
    except json.JSONDecodeError:
        payload = {}
    if not isinstance(payload, dict):
        payload = {"value": str(payload)}
    return DispatchEventOut(
        id=row.id,
        execution_id=row.execution_id,
        dispatch_request_id=row.dispatch_request_id,
        sequence=row.sequence,
        event_type=row.event_type,
        event_payload=payload,
        created_at=row.created_at.isoformat() if row.created_at else None,
    )


@router.post('', response_model=DispatchOut)
def dispatch_work(
    payload: DispatchCreate,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> DispatchOut:
    ensure_project_scope(db, principal, payload.project_id)
    if payload.provider not in PROVIDER_REGISTRY:
        raise HTTPException(status_code=422, detail=f"unsupported provider: {payload.provider}")

    auth = evaluate_authorization(principal, action='dispatch', high_risk=True)
    if auth.decision != 'allow':
        raise HTTPException(status_code=403, detail=f'dispatch denied: {auth.reason_codes}')

    _validate_dispatch_policy(
        project_id=payload.project_id,
        provider=payload.provider,
        model=payload.model,
        request_payload=payload.payload,
        db=db,
        principal=principal,
    )

    if payload.message_id:
        msg = db.get(CollabMessage, payload.message_id)
        if msg is None or msg.project_id != payload.project_id:
            raise HTTPException(status_code=404, detail='linked message not found')
        if msg.state != 'approved':
            raise HTTPException(status_code=400, detail='linked message must be approved before dispatch')

    request_row, _, _ = create_dispatch(
        db,
        tenant_id=principal.tenant_id,
        project_id=payload.project_id,
        requested_by_user_id=principal.user_id,
        message_id=payload.message_id,
        target_scope=payload.target_scope,
        target_value=payload.target_value,
        provider=payload.provider,
        model=payload.model,
        payload=payload.payload,
        policy_reason_codes=auth.reason_codes,
        settings=get_settings(),
    )
    db.commit()
    return _dispatch_out(request_row)


@router.get('', response_model=list[DispatchOut])
def list_dispatch(
    project_id: str,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> list[DispatchOut]:
    ensure_project_scope(db, principal, project_id)
    rows = db.scalars(
        select(DispatchRequest)
        .where(DispatchRequest.project_id == project_id)
        .order_by(DispatchRequest.created_at.asc(), DispatchRequest.id.asc())
    ).all()
    return [_dispatch_out(row) for row in rows]


@router.get('/results', response_model=list[DispatchResultOut])
def list_dispatch_results(
    dispatch_request_id: str,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> list[DispatchResultOut]:
    dispatch = db.get(DispatchRequest, dispatch_request_id)
    if dispatch is None:
        return []
    ensure_project_scope(db, principal, dispatch.project_id)
    rows = db.scalars(
        select(DispatchResult)
        .where(DispatchResult.dispatch_request_id == dispatch_request_id)
        .order_by(DispatchResult.created_at.asc(), DispatchResult.id.asc())
    ).all()
    return [
        DispatchResultOut(
            id=row.id,
            dispatch_request_id=row.dispatch_request_id,
            worker_id=row.worker_id,
            status=row.status,
            provider_reference=row.provider_reference,
            output=row.output,
            error=row.error,
        )
        for row in rows
    ]


@router.post('/{dispatch_request_id}/execute', response_model=DispatchExecutionOut)
def execute_dispatch(
    dispatch_request_id: str,
    payload: DispatchExecuteRequest,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> DispatchExecutionOut:
    dispatch = db.get(DispatchRequest, dispatch_request_id)
    if dispatch is None:
        raise HTTPException(status_code=404, detail='dispatch request not found')
    ensure_project_scope(db, principal, dispatch.project_id)

    auth = evaluate_authorization(principal, action='dispatch', high_risk=True)
    if auth.decision != 'allow':
        raise HTTPException(status_code=403, detail=f'dispatch denied: {auth.reason_codes}')

    if not payload.force and dispatch.state == 'failed':
        raise HTTPException(status_code=400, detail='dispatch is failed; use force=true to retry execution')

    execution, _, _ = execute_dispatch_request(
        db,
        tenant_id=principal.tenant_id,
        dispatch_request=dispatch,
        requested_by_user_id=principal.user_id,
        settings=get_settings(),
        policy_reason_codes=auth.reason_codes,
    )
    db.commit()
    return _execution_out(execution)


@router.get('/{dispatch_request_id}/executions', response_model=list[DispatchExecutionOut])
def list_dispatch_executions(
    dispatch_request_id: str,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> list[DispatchExecutionOut]:
    dispatch = db.get(DispatchRequest, dispatch_request_id)
    if dispatch is None:
        return []
    ensure_project_scope(db, principal, dispatch.project_id)
    rows = db.scalars(
        select(DispatchExecution)
        .where(DispatchExecution.dispatch_request_id == dispatch_request_id)
        .order_by(DispatchExecution.started_at.asc(), DispatchExecution.id.asc())
    ).all()
    return [_execution_out(row) for row in rows]


@router.get('/executions/{execution_id}/events', response_model=list[DispatchEventOut])
def list_execution_events(
    execution_id: str,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> list[DispatchEventOut]:
    execution = db.get(DispatchExecution, execution_id)
    if execution is None:
        return []
    dispatch = db.get(DispatchRequest, execution.dispatch_request_id)
    if dispatch is None:
        return []
    ensure_project_scope(db, principal, dispatch.project_id)
    rows = db.scalars(
        select(DispatchEvent)
        .where(DispatchEvent.execution_id == execution_id)
        .order_by(DispatchEvent.sequence.asc(), DispatchEvent.created_at.asc())
    ).all()
    return [_event_out(row) for row in rows]


@router.get('/executions/{execution_id}/stream')
def stream_execution_events(
    execution_id: str,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    execution = db.get(DispatchExecution, execution_id)
    if execution is None:
        raise HTTPException(status_code=404, detail='dispatch execution not found')
    dispatch = db.get(DispatchRequest, execution.dispatch_request_id)
    if dispatch is None:
        raise HTTPException(status_code=404, detail='dispatch request not found')
    ensure_project_scope(db, principal, dispatch.project_id)
    rows = db.scalars(
        select(DispatchEvent)
        .where(DispatchEvent.execution_id == execution_id)
        .order_by(DispatchEvent.sequence.asc(), DispatchEvent.created_at.asc())
    ).all()

    def _iter_sse():
        for row in rows:
            try:
                payload = json.loads(row.event_payload_json or "{}")
            except json.JSONDecodeError:
                payload = {}
            if not isinstance(payload, dict):
                payload = {"value": str(payload)}
            yield f"event: {row.event_type}\n"
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    return StreamingResponse(_iter_sse(), media_type='text/event-stream')
