from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config import Settings
from conftest import bearer, issue_token, setup_project


def test_settings_reject_default_secrets_in_production() -> None:
    with pytest.raises(ValidationError):
        Settings(environment="production")


def test_settings_allow_strong_secrets_in_production() -> None:
    cfg = Settings(
        environment="production",
        policy_secret="p" * 48,
        auth_secret="a" * 48,
        extension_signing_secret="e" * 48,
    )
    assert cfg.environment == "production"


def test_dispatch_rejects_unsupported_provider(client) -> None:
    officer = issue_token(client, "TenantVal", "officer@val.test", ["officer"], clearance="restricted")
    _, _, project_id = setup_project(client, officer)

    res = client.post(
        "/v1/dispatch",
        headers=bearer(officer),
        json={
            "project_id": project_id,
            "target_scope": "group",
            "target_value": "engineers",
            "provider": "unsupported_provider",
            "model": "gpt-5.4",
            "payload": {"task": "noop"},
        },
    )
    assert res.status_code == 422


def test_digestion_rejects_missing_repo_root(client, tmp_path: Path) -> None:
    officer = issue_token(client, "TenantDig", "officer@dig.test", ["officer"], clearance="restricted")
    _, _, project_id = setup_project(client, officer)
    missing = tmp_path / "does-not-exist"

    res = client.post(
        "/v1/digestion/run",
        headers=bearer(officer),
        json={"project_id": project_id, "repo_root": str(missing), "chunk_size": 10},
    )
    assert res.status_code == 400
    assert "existing directory" in res.json()["detail"]


def test_digestion_rejects_invalid_chunk_size(client, tmp_path: Path) -> None:
    officer = issue_token(client, "TenantChunk", "officer@chunk.test", ["officer"], clearance="restricted")
    _, _, project_id = setup_project(client, officer)
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    (repo_root / "a.py").write_text("print('ok')\n", encoding="utf-8")

    res = client.post(
        "/v1/digestion/run",
        headers=bearer(officer),
        json={"project_id": project_id, "repo_root": str(repo_root), "chunk_size": 0},
    )
    assert res.status_code == 422
