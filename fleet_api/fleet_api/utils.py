from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def sha256_short(value: str, n: int = 10) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:n]


def read_json(path: Path) -> Any | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8", errors="replace"))


def tail_lines(path: Path, limit: int = 30) -> list[str]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return lines[-limit:]


def run_local(
    command: list[str] | str,
    cwd: Path | None = None,
    timeout: int = 120,
    check: bool = False,
) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            command,
            cwd=str(cwd) if cwd else None,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=timeout,
            shell=isinstance(command, str),
        )
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "returncode": -1,
            "stdout": "",
            "stderr": str(exc),
            "command": command,
        }
    if check and proc.returncode != 0:
        raise RuntimeError(f"command failed ({proc.returncode}): {command}\n{proc.stderr.strip()}")
    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "command": command,
    }
