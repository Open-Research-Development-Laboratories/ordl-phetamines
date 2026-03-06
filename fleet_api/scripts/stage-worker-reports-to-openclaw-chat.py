#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _bootstrap_imports() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    fleet_pkg_root = repo_root / "fleet_api"
    if str(fleet_pkg_root) not in sys.path:
        sys.path.insert(0, str(fleet_pkg_root))


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Collect latest worker handoff markdown and stage it into the active "
            "OpenClaw chat session before final synthesis."
        )
    )
    parser.add_argument(
        "--roles",
        nargs="*",
        default=None,
        help="Worker roles to include (default: all enabled roles).",
    )
    parser.add_argument(
        "--handoff-glob",
        default="/development/crew-handoff/*.md",
        help="Remote glob used to discover latest worker handoff file.",
    )
    parser.add_argument(
        "--session-id",
        default=None,
        help="Optional OpenClaw sessionId; defaults to most recently active session.",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=3200,
        help="Maximum characters per staged chat chunk.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only emit final JSON.",
    )
    args = parser.parse_args()

    def status(message: str) -> None:
        if not args.quiet:
            print(message, file=sys.stderr, flush=True)

    status("[1/4] Loading fleet config and orchestrator...")
    _bootstrap_imports()
    from fleet_api.config import load_config  # noqa: WPS433
    from fleet_api.orchestrator import FleetOrchestrator  # noqa: WPS433

    cfg = load_config()
    orch = FleetOrchestrator(cfg)
    roles = args.roles or orch.list_worker_roles()
    if not roles:
        print(json.dumps({"ok": False, "error": "no enabled worker roles"}, indent=2))
        return 2

    status(f"[2/4] Collecting latest handoff files for roles: {', '.join(roles)}")
    status("[3/4] Staging worker dumps to OpenClaw chat...")
    result = orch.stage_worker_handoffs(
        roles=roles,
        handoff_glob=args.handoff_glob,
        session_id=args.session_id or None,
        max_chunk_chars=args.max_chars,
    )

    status("[4/4] Done. Emitting JSON summary.")
    print(json.dumps(result, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
