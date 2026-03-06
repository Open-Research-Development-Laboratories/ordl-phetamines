#!/usr/bin/env python3
from __future__ import annotations

import argparse
import getpass
import json
import os
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
            "Resync worker ordlctl/Kimi credentials from desktop local config "
            "without manually copying tokens."
        )
    )
    parser.add_argument(
        "--roles",
        nargs="*",
        default=None,
        help="Worker roles to resync (default: all enabled roles).",
    )
    parser.add_argument(
        "--rotate-identity",
        action="store_true",
        help="Append timestamp to worker instance/device IDs during resync.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only print final JSON output.",
    )
    args = parser.parse_args()

    def status(message: str) -> None:
        if not args.quiet:
            print(message, file=sys.stderr, flush=True)

    status("[1/4] Loading fleet configuration...")
    _bootstrap_imports()
    from fleet_api.config import load_config  # noqa: WPS433
    from fleet_api.orchestrator import FleetOrchestrator  # noqa: WPS433

    if not os.getenv("FLEET_SSH_PASSWORD"):
        status("FLEET_SSH_PASSWORD is not set; waiting for password input...")
        os.environ["FLEET_SSH_PASSWORD"] = getpass.getpass("FLEET_SSH_PASSWORD: ")

    cfg = load_config()
    orch = FleetOrchestrator(cfg)
    roles = args.roles or orch.list_worker_roles()

    if not roles:
        print(json.dumps({"ok": False, "error": "no enabled worker roles"}, indent=2))
        return 2

    try:
        status(f"[2/4] Reading desktop tokens and resyncing workers: {', '.join(roles)}")
        result = orch.resync_workers(roles, rotate_identity=args.rotate_identity, progress=status)
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"ok": False, "error": str(exc), "roles": roles}, indent=2))
        return 1

    status("[3/4] Worker resync complete; approvals and result assembly done.")
    status("[4/4] Printing final JSON result.")
    print(json.dumps({"ok": True, "roles": roles, "result": result}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
