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
    handoffs = []
    for role in roles:
        handoff = orch.latest_worker_handoff(role=role, handoff_glob=args.handoff_glob)
        handoffs.append(handoff)

    failures = [x for x in handoffs if not x.get("ok")]
    if failures:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "failed to collect one or more worker handoffs",
                    "handoffs": handoffs,
                },
                indent=2,
            )
        )
        return 1

    status("[3/4] Staging worker dumps to OpenClaw chat...")
    staged = []
    for item in handoffs:
        role = item["role"]
        host = item["host"]
        path = item["path"]
        content = item["content"]
        title = f"{role} @ {host} :: {Path(path).name}"
        body = (
            "UNREVIEWED WORKER DUMP\n"
            "Human-in-the-middle review is expected before final synthesis.\n\n"
            f"role: {role}\n"
            f"host: {host}\n"
            f"source: {path}\n\n"
            "----- BEGIN WORKER REPORT -----\n"
            f"{content}\n"
            "----- END WORKER REPORT -----\n"
        )
        stage_result = orch.stage_text_to_openclaw_chat(
            title=title,
            body=body,
            session_id=args.session_id,
            max_chunk_chars=args.max_chars,
        )
        staged.append(
            {
                "role": role,
                "host": host,
                "path": path,
                "content_chars": len(content),
                "stage": stage_result,
            }
        )

    status("[4/4] Done. Emitting JSON summary.")
    ok = all(x["stage"].get("ok") for x in staged)
    print(
        json.dumps(
            {
                "ok": ok,
                "roles": roles,
                "handoff_glob": args.handoff_glob,
                "staged": staged,
            },
            indent=2,
        )
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
