from __future__ import annotations

import hashlib
import hmac

from tests.conftest import bearer, issue_token, setup_project


def test_rev8_route_set_smoke(client):
    officer = issue_token(client, "Tenant-Rev8", "officer@rev8.test", ["officer"], clearance="restricted")
    org_id, _, project_id = setup_project(client, officer)

    got = client.get(f"/v1/orgs/{org_id}", headers=bearer(officer))
    assert got.status_code == 200, got.text

    put_org = client.put(
        f"/v1/orgs/{org_id}",
        headers=bearer(officer),
        json={"name": "Org Updated"},
    )
    assert put_org.status_code == 200, put_org.text

    put_defaults = client.put(
        f"/v1/orgs/{org_id}/defaults",
        headers=bearer(officer),
        json={"defaults": {"session_timeout_minutes": 60}},
    )
    assert put_defaults.status_code == 200, put_defaults.text

    post_member = client.post(
        f"/v1/orgs/{org_id}/members",
        headers=bearer(officer),
        json={"name": "Board One", "role": "Chair", "clearance": "restricted"},
    )
    assert post_member.status_code == 200, post_member.text

    post_region = client.post(
        f"/v1/orgs/{org_id}/regions",
        headers=bearer(officer),
        json={"code": "us-east-1", "name": "US East"},
    )
    assert post_region.status_code == 200, post_region.text

    # Provider alias paths
    create_provider = client.post(
        "/v1/providers",
        headers=bearer(officer),
        json={"id": "openai_codex", "auth_mode": "managed_secret", "configured": True},
    )
    assert create_provider.status_code in {200, 409}, create_provider.text

    provider_test = client.post("/v1/providers/openai_codex/test", headers=bearer(officer), json={})
    assert provider_test.status_code == 200, provider_test.text

    provider_cfg = client.put(
        "/v1/providers/openai_codex/config",
        headers=bearer(officer),
        json={"default_model": "gpt-5.4"},
    )
    assert provider_cfg.status_code == 200, provider_cfg.text

    # Extension verify + batch
    name = "ext-rev8"
    version = "1.0.0"
    scopes = ["dispatch.read"]
    canonical = f"{name}:{version}:{','.join(sorted(scopes))}"
    signature = hmac.new(
        b"ordl-dev-extension-secret-please-change-this-32b",
        canonical.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    created_ext = client.post(
        "/v1/extensions",
        headers=bearer(officer),
        json={
            "tenant_id": client.get("/v1/auth/me", headers=bearer(officer)).json()["tenant_id"],
            "name": name,
            "version": version,
            "scopes": scopes,
            "signature": signature,
        },
    )
    assert created_ext.status_code == 200, created_ext.text
    ext_id = created_ext.json()["id"]

    verify = client.post("/v1/extensions/verify", headers=bearer(officer), json={"extension_ids": [ext_id]})
    assert verify.status_code == 200, verify.text
    assert verify.json()["count"] == 1

    batch = client.post(
        "/v1/extensions/batch",
        headers=bearer(officer),
        json={"operation": "disable", "extension_ids": [ext_id], "reason": "test"},
    )
    assert batch.status_code == 200, batch.text
    assert batch.json()["updated"] == 1

    evidence = client.post(
        "/v1/audit/evidence",
        headers=bearer(officer),
        json={"project_id": project_id, "format": "json"},
    )
    assert evidence.status_code == 200, evidence.text
    assert evidence.json()["project_id"] == project_id
