from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_list(value: str | None, default: list[str] | None = None) -> list[str]:
    if value is None:
        return list(default or [])
    items = [x.strip() for x in value.split(",")]
    return [x for x in items if x]


@dataclass(frozen=True)
class WorkerTarget:
    role: str
    host: str
    user: str
    workspace: str
    enabled: bool = True


@dataclass(frozen=True)
class AppConfig:
    bind: str
    port: int
    api_key: str
    jobs_max_workers: int
    state_dir: Path
    workspace_root: Path
    remote_workspace_root: str
    remote_command_enabled: bool
    ssh_password: str | None
    hub_host: str
    hub_port: int
    ordlctl_agent_id: str
    status_max_parallel: int
    health_signal_recency_minutes: int
    gateway_candidates: tuple[str, ...]
    connectivity_monitor_enabled: bool
    connectivity_monitor_interval_seconds: int
    connectivity_reconnect_attempts: int
    update_default_command: str
    update_rollback_template: str
    update_verify_recency_minutes: int
    discovery_default_cidrs: tuple[str, ...]
    discovery_max_hosts: int
    included_corpus_paths: tuple[str, ...] = field(default_factory=tuple)
    workers: dict[str, WorkerTarget] = field(default_factory=dict)


def load_config() -> AppConfig:
    repo_root = Path(__file__).resolve().parents[2]
    default_state = repo_root / "fleet_api" / "state"
    default_workspace = Path(os.getenv("FLEET_WORKSPACE_ROOT", r"C:\development"))
    remote_workspace = os.getenv("FLEET_REMOTE_WORKSPACE_ROOT", "/development")
    user = os.getenv("FLEET_SSH_USER", "winsock")

    workers = {
        "worker-build-laptop": WorkerTarget(
            role="worker-build-laptop",
            host=os.getenv("FLEET_LAPTOP_HOST", "10.0.0.28"),
            user=user,
            workspace=remote_workspace,
            enabled=not _as_bool(os.getenv("FLEET_DISABLE_LAPTOP"), False),
        ),
        "worker-batch-server": WorkerTarget(
            role="worker-batch-server",
            host=os.getenv("FLEET_SERVER_HOST", "10.0.0.27"),
            user=user,
            workspace=remote_workspace,
            enabled=not _as_bool(os.getenv("FLEET_DISABLE_SERVER"), False),
        ),
    }

    corpus = (
        "AGENTS.md",
        "DIRECTIVES.md",
        "KIMI-FLEET-SETUP.md",
        "KIMI-RELAY-SOP.md",
        "KIMI-STARTUP-PROMPT.txt",
        "SOUL.md",
        "USER.md",
        "TOOLS.md",
        "IDENTITY.md",
        "README.md",
        "laws",
        "policy",
        "specs",
        "tests",
        "scripts",
        "memory",
        "skills",
    )

    default_gateway = f"ws://{os.getenv('FLEET_HUB_HOST', '10.0.0.48')}:{int(os.getenv('FLEET_HUB_PORT', '18789'))}"
    gateway_candidates = tuple(
        _as_list(
            os.getenv("FLEET_GATEWAY_CANDIDATES"),
            default=[default_gateway],
        )
    )
    discovery_cidrs = tuple(
        _as_list(
            os.getenv("FLEET_DISCOVERY_CIDRS"),
            default=["10.0.0.0/24"],
        )
    )

    return AppConfig(
        bind=os.getenv("FLEET_API_BIND", "127.0.0.1"),
        port=int(os.getenv("FLEET_API_PORT", "8890")),
        api_key=os.getenv("FLEET_API_KEY", "change-me-now"),
        jobs_max_workers=int(os.getenv("FLEET_API_MAX_WORKERS", "6")),
        state_dir=Path(os.getenv("FLEET_API_STATE_DIR", str(default_state))),
        workspace_root=default_workspace,
        remote_workspace_root=remote_workspace,
        remote_command_enabled=_as_bool(os.getenv("FLEET_ENABLE_REMOTE_COMMAND"), False),
        ssh_password=os.getenv("FLEET_SSH_PASSWORD"),
        hub_host=os.getenv("FLEET_HUB_HOST", "10.0.0.48"),
        hub_port=int(os.getenv("FLEET_HUB_PORT", "18789")),
        ordlctl_agent_id=os.getenv("FLEET_AGENT_ID", "arch"),
        status_max_parallel=int(os.getenv("FLEET_STATUS_MAX_PARALLEL", "4")),
        health_signal_recency_minutes=int(os.getenv("FLEET_HEALTH_SIGNAL_RECENCY_MINUTES", "180")),
        gateway_candidates=gateway_candidates,
        connectivity_monitor_enabled=_as_bool(os.getenv("FLEET_CONNECTIVITY_MONITOR_ENABLED"), True),
        connectivity_monitor_interval_seconds=int(os.getenv("FLEET_CONNECTIVITY_MONITOR_INTERVAL_SECONDS", "90")),
        connectivity_reconnect_attempts=int(os.getenv("FLEET_CONNECTIVITY_RECONNECT_ATTEMPTS", "2")),
        update_default_command=os.getenv("FLEET_UPDATE_DEFAULT_COMMAND", "npm install -g ordlctl@latest"),
        update_rollback_template=os.getenv("FLEET_UPDATE_ROLLBACK_TEMPLATE", "npm install -g ordlctl@{version}"),
        update_verify_recency_minutes=int(os.getenv("FLEET_UPDATE_VERIFY_RECENCY_MINUTES", "15")),
        discovery_default_cidrs=discovery_cidrs,
        discovery_max_hosts=int(os.getenv("FLEET_DISCOVERY_MAX_HOSTS", "256")),
        included_corpus_paths=corpus,
        workers=workers,
    )
