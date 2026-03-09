from __future__ import annotations

from pathlib import Path

import pytest

from fleet_api.fleet_api.config import AppConfig
from fleet_api.fleet_api.orchestrator import FleetOrchestrator


def _base_config(*, remote_command_enabled: bool) -> AppConfig:
    return AppConfig(
        bind="127.0.0.1",
        port=8890,
        api_key="test-key",
        jobs_max_workers=1,
        state_dir=Path("/tmp"),
        workspace_root=Path("/tmp"),
        remote_workspace_root="/tmp",
        remote_command_enabled=remote_command_enabled,
        ssh_password="dummy",
        hub_host="localhost",
        hub_port=18789,
        ordlctl_agent_id="arch",
        status_max_parallel=1,
        health_signal_recency_minutes=180,
        gateway_candidates=("ws://localhost:18789",),
        connectivity_monitor_enabled=False,
        connectivity_monitor_interval_seconds=90,
        connectivity_reconnect_attempts=2,
        update_default_command="npm install -g ordlctl@latest",
        update_rollback_template="npm install -g ordlctl@{version}",
        update_verify_recency_minutes=15,
        discovery_default_cidrs=("198.51.100.0/24",),
        discovery_max_hosts=256,
        included_corpus_paths=(),
        workers={},
    )


def test_rolling_update_rejects_custom_command_when_remote_command_disabled() -> None:
    orch = FleetOrchestrator(_base_config(remote_command_enabled=False))

    with pytest.raises(PermissionError, match="custom update_command is disabled"):
        orch.rolling_update(update_command="echo pwned")


def test_rolling_update_allows_custom_command_when_remote_command_enabled() -> None:
    orch = FleetOrchestrator(_base_config(remote_command_enabled=True))

    result = orch.rolling_update(update_command="echo ok")

    assert result["ok"] is True
    assert result["ordered_roles"] == []

from fleet_api.fleet_api import create_app


class _DummyOrchestrator:
    def __init__(self) -> None:
        self.kwargs = None

    def list_worker_roles(self, enabled_only: bool = True):
        return []

    def rolling_update(self, roles=None, **kwargs):
        self.kwargs = {"roles": roles, **kwargs}
        return {"ok": True}



def test_rolling_update_endpoint_blocks_custom_command_when_disabled(monkeypatch) -> None:
    monkeypatch.setenv("FLEET_API_KEY", "k")
    monkeypatch.setenv("FLEET_CONNECTIVITY_MONITOR_ENABLED", "false")
    monkeypatch.delenv("FLEET_ENABLE_REMOTE_COMMAND", raising=False)
    app = create_app()
    app.extensions["fleet.orchestrator"] = _DummyOrchestrator()
    client = app.test_client()

    response = client.post(
        "/v1/fleet/update/rolling",
        json={"update_command": "echo pwned"},
        headers={"X-API-Key": "k"},
    )

    assert response.status_code == 403
    assert response.get_json()["error"] == "custom update_command is disabled"



def test_rolling_update_endpoint_uses_default_path_when_no_custom_command(monkeypatch) -> None:
    monkeypatch.setenv("FLEET_API_KEY", "k")
    monkeypatch.setenv("FLEET_CONNECTIVITY_MONITOR_ENABLED", "false")
    monkeypatch.delenv("FLEET_ENABLE_REMOTE_COMMAND", raising=False)
    app = create_app()
    dummy = _DummyOrchestrator()
    app.extensions["fleet.orchestrator"] = dummy
    client = app.test_client()

    response = client.post(
        "/v1/fleet/update/rolling",
        json={"async": False},
        headers={"X-API-Key": "k"},
    )

    assert response.status_code == 200
    assert response.get_json()["ok"] is True
    assert dummy.kwargs["update_command"] is None
