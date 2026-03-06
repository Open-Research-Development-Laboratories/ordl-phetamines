from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import append_audit_event, build_actor_snapshot
from app.common import (
    default_project_policy_profiles,
    ensure_project_scope,
    ensure_tenant_scope,
    get_config_state,
    upsert_config_state,
)
from app.config import get_settings
from app.db import get_db
from app.models import Org, Project, SeatAssignment, Team
from app.schemas import (
    OrgBoardMemberCreate,
    OrgBoardMemberUpdate,
    OrgCreate,
    OrgCurrentUpdate,
    OrgOut,
    OrgPolicyDefaultsUpdate,
    OrgRegionCreate,
    OrgRegionUpdate,
    ProjectCreate,
    ProjectDefaultsUpdate,
    ProjectOut,
    ProjectPolicyProfilesUpdate,
    TeamCreate,
    TeamOut,
    TeamScopeMatrixUpdate,
)
from app.security import Principal, get_current_principal

router = APIRouter(tags=['governance'])


def _first_org_for_tenant(db: Session, tenant_id: str) -> Org:
    org = db.scalar(select(Org).where(Org.tenant_id == tenant_id).order_by(Org.created_at.asc()).limit(1))
    if org is None:
        raise HTTPException(status_code=404, detail='org not found for tenant')
    return org


def _org_in_tenant(db: Session, tenant_id: str, org_id: str) -> Org:
    org = db.get(Org, org_id)
    if org is None:
        raise HTTPException(status_code=404, detail='org not found')
    if org.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail='tenant scope denied')
    return org


@router.post('/orgs', response_model=OrgOut)
def create_org(
    payload: OrgCreate,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> OrgOut:
    ensure_tenant_scope(db, principal)
    if payload.tenant_id != principal.tenant_id and 'board_member' not in principal.roles:
        raise HTTPException(status_code=403, detail='tenant scope denied')

    org = Org(
        tenant_id=payload.tenant_id,
        name=payload.name,
        owner_user_id=principal.user_id,
        board_scope_mode='scoped',
    )
    db.add(org)
    append_audit_event(
        db,
        tenant_id=payload.tenant_id,
        project_id=None,
        event_type='org.created',
        payload={'org_name': payload.name, 'owner_user_id': principal.user_id},
        actor=build_actor_snapshot(db, principal),
        resource={'resource_type': 'org', 'resource_id': org.id},
    )
    db.commit()
    return OrgOut(
        id=org.id,
        tenant_id=org.tenant_id,
        name=org.name,
        owner_user_id=org.owner_user_id,
        board_scope_mode=org.board_scope_mode,
    )


@router.get('/orgs', response_model=list[OrgOut])
def list_orgs(principal: Principal = Depends(get_current_principal), db: Session = Depends(get_db)) -> list[OrgOut]:
    rows = db.scalars(select(Org).where(Org.tenant_id == principal.tenant_id)).all()
    return [
        OrgOut(
            id=row.id,
            tenant_id=row.tenant_id,
            name=row.name,
            owner_user_id=row.owner_user_id,
            board_scope_mode=row.board_scope_mode,
        )
        for row in rows
    ]


@router.get('/orgs/current', response_model=OrgOut)
def get_current_org(
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> OrgOut:
    org = _first_org_for_tenant(db, principal.tenant_id)
    return OrgOut(
        id=org.id,
        tenant_id=org.tenant_id,
        name=org.name,
        owner_user_id=org.owner_user_id,
        board_scope_mode=org.board_scope_mode,
    )


@router.patch('/orgs/current', response_model=OrgOut)
def patch_current_org(
    payload: OrgCurrentUpdate,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> OrgOut:
    org = _first_org_for_tenant(db, principal.tenant_id)
    if payload.name is not None:
        org.name = payload.name
    if payload.board_scope_mode is not None:
        org.board_scope_mode = payload.board_scope_mode
    append_audit_event(
        db,
        tenant_id=principal.tenant_id,
        project_id=None,
        event_type='org.updated',
        payload={'org_id': org.id, 'name': org.name, 'board_scope_mode': org.board_scope_mode},
        actor=build_actor_snapshot(db, principal),
        resource={'resource_type': 'org', 'resource_id': org.id},
    )
    db.commit()
    return OrgOut(
        id=org.id,
        tenant_id=org.tenant_id,
        name=org.name,
        owner_user_id=org.owner_user_id,
        board_scope_mode=org.board_scope_mode,
    )


@router.get('/orgs/board')
def list_org_board(
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> list[dict]:
    members = get_config_state(
        db,
        tenant_id=principal.tenant_id,
        scope_type='org',
        scope_id='current',
        config_key='board_members',
        default=[],
    )
    return members


@router.post('/orgs/board')
def add_org_board_member(
    payload: OrgBoardMemberCreate,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> dict:
    members = get_config_state(
        db,
        tenant_id=principal.tenant_id,
        scope_type='org',
        scope_id='current',
        config_key='board_members',
        default=[],
    )
    record = {
        'id': str(uuid.uuid4()),
        'name': payload.name,
        'role': payload.role,
        'clearance': payload.clearance,
        'appointed': payload.appointed,
        'expires': payload.expires,
        'status': payload.status,
    }
    members.append(record)
    upsert_config_state(
        db,
        tenant_id=principal.tenant_id,
        scope_type='org',
        scope_id='current',
        config_key='board_members',
        value=members,
        updated_by_user_id=principal.user_id,
    )
    append_audit_event(
        db,
        tenant_id=principal.tenant_id,
        project_id=None,
        event_type='org.board_member.added',
        payload=record,
        actor=build_actor_snapshot(db, principal),
        resource={'resource_type': 'org_board_member', 'resource_id': record['id']},
    )
    db.commit()
    return record


@router.patch('/orgs/board/{member_id}')
def patch_org_board_member(
    member_id: str,
    payload: OrgBoardMemberUpdate,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> dict:
    members = get_config_state(
        db,
        tenant_id=principal.tenant_id,
        scope_type='org',
        scope_id='current',
        config_key='board_members',
        default=[],
    )
    target = next((item for item in members if item.get('id') == member_id), None)
    if target is None:
        raise HTTPException(status_code=404, detail='board member not found')
    patch = payload.model_dump(exclude_none=True)
    target.update(patch)
    upsert_config_state(
        db,
        tenant_id=principal.tenant_id,
        scope_type='org',
        scope_id='current',
        config_key='board_members',
        value=members,
        updated_by_user_id=principal.user_id,
    )
    append_audit_event(
        db,
        tenant_id=principal.tenant_id,
        project_id=None,
        event_type='org.board_member.updated',
        payload={'member_id': member_id, 'patch': patch},
        actor=build_actor_snapshot(db, principal),
        resource={'resource_type': 'org_board_member', 'resource_id': member_id},
    )
    db.commit()
    return target


@router.delete('/orgs/board/{member_id}')
def delete_org_board_member(
    member_id: str,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> dict:
    members = get_config_state(
        db,
        tenant_id=principal.tenant_id,
        scope_type='org',
        scope_id='current',
        config_key='board_members',
        default=[],
    )
    filtered = [item for item in members if item.get('id') != member_id]
    if len(filtered) == len(members):
        raise HTTPException(status_code=404, detail='board member not found')
    upsert_config_state(
        db,
        tenant_id=principal.tenant_id,
        scope_type='org',
        scope_id='current',
        config_key='board_members',
        value=filtered,
        updated_by_user_id=principal.user_id,
    )
    append_audit_event(
        db,
        tenant_id=principal.tenant_id,
        project_id=None,
        event_type='org.board_member.removed',
        payload={'member_id': member_id},
        actor=build_actor_snapshot(db, principal),
        resource={'resource_type': 'org_board_member', 'resource_id': member_id},
    )
    db.commit()
    return {'status': 'removed', 'member_id': member_id}


@router.get('/orgs/board/{member_id}/history')
def org_board_member_history(
    member_id: str,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> list[dict]:
    rows = db.execute(
        select(Project.id)  # cheap no-op scope check path through tenant context
        .join(Team, Team.id == Project.team_id)
        .join(Org, Org.id == Team.org_id)
        .where(Org.tenant_id == principal.tenant_id)
        .limit(1)
    ).all()
    _ = rows  # explicitly consume scope check query

    from app.models import AuditEvent

    events = db.scalars(
        select(AuditEvent)
        .where(
            AuditEvent.tenant_id == principal.tenant_id,
            AuditEvent.event_type.like('org.board_member.%'),
        )
        .order_by(AuditEvent.created_at.desc())
        .limit(200)
    ).all()
    history: list[dict] = []
    for event in events:
        payload = json.loads(event.payload_json or '{}')
        if payload.get('member_id') == member_id or payload.get('id') == member_id:
            history.append(
                {
                    'event_type': event.event_type,
                    'payload': payload,
                    'created_at': event.created_at.isoformat(),
                }
            )
    return history


@router.get('/orgs/regions')
def list_org_regions(
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> list[dict]:
    return get_config_state(
        db,
        tenant_id=principal.tenant_id,
        scope_type='org',
        scope_id='current',
        config_key='regions',
        default=[],
    )


@router.post('/orgs/regions')
def add_org_region(
    payload: OrgRegionCreate,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> dict:
    regions = get_config_state(
        db,
        tenant_id=principal.tenant_id,
        scope_type='org',
        scope_id='current',
        config_key='regions',
        default=[],
    )
    if any(item.get('code') == payload.code for item in regions):
        raise HTTPException(status_code=409, detail='region already exists')
    record = payload.model_dump()
    regions.append(record)
    upsert_config_state(
        db,
        tenant_id=principal.tenant_id,
        scope_type='org',
        scope_id='current',
        config_key='regions',
        value=regions,
        updated_by_user_id=principal.user_id,
    )
    db.commit()
    return record


@router.patch('/orgs/regions/{code}')
def patch_org_region(
    code: str,
    payload: OrgRegionUpdate,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> dict:
    regions = get_config_state(
        db,
        tenant_id=principal.tenant_id,
        scope_type='org',
        scope_id='current',
        config_key='regions',
        default=[],
    )
    target = next((item for item in regions if item.get('code') == code), None)
    if target is None:
        raise HTTPException(status_code=404, detail='region not found')
    target.update(payload.model_dump(exclude_none=True))
    upsert_config_state(
        db,
        tenant_id=principal.tenant_id,
        scope_type='org',
        scope_id='current',
        config_key='regions',
        value=regions,
        updated_by_user_id=principal.user_id,
    )
    db.commit()
    return target


@router.get('/orgs/policy-defaults')
def get_org_policy_defaults(
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> dict:
    return get_config_state(
        db,
        tenant_id=principal.tenant_id,
        scope_type='org',
        scope_id='current',
        config_key='policy_defaults',
        default={},
    )


@router.put('/orgs/policy-defaults')
def put_org_policy_defaults(
    payload: OrgPolicyDefaultsUpdate,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> dict:
    upsert_config_state(
        db,
        tenant_id=principal.tenant_id,
        scope_type='org',
        scope_id='current',
        config_key='policy_defaults',
        value=payload.defaults,
        updated_by_user_id=principal.user_id,
    )
    db.commit()
    return payload.defaults


@router.post('/teams', response_model=TeamOut)
def create_team(
    payload: TeamCreate,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> TeamOut:
    org = db.get(Org, payload.org_id)
    if org is None:
        raise HTTPException(status_code=404, detail='org not found')
    if org.tenant_id != principal.tenant_id:
        raise HTTPException(status_code=403, detail='tenant scope denied')

    team = Team(org_id=payload.org_id, name=payload.name)
    db.add(team)
    db.commit()
    return TeamOut(id=team.id, org_id=team.org_id, name=team.name)


@router.get('/teams', response_model=list[TeamOut])
def list_teams(
    org_id: str | None = Query(default=None),
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> list[TeamOut]:
    stmt = select(Team)
    if org_id:
        stmt = stmt.where(Team.org_id == org_id)
    rows = db.scalars(stmt).all()

    results: list[TeamOut] = []
    for row in rows:
        org = db.get(Org, row.org_id)
        if org and org.tenant_id == principal.tenant_id:
            results.append(TeamOut(id=row.id, org_id=row.org_id, name=row.name))
    return results


@router.post('/projects', response_model=ProjectOut)
def create_project(
    payload: ProjectCreate,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> ProjectOut:
    team = db.get(Team, payload.team_id)
    if team is None:
        raise HTTPException(status_code=404, detail='team not found')
    org = db.get(Org, team.org_id)
    if org is None or org.tenant_id != principal.tenant_id:
        raise HTTPException(status_code=403, detail='tenant scope denied')

    project = Project(
        team_id=payload.team_id,
        code=payload.code,
        name=payload.name,
        ingress_mode=payload.ingress_mode,
        visibility_mode=payload.visibility_mode,
    )
    db.add(project)
    db.flush()

    owner = SeatAssignment(
        project_id=project.id,
        user_id=principal.user_id,
        role='officer',
        rank='owner',
        position='project_owner',
        group_name='leadership',
        clearance_tier=principal.clearance_tier,
        compartments_json=json.dumps(principal.compartments, sort_keys=True),
        status='active',
    )
    db.add(owner)

    append_audit_event(
        db,
        tenant_id=principal.tenant_id,
        project_id=project.id,
        event_type='project.created',
        payload={'project_code': project.code, 'project_name': project.name},
        actor=build_actor_snapshot(db, principal, project.id),
        resource={'resource_type': 'project', 'resource_id': project.id},
    )

    db.commit()
    return ProjectOut(
        id=project.id,
        team_id=project.team_id,
        code=project.code,
        name=project.name,
        ingress_mode=project.ingress_mode,
        visibility_mode=project.visibility_mode,
    )


@router.get('/projects', response_model=list[ProjectOut])
def list_projects(
    team_id: str | None = Query(default=None),
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> list[ProjectOut]:
    stmt = select(Project)
    if team_id:
        stmt = stmt.where(Project.team_id == team_id)
    rows = db.scalars(stmt).all()
    results: list[ProjectOut] = []

    for row in rows:
        team = db.get(Team, row.team_id)
        if not team:
            continue
        org = db.get(Org, team.org_id)
        if org and org.tenant_id == principal.tenant_id:
            results.append(
                ProjectOut(
                    id=row.id,
                    team_id=row.team_id,
                    code=row.code,
                    name=row.name,
                    ingress_mode=row.ingress_mode,
                    visibility_mode=row.visibility_mode,
                )
            )
    return results


@router.get('/projects/{project_id}', response_model=ProjectOut)
def get_project(project_id: str, principal: Principal = Depends(get_current_principal), db: Session = Depends(get_db)) -> ProjectOut:
    project = ensure_project_scope(db, principal, project_id)
    return ProjectOut(
        id=project.id,
        team_id=project.team_id,
        code=project.code,
        name=project.name,
        ingress_mode=project.ingress_mode,
        visibility_mode=project.visibility_mode,
    )


@router.put('/projects/{project_id}/defaults')
def put_project_defaults(
    project_id: str,
    payload: ProjectDefaultsUpdate,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> dict:
    ensure_project_scope(db, principal, project_id)
    upsert_config_state(
        db,
        tenant_id=principal.tenant_id,
        scope_type='project',
        scope_id=project_id,
        config_key='defaults',
        value=payload.defaults,
        updated_by_user_id=principal.user_id,
    )
    db.commit()
    return payload.defaults


@router.get('/projects/{project_id}/policy-profiles')
def get_project_policy_profiles(
    project_id: str,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> dict:
    ensure_project_scope(db, principal, project_id)
    settings = get_settings()
    return get_config_state(
        db,
        tenant_id=principal.tenant_id,
        scope_type='project',
        scope_id=project_id,
        config_key='policy_profiles',
        default=default_project_policy_profiles(settings.environment),
    )


@router.put('/projects/{project_id}/policy-profiles')
def put_project_policy_profiles(
    project_id: str,
    payload: ProjectPolicyProfilesUpdate,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> dict:
    ensure_project_scope(db, principal, project_id)
    profiles = payload.profiles
    if not isinstance(profiles, dict):
        raise HTTPException(status_code=422, detail='profiles must be an object')
    settings = get_settings()
    merged = default_project_policy_profiles(settings.environment)
    merged.update(profiles)
    upsert_config_state(
        db,
        tenant_id=principal.tenant_id,
        scope_type='project',
        scope_id=project_id,
        config_key='policy_profiles',
        value=merged,
        updated_by_user_id=principal.user_id,
    )
    append_audit_event(
        db,
        tenant_id=principal.tenant_id,
        project_id=project_id,
        event_type='project.policy_profiles.updated',
        payload={'project_id': project_id, 'sections': sorted([str(k) for k in merged.keys()])},
        actor=build_actor_snapshot(db, principal, project_id),
        resource={'resource_type': 'project_policy_profiles', 'resource_id': project_id},
    )
    db.commit()
    return merged


@router.put('/teams/{team_id}/scope')
def put_team_scope_matrix(
    team_id: str,
    payload: TeamScopeMatrixUpdate,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> dict:
    team = db.get(Team, team_id)
    if team is None:
        raise HTTPException(status_code=404, detail='team not found')
    org = db.get(Org, team.org_id)
    if org is None or org.tenant_id != principal.tenant_id:
        raise HTTPException(status_code=403, detail='tenant scope denied')
    upsert_config_state(
        db,
        tenant_id=principal.tenant_id,
        scope_type='team',
        scope_id=team_id,
        config_key='scope_matrix',
        value=payload.scope_matrix,
        updated_by_user_id=principal.user_id,
    )
    db.commit()
    return payload.scope_matrix


@router.get('/orgs/{org_id}', response_model=OrgOut)
def get_org_by_id(
    org_id: str,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> OrgOut:
    org = _org_in_tenant(db, principal.tenant_id, org_id)
    return OrgOut(
        id=org.id,
        tenant_id=org.tenant_id,
        name=org.name,
        owner_user_id=org.owner_user_id,
        board_scope_mode=org.board_scope_mode,
    )


@router.put('/orgs/{org_id}', response_model=OrgOut)
def put_org_by_id(
    org_id: str,
    payload: OrgCurrentUpdate,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> OrgOut:
    org = _org_in_tenant(db, principal.tenant_id, org_id)
    if payload.name is not None:
        org.name = payload.name
    if payload.board_scope_mode is not None:
        org.board_scope_mode = payload.board_scope_mode
    append_audit_event(
        db,
        tenant_id=principal.tenant_id,
        project_id=None,
        event_type='org.updated',
        payload={'org_id': org.id, 'name': org.name, 'board_scope_mode': org.board_scope_mode},
        actor=build_actor_snapshot(db, principal),
        resource={'resource_type': 'org', 'resource_id': org.id},
    )
    db.commit()
    return OrgOut(
        id=org.id,
        tenant_id=org.tenant_id,
        name=org.name,
        owner_user_id=org.owner_user_id,
        board_scope_mode=org.board_scope_mode,
    )


@router.put('/orgs/{org_id}/defaults')
def put_org_defaults_by_id(
    org_id: str,
    payload: OrgPolicyDefaultsUpdate,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> dict:
    _org_in_tenant(db, principal.tenant_id, org_id)
    upsert_config_state(
        db,
        tenant_id=principal.tenant_id,
        scope_type='org',
        scope_id=org_id,
        config_key='policy_defaults',
        value=payload.defaults,
        updated_by_user_id=principal.user_id,
    )
    db.commit()
    return payload.defaults


@router.post('/orgs/{org_id}/members')
def add_org_member_by_id(
    org_id: str,
    payload: OrgBoardMemberCreate,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> dict:
    _org_in_tenant(db, principal.tenant_id, org_id)
    members = get_config_state(
        db,
        tenant_id=principal.tenant_id,
        scope_type='org',
        scope_id=org_id,
        config_key='board_members',
        default=[],
    )
    record = {
        'id': str(uuid.uuid4()),
        'name': payload.name,
        'role': payload.role,
        'clearance': payload.clearance,
        'appointed': payload.appointed,
        'expires': payload.expires,
        'status': payload.status,
    }
    members.append(record)
    upsert_config_state(
        db,
        tenant_id=principal.tenant_id,
        scope_type='org',
        scope_id=org_id,
        config_key='board_members',
        value=members,
        updated_by_user_id=principal.user_id,
    )
    db.commit()
    return record


@router.post('/orgs/{org_id}/regions')
def add_org_region_by_id(
    org_id: str,
    payload: OrgRegionCreate,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> dict:
    _org_in_tenant(db, principal.tenant_id, org_id)
    regions = get_config_state(
        db,
        tenant_id=principal.tenant_id,
        scope_type='org',
        scope_id=org_id,
        config_key='regions',
        default=[],
    )
    if any(item.get('code') == payload.code for item in regions):
        raise HTTPException(status_code=409, detail='region already exists')
    record = payload.model_dump()
    regions.append(record)
    upsert_config_state(
        db,
        tenant_id=principal.tenant_id,
        scope_type='org',
        scope_id=org_id,
        config_key='regions',
        value=regions,
        updated_by_user_id=principal.user_id,
    )
    db.commit()
    return record
