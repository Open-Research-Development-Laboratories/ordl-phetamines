from __future__ import annotations

from tests.conftest import bearer, issue_token, setup_project


def _seat_member(client, officer_token: str, member_token: str, project_id: str, role: str = "architect") -> None:
    member_me = client.get("/v1/auth/me", headers=bearer(member_token))
    assert member_me.status_code == 200, member_me.text
    member_id = member_me.json()["user_id"]
    seat = client.post(
        "/v1/seats",
        headers=bearer(officer_token),
        json={
            "project_id": project_id,
            "user_id": member_id,
            "role": role,
            "rank": "member",
            "position": role,
            "group_name": "protocols",
            "clearance_tier": "restricted",
            "compartments": ["alpha", "ops"],
            "status": "active",
        },
    )
    assert seat.status_code == 200, seat.text


def test_protocol_standards_lifecycle(client):
    officer = issue_token(client, "Tenant-Proto", "officer@proto.test", ["officer"], clearance="restricted")
    architect = issue_token(client, "Tenant-Proto", "architect@proto.test", ["architect"], clearance="restricted")
    _, _, project_id = setup_project(client, officer)
    _seat_member(client, officer, architect, project_id, role="architect")

    standard = client.post(
        "/v1/protocols/standards",
        headers=bearer(officer),
        json={
            "code": "mcp",
            "name": "Model Context Protocol",
            "domain": "agent_to_tool",
            "steward": "Agentic AI Foundation",
            "home_url": "https://modelcontextprotocol.io/",
            "status": "adopted",
            "adoption_tier": "core",
            "description": "Agent-to-tool interoperability baseline.",
            "tags": ["mcp", "agent", "tooling"],
            "source_urls": [
                "https://modelcontextprotocol.io/",
                "https://blog.modelcontextprotocol.io/posts/2025-12-09-mcp-joins-agentic-ai-foundation/",
            ],
        },
    )
    assert standard.status_code == 200, standard.text
    standard_id = standard.json()["id"]

    version = client.post(
        f"/v1/protocols/standards/{standard_id}/versions",
        headers=bearer(officer),
        json={
            "version": "1.0.0",
            "lifecycle_status": "adopted",
            "specification_url": "https://modelcontextprotocol.io/specification/",
            "schema_uri": "https://modelcontextprotocol.io/specification/2026-03-26/schema",
            "required_by_default": True,
            "change_notes": "Baseline enterprise requirement.",
            "compatibility": {"transport": ["stdio", "http"]},
        },
    )
    assert version.status_code == 200, version.text
    version_id = version.json()["id"]

    versions = client.get(f"/v1/protocols/standards/{standard_id}/versions", headers=bearer(architect))
    assert versions.status_code == 200, versions.text
    assert len(versions.json()) == 1
    assert versions.json()[0]["id"] == version_id

    listed = client.get("/v1/protocols/standards", headers=bearer(architect))
    assert listed.status_code == 200, listed.text
    standards = listed.json()
    assert len(standards) == 1
    assert standards[0]["code"] == "mcp"
    assert standards[0]["latest_version"] == "1.0.0"

    validate = client.post(
        "/v1/protocols/validate",
        headers=bearer(architect),
        json={
            "project_id": project_id,
            "requirements": [{"standard_code": "mcp", "minimum_version": "1.0.0"}],
        },
    )
    assert validate.status_code == 200, validate.text
    assert validate.json()["ok"] is True
    assert validate.json()["items"][0]["result"] == "pass"

    compatibility_before = client.get(
        "/v1/protocols/compatibility",
        headers=bearer(architect),
        params={"project_id": project_id},
    )
    assert compatibility_before.status_code == 200, compatibility_before.text
    payload_before = compatibility_before.json()
    assert payload_before["compatible"] is False
    assert payload_before["items"][0]["conformance_status"] == "none"

    run = client.post(
        "/v1/protocols/conformance/runs",
        headers=bearer(architect),
        json={
            "project_id": project_id,
            "standard_id": standard_id,
            "standard_version_id": version_id,
            "suite_name": "baseline",
            "target_scope": "project",
            "status": "pass",
            "score": 98,
            "findings": [],
            "evidence_refs": ["/reports/mcp-conformance-01.json"],
            "run_metadata": {"runner": "batch-suite"},
        },
    )
    assert run.status_code == 200, run.text
    assert run.json()["status"] == "pass"
    assert run.json()["standard_version_id"] == version_id

    compatibility_after = client.get(
        "/v1/protocols/compatibility",
        headers=bearer(architect),
        params={"project_id": project_id},
    )
    assert compatibility_after.status_code == 200, compatibility_after.text
    payload_after = compatibility_after.json()
    assert payload_after["compatible"] is True
    assert payload_after["items"][0]["conformance_status"] == "pass"

    conformance_runs = client.get(
        "/v1/protocols/conformance/runs",
        headers=bearer(architect),
        params={"project_id": project_id, "standard_id": standard_id},
    )
    assert conformance_runs.status_code == 200, conformance_runs.text
    assert len(conformance_runs.json()) == 1
    assert conformance_runs.json()[0]["id"] == run.json()["id"]


def test_protocol_standards_tenant_isolation(client):
    officer_a = issue_token(client, "Tenant-Proto-A", "officer@proto-a.test", ["officer"], clearance="restricted")
    _, _, project_a = setup_project(client, officer_a)

    standard = client.post(
        "/v1/protocols/standards",
        headers=bearer(officer_a),
        json={
            "code": "a2a",
            "name": "Agent2Agent",
            "domain": "agent_to_agent",
            "steward": "Linux Foundation",
            "home_url": "https://github.com/a2aproject/A2A",
            "adoption_tier": "recommended",
            "source_urls": ["https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/"],
        },
    )
    assert standard.status_code == 200, standard.text
    standard_id = standard.json()["id"]

    officer_b = issue_token(client, "Tenant-Proto-B", "officer@proto-b.test", ["officer"], clearance="restricted")

    tenant_b_list = client.get("/v1/protocols/standards", headers=bearer(officer_b))
    assert tenant_b_list.status_code == 200, tenant_b_list.text
    assert tenant_b_list.json() == []

    cross_tenant_version = client.post(
        f"/v1/protocols/standards/{standard_id}/versions",
        headers=bearer(officer_b),
        json={"version": "0.2.0"},
    )
    assert cross_tenant_version.status_code == 403, cross_tenant_version.text

    cross_tenant_run = client.post(
        "/v1/protocols/conformance/runs",
        headers=bearer(officer_b),
        json={
            "project_id": project_a,
            "standard_id": standard_id,
            "status": "pass",
            "score": 90,
        },
    )
    assert cross_tenant_run.status_code == 403, cross_tenant_run.text


def test_protocol_bootstrap_adopted(client):
    officer = issue_token(client, "Tenant-Proto-Bootstrap", "officer@bootstrap.test", ["officer"], clearance="restricted")
    _, _, project_id = setup_project(client, officer)

    boot = client.post(
        "/v1/protocols/bootstrap/adopted",
        headers=bearer(officer),
        json={"overwrite_existing": False, "include_versions": True},
    )
    assert boot.status_code == 200, boot.text
    payload = boot.json()
    assert "mcp" in payload["created_standards"]
    assert "a2a" in payload["created_standards"]
    assert len(payload["created_versions"]) >= 2

    standards = client.get("/v1/protocols/standards", headers=bearer(officer))
    assert standards.status_code == 200, standards.text
    codes = {row["code"] for row in standards.json()}
    assert {"mcp", "a2a", "webmcp"}.issubset(codes)

    compat = client.get(
        "/v1/protocols/compatibility",
        headers=bearer(officer),
        params={"project_id": project_id},
    )
    assert compat.status_code == 200, compat.text
    assert any(item["code"] == "mcp" for item in compat.json()["items"])
