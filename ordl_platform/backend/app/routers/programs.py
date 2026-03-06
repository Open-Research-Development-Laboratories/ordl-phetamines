from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import append_audit_event, build_actor_snapshot
from app.authz import evaluate_authorization
from app.common import ensure_project_scope, ensure_tenant_scope
from app.db import get_db
from app.models import (
    ChangeRequest,
    Org,
    Program,
    ProgramMilestone,
    ProgramRisk,
    Team,
)
from app.schemas import (
    ChangeRequestCreate,
    ChangeRequestDecision,
    ChangeRequestOut,
    ProgramCreate,
    ProgramMilestoneCreate,
    ProgramMilestoneOut,
    ProgramOut,
    ProgramRiskCreate,
    ProgramRiskOut,
)
from app.security import Principal, get_current_principal

router = APIRouter(tags=["programs"])


def _authorize(principal: Principal, action: str, denied_detail: str) -> None:
    auth = evaluate_authorization(principal, action=action)
    if auth.decision != "allow":
        raise HTTPException(status_code=403, detail=f"{denied_detail}: {auth.reason_codes}")


def _program_out(row: Program) -> ProgramOut:
    return ProgramOut(
        id=row.id,
        org_id=row.org_id,
        team_id=row.team_id,
        code=row.code,
        name=row.name,
        status=row.status,
        summary=row.summary,
        owner_user_id=row.owner_user_id,
    )


def _milestone_out(row: ProgramMilestone) -> ProgramMilestoneOut:
    return ProgramMilestoneOut(
        id=row.id,
        program_id=row.program_id,
        title=row.title,
        target_at=row.target_at.isoformat() if row.target_at else None,
        status=row.status,
        owner_user_id=row.owner_user_id,
        notes=row.notes,
    )


def _risk_out(row: ProgramRisk) -> ProgramRiskOut:
    return ProgramRiskOut(
        id=row.id,
        program_id=row.program_id,
        title=row.title,
        severity=row.severity,
        probability=row.probability,
        impact=row.impact,
        status=row.status,
        owner_user_id=row.owner_user_id,
        mitigation=row.mitigation,
    )


def _change_request_out(row: ChangeRequest) -> ChangeRequestOut:
    return ChangeRequestOut(
        id=row.id,
        project_id=row.project_id,
        requested_by_user_id=row.requested_by_user_id,
        reviewer_user_id=row.reviewer_user_id,
        title=row.title,
        description=row.description,
        priority=row.priority,
        status=row.status,
        decision_notes=row.decision_notes,
    )


def _program_in_scope(db: Session, principal: Principal, program_id: str) -> Program:
    row = db.scalar(
        select(Program)
        .join(Org, Org.id == Program.org_id)
        .where(Program.id == program_id, Org.tenant_id == principal.tenant_id)
    )
    if row is None:
        exists = db.scalar(select(Program.id).where(Program.id == program_id))
        if exists is None:
            raise HTTPException(status_code=404, detail="program not found")
        raise HTTPException(status_code=403, detail="program tenant scope denied")
    return row


@router.post("/programs", response_model=ProgramOut)
def create_program(
    payload: ProgramCreate,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> ProgramOut:
    ensure_tenant_scope(db, principal)
    _authorize(principal, action="manage_seats", denied_detail="program creation denied")

    org = db.get(Org, payload.org_id)
    if org is None:
        raise HTTPException(status_code=404, detail="org not found")
    if org.tenant_id != principal.tenant_id:
        raise HTTPException(status_code=403, detail="tenant scope denied")

    if payload.team_id:
        team = db.get(Team, payload.team_id)
        if team is None:
            raise HTTPException(status_code=404, detail="team not found")
        if team.org_id != payload.org_id:
            raise HTTPException(status_code=400, detail="team must belong to the selected org")

    row = Program(
        org_id=payload.org_id,
        team_id=payload.team_id,
        code=payload.code,
        name=payload.name,
        status=payload.status,
        summary=payload.summary,
        owner_user_id=principal.user_id,
    )
    db.add(row)
    db.flush()

    append_audit_event(
        db,
        tenant_id=principal.tenant_id,
        project_id=None,
        event_type="program.created",
        payload={"program_id": row.id, "org_id": row.org_id, "code": row.code, "name": row.name},
        actor=build_actor_snapshot(db, principal),
        resource={"resource_type": "program", "resource_id": row.id},
    )
    db.commit()
    return _program_out(row)


@router.get("/programs", response_model=list[ProgramOut])
def list_programs(
    org_id: str | None = Query(default=None),
    team_id: str | None = Query(default=None),
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> list[ProgramOut]:
    ensure_tenant_scope(db, principal)
    _authorize(principal, action="read_project", denied_detail="program listing denied")

    stmt = select(Program).join(Org, Org.id == Program.org_id).where(Org.tenant_id == principal.tenant_id)
    if org_id:
        stmt = stmt.where(Program.org_id == org_id)
    if team_id:
        stmt = stmt.where(Program.team_id == team_id)
    rows = db.scalars(stmt.order_by(Program.created_at.asc())).all()
    return [_program_out(row) for row in rows]


@router.get("/programs/{program_id}", response_model=ProgramOut)
def get_program(
    program_id: str,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> ProgramOut:
    _authorize(principal, action="read_project", denied_detail="program read denied")
    row = _program_in_scope(db, principal, program_id)
    return _program_out(row)


@router.post("/programs/{program_id}/milestones", response_model=ProgramMilestoneOut)
def create_program_milestone(
    program_id: str,
    payload: ProgramMilestoneCreate,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> ProgramMilestoneOut:
    _authorize(principal, action="manage_seats", denied_detail="program milestone creation denied")
    program = _program_in_scope(db, principal, program_id)

    row = ProgramMilestone(
        program_id=program.id,
        title=payload.title,
        target_at=payload.target_at,
        status=payload.status,
        owner_user_id=payload.owner_user_id or principal.user_id,
        notes=payload.notes,
    )
    db.add(row)
    db.flush()

    append_audit_event(
        db,
        tenant_id=principal.tenant_id,
        project_id=None,
        event_type="program.milestone.created",
        payload={"program_id": program.id, "milestone_id": row.id, "title": row.title},
        actor=build_actor_snapshot(db, principal),
        resource={"resource_type": "program_milestone", "resource_id": row.id},
    )
    db.commit()
    return _milestone_out(row)


@router.get("/programs/{program_id}/milestones", response_model=list[ProgramMilestoneOut])
def list_program_milestones(
    program_id: str,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> list[ProgramMilestoneOut]:
    _authorize(principal, action="read_project", denied_detail="program milestone listing denied")
    program = _program_in_scope(db, principal, program_id)
    rows = db.scalars(
        select(ProgramMilestone)
        .where(ProgramMilestone.program_id == program.id)
        .order_by(ProgramMilestone.created_at.asc())
    ).all()
    return [_milestone_out(row) for row in rows]


@router.post("/programs/{program_id}/risks", response_model=ProgramRiskOut)
def create_program_risk(
    program_id: str,
    payload: ProgramRiskCreate,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> ProgramRiskOut:
    _authorize(principal, action="manage_seats", denied_detail="program risk creation denied")
    program = _program_in_scope(db, principal, program_id)

    row = ProgramRisk(
        program_id=program.id,
        title=payload.title,
        severity=payload.severity,
        probability=payload.probability,
        impact=payload.impact,
        status=payload.status,
        owner_user_id=payload.owner_user_id or principal.user_id,
        mitigation=payload.mitigation,
    )
    db.add(row)
    db.flush()

    append_audit_event(
        db,
        tenant_id=principal.tenant_id,
        project_id=None,
        event_type="program.risk.created",
        payload={"program_id": program.id, "risk_id": row.id, "title": row.title},
        actor=build_actor_snapshot(db, principal),
        resource={"resource_type": "program_risk", "resource_id": row.id},
    )
    db.commit()
    return _risk_out(row)


@router.get("/programs/{program_id}/risks", response_model=list[ProgramRiskOut])
def list_program_risks(
    program_id: str,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> list[ProgramRiskOut]:
    _authorize(principal, action="read_project", denied_detail="program risk listing denied")
    program = _program_in_scope(db, principal, program_id)
    rows = db.scalars(
        select(ProgramRisk).where(ProgramRisk.program_id == program.id).order_by(ProgramRisk.created_at.asc())
    ).all()
    return [_risk_out(row) for row in rows]


@router.post("/projects/{project_id}/change-requests", response_model=ChangeRequestOut)
def create_change_request(
    project_id: str,
    payload: ChangeRequestCreate,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> ChangeRequestOut:
    ensure_project_scope(db, principal, project_id)
    _authorize(principal, action="write_message", denied_detail="change request creation denied")

    row = ChangeRequest(
        project_id=project_id,
        requested_by_user_id=principal.user_id,
        reviewer_user_id=payload.reviewer_user_id,
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
        status="submitted",
        decision_notes="",
    )
    db.add(row)
    db.flush()

    append_audit_event(
        db,
        tenant_id=principal.tenant_id,
        project_id=project_id,
        event_type="change_request.created",
        payload={"change_request_id": row.id, "title": row.title, "priority": row.priority},
        actor=build_actor_snapshot(db, principal, project_id),
        resource={"resource_type": "change_request", "resource_id": row.id},
    )
    db.commit()
    return _change_request_out(row)


@router.get("/projects/{project_id}/change-requests", response_model=list[ChangeRequestOut])
def list_change_requests(
    project_id: str,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> list[ChangeRequestOut]:
    ensure_project_scope(db, principal, project_id)
    _authorize(principal, action="read_project", denied_detail="change request listing denied")
    rows = db.scalars(
        select(ChangeRequest).where(ChangeRequest.project_id == project_id).order_by(ChangeRequest.created_at.asc())
    ).all()
    return [_change_request_out(row) for row in rows]


@router.post("/change-requests/{change_request_id}/decision", response_model=ChangeRequestOut)
def decide_change_request(
    change_request_id: str,
    payload: ChangeRequestDecision,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> ChangeRequestOut:
    row = db.get(ChangeRequest, change_request_id)
    if row is None:
        raise HTTPException(status_code=404, detail="change request not found")
    ensure_project_scope(db, principal, row.project_id)
    _authorize(principal, action="approve_message", denied_detail="change request decision denied")

    row.status = payload.status
    row.decision_notes = payload.decision_notes
    row.reviewer_user_id = principal.user_id

    append_audit_event(
        db,
        tenant_id=principal.tenant_id,
        project_id=row.project_id,
        event_type="change_request.decided",
        payload={
            "change_request_id": row.id,
            "status": row.status,
            "reviewer_user_id": row.reviewer_user_id,
        },
        actor=build_actor_snapshot(db, principal, row.project_id),
        resource={"resource_type": "change_request", "resource_id": row.id},
    )
    db.commit()
    return _change_request_out(row)
