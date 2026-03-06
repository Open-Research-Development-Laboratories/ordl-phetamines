from __future__ import annotations

import json
import posixpath
import re
import shlex
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable, Iterable

import paramiko

from .config import AppConfig, WorkerTarget
from .utils import read_json, run_local, sha256_short


SIGNAL_PATTERN = (
    "handshake complete|local gateway connected|pairing required|"
    "device signature expired|token mismatch|auth failed"
)


class FleetOrchestrator:
    def __init__(self, cfg: AppConfig) -> None:
        self.cfg = cfg

    def list_worker_roles(self, enabled_only: bool = True) -> list[str]:
        roles: list[str] = []
        for role, target in self.cfg.workers.items():
            if not enabled_only or target.enabled:
                roles.append(role)
        return roles

    def desktop_devices(self) -> dict[str, Any]:
        result = self._run_openclaw(["devices", "list", "--json"], timeout=60)
        if not result["ok"]:
            return {
                "ok": False,
                "error": result["stderr"].strip() or "openclaw devices list failed",
                "stdout": result["stdout"],
            }
        try:
            data = json.loads(result["stdout"])
            return {
                "ok": True,
                "pending_count": len(data.get("pending", []) or []),
                "paired_count": len(data.get("paired", []) or []),
                "pending": data.get("pending", []),
                "paired": data.get("paired", []),
            }
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": f"invalid JSON from openclaw: {exc}", "raw": result["stdout"]}

    def fleet_status(self, roles: list[str] | None = None) -> dict[str, Any]:
        roles = roles or self.list_worker_roles()
        workers: dict[str, Any] = {}
        for role in roles:
            workers[role] = self.worker_status(role)
        return {
            "desktop": self.desktop_devices(),
            "workers": workers,
        }

    def worker_status(self, role: str) -> dict[str, Any]:
        target = self._target(role)
        with self._connect(target) as client:
            proc = self._remote_run(client, _gateway_probe_cmd(), timeout=30)
            logs = self._remote_run(
                client,
                _signal_probe_cmd(limit=40),
                timeout=45,
            )
            corpus = self._verify_corpus_remote(client, target.workspace)

        lines = _normalize_signal_lines(logs["stdout"].splitlines())
        return {
            "role": role,
            "host": target.host,
            "user": target.user,
            "process_up": bool(proc["stdout"].strip()),
            "process_raw": proc["stdout"],
            "log_lines": lines,
            "corpus": corpus,
        }

    def worker_logs(self, role: str, limit: int = 80) -> dict[str, Any]:
        target = self._target(role)
        with self._connect(target) as client:
            logs = self._remote_run(
                client,
                _signal_probe_cmd(limit=max(5, min(limit, 500))),
                timeout=45,
            )
        return {
            "role": role,
            "host": target.host,
            "lines": _normalize_signal_lines(logs["stdout"].splitlines()),
            "stderr": logs["stderr"],
        }

    def restart_workers(self, roles: list[str]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for role in roles:
            target = self._target(role)
            with self._connect(target) as client:
                steps = [
                    "openclaw gateway stop || true",
                    "pkill -f openclaw-gateway || true",
                    "OPENCLAW_SKIP_GMAIL_WATCHER=1 nohup openclaw gateway run --bind loopback > ~/openclaw-worker.log 2>&1 &",
                    "sleep 8",
                    _gateway_probe_cmd(),
                    (
                        _signal_probe_cmd(limit=20)
                    ),
                ]
                out[role] = self._run_steps(client, steps, timeout=45)
        return out

    def resync_workers(
        self,
        roles: list[str],
        rotate_identity: bool = False,
        progress: Callable[[str], None] | None = None,
    ) -> dict[str, Any]:
        bundle = self._desktop_token_bundle()
        if not bundle["ok"]:
            raise RuntimeError(bundle["error"])

        hub_url = f"ws://{self.cfg.hub_host}:{self.cfg.hub_port}"
        timestamp = int(time.time())
        results: dict[str, Any] = {}

        for role in roles:
            target = self._target(role)
            if progress:
                progress(f"[resync] role={role} host={target.host} connect/start")
            with self._connect(target) as client:
                suffix = _role_suffix(role)
                instance_id = f"connector-worker-{suffix}"
                device_id = f"worker-{suffix}"
                if rotate_identity:
                    instance_id = f"{instance_id}-{timestamp}"
                    device_id = f"{device_id}-{timestamp}"
                if progress:
                    progress(f"[resync] role={role} applying config and restarting gateway")

                steps = [
                    "openclaw gateway stop || true",
                    "pkill -f openclaw-gateway || true",
                    "openclaw config set gateway.mode local",
                    "openclaw config set gateway.bind loopback",
                    "openclaw config set channels.discord.enabled false",
                    "openclaw config set hooks.enabled false",
                    "openclaw config set plugins.entries.kimi-claw.enabled true",
                    "openclaw config set plugins.entries.kimi-claw.config.bridge.mode acp",
                    "openclaw config set plugins.entries.kimi-claw.config.bridge.url wss://www.kimi.com/api-claw/bots/agent-ws",
                    "openclaw config set plugins.entries.kimi-claw.config.bridge.kimiapiHost https://www.kimi.com/api-claw",
                    f"openclaw config set plugins.entries.kimi-claw.config.bridge.userId {shlex.quote(bundle['kimi_user_id'])}",
                    f"openclaw config set plugins.entries.kimi-claw.config.bridge.token {shlex.quote(bundle['kimi_token'])}",
                    f"openclaw config set plugins.entries.kimi-claw.config.bridge.instanceId {shlex.quote(instance_id)}",
                    f"openclaw config set plugins.entries.kimi-claw.config.bridge.deviceId {shlex.quote(device_id)}",
                    f"openclaw config set plugins.entries.kimi-claw.config.gateway.url {shlex.quote(hub_url)}",
                    f"openclaw config set plugins.entries.kimi-claw.config.gateway.token {shlex.quote(bundle['hub_token'])}",
                    f"openclaw config set plugins.entries.kimi-claw.config.gateway.agentId {shlex.quote(self.cfg.openclaw_agent_id)}",
                    "openclaw config set plugins.allow '[\"kimi-claw\"]'",
                    "OPENCLAW_SKIP_GMAIL_WATCHER=1 nohup openclaw gateway run --bind loopback > ~/openclaw-worker.log 2>&1 &",
                    "sleep 8",
                    "pgrep -af openclaw-gateway || true",
                    (
                        _signal_probe_cmd(limit=25)
                    ),
                ]
                results[role] = self._run_steps(client, steps, timeout=50)
                if progress:
                    progress(f"[resync] role={role} done")

        if progress:
            progress("[resync] approving pending desktop pairing requests")
        approvals = self.approve_pending_devices()
        if progress:
            progress("[resync] approvals complete")
        return {
            "token_bundle": bundle["masked"],
            "workers": results,
            "approvals": approvals,
        }

    def approve_pending_devices(self) -> dict[str, Any]:
        devices = self.desktop_devices()
        if not devices.get("ok"):
            return {"ok": False, "error": devices.get("error", "failed to read devices")}
        pending = devices.get("pending", [])
        approvals = []
        for item in pending:
            req_id = item.get("requestId")
            if not req_id:
                continue
            result = self._run_openclaw(["devices", "approve", req_id], timeout=60)
            approvals.append(
                {
                    "request_id": req_id,
                    "ok": result["ok"],
                    "stdout": result["stdout"],
                    "stderr": result["stderr"],
                }
            )
        return {
            "ok": True,
            "pending_before": len(pending),
            "approvals": approvals,
        }

    def verify_corpus(self, roles: list[str]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for role in roles:
            target = self._target(role)
            with self._connect(target) as client:
                out[role] = self._verify_corpus_remote(client, target.workspace)
        return out

    def sync_corpus(self, roles: list[str], include_paths: list[str] | None = None) -> dict[str, Any]:
        include = tuple(include_paths or self.cfg.included_corpus_paths)
        files = list(_iter_local_files(self.cfg.workspace_root, include))
        if not files:
            raise RuntimeError(f"no local files found under {self.cfg.workspace_root}")

        results: dict[str, Any] = {}
        for role in roles:
            target = self._target(role)
            with self._connect(target) as client:
                sftp = client.open_sftp()
                uploaded = 0
                failed: list[dict[str, str]] = []
                try:
                    for local_path, rel_path in files:
                        remote_path = posixpath.join(target.workspace, rel_path)
                        try:
                            _ensure_remote_dir(sftp, remote_path)
                            sftp.put(str(local_path), remote_path)
                            uploaded += 1
                        except Exception as exc:  # noqa: BLE001
                            failed.append({"path": remote_path, "error": str(exc)})
                finally:
                    sftp.close()
                verify = self._verify_corpus_remote(client, target.workspace)
                results[role] = {
                    "uploaded": uploaded,
                    "failed_count": len(failed),
                    "failed": failed,
                    "verify": verify,
                }
        return {
            "local_root": str(self.cfg.workspace_root),
            "include_paths": list(include),
            "workers": results,
        }

    def remote_command(self, role: str, command: str, timeout: int = 120) -> dict[str, Any]:
        target = self._target(role)
        with self._connect(target) as client:
            out = self._remote_run(client, command, timeout=timeout)
        return {
            "role": role,
            "host": target.host,
            "command": command,
            **out,
        }

    def latest_worker_handoff(self, role: str, handoff_glob: str = "/development/crew-handoff/*.md") -> dict[str, Any]:
        target = self._target(role)
        with self._connect(target) as client:
            latest = self._remote_run(
                client,
                f"ls -1t {shlex.quote(handoff_glob)} 2>/dev/null | head -n 1",
                timeout=30,
            )
            path = latest["stdout"].strip()
            if not path:
                return {
                    "role": role,
                    "host": target.host,
                    "ok": False,
                    "error": f"no handoff files matched {handoff_glob}",
                    "path": None,
                    "content": "",
                }
            content = self._remote_run(client, f"cat {shlex.quote(path)}", timeout=60)
        return {
            "role": role,
            "host": target.host,
            "ok": content["ok"],
            "error": content["stderr"] if not content["ok"] else "",
            "path": path,
            "content": content["stdout"],
        }

    def active_openclaw_session(self) -> dict[str, Any]:
        result = self._run_openclaw(["sessions", "--json"], timeout=60)
        if not result["ok"]:
            return {
                "ok": False,
                "error": result["stderr"].strip() or "openclaw sessions --json failed",
                "session_id": None,
            }
        try:
            payload = json.loads(result["stdout"])
            sessions = payload.get("sessions", []) or []
            if not sessions:
                return {
                    "ok": False,
                    "error": "no openclaw sessions found",
                    "session_id": None,
                }
            sessions_sorted = sorted(sessions, key=lambda x: x.get("updatedAt", 0), reverse=True)
            top = sessions_sorted[0]
            return {
                "ok": True,
                "session_id": top.get("sessionId"),
                "session_key": top.get("key"),
                "agent_id": top.get("agentId"),
                "updated_at": top.get("updatedAt"),
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "ok": False,
                "error": f"failed to parse session list: {exc}",
                "session_id": None,
            }

    def stage_text_to_openclaw_chat(
        self,
        title: str,
        body: str,
        session_id: str | None = None,
        max_chunk_chars: int = 3200,
    ) -> dict[str, Any]:
        chosen = session_id
        if not chosen:
            session = self.active_openclaw_session()
            if not session.get("ok"):
                return {
                    "ok": False,
                    "error": session.get("error", "failed to resolve active openclaw session"),
                    "session_id": None,
                    "chunks": [],
                }
            chosen = session.get("session_id")
            if not chosen:
                return {
                    "ok": False,
                    "error": "active session has no sessionId",
                    "session_id": None,
                    "chunks": [],
                }

        chunks = _chunk_text_for_messages(body, max_chars=max(1000, min(max_chunk_chars, 8000)))
        if not chunks:
            chunks = ["(empty)"]

        posted: list[dict[str, Any]] = []
        total = len(chunks)
        for idx, chunk in enumerate(chunks, start=1):
            header = f"[WORKER-DUMP] {title} (part {idx}/{total})"
            message = f"{header}\n\n{chunk}"
            result = self._run_openclaw(
                [
                    "agent",
                    "--session-id",
                    chosen,
                    "--thinking",
                    "off",
                    "--message",
                    message,
                    "--json",
                ],
                timeout=180,
            )
            posted.append(
                {
                    "part": idx,
                    "ok": result["ok"],
                    "stdout": result["stdout"],
                    "stderr": result["stderr"],
                }
            )
            if not result["ok"]:
                break

        return {
            "ok": all(x["ok"] for x in posted),
            "session_id": chosen,
            "parts": len(posted),
            "chunks_expected": total,
            "chunks": posted,
        }

    def _desktop_token_bundle(self) -> dict[str, Any]:
        # Read local config file first to avoid CLI redaction placeholders.
        hub = self._read_openclaw_json_key("gateway.auth.token") or self._desktop_get_config("gateway.auth.token")
        kimi = self._read_openclaw_json_key("plugins.entries.kimi-claw.config.bridge.token") or self._desktop_get_config("plugins.entries.kimi-claw.config.bridge.token")
        user_id = self._read_openclaw_json_key("plugins.entries.kimi-claw.config.bridge.userId") or self._desktop_get_config("plugins.entries.kimi-claw.config.bridge.userId")
        if not hub or not kimi or not user_id:
            return {"ok": False, "error": "failed to read desktop openclaw token values"}
        if _looks_redacted(hub) or _looks_redacted(kimi):
            return {"ok": False, "error": "desktop token values are redacted; read from local ~/.openclaw/openclaw.json failed"}
        return {
            "ok": True,
            "hub_token": hub,
            "kimi_token": kimi,
            "kimi_user_id": user_id,
            "masked": {
                "hub_token_len": len(hub),
                "hub_token_sha256_10": sha256_short(hub),
                "kimi_token_len": len(kimi),
                "kimi_token_sha256_10": sha256_short(kimi),
                "kimi_user_id": user_id,
            },
        }

    def _desktop_get_config(self, key: str) -> str | None:
        res = self._run_openclaw(["config", "get", key], timeout=40)
        if not res["ok"]:
            return self._read_openclaw_json_key(key)
        lines = [x.strip() for x in res["stdout"].splitlines() if x.strip()]
        if not lines:
            return None
        filtered = []
        for line in lines:
            if line.startswith("🦞"):
                continue
            if "OpenClaw" in line and "202" in line:
                continue
            if line.startswith("Config warnings"):
                continue
            if line.startswith("│") or line.startswith("◇") or line.startswith("├"):
                continue
            filtered.append(line)
        if filtered:
            val = filtered[-1]
            if _looks_redacted(val):
                return self._read_openclaw_json_key(key)
            return val
        fallback = lines[-1]
        if _looks_redacted(fallback):
            return self._read_openclaw_json_key(key)
        return fallback or self._read_openclaw_json_key(key)

    def _run_openclaw(self, args: list[str], timeout: int = 60) -> dict[str, Any]:
        candidates = ["openclaw", "openclaw.cmd"]
        roaming = Path.home() / "AppData" / "Roaming" / "npm"
        candidates.append(str(roaming / "openclaw.cmd"))
        candidates.append(str(roaming / "openclaw"))

        last = {"ok": False, "stdout": "", "stderr": "openclaw executable not found", "returncode": -1}
        for bin_path in candidates:
            res = run_local([bin_path, *args], timeout=timeout)
            if res["ok"]:
                return res
            last = res
            stderr = (res.get("stderr") or "").lower()
            if "no such file" in stderr or "cannot find the file" in stderr or "not recognized" in stderr:
                continue
            # If executable exists but command failed, return that error immediately.
            return res
        return last

    def _read_openclaw_json_key(self, dotted_key: str) -> str | None:
        cfg_path = Path.home() / ".openclaw" / "openclaw.json"
        try:
            data = read_json(cfg_path)
            if not isinstance(data, dict):
                return None
            node: Any = data
            for part in dotted_key.split("."):
                if not isinstance(node, dict) or part not in node:
                    return None
                node = node[part]
            return node if isinstance(node, str) else None
        except Exception:  # noqa: BLE001
            return None

    def _target(self, role: str) -> WorkerTarget:
        target = self.cfg.workers.get(role)
        if not target:
            raise KeyError(f"unknown role: {role}")
        if not target.enabled:
            raise RuntimeError(f"role disabled: {role}")
        return target

    def _connect(self, target: WorkerTarget):
        if not self.cfg.ssh_password:
            raise RuntimeError("FLEET_SSH_PASSWORD is required for remote orchestration")
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=target.host,
            username=target.user,
            password=self.cfg.ssh_password,
            timeout=20,
            banner_timeout=30,
        )
        return client

    def _remote_run(self, client: paramiko.SSHClient, command: str, timeout: int = 120) -> dict[str, Any]:
        try:
            wrapped = f"bash -lc {json.dumps(command)}"
            stdin, stdout, stderr = client.exec_command(wrapped, timeout=timeout)
            out = stdout.read().decode("utf-8", errors="replace")
            err = stderr.read().decode("utf-8", errors="replace")
            return {
                "ok": True,
                "stdout": out.strip(),
                "stderr": err.strip(),
                "command": command,
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "ok": False,
                "stdout": "",
                "stderr": str(exc),
                "command": command,
            }

    def _run_steps(self, client: paramiko.SSHClient, commands: list[str], timeout: int = 60) -> dict[str, Any]:
        steps: list[dict[str, Any]] = []
        for cmd in commands:
            out = self._remote_run(client, cmd, timeout=timeout)
            steps.append(out)
            if not out.get("ok"):
                break
        return {"steps": steps}

    def _verify_corpus_remote(self, client: paramiko.SSHClient, workspace: str) -> dict[str, Any]:
        required = (
            "AGENTS.md",
            "DIRECTIVES.md",
            "KIMI-FLEET-SETUP.md",
            "KIMI-RELAY-SOP.md",
            "KIMI-STARTUP-PROMPT.txt",
            "laws/KIMI.md",
            "laws/BOOK-MODE.md",
        )
        checks = []
        for rel in required:
            cmd = f"test -f {shlex.quote(posixpath.join(workspace, rel))} && echo PRESENT:{rel} || echo MISSING:{rel}"
            checks.append(self._remote_run(client, cmd, timeout=25)["stdout"])
        present = [x.split(":", 1)[1] for x in checks if x.startswith("PRESENT:")]
        missing = [x.split(":", 1)[1] for x in checks if x.startswith("MISSING:")]
        return {
            "present": present,
            "missing": missing,
            "ok": len(missing) == 0,
        }


def _role_suffix(role: str) -> str:
    if role == "worker-build-laptop":
        return "build-laptop"
    if role == "worker-batch-server":
        return "batch-server"
    return role.replace("worker-", "")


def _iter_local_files(root: Path, includes: Iterable[str]) -> Iterable[tuple[Path, str]]:
    seen: set[str] = set()
    for rel in includes:
        path = root / rel
        if not path.exists():
            continue
        if path.is_file():
            as_rel = path.relative_to(root).as_posix()
            if as_rel not in seen:
                seen.add(as_rel)
                yield path, as_rel
            continue
        for item in path.rglob("*"):
            if not item.is_file():
                continue
            as_rel = item.relative_to(root).as_posix()
            if as_rel in seen:
                continue
            seen.add(as_rel)
            yield item, as_rel


def _ensure_remote_dir(sftp: paramiko.SFTPClient, remote_file: str) -> None:
    parts = remote_file.strip("/").split("/")[:-1]
    current = ""
    for part in parts:
        current += "/" + part
        try:
            sftp.stat(current)
        except FileNotFoundError:
            sftp.mkdir(current)


def _signal_probe_cmd(limit: int = 25) -> str:
    tail_n = max(5, min(limit, 500))
    return (
        "latest=$(ls -1t /tmp/openclaw/openclaw-*.log 2>/dev/null | head -n 1); "
        f"grep -aE '{SIGNAL_PATTERN}' ~/openclaw-worker.log $latest 2>/dev/null | tail -n {tail_n} || true"
    )


def _gateway_probe_cmd() -> str:
    # Some hosts expose a dedicated "openclaw-gateway" process, others only show
    # the "openclaw gateway run ..." parent command.
    return (
        "pgrep -af openclaw-gateway || "
        "pgrep -af 'openclaw.*gateway run' || true"
    )


def _normalize_signal_lines(lines: list[str]) -> list[str]:
    out: list[str] = []
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if ":{\"" in line:
            _, _, json_part = line.partition(":{")
            payload = "{" + json_part
            try:
                obj = json.loads(payload)
                msg = obj.get("1")
                ts = obj.get("time") or obj.get("_meta", {}).get("date")
                if msg and ts:
                    out.append(f"{ts} {msg}")
                    continue
                if msg:
                    out.append(str(msg))
                    continue
            except Exception:  # noqa: BLE001
                pass
        m = re.search(r'"1":"([^"]+)"', line)
        if m:
            out.append(m.group(1))
        else:
            out.append(line)
    return out


def _looks_redacted(value: str | None) -> bool:
    if not value:
        return False
    return "__OPENCLAW_REDACTED__" in value


def _chunk_text_for_messages(text: str, max_chars: int = 3200) -> list[str]:
    clean = (text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not clean:
        return []
    lines = clean.splitlines()
    chunks: list[str] = []
    bucket: list[str] = []
    size = 0
    for line in lines:
        entry = line if line else " "
        line_len = len(entry) + 1
        if bucket and size + line_len > max_chars:
            chunks.append("\n".join(bucket).strip())
            bucket = []
            size = 0
        if len(entry) > max_chars:
            if bucket:
                chunks.append("\n".join(bucket).strip())
                bucket = []
                size = 0
            chunks.extend(_split_long_line(entry, max_chars))
            continue
        bucket.append(entry)
        size += line_len
    if bucket:
        chunks.append("\n".join(bucket).strip())
    return [x for x in chunks if x]


def _split_long_line(line: str, max_chars: int) -> list[str]:
    out: list[str] = []
    cursor = 0
    size = len(line)
    while cursor < size:
        out.append(line[cursor : cursor + max_chars])
        cursor += max_chars
    return out
