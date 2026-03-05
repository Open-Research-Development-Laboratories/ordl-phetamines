from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

from .utils import read_json, tail_lines


class PolicyOps:
    def __init__(self, workspace_root: Path) -> None:
        self.root = workspace_root
        self.policy_dir = self.root / "policy"
        self.tests_dir = self.root / "tests"

    def snapshot(self, audit_tail: int = 20, queue_tail: int = 15) -> dict[str, Any]:
        status_path = self.policy_dir / "status.json"
        queue_path = self.policy_dir / "blocked-queue.jsonl"
        audit_path = self.policy_dir / "audit.log"

        status_obj = read_json(status_path)
        queue_lines = tail_lines(queue_path, queue_tail)
        audit_lines = tail_lines(audit_path, audit_tail)

        return {
            "status": status_obj,
            "status_path": str(status_path),
            "blocked_queue_count": _line_count(queue_path),
            "blocked_queue_tail": queue_lines,
            "audit_tail": audit_lines,
            "policy_dir_exists": self.policy_dir.exists(),
            "tests_dir_exists": self.tests_dir.exists(),
        }

    def run_tests(self) -> dict[str, Any]:
        script = self.tests_dir / "run-policy-tests.js"
        if not script.exists():
            return {
                "ok": False,
                "error": f"missing file: {script}",
                "returncode": 2,
                "stdout": "",
                "stderr": "",
            }
        proc = subprocess.run(
            ["node", str(script)],
            cwd=str(self.root),
            text=True,
            capture_output=True,
            timeout=180,
        )
        summary = _parse_test_summary(proc.stdout)
        return {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "summary": summary,
        }

    def decide(self, event: dict[str, Any]) -> dict[str, Any]:
        script = (
            "const fs=require('fs');"
            "const {decide}=require('./policy/engine');"
            "const payload=JSON.parse(fs.readFileSync(0,'utf8'));"
            "process.stdout.write(JSON.stringify(decide(payload)));"
        )
        proc = subprocess.run(
            ["node", "-e", script],
            cwd=str(self.root),
            input=json.dumps(event),
            text=True,
            capture_output=True,
            timeout=60,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"policy decide failed: {proc.stderr.strip()}")
        return json.loads(proc.stdout)


def _line_count(path: Path) -> int:
    if not path.exists():
        return 0
    return len(path.read_text(encoding="utf-8", errors="replace").splitlines())


def _parse_test_summary(stdout: str) -> dict[str, int]:
    m = re.search(r"Result:\s+(\d+)\s+passed,\s+(\d+)\s+failed", stdout)
    if not m:
        return {"passed": 0, "failed": 0}
    return {"passed": int(m.group(1)), "failed": int(m.group(2))}

