from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


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
    openclaw_agent_id: str
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
        openclaw_agent_id=os.getenv("FLEET_AGENT_ID", "arch"),
        included_corpus_paths=corpus,
        workers=workers,
    )
