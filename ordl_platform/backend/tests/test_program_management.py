from __future__ import annotations

from tests.conftest import bearer, issue_token, setup_project


def _add_active_seat(client, officer_token: str, project_id: str, member_token: str, role: str) -> str:
    me = client.get("/v1/auth/me", headers=bearer(member_token))
    assert me.status_code == 200, me.text
    user_id = me.json()["user_id"]
    seat = client.post(
        "/v1/seats",
        headers=bearer(officer_token),
        json={
            "project_id": project_id,
            "user_id": user_id,
            "role": role,
            "rank": "member",
            "position": role,
            "group_name": "delivery",
            "clearance_tier": "restricted",
            "compartments": ["alpha", "ops"],
            "status": "active",
        },
    )
    assert seat.status_code == 200, seat.text
    return user_id


def test_program_and_change_request_lifecycle(client):
    officer = issue_token(client, "Tenant-Program", "officer@program.test", ["officer"], clearance="restricted")
    architect = issue_token(client, "Tenant-Program", "architect@program.test", ["architect"], clearance="restricted")

    org_id, team_id, project_id = setup_project(client, officer)
    _add_active_seat(client, officer, project_id, architect, "architect")

    create_program = client.post(
        "/v1/programs",
        headers=bearer(officer),
        json={
            "org_id": org_id,
            "team_id": team_id,
            "code": "PGM-ALPHA",
            "name": "Alpha Governance Rollout",
            "status": "active",
            "summary": "Program-level controls for phase one launch.",
        },
    )
    assert create_program.status_code == 200, create_program.text
    program_id = create_program.json()["id"]

    list_programs = client.get(f"/v1/programs?org_id={org_id}", headers=bearer(architect))
    assert list_programs.status_code == 200, list_programs.text
    assert any(item["id"] == program_id for item in list_programs.json())

    milestone = client.post(
        f"/v1/programs/{program_id}/milestones",
        headers=bearer(officer),
        json={
            "title": "Pilot Cutover",
            "target_at": "2026-04-01T12:00:00Z",
            "status": "planned",
            "notes": "Switch pilot projects to policy-gated dispatch.",
        },
    )
    assert milestone.status_code == 200, milestone.text

    milestones = client.get(f"/v1/programs/{program_id}/milestones", headers=bearer(architect))
    assert milestones.status_code == 200, milestones.text
    assert len(milestones.json()) == 1

    risk = client.post(
        f"/v1/programs/{program_id}/risks",
        headers=bearer(officer),
        json={
            "title": "Provider drift",
            "severity": "high",
            "probability": "medium",
            "impact": "high",
            "status": "open",
            "mitigation": "Add conformance checks to release gate.",
        },
    )
    assert risk.status_code == 200, risk.text

    risks = client.get(f"/v1/programs/{program_id}/risks", headers=bearer(architect))
    assert risks.status_code == 200, risks.text
    assert len(risks.json()) == 1

    create_change_request = client.post(
        f"/v1/projects/{project_id}/change-requests",
        headers=bearer(architect),
        json={
            "title": "Require signed extension manifests",
            "description": "Block unsigned extension loads for production policy.",
            "priority": "high",
        },
    )
    assert create_change_request.status_code == 200, create_change_request.text
    change_request_id = create_change_request.json()["id"]
    assert create_change_request.json()["status"] == "submitted"

    list_change_requests = client.get(f"/v1/projects/{project_id}/change-requests", headers=bearer(architect))
    assert list_change_requests.status_code == 200, list_change_requests.text
    assert any(item["id"] == change_request_id for item in list_change_requests.json())

    denied_decision = client.post(
        f"/v1/change-requests/{change_request_id}/decision",
        headers=bearer(architect),
        json={"status": "approved", "decision_notes": "architect cannot approve"},
    )
    assert denied_decision.status_code == 403, denied_decision.text

    approved = client.post(
        f"/v1/change-requests/{change_request_id}/decision",
        headers=bearer(officer),
        json={"status": "approved", "decision_notes": "approved for implementation"},
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved"


def test_program_and_change_request_tenant_isolation(client):
    officer_a = issue_token(client, "Tenant-Program-A", "officer-a@program.test", ["officer"], clearance="restricted")
    officer_b = issue_token(client, "Tenant-Program-B", "officer-b@program.test", ["officer"], clearance="restricted")

    org_id, team_id, project_id = setup_project(client, officer_a)

    create_program = client.post(
        "/v1/programs",
        headers=bearer(officer_a),
        json={
            "org_id": org_id,
            "team_id": team_id,
            "code": "PGM-BETA",
            "name": "Beta Isolation Program",
            "status": "active",
        },
    )
    assert create_program.status_code == 200, create_program.text
    program_id = create_program.json()["id"]

    denied_program = client.get(f"/v1/programs/{program_id}", headers=bearer(officer_b))
    assert denied_program.status_code in {403, 404}

    denied_project_change_requests = client.get(
        f"/v1/projects/{project_id}/change-requests",
        headers=bearer(officer_b),
    )
    assert denied_project_change_requests.status_code in {403, 404}
