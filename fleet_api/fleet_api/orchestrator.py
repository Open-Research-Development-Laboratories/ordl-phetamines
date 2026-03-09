from __future__ import annotations

import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import ipaddress
import json
import posixpath
import re
import shlex
import socket
import time
from dataclasses import asdict
from pathlib import Path
from threading import Lock
from typing import Any, Callable, Iterable
from urllib.parse import urlparse

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
        self._connectivity_state_path = self.cfg.state_dir / "connectivity-state.json"
        self._connectivity_lock = Lock()

    def list_worker_roles(self, enabled_only: bool = True) -> list[str]:
        roles: list[str] = []
        for role, target in self.cfg.workers.items():
            if not enabled_only or target.enabled:
                roles.append(role)
        return roles

    def _load_connectivity_state(self) -> dict[str, Any]:
        with self._connectivity_lock:
            try:
                payload = read_json(self._connectivity_state_path)
                if isinstance(payload, dict):
                    workers = payload.get("workers")
                    if isinstance(workers, dict):
                        return payload
            except Exception:  # noqa: BLE001
                pass
            return {"workers": {}}

    def _save_connectivity_state(self, payload: dict[str, Any]) -> None:
        with self._connectivity_lock:
            self._connectivity_state_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self._connectivity_state_path.with_suffix(".tmp")
            with tmp.open("w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2, sort_keys=True)
            tmp.replace(self._connectivity_state_path)

    def _record_gateway_success(self, role: str, gateway_url: str, gateway_rtt_ms: float | None = None) -> None:
        state = self._load_connectivity_state()
        workers = state.setdefault("workers", {})
        entry = workers.setdefault(role, {})
        entry["last_success_gateway"] = gateway_url
        entry["last_success_at"] = datetime.now(timezone.utc).isoformat()
        if gateway_rtt_ms is not None:
            entry["last_gateway_rtt_ms"] = round(gateway_rtt_ms, 3)
        state["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._save_connectivity_state(state)

    def _get_last_success_gateway(self, role: str) -> str | None:
        state = self._load_connectivity_state()
        workers = state.get("workers", {})
        if not isinstance(workers, dict):
            return None
        entry = workers.get(role, {})
        if isinstance(entry, dict):
            value = entry.get("last_success_gateway")
            return value if isinstance(value, str) and value.strip() else None
        return None

    def _gateway_candidates(self) -> list[str]:
        out: list[str] = []
        default_gateway = f"ws://{self.cfg.hub_host}:{self.cfg.hub_port}"
        for item in [default_gateway, *self.cfg.gateway_candidates]:
            if not isinstance(item, str) or not item.strip():
                continue
            if item not in out:
                out.append(item)
        return out

    def desktop_devices(self) -> dict[str, Any]:
        result = self._run_ordlctl(["devices", "list", "--json"], timeout=60)
        if not result["ok"]:
            return {
                "ok": False,
                "error": result["stderr"].strip() or "ordlctl devices list failed",
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
            return {"ok": False, "error": f"invalid JSON from ordlctl: {exc}", "raw": result["stdout"]}

    def fleet_status(self, roles: list[str] | None = None) -> dict[str, Any]:
        roles = roles or self.list_worker_roles()
        desktop = self.desktop_devices()
        if not roles:
            return {"desktop": desktop, "workers": {}}

        workers: dict[str, Any] = {}
        max_workers = max(1, min(len(roles), self.cfg.status_max_parallel))
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            future_to_role = {pool.submit(self.worker_status, role): role for role in roles}
            for fut in as_completed(future_to_role):
                role = future_to_role[fut]
                try:
                    workers[role] = fut.result()
                except Exception as exc:  # noqa: BLE001
                    workers[role] = {
                        "role": role,
                        "host": self._target(role).host,
                        "user": self._target(role).user,
                        "process_up": False,
                        "process_raw": "",
                        "log_lines": [],
                        "corpus": {"ok": False, "missing": ["status_probe_failed"], "present": []},
                        "error": str(exc),
                    }

        ordered_workers = {role: workers[role] for role in roles if role in workers}
        return {
            "desktop": desktop,
            "workers": ordered_workers,
        }

    def fleet_health(
        self,
        roles: list[str] | None = None,
        recency_minutes: int | None = None,
    ) -> dict[str, Any]:
        status = self.fleet_status(roles=roles)
        desktop = status["desktop"]
        workers = status["workers"]
        roles = list(workers.keys())

        recency = max(5, recency_minutes or self.cfg.health_signal_recency_minutes)
        max_age_seconds = recency * 60

        expected_hosts = [self._target(role).host for role in roles]
        pairing = _evaluate_pairings(desktop.get("paired", []) if desktop.get("ok") else [], expected_hosts)

        worker_checks: dict[str, Any] = {}
        workers_ok = True
        for role, item in workers.items():
            signal = _summarize_worker_signals(item.get("log_lines", []), max_age_seconds=max_age_seconds)
            corpus_ok = bool(item.get("corpus", {}).get("ok"))
            process_up = bool(item.get("process_up"))
            role_ok = (
                process_up
                and corpus_ok
                and signal["has_handshake"]
                and signal["has_local_gateway"]
                and signal["recent_handshake"]
                and signal["recent_local_gateway"]
                and not signal["has_critical_errors"]
            )
            workers_ok = workers_ok and role_ok
            worker_checks[role] = {
                "ok": role_ok,
                "process_up": process_up,
                "corpus_ok": corpus_ok,
                **signal,
            }

        desktop_ok = (
            bool(desktop.get("ok"))
            and int(desktop.get("pending_count", 0)) == 0
            and bool(pairing["all_paired"])
        )
        fleet_ok = desktop_ok and workers_ok

        return {
            "ok": fleet_ok,
            "desktop": {
                "ok": desktop_ok,
                "pending_count": int(desktop.get("pending_count", 0) if desktop.get("ok") else 0),
                "paired_count": int(desktop.get("paired_count", 0) if desktop.get("ok") else 0),
                "pairing": pairing,
            },
            "workers": worker_checks,
            "recency_minutes": recency,
            "expected_roles": roles,
        }

    def reconnect_policy(self, roles: list[str] | None = None) -> dict[str, Any]:
        roles = roles or self.list_worker_roles()
        state = self._load_connectivity_state()
        items: dict[str, Any] = {}
        for role in roles:
            target = self._target(role)
            last_gateway = self._get_last_success_gateway(role)
            candidates = self._gateway_candidates()
            ordered = _order_gateway_candidates(last_gateway, candidates)
            items[role] = {
                "role": role,
                "host": target.host,
                "last_success_gateway": last_gateway,
                "ordered_candidates": ordered,
                "state": state.get("workers", {}).get(role, {}),
            }
        return {
            "ok": True,
            "roles": roles,
            "policy": items,
        }

    def ensure_connectivity(
        self,
        roles: list[str] | None = None,
        recency_minutes: int | None = None,
        reconnect_attempts: int | None = None,
    ) -> dict[str, Any]:
        roles = roles or self.list_worker_roles()
        recency = max(5, recency_minutes or self.cfg.health_signal_recency_minutes)
        max_age_seconds = recency * 60
        attempts = max(1, reconnect_attempts or self.cfg.connectivity_reconnect_attempts)

        outcome: dict[str, Any] = {}
        all_ok = True
        for role in roles:
            status = self.worker_status(role)
            signal = _summarize_worker_signals(status.get("log_lines", []), max_age_seconds=max_age_seconds)
            healthy = _worker_signal_ok(status, signal)
            role_result: dict[str, Any] = {
                "role": role,
                "host": self._target(role).host,
                "initial_status": status,
                "initial_signal": signal,
                "healthy_before": healthy,
                "attempts": [],
            }
            if healthy:
                role_result["healthy_after"] = True
                outcome[role] = role_result
                continue

            for idx in range(1, attempts + 1):
                attempt = self._reconnect_worker(role=role, recency_minutes=recency)
                role_result["attempts"].append(attempt)
                if attempt.get("ok"):
                    break

            final_status = self.worker_status(role)
            final_signal = _summarize_worker_signals(final_status.get("log_lines", []), max_age_seconds=max_age_seconds)
            final_ok = _worker_signal_ok(final_status, final_signal)
            role_result["final_status"] = final_status
            role_result["final_signal"] = final_signal
            role_result["healthy_after"] = final_ok
            outcome[role] = role_result
            all_ok = all_ok and final_ok

        return {
            "ok": all_ok,
            "roles": roles,
            "recency_minutes": recency,
            "reconnect_attempts": attempts,
            "workers": outcome,
        }

    def rolling_update(
        self,
        roles: list[str] | None = None,
        *,
        canary_role: str | None = None,
        update_command: str | None = None,
        rollback_on_fail: bool = True,
        verify_recency_minutes: int | None = None,
    ) -> dict[str, Any]:
        roles = roles or self.list_worker_roles()
        ordered_roles = _order_roles_for_canary(roles, canary_role)
        command_override = (update_command or "").strip()
        if command_override and not self.cfg.remote_command_enabled:
            raise PermissionError("custom update_command is disabled")
        command = command_override or self.cfg.update_default_command.strip()
        recency = max(5, verify_recency_minutes or self.cfg.update_verify_recency_minutes)
        results: dict[str, Any] = {}
        all_ok = True

        for role in ordered_roles:
            target = self._target(role)
            with self._connect(target) as client:
                pre = self._remote_run(client, "ordlctl --version 2>/dev/null | head -n 1 || true", timeout=40)
                pre_version = (pre.get("stdout") or "").strip()
                semver = _extract_semver(pre_version)
                pre_gateway = self._remote_run(
                    client,
                    "ordlctl config get plugins.entries.kimi-claw.config.gateway.url 2>/dev/null | tail -n 1 || true",
                    timeout=40,
                )
                previous_gateway = (pre_gateway.get("stdout") or "").strip()
                update_steps = [
                    "ordlctl gateway stop || true",
                    "pkill -f '[o]penclaw-gateway' || true",
                    command,
                    "nohup ordlctl gateway run --bind loopback > ~/ordlctl-worker.log 2>&1 &",
                    "sleep 10",
                    _gateway_probe_cmd(),
                    _signal_probe_cmd(limit=30),
                ]
                run = self._run_steps(client, update_steps, timeout=120)

            final_status = self.worker_status(role)
            final_signal = _summarize_worker_signals(final_status.get("log_lines", []), max_age_seconds=recency * 60)
            ok = _worker_signal_ok(final_status, final_signal)

            role_result: dict[str, Any] = {
                "role": role,
                "host": target.host,
                "pre_version": pre_version,
                "previous_gateway": previous_gateway,
                "update_command": command,
                "update_steps": run.get("steps", []),
                "status_after_update": final_status,
                "signal_after_update": final_signal,
                "ok": ok,
            }

            if not ok and rollback_on_fail and semver:
                rollback_cmd = self.cfg.update_rollback_template.format(version=semver)
                with self._connect(target) as client:
                    rollback_steps = [
                        "ordlctl gateway stop || true",
                        "pkill -f '[o]penclaw-gateway' || true",
                        rollback_cmd,
                        "nohup ordlctl gateway run --bind loopback > ~/ordlctl-worker.log 2>&1 &",
                        "sleep 10",
                        _gateway_probe_cmd(),
                        _signal_probe_cmd(limit=30),
                    ]
                    rollback_run = self._run_steps(client, rollback_steps, timeout=120)
                post_rollback_status = self.worker_status(role)
                post_rollback_signal = _summarize_worker_signals(
                    post_rollback_status.get("log_lines", []),
                    max_age_seconds=recency * 60,
                )
                rollback_ok = _worker_signal_ok(post_rollback_status, post_rollback_signal)
                role_result["rollback"] = {
                    "rollback_command": rollback_cmd,
                    "steps": rollback_run.get("steps", []),
                    "status_after_rollback": post_rollback_status,
                    "signal_after_rollback": post_rollback_signal,
                    "ok": rollback_ok,
                }
                role_result["ok"] = rollback_ok
                ok = rollback_ok

            results[role] = role_result
            all_ok = all_ok and ok
            if not ok:
                break

        return {
            "ok": all_ok,
            "ordered_roles": ordered_roles,
            "canary_role": canary_role,
            "results": results,
        }

    def rollout_gateway_endpoint(
        self,
        *,
        new_gateway_url: str,
        roles: list[str] | None = None,
        canary_role: str | None = None,
        verify_recency_minutes: int | None = None,
        rollback_on_fail: bool = True,
    ) -> dict[str, Any]:
        roles = roles or self.list_worker_roles()
        ordered_roles = _order_roles_for_canary(roles, canary_role)
        recency = max(5, verify_recency_minutes or self.cfg.update_verify_recency_minutes)
        results: dict[str, Any] = {}
        all_ok = True

        for role in ordered_roles:
            target = self._target(role)
            with self._connect(target) as client:
                existing = self._remote_run(
                    client,
                    "ordlctl config get plugins.entries.kimi-claw.config.gateway.url 2>/dev/null | tail -n1 || true",
                    timeout=40,
                )
                old_gateway = (existing.get("stdout") or "").strip()
                steps = [
                    "ordlctl gateway stop || true",
                    "pkill -f '[o]penclaw-gateway' || true",
                    f"ordlctl config set plugins.entries.kimi-claw.config.gateway.url {shlex.quote(new_gateway_url)}",
                    "nohup ordlctl gateway run --bind loopback > ~/ordlctl-worker.log 2>&1 &",
                    "sleep 10",
                    _gateway_probe_cmd(),
                    _signal_probe_cmd(limit=25),
                ]
                run = self._run_steps(client, steps, timeout=120)

            status = self.worker_status(role)
            signal = _summarize_worker_signals(status.get("log_lines", []), max_age_seconds=recency * 60)
            ok = _worker_signal_ok(status, signal)
            role_result: dict[str, Any] = {
                "role": role,
                "host": target.host,
                "old_gateway_url": old_gateway,
                "new_gateway_url": new_gateway_url,
                "steps": run.get("steps", []),
                "status_after_rollout": status,
                "signal_after_rollout": signal,
                "ok": ok,
            }

            if ok:
                self._record_gateway_success(role=role, gateway_url=new_gateway_url)

            if not ok and rollback_on_fail and old_gateway:
                with self._connect(target) as client:
                    rollback_steps = [
                        "ordlctl gateway stop || true",
                        "pkill -f '[o]penclaw-gateway' || true",
                        f"ordlctl config set plugins.entries.kimi-claw.config.gateway.url {shlex.quote(old_gateway)}",
                        "nohup ordlctl gateway run --bind loopback > ~/ordlctl-worker.log 2>&1 &",
                        "sleep 10",
                        _gateway_probe_cmd(),
                        _signal_probe_cmd(limit=25),
                    ]
                    rollback_run = self._run_steps(client, rollback_steps, timeout=120)
                rollback_status = self.worker_status(role)
                rollback_signal = _summarize_worker_signals(
                    rollback_status.get("log_lines", []),
                    max_age_seconds=recency * 60,
                )
                rollback_ok = _worker_signal_ok(rollback_status, rollback_signal)
                role_result["rollback"] = {
                    "steps": rollback_run.get("steps", []),
                    "status_after_rollback": rollback_status,
                    "signal_after_rollback": rollback_signal,
                    "ok": rollback_ok,
                }
                role_result["ok"] = rollback_ok
                ok = rollback_ok

            results[role] = role_result
            all_ok = all_ok and ok
            if not ok:
                break

        return {
            "ok": all_ok,
            "new_gateway_url": new_gateway_url,
            "ordered_roles": ordered_roles,
            "canary_role": canary_role,
            "results": results,
        }

    def discover_node_candidates(
        self,
        *,
        cidrs: list[str] | None = None,
        hosts: list[str] | None = None,
        max_hosts: int | None = None,
        attempt_ssh: bool = True,
        auto_deploy: bool = False,
    ) -> dict[str, Any]:
        limit = max(1, min(max_hosts or self.cfg.discovery_max_hosts, 2048))
        cidr_list = cidrs or list(self.cfg.discovery_default_cidrs)
        explicit_hosts = [h.strip() for h in (hosts or []) if isinstance(h, str) and h.strip()]
        scan_hosts = _expand_scan_hosts(cidr_list=cidr_list, explicit_hosts=explicit_hosts, max_hosts=limit)

        known_hosts = {self.cfg.hub_host}
        known_hosts.update(t.host for t in self.cfg.workers.values())

        findings: list[dict[str, Any]] = []
        default_user = "winsock"
        if self.cfg.workers:
            default_user = next(iter(self.cfg.workers.values())).user

        for host in scan_hosts:
            ssh_open = _tcp_open(host, 22, timeout=0.5)
            gateway_open = _tcp_open(host, self.cfg.hub_port, timeout=0.5)
            entry: dict[str, Any] = {
                "host": host,
                "known_host": host in known_hosts,
                "ports": {"ssh_22": ssh_open, f"gateway_{self.cfg.hub_port}": gateway_open},
                "ssh_probe": None,
                "score": 0,
                "recommended_roles": [],
                "auto_deploy": None,
            }

            if attempt_ssh and ssh_open and self.cfg.ssh_password:
                try:
                    facts = _collect_host_facts(host=host, user=default_user, password=self.cfg.ssh_password)
                    entry["ssh_probe"] = facts
                    score, roles = _score_discovery_candidate(facts, gateway_open=gateway_open)
                    entry["score"] = score
                    entry["recommended_roles"] = roles

                    if auto_deploy and not entry["known_host"] and "worker-node" in roles:
                        deployed = self._bootstrap_discovered_host(host=host)
                        entry["auto_deploy"] = deployed
                except Exception as exc:  # noqa: BLE001
                    entry["ssh_probe"] = {"ok": False, "error": str(exc)}
            findings.append(entry)

        report = {
            "ok": True,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "cidrs": cidr_list,
            "hosts": explicit_hosts,
            "max_hosts": limit,
            "count": len(findings),
            "findings": findings,
        }
        report_path = self.cfg.state_dir / f"discovery-report-{int(time.time())}.json"
        with report_path.open("w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2, sort_keys=True)
        report["report_path"] = str(report_path)
        return report

    def _bootstrap_discovered_host(self, host: str) -> dict[str, Any]:
        token_bundle = self._desktop_token_bundle()
        if not token_bundle.get("ok"):
            return {"ok": False, "error": token_bundle.get("error", "missing desktop token bundle")}
        target_user = self.cfg.workers[next(iter(self.cfg.workers))].user
        target = WorkerTarget(
            role=f"discovered-{host}",
            host=host,
            user=target_user,
            workspace=self.cfg.remote_workspace_root,
            enabled=True,
        )
        with self._connect(target) as client:
            suffix = host.replace(".", "-")
            instance_id = f"connector-worker-discovered-{suffix}"
            device_id = f"worker-discovered-{suffix}"
            hub_url = f"ws://{self.cfg.hub_host}:{self.cfg.hub_port}"
            steps = [
                "ordlctl gateway stop || true",
                "pkill -f '[o]penclaw-gateway' || true",
                "ordlctl config set gateway.mode local",
                "ordlctl config set gateway.bind loopback",
                "ordlctl config set plugins.entries.kimi-claw.enabled true",
                "ordlctl config set plugins.entries.kimi-claw.config.bridge.mode acp",
                f"ordlctl config set plugins.entries.kimi-claw.config.bridge.userId {shlex.quote(token_bundle['kimi_user_id'])}",
                f"ordlctl config set plugins.entries.kimi-claw.config.bridge.token {shlex.quote(token_bundle['kimi_token'])}",
                f"ordlctl config set plugins.entries.kimi-claw.config.bridge.instanceId {shlex.quote(instance_id)}",
                f"ordlctl config set plugins.entries.kimi-claw.config.bridge.deviceId {shlex.quote(device_id)}",
                f"ordlctl config set plugins.entries.kimi-claw.config.gateway.url {shlex.quote(hub_url)}",
                f"ordlctl config set plugins.entries.kimi-claw.config.gateway.token {shlex.quote(token_bundle['hub_token'])}",
                f"ordlctl config set plugins.entries.kimi-claw.config.gateway.agentId {shlex.quote(self.cfg.ordlctl_agent_id)}",
                "nohup ordlctl gateway run --bind loopback > ~/ordlctl-worker.log 2>&1 &",
                "sleep 8",
                _gateway_probe_cmd(),
                _signal_probe_cmd(limit=20),
            ]
            out = self._run_steps(client, steps, timeout=90)
        return {"ok": True, "steps": out.get("steps", [])}

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
                    "ordlctl gateway stop || true",
                    "pkill -f '[o]penclaw-gateway' || true",
                    "nohup ordlctl gateway run --bind loopback > ~/ordlctl-worker.log 2>&1 &",
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
                    "ordlctl gateway stop || true",
                    "pkill -f '[o]penclaw-gateway' || true",
                    "ordlctl config set gateway.mode local",
                    "ordlctl config set gateway.bind loopback",
                    "ordlctl config set channels.discord.enabled false",
                    "ordlctl config set hooks.enabled false",
                    "ordlctl config set plugins.entries.kimi-claw.enabled true",
                    "ordlctl config set plugins.entries.kimi-claw.config.bridge.mode acp",
                    "ordlctl config set plugins.entries.kimi-claw.config.bridge.url wss://www.kimi.com/api-claw/bots/agent-ws",
                    "ordlctl config set plugins.entries.kimi-claw.config.bridge.kimiapiHost https://www.kimi.com/api-claw",
                    f"ordlctl config set plugins.entries.kimi-claw.config.bridge.userId {shlex.quote(bundle['kimi_user_id'])}",
                    f"ordlctl config set plugins.entries.kimi-claw.config.bridge.token {shlex.quote(bundle['kimi_token'])}",
                    f"ordlctl config set plugins.entries.kimi-claw.config.bridge.instanceId {shlex.quote(instance_id)}",
                    f"ordlctl config set plugins.entries.kimi-claw.config.bridge.deviceId {shlex.quote(device_id)}",
                    f"ordlctl config set plugins.entries.kimi-claw.config.gateway.url {shlex.quote(hub_url)}",
                    f"ordlctl config set plugins.entries.kimi-claw.config.gateway.token {shlex.quote(bundle['hub_token'])}",
                    f"ordlctl config set plugins.entries.kimi-claw.config.gateway.agentId {shlex.quote(self.cfg.ordlctl_agent_id)}",
                    "ordlctl config set plugins.allow '[\"kimi-claw\"]'",
                    "nohup ordlctl gateway run --bind loopback > ~/ordlctl-worker.log 2>&1 &",
                    "sleep 8",
                    "pgrep -af ordlctl-gateway || true",
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
            result = self._run_ordlctl(["devices", "approve", req_id], timeout=60)
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

    def _reconnect_worker(self, role: str, recency_minutes: int) -> dict[str, Any]:
        target = self._target(role)
        candidates = self._gateway_candidates()
        with self._connect(target) as client:
            selected = self._select_gateway_for_worker(client=client, role=role, candidates=candidates)
            gateway_url = selected["selected_gateway"]
            steps = [
                "ordlctl gateway stop || true",
                "pkill -f '[o]penclaw-gateway' || true",
                f"ordlctl config set plugins.entries.kimi-claw.config.gateway.url {shlex.quote(gateway_url)}",
                "nohup ordlctl gateway run --bind loopback > ~/ordlctl-worker.log 2>&1 &",
                "sleep 8",
                _gateway_probe_cmd(),
                _signal_probe_cmd(limit=25),
            ]
            run = self._run_steps(client, steps, timeout=60)

        status = self.worker_status(role)
        signal = _summarize_worker_signals(status.get("log_lines", []), max_age_seconds=max(5, recency_minutes) * 60)
        ok = _worker_signal_ok(status, signal)
        if ok:
            self._record_gateway_success(role=role, gateway_url=gateway_url, gateway_rtt_ms=selected.get("selected_rtt_ms"))
        return {
            "ok": ok,
            "role": role,
            "host": target.host,
            "selected_gateway": gateway_url,
            "gateway_rtts_ms": selected.get("gateway_rtts_ms", {}),
            "steps": run.get("steps", []),
            "status": status,
            "signal": signal,
        }

    def _select_gateway_for_worker(
        self,
        *,
        client: paramiko.SSHClient,
        role: str,
        candidates: list[str],
    ) -> dict[str, Any]:
        last_success = self._get_last_success_gateway(role)
        ordered = _order_gateway_candidates(last_success, candidates)
        rtts: dict[str, float | None] = {}
        for url in ordered:
            host = _gateway_host(url)
            rtts[url] = self._remote_ping_ms(client, host) if host else None

        if last_success and last_success in ordered:
            selected = last_success
        else:
            ranked = sorted(
                ordered,
                key=lambda x: (999999 if rtts.get(x) is None else float(rtts[x]), ordered.index(x)),
            )
            selected = ranked[0] if ranked else ordered[0]

        return {
            "selected_gateway": selected,
            "selected_rtt_ms": rtts.get(selected),
            "gateway_rtts_ms": rtts,
            "ordered_candidates": ordered,
        }

    def _remote_ping_ms(self, client: paramiko.SSHClient, host: str) -> float | None:
        cmd = (
            f"ping -c 1 -W 1 {shlex.quote(host)} 2>/dev/null | "
            "grep -o 'time=[0-9.]*' | head -n1 | cut -d= -f2 || true"
        )
        out = self._remote_run(client, cmd, timeout=10)
        token = (out.get("stdout") or "").strip()
        if not token:
            return None
        try:
            return float(token)
        except ValueError:
            return None

    def latest_worker_handoff(self, role: str, handoff_glob: str = "/development/crew-handoff/*.md") -> dict[str, Any]:
        target = self._target(role)
        safe_glob = _safe_remote_glob(handoff_glob)
        with self._connect(target) as client:
            latest = self._remote_run(
                client,
                f"ls -1t {safe_glob} 2>/dev/null | head -n 1",
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

    def active_ordlctl_session(self) -> dict[str, Any]:
        result = self._run_ordlctl(["sessions", "--json"], timeout=60)
        if not result["ok"]:
            return {
                "ok": False,
                "error": result["stderr"].strip() or "ordlctl sessions --json failed",
                "session_id": None,
            }
        try:
            payload = json.loads(result["stdout"])
            sessions = payload.get("sessions", []) or []
            if not sessions:
                return {
                    "ok": False,
                    "error": "no ordlctl sessions found",
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

    def stage_text_to_ordlctl_chat(
        self,
        title: str,
        body: str,
        session_id: str | None = None,
        max_chunk_chars: int = 3200,
    ) -> dict[str, Any]:
        chosen = session_id
        if not chosen:
            session = self.active_ordlctl_session()
            if not session.get("ok"):
                return {
                    "ok": False,
                    "error": session.get("error", "failed to resolve active ordlctl session"),
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
            result = self._run_ordlctl(
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

    def stage_worker_handoffs(
        self,
        roles: list[str],
        handoff_glob: str = "/development/crew-handoff/*.md",
        session_id: str | None = None,
        max_chunk_chars: int = 3200,
    ) -> dict[str, Any]:
        staged: list[dict[str, Any]] = []
        for role in roles:
            handoff = self.latest_worker_handoff(role=role, handoff_glob=handoff_glob)
            if not handoff.get("ok"):
                staged.append(
                    {
                        "role": role,
                        "ok": False,
                        "error": handoff.get("error", "failed to collect handoff"),
                        "handoff": handoff,
                    }
                )
                continue
            title = f"{handoff['role']} @ {handoff['host']} :: {Path(handoff['path']).name}"
            body = (
                "UNREVIEWED WORKER DUMP\n"
                "Human-in-the-middle review is expected before final synthesis.\n\n"
                f"role: {handoff['role']}\n"
                f"host: {handoff['host']}\n"
                f"source: {handoff['path']}\n\n"
                "----- BEGIN WORKER REPORT -----\n"
                f"{handoff['content']}\n"
                "----- END WORKER REPORT -----\n"
            )
            stage = self.stage_text_to_ordlctl_chat(
                title=title,
                body=body,
                session_id=session_id,
                max_chunk_chars=max_chunk_chars,
            )
            staged.append(
                {
                    "role": handoff["role"],
                    "host": handoff["host"],
                    "path": handoff["path"],
                    "content_chars": len(handoff["content"]),
                    "ok": stage.get("ok", False),
                    "stage": stage,
                }
            )
        return {
            "ok": all(x.get("ok", False) for x in staged) if staged else False,
            "roles": roles,
            "handoff_glob": handoff_glob,
            "staged": staged,
        }

    def _desktop_token_bundle(self) -> dict[str, Any]:
        # Read local config file first to avoid CLI redaction placeholders.
        hub = self._read_ordlctl_json_key("gateway.auth.token") or self._desktop_get_config("gateway.auth.token")
        kimi = self._read_ordlctl_json_key("plugins.entries.kimi-claw.config.bridge.token") or self._desktop_get_config("plugins.entries.kimi-claw.config.bridge.token")
        user_id = self._read_ordlctl_json_key("plugins.entries.kimi-claw.config.bridge.userId") or self._desktop_get_config("plugins.entries.kimi-claw.config.bridge.userId")
        if not hub or not kimi or not user_id:
            return {"ok": False, "error": "failed to read desktop ordlctl token values"}
        if _looks_redacted(hub) or _looks_redacted(kimi):
            return {"ok": False, "error": "desktop token values are redacted; read from local ~/.ordlctl/ordlctl.json failed"}
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
        res = self._run_ordlctl(["config", "get", key], timeout=40)
        if not res["ok"]:
            return self._read_ordlctl_json_key(key)
        lines = [x.strip() for x in res["stdout"].splitlines() if x.strip()]
        if not lines:
            return None
        filtered = []
        for line in lines:
            if line.startswith("🦞"):
                continue
            if "ordlctl" in line and "202" in line:
                continue
            if line.startswith("Config warnings"):
                continue
            if line.startswith("│") or line.startswith("◇") or line.startswith("├"):
                continue
            filtered.append(line)
        if filtered:
            val = filtered[-1]
            if _looks_redacted(val):
                return self._read_ordlctl_json_key(key)
            return val
        fallback = lines[-1]
        if _looks_redacted(fallback):
            return self._read_ordlctl_json_key(key)
        return fallback or self._read_ordlctl_json_key(key)

    def _run_ordlctl(self, args: list[str], timeout: int = 60) -> dict[str, Any]:
        candidates = ["ordlctl", "ordlctl.cmd", "openclaw", "openclaw.cmd"]
        roaming = Path.home() / "AppData" / "Roaming" / "npm"
        candidates.append(str(roaming / "ordlctl.cmd"))
        candidates.append(str(roaming / "ordlctl"))
        candidates.append(str(roaming / "openclaw.cmd"))
        candidates.append(str(roaming / "openclaw"))

        last = {"ok": False, "stdout": "", "stderr": "cli executable not found (tried ordlctl/openclaw)", "returncode": -1}
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

    def _read_ordlctl_json_key(self, dotted_key: str) -> str | None:
        cfg_path = Path.home() / ".ordlctl" / "ordlctl.json"
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
        def _exec(raw_command: str) -> dict[str, Any]:
            payload = base64.b64encode(raw_command.encode("utf-8")).decode("ascii")
            wrapped = (
                "python3 - <<'PY'\n"
                "import base64\n"
                "import subprocess\n"
                "import sys\n"
                f"cmd = base64.b64decode('{payload}').decode('utf-8', errors='replace')\n"
                "proc = subprocess.run(['bash', '-lc', cmd], text=True, capture_output=True)\n"
                "sys.stdout.write(proc.stdout)\n"
                "sys.stderr.write(proc.stderr)\n"
                "sys.exit(proc.returncode)\n"
                "PY"
            )
            _, stdout, stderr = client.exec_command(wrapped, timeout=timeout)
            out = stdout.read().decode("utf-8", errors="replace")
            err = stderr.read().decode("utf-8", errors="replace")
            rc = stdout.channel.recv_exit_status()
            return {
                "ok": rc == 0,
                "returncode": rc,
                "stdout": out.strip(),
                "stderr": err.strip(),
                "command": raw_command,
            }

        try:
            result = _exec(command)
            if result["ok"]:
                return result
            stderr = (result.get("stderr") or "").lower()
            if "ordlctl: command not found" in stderr and "ordlctl" in command:
                fallback_command = command.replace("ordlctl", "openclaw")
                fallback = _exec(fallback_command)
                if fallback["ok"]:
                    return fallback
                # Keep the original command visible but append fallback diagnostics.
                fallback_err = fallback.get("stderr", "")
                result["stderr"] = f"{result.get('stderr', '')}\nfallback(openclaw): {fallback_err}".strip()
            return result
        except Exception as exc:  # noqa: BLE001
            return {
                "ok": False,
                "returncode": -1,
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


def _worker_signal_ok(status: dict[str, Any], signal: dict[str, Any]) -> bool:
    return bool(status.get("process_up")) and signal.get("has_handshake", False) and signal.get("has_local_gateway", False) and signal.get("recent_handshake", False) and signal.get("recent_local_gateway", False) and not signal.get("has_critical_errors", False)


def _order_gateway_candidates(last_success: str | None, candidates: list[str]) -> list[str]:
    ordered: list[str] = []
    if last_success and last_success in candidates:
        ordered.append(last_success)
    for item in candidates:
        if item not in ordered:
            ordered.append(item)
    return ordered


def _gateway_host(url: str) -> str | None:
    try:
        parsed = urlparse(url)
    except Exception:  # noqa: BLE001
        return None
    return parsed.hostname


def _order_roles_for_canary(roles: list[str], canary_role: str | None) -> list[str]:
    if not canary_role or canary_role not in roles:
        return list(roles)
    return [canary_role, *[x for x in roles if x != canary_role]]


def _extract_semver(value: str | None) -> str | None:
    if not value:
        return None
    m = re.search(r"(\d+\.\d+\.\d+)", value)
    if not m:
        return None
    return m.group(1)


def _expand_scan_hosts(*, cidr_list: list[str], explicit_hosts: list[str], max_hosts: int) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()

    for host in explicit_hosts:
        if host not in seen:
            seen.add(host)
            out.append(host)
        if len(out) >= max_hosts:
            return out

    for cidr in cidr_list:
        try:
            network = ipaddress.ip_network(cidr, strict=False)
        except ValueError:
            continue
        for ip in network.hosts():
            host = str(ip)
            if host in seen:
                continue
            seen.add(host)
            out.append(host)
            if len(out) >= max_hosts:
                return out
    return out


def _tcp_open(host: str, port: int, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _collect_host_facts(*, host: str, user: str, password: str) -> dict[str, Any]:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=host, username=user, password=password, timeout=10, banner_timeout=15)
    try:
        commands = {
            "hostname": "hostname",
            "uname": "uname -srm || true",
            "cpu_count": "nproc 2>/dev/null || getconf _NPROCESSORS_ONLN 2>/dev/null || echo 0",
            "mem_mb": "awk '/MemTotal/ {print int($2/1024)}' /proc/meminfo 2>/dev/null || echo 0",
            "disk_free_kb": "df -k / | awk 'NR==2 {print $4}' 2>/dev/null || echo 0",
            "ordlctl_version": "ordlctl --version 2>/dev/null | head -n1 || true",
            "node_version": "node -v 2>/dev/null || true",
            "python_version": "python3 --version 2>/dev/null || true",
        }
        output: dict[str, Any] = {"ok": True}
        for key, cmd in commands.items():
            _, stdout, stderr = client.exec_command(cmd, timeout=20)
            val = stdout.read().decode("utf-8", errors="replace").strip()
            err = stderr.read().decode("utf-8", errors="replace").strip()
            output[key] = val
            if err:
                output[f"{key}_stderr"] = err
        return output
    finally:
        client.close()


def _score_discovery_candidate(facts: dict[str, Any], *, gateway_open: bool) -> tuple[int, list[str]]:
    score = 0
    roles: list[str] = []

    cpu = int(str(facts.get("cpu_count", "0") or "0").strip() or "0")
    mem = int(str(facts.get("mem_mb", "0") or "0").strip() or "0")
    has_ordlctl = bool(str(facts.get("ordlctl_version", "")).strip())
    has_node = bool(str(facts.get("node_version", "")).strip())

    if cpu >= 2:
        score += 1
    if cpu >= 4:
        score += 1
    if mem >= 4096:
        score += 1
    if mem >= 8192:
        score += 1
    if has_node:
        score += 1
    if has_ordlctl:
        score += 2
    if gateway_open:
        score += 1

    if has_ordlctl and cpu >= 2 and mem >= 4096:
        roles.append("worker-node")
    if has_ordlctl and cpu >= 4 and mem >= 8192:
        roles.append("batch-node")
    if gateway_open:
        roles.append("gateway-candidate")

    if not roles:
        roles.append("observer-only")
    return score, roles


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
        "latest=$(ls -1t /tmp/ordlctl/ordlctl-*.log 2>/dev/null | head -n 1); "
        f"grep -aE '{SIGNAL_PATTERN}' ~/ordlctl-worker.log $latest 2>/dev/null | tail -n {tail_n} || true"
    )


def _gateway_probe_cmd() -> str:
    # Some hosts expose a dedicated "ordlctl-gateway" process, others only show
    # the "ordlctl gateway run ..." parent command.
    return (
        "pgrep -af ordlctl-gateway || "
        "pgrep -af 'ordlctl.*gateway run' || true"
    )


CRITICAL_SIGNAL_PATTERNS = (
    "device signature expired",
    "token mismatch",
    "pairing required",
)

WARNING_SIGNAL_PATTERNS = (
    "auth failed",
)


def _normalize_signal_lines(lines: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        normalized = line

        first_brace = line.find("{")
        if first_brace >= 0:
            payload = line[first_brace:]
            try:
                obj = json.loads(payload)
                msg = obj.get("1") or obj.get("message") or obj.get("0")
                ts = obj.get("time") or obj.get("_meta", {}).get("date")
                if msg and ts:
                    normalized = f"{ts} {msg}"
                elif msg:
                    normalized = str(msg)
            except Exception:  # noqa: BLE001
                pass

        if normalized == line:
            m = re.search(r'"1":"([^"]+)"', line)
            if m:
                normalized = m.group(1)

        if normalized not in seen:
            seen.add(normalized)
            out.append(normalized)
    return out


def _parse_iso_timestamp(value: str) -> datetime | None:
    token = value.strip()
    if not token:
        return None
    if token.endswith("Z"):
        token = token[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(token)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _line_timestamp(line: str) -> datetime | None:
    token = line.split(" ", 1)[0]
    parsed = _parse_iso_timestamp(token)
    if parsed is not None:
        return parsed

    for candidate in re.split(r"\s+", line):
        cleaned = candidate.strip("[](),")
        parsed = _parse_iso_timestamp(cleaned)
        if parsed is not None:
            return parsed

    m = re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})", line)
    if m:
        return _parse_iso_timestamp(m.group(0))
    return None


def _summarize_worker_signals(
    lines: list[str],
    *,
    max_age_seconds: int,
    now: datetime | None = None,
) -> dict[str, Any]:
    now_utc = now.astimezone(timezone.utc) if now else datetime.now(timezone.utc)

    has_handshake = False
    has_local_gateway = False
    last_handshake: datetime | None = None
    last_local_gateway: datetime | None = None
    last_success_idx = -1
    parsed_entries: list[tuple[int, str, str, datetime | None]] = []

    for idx, line in enumerate(lines):
        lower = line.lower()
        ts = _line_timestamp(line)
        parsed_entries.append((idx, line, lower, ts))
        if "handshake complete" in lower:
            has_handshake = True
            if ts and (last_handshake is None or ts > last_handshake):
                last_handshake = ts
            last_success_idx = idx
        if "local gateway connected" in lower:
            has_local_gateway = True
            if ts and (last_local_gateway is None or ts > last_local_gateway):
                last_local_gateway = ts
            last_success_idx = idx

    critical_errors: list[str] = []
    warning_errors: list[str] = []
    for idx, line, lower, _ in parsed_entries:
        if last_success_idx >= 0 and idx < last_success_idx:
            continue
        if any(pattern in lower for pattern in CRITICAL_SIGNAL_PATTERNS):
            critical_errors.append(line)
            continue
        if any(pattern in lower for pattern in WARNING_SIGNAL_PATTERNS):
            warning_errors.append(line)

    recent_handshake = (
        (now_utc - last_handshake).total_seconds() <= max_age_seconds if last_handshake else False
    )
    recent_local_gateway = (
        (now_utc - last_local_gateway).total_seconds() <= max_age_seconds if last_local_gateway else False
    )

    return {
        "has_handshake": has_handshake,
        "has_local_gateway": has_local_gateway,
        "recent_handshake": recent_handshake,
        "recent_local_gateway": recent_local_gateway,
        "last_handshake_at": last_handshake.isoformat() if last_handshake else None,
        "last_local_gateway_at": last_local_gateway.isoformat() if last_local_gateway else None,
        "has_critical_errors": bool(critical_errors),
        "critical_errors": critical_errors[-5:],
        "has_warning_errors": bool(warning_errors),
        "warning_errors": warning_errors[-5:],
    }


def _evaluate_pairings(paired_devices: list[dict[str, Any]], expected_hosts: list[str]) -> dict[str, Any]:
    observed: set[str] = set()
    for item in paired_devices:
        for key in ("remoteIp", "displayName", "host"):
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                observed.add(value.strip())

    missing = []
    for host in expected_hosts:
        if any(host == seen or host in seen for seen in observed):
            continue
        missing.append(host)

    return {
        "expected_hosts": expected_hosts,
        "observed_markers": sorted(observed),
        "missing_hosts": missing,
        "all_paired": len(missing) == 0,
    }


def _looks_redacted(value: str | None) -> bool:
    if not value:
        return False
    return "__ordlctl_REDACTED__" in value


def _safe_remote_glob(pattern: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_./*?-]+", pattern or ""):
        raise ValueError(f"unsupported handoff glob: {pattern!r}")
    return pattern


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
