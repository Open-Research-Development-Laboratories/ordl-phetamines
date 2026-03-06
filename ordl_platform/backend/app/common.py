from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import Iterable

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CollabMessage, ConfigState, Org, Project, SeatAssignment, Team, Tenant, User
from app.security import Principal


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def json_list(value: str | None) -> list[str]:
    try:
        loaded = json.loads(value or '[]')
    except json.JSONDecodeError:
        return []
    if not isinstance(loaded, list):
        return []
    return [str(item) for item in loaded]


def json_obj(value: str | None, default: dict | None = None) -> dict:
    fallback = default or {}
    try:
        loaded = json.loads(value or '{}')
    except json.JSONDecodeError:
        return dict(fallback)
    if not isinstance(loaded, dict):
        return dict(fallback)
    return loaded


def default_project_policy_profiles(environment: str = "development") -> dict:
    env = (environment or "development").lower()
    prod_like = env in {"production", "prod"}
    return {
        "version": "v1",
        "model": {
            "enforce_snapshot_pinning": True if prod_like else True,
            "allowed_snapshot_patterns": [
                r".*-\d{4}-\d{2}-\d{2}$",
                r".*\.\d+(\.\d+)?([.-][A-Za-z0-9_]+)?$",
            ],
            "blocked_aliases": [
                "gpt-5",
                "gpt-5-mini",
                "gpt-5-nano",
                "gpt-4.1",
                "gpt-4o",
                "gpt-4o-mini",
                "o3",
                "o4-mini",
            ],
            "require_eval_for_promotion": True,
            "min_eval_score_bp": 8000,
        },
        "instructions": {
            "require_instructions_for_openai": False,
            "min_instruction_chars": 12,
        },
        "schema": {
            "require_json_schema_for_machine_consumed": True,
            "require_strict_json_schema": True,
        },
        "tooling": {
            "enforce_tool_allowlist": False,
            "allowed_tools": [],
        },
    }


def get_config_state(
    db: Session,
    *,
    tenant_id: str,
    scope_type: str,
    scope_id: str,
    config_key: str,
    default: dict | list | None = None,
) -> dict | list:
    row = db.scalar(
        select(ConfigState).where(
            ConfigState.tenant_id == tenant_id,
            ConfigState.scope_type == scope_type,
            ConfigState.scope_id == scope_id,
            ConfigState.config_key == config_key,
        )
    )
    if row is None:
        if default is None:
            return {}
        return default
    try:
        parsed = json.loads(row.value_json or '{}')
    except json.JSONDecodeError:
        return default if default is not None else {}
    if default is not None and not isinstance(parsed, type(default)):
        return default
    return parsed


def upsert_config_state(
    db: Session,
    *,
    tenant_id: str,
    scope_type: str,
    scope_id: str,
    config_key: str,
    value: dict | list,
    updated_by_user_id: str,
) -> ConfigState:
    row = db.scalar(
        select(ConfigState).where(
            ConfigState.tenant_id == tenant_id,
            ConfigState.scope_type == scope_type,
            ConfigState.scope_id == scope_id,
            ConfigState.config_key == config_key,
        )
    )
    if row is None:
        row = ConfigState(
            tenant_id=tenant_id,
            scope_type=scope_type,
            scope_id=scope_id,
            config_key=config_key,
            updated_by_user_id=updated_by_user_id,
        )
        db.add(row)
    row.value_json = json.dumps(value, sort_keys=True)
    row.updated_by_user_id = updated_by_user_id
    return row


def ensure_tenant_scope(db: Session, principal: Principal) -> Tenant:
    tenant = db.get(Tenant, principal.tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail='tenant not found')
    return tenant


def ensure_user_scope(db: Session, principal: Principal) -> User:
    user = db.get(User, principal.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail='user not found')
    return user


def ensure_project_scope(db: Session, principal: Principal, project_id: str) -> Project:
    project = db.scalar(
        select(Project)
        .join(Team, Team.id == Project.team_id)
        .join(Org, Org.id == Team.org_id)
        .where(
            Project.id == project_id,
            Org.tenant_id == principal.tenant_id,
        )
    )
    if project is None:
        project_exists = db.scalar(select(Project.id).where(Project.id == project_id))
        if project_exists is None:
            raise HTTPException(status_code=404, detail='project not found')
        raise HTTPException(status_code=403, detail='project tenant scope denied')

    is_officer = any(role in {'officer', 'board_member'} for role in principal.roles)
    if not is_officer:
        seat_id = db.scalar(
            select(SeatAssignment.id).where(
                SeatAssignment.project_id == project_id,
                SeatAssignment.user_id == principal.user_id,
                SeatAssignment.status == 'active',
            )
        )
        if seat_id is None:
            raise HTTPException(status_code=403, detail='project scope denied')
    return project


def message_transition_allowed(message: CollabMessage, principal: Principal, target_state: str) -> bool:
    transitions = {
        'draft': {'review', 'superseded'},
        'review': {'draft', 'approved', 'superseded'},
        'approved': {'dispatched', 'superseded'},
        'dispatched': {'superseded'},
        'superseded': set(),
    }
    next_states: Iterable[str] = transitions.get(message.state, set())
    if target_state not in next_states:
        return False
    if principal.user_id in {message.author_user_id, message.reviewer_user_id}:
        return True
    return any(role in {'officer', 'board_member'} for role in principal.roles)
