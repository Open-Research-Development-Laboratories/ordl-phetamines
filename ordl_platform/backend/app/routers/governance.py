from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import append_audit_event, build_actor_snapshot
from app.common import ensure_project_scope, ensure_tenant_scope
from app.db import get_db
from app.models import Org, Project, SeatAssignment, Team
from app.schemas import OrgCreate, OrgOut, ProjectCreate, ProjectOut, TeamCreate, TeamOut
from app.security import Principal, get_current_principal

router = APIRouter(tags=['governance'])


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
