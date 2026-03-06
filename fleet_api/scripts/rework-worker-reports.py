#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path


def _bootstrap_imports() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    fleet_pkg_root = repo_root / "fleet_api"
    if str(fleet_pkg_root) not in sys.path:
        sys.path.insert(0, str(fleet_pkg_root))


def _extract_agent_text(stdout: str) -> str:
    raw = (stdout or "").strip()
    if not raw:
        return ""
    try:
        payload = json.loads(raw)
    except Exception:  # noqa: BLE001
        return raw
    result = payload.get("result", {}) or {}
    blocks = result.get("payloads", []) or []
    text_parts: list[str] = []
    for block in blocks:
        if isinstance(block, dict):
            text = block.get("text")
            if isinstance(text, str) and text.strip():
                text_parts.append(text.strip())
    return "\n\n".join(text_parts).strip()


def _strip_fences(text: str) -> str:
    content = text.strip()
    if content.startswith("```") and content.endswith("```"):
        lines = content.splitlines()
        if len(lines) >= 3:
            return "\n".join(lines[1:-1]).strip()
    return content


def _build_rework_prompt(role: str, source_path: str, source_text: str, feedback: str) -> str:
    return (
        "Revise this worker report based on reviewer feedback.\n"
        "You already have the full source report below. Do not ask for more input.\n"
        "Return ONLY revised markdown (no preamble).\n"
        "Keep factual claims grounded in the source report.\n"
        "If a requested change cannot be satisfied from source evidence, state that explicitly under Open Questions.\n\n"
        f"Role: {role}\n"
        f"Source file: {source_path}\n\n"
        "Reviewer feedback:\n"
        f"{feedback.strip()}\n\n"
        "Source report:\n"
        "```markdown\n"
        f"{source_text.rstrip()}\n"
        "```\n"
    )


def _looks_unusable_rework(text: str) -> bool:
    clean = (text or "").strip()
    if not clean:
        return True
    bad_patterns = (
        r"\bpaste the report\b",
        r"\bsend .*report\b",
        r"\bprovide .*report\b",
        r"\bgive .*file path\b",
        r"\bi[' ]?ll revise it\b",
    )
    lowered = clean.lower()
    if any(re.search(p, lowered) for p in bad_patterns):
        return True
    if len(clean) < 220:
        return True
    return False


def _fallback_rework(source_path: str, source_text: str, feedback: str) -> str:
    return (
        "# Revised Worker Report (Fallback)\n\n"
        "## Reviewer Feedback Applied\n"
        f"- {feedback.strip()}\n\n"
        "## Notes\n"
        "- Automated fallback used because model output was incomplete.\n"
        f"- Source file: `{source_path}`\n\n"
        "## Source Report (Verbatim)\n\n"
        f"{source_text.rstrip()}\n"
    )


def _write_remote_markdown(orch, role: str, remote_path: str, content: str) -> dict:
    blob = base64.b64encode(content.encode("utf-8")).decode("ascii")
    cmd = (
        "python3 - <<'PY'\n"
        "import base64\n"
        "import pathlib\n"
        f"path = {json.dumps(remote_path)}\n"
        f"data = base64.b64decode({json.dumps(blob)}).decode('utf-8', errors='replace')\n"
        "p = pathlib.Path(path)\n"
        "p.parent.mkdir(parents=True, exist_ok=True)\n"
        "p.write_text(data, encoding='utf-8')\n"
        "print(path)\n"
        "PY"
    )
    return orch.remote_command(role=role, command=cmd, timeout=120)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Rework latest worker handoff reports using reviewer feedback, "
            "write revised files back to workers, and emit JSON summary."
        )
    )
    parser.add_argument("--roles", nargs="*", default=None, help="Worker roles (default: enabled roles)")
    parser.add_argument("--handoff-glob", default="/development/crew-handoff/*.md", help="Remote handoff glob")
    parser.add_argument("--feedback", required=True, help="Reviewer feedback for rework")
    parser.add_argument("--max-source-chars", type=int, default=12000, help="Max chars from source report")
    parser.add_argument("--thinking", default="low", choices=["off", "minimal", "low", "medium", "high"], help="ordlctl agent thinking level")
    parser.add_argument("--quiet", action="store_true", help="Print only JSON")
    args = parser.parse_args()

    def status(msg: str) -> None:
        if not args.quiet:
            print(msg, file=sys.stderr, flush=True)

    _bootstrap_imports()
    from fleet_api.config import load_config  # noqa: WPS433
    from fleet_api.orchestrator import FleetOrchestrator  # noqa: WPS433

    cfg = load_config()
    orch = FleetOrchestrator(cfg)
    roles = args.roles or orch.list_worker_roles()
    if not roles:
        print(json.dumps({"ok": False, "error": "no enabled worker roles"}, indent=2))
        return 2

    status(f"[rework] collecting latest handoffs for: {', '.join(roles)}")
    results: list[dict] = []
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")

    for role in roles:
        handoff = orch.latest_worker_handoff(role=role, handoff_glob=args.handoff_glob)
        if not handoff.get("ok"):
            results.append({"role": role, "ok": False, "error": handoff.get("error", "handoff lookup failed")})
            continue

        source_text = (handoff.get("content") or "").strip()
        if len(source_text) > args.max_source_chars:
            source_text = source_text[: args.max_source_chars].rstrip() + "\n\n[TRUNCATED]"

        prompt = _build_rework_prompt(
            role=role,
            source_path=handoff["path"],
            source_text=source_text,
            feedback=args.feedback,
        )

        revised = ""
        attempts = 2
        for attempt in range(1, attempts + 1):
            status(f"[rework] role={role} requesting revised report from ordlctl agent (attempt {attempt}/{attempts})")
            agent = orch._run_ordlctl(  # noqa: SLF001
                [
                    "agent",
                    "--agent",
                    "main",
                    "--thinking",
                    args.thinking if attempt == 1 else "medium",
                    "--message",
                    prompt,
                    "--json",
                ],
                timeout=240,
            )
            if not agent.get("ok"):
                if attempt == attempts:
                    results.append(
                        {
                            "role": role,
                            "ok": False,
                            "error": "ordlctl agent request failed",
                            "stderr": agent.get("stderr", ""),
                        }
                    )
                    revised = ""
                    break
                continue
            try:
                candidate = _strip_fences(_extract_agent_text(agent.get("stdout", "")))
            except Exception:  # noqa: BLE001
                candidate = ""

            if not _looks_unusable_rework(candidate):
                revised = candidate
                break

            prompt = (
                _build_rework_prompt(
                    role=role,
                    source_path=handoff["path"],
                    source_text=source_text,
                    feedback=args.feedback,
                )
                + "\nIMPORTANT: Do not ask questions. Produce the revised markdown now.\n"
            )

        if not revised:
            revised = _fallback_rework(
                source_path=handoff["path"],
                source_text=source_text,
                feedback=args.feedback,
            )

        remote_path = f"/development/crew-handoff/{role}-rework-{ts}.md"
        save = _write_remote_markdown(orch, role=role, remote_path=remote_path, content=revised)
        if not save.get("ok"):
            results.append(
                {
                    "role": role,
                    "ok": False,
                    "error": "failed to write revised report to worker",
                    "stderr": save.get("stderr", ""),
                }
            )
            continue

        results.append(
            {
                "role": role,
                "ok": True,
                "source_path": handoff["path"],
                "revised_path": remote_path,
                "source_chars": len(handoff.get("content", "")),
                "revised_chars": len(revised),
            }
        )

    out = {
        "ok": all(x.get("ok", False) for x in results) if results else False,
        "roles": roles,
        "feedback": args.feedback,
        "results": results,
    }
    print(json.dumps(out, indent=2))
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
