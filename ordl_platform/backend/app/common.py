from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import Iterable

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CollabMessage, Org, Project, SeatAssignment, Team, Tenant, User
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
