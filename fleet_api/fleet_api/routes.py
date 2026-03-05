from __future__ import annotations

from dataclasses import asdict
from typing import Any

from flask import Blueprint, current_app, jsonify, render_template, request

from .auth import require_api_key
from .dispatch import build_dispatch, validate_request, validate_response

bp = Blueprint("fleet_api", __name__)


@bp.get("/")
def dashboard():
    return render_template("index.html")


@bp.get("/health")
def health():
    return jsonify({"ok": True, "service": "fleet-api"})


@bp.get("/v1/info")
@require_api_key
def info():
    cfg = current_app.extensions["fleet.config"]
    orch = current_app.extensions["fleet.orchestrator"]
    workers = {k: {"host": v.host, "user": v.user, "workspace": v.workspace, "enabled": v.enabled} for k, v in cfg.workers.items()}
    return jsonify(
        {
            "ok": True,
            "bind": cfg.bind,
            "port": cfg.port,
            "workspace_root": str(cfg.workspace_root),
            "remote_workspace_root": cfg.remote_workspace_root,
            "hub": {"host": cfg.hub_host, "port": cfg.hub_port, "agent_id": cfg.openclaw_agent_id},
            "workers": workers,
            "roles_enabled": orch.list_worker_roles(enabled_only=True),
        }
    )


@bp.get("/v1/jobs")
@require_api_key
def jobs_list():
    jobs = current_app.extensions["fleet.jobs"]
    limit = int(request.args.get("limit", "50"))
    return jsonify({"ok": True, "jobs": [asdict(x) for x in jobs.list(limit=limit)]})


@bp.get("/v1/jobs/<job_id>")
@require_api_key
def jobs_get(job_id: str):
    jobs = current_app.extensions["fleet.jobs"]
    rec = jobs.get(job_id)
    if not rec:
        return jsonify({"ok": False, "error": "not_found"}), 404
    return jsonify({"ok": True, "job": asdict(rec)})


@bp.get("/v1/fleet/status")
@require_api_key
def fleet_status():
    orch = current_app.extensions["fleet.orchestrator"]
    roles = _roles_from_request()
    data = orch.fleet_status(roles=roles)
    return jsonify({"ok": True, **data})


@bp.post("/v1/fleet/restart")
@require_api_key
def fleet_restart():
    orch = current_app.extensions["fleet.orchestrator"]
    jobs = current_app.extensions["fleet.jobs"]
    payload = request.get_json(silent=True) or {}
    roles = _roles_from_payload(payload)
    if _want_async(payload):
        rec = jobs.submit("fleet.restart", orch.restart_workers, roles)
        return jsonify({"ok": True, "job": asdict(rec)}), 202
    return jsonify({"ok": True, "result": orch.restart_workers(roles)})


@bp.post("/v1/fleet/resync")
@require_api_key
def fleet_resync():
    orch = current_app.extensions["fleet.orchestrator"]
    jobs = current_app.extensions["fleet.jobs"]
    payload = request.get_json(silent=True) or {}
    roles = _roles_from_payload(payload)
    rotate_identity = bool(payload.get("rotate_identity", False))
    if _want_async(payload):
        rec = jobs.submit("fleet.resync", orch.resync_workers, roles, rotate_identity)
        return jsonify({"ok": True, "job": asdict(rec)}), 202
    return jsonify({"ok": True, "result": orch.resync_workers(roles, rotate_identity=rotate_identity)})


@bp.post("/v1/fleet/sync-corpus")
@require_api_key
def fleet_sync_corpus():
    orch = current_app.extensions["fleet.orchestrator"]
    jobs = current_app.extensions["fleet.jobs"]
    payload = request.get_json(silent=True) or {}
    roles = _roles_from_payload(payload)
    include = payload.get("include_paths")
    if _want_async(payload):
        rec = jobs.submit("fleet.sync-corpus", orch.sync_corpus, roles, include)
        return jsonify({"ok": True, "job": asdict(rec)}), 202
    return jsonify({"ok": True, "result": orch.sync_corpus(roles, include_paths=include)})


@bp.post("/v1/fleet/verify-corpus")
@require_api_key
def fleet_verify_corpus():
    orch = current_app.extensions["fleet.orchestrator"]
    payload = request.get_json(silent=True) or {}
    roles = _roles_from_payload(payload)
    return jsonify({"ok": True, "result": orch.verify_corpus(roles)})


@bp.get("/v1/fleet/logs/<role>")
@require_api_key
def fleet_logs(role: str):
    orch = current_app.extensions["fleet.orchestrator"]
    limit = int(request.args.get("limit", "80"))
    return jsonify({"ok": True, "result": orch.worker_logs(role, limit=limit)})


@bp.post("/v1/fleet/command")
@require_api_key
def fleet_command():
    cfg = current_app.extensions["fleet.config"]
    if not cfg.remote_command_enabled:
        return jsonify({"ok": False, "error": "remote command endpoint disabled"}), 403
    orch = current_app.extensions["fleet.orchestrator"]
    payload = request.get_json(silent=True) or {}
    role = payload.get("role")
    command = payload.get("command")
    timeout = int(payload.get("timeout", 120))
    if not role or not command:
        return jsonify({"ok": False, "error": "role and command are required"}), 400
    return jsonify({"ok": True, "result": orch.remote_command(role=role, command=command, timeout=timeout)})


@bp.post("/v1/dispatch/build")
@require_api_key
def dispatch_build():
    payload = request.get_json(silent=True) or {}
    objective = str(payload.get("objective", "")).strip()
    inputs = [str(x) for x in payload.get("inputs", [])]
    constraints = [str(x) for x in payload.get("constraints", [])]
    quality = str(payload.get("quality_bar", "strict"))
    if not objective:
        return jsonify({"ok": False, "error": "objective is required"}), 400
    text = build_dispatch(objective=objective, inputs=inputs, constraints=constraints, quality_bar=quality)
    return jsonify({"ok": True, "dispatch": text})


@bp.post("/v1/dispatch/validate")
@require_api_key
def dispatch_validate():
    payload = request.get_json(silent=True) or {}
    text = str(payload.get("text", ""))
    mode = str(payload.get("mode", "request")).strip().lower()
    if mode not in {"request", "response"}:
        return jsonify({"ok": False, "error": "mode must be request or response"}), 400
    result = validate_request(text) if mode == "request" else validate_response(text)
    return jsonify({"ok": True, "result": asdict(result)})


@bp.get("/v1/policy/snapshot")
@require_api_key
def policy_snapshot():
    policy = current_app.extensions["fleet.policy"]
    audit_tail = int(request.args.get("audit_tail", "20"))
    queue_tail = int(request.args.get("queue_tail", "15"))
    return jsonify({"ok": True, "result": policy.snapshot(audit_tail=audit_tail, queue_tail=queue_tail)})


@bp.post("/v1/policy/tests")
@require_api_key
def policy_tests():
    policy = current_app.extensions["fleet.policy"]
    jobs = current_app.extensions["fleet.jobs"]
    payload = request.get_json(silent=True) or {}
    if _want_async(payload):
        rec = jobs.submit("policy.tests", policy.run_tests)
        return jsonify({"ok": True, "job": asdict(rec)}), 202
    return jsonify({"ok": True, "result": policy.run_tests()})


@bp.post("/v1/policy/decide")
@require_api_key
def policy_decide():
    policy = current_app.extensions["fleet.policy"]
    payload = request.get_json(silent=True) or {}
    event = payload.get("event")
    if not isinstance(event, dict):
        return jsonify({"ok": False, "error": "event object required"}), 400
    return jsonify({"ok": True, "result": policy.decide(event)})


@bp.get("/v1/playbooks")
@require_api_key
def playbooks():
    cfg = current_app.extensions["fleet.config"]
    return jsonify(
        {
            "ok": True,
            "playbooks": {
                "startup_docs": [str(cfg.workspace_root / x) for x in cfg.included_corpus_paths if "." in x],
                "roles": list(cfg.workers.keys()),
                "dispatch_output_order": ["Summary", "Risks", "Action List", "Open Questions"],
                "recommended_flow": [
                    "GET /v1/fleet/status",
                    "POST /v1/fleet/resync",
                    "POST /v1/fleet/sync-corpus",
                    "POST /v1/dispatch/build",
                    "POST /v1/dispatch/validate",
                    "GET /v1/policy/snapshot",
                    "POST /v1/policy/tests",
                ],
            },
        }
    )


def _roles_from_request() -> list[str] | None:
    roles = request.args.get("roles")
    if not roles:
        return None
    return [x.strip() for x in roles.split(",") if x.strip()]


def _roles_from_payload(payload: dict[str, Any]) -> list[str]:
    orch = current_app.extensions["fleet.orchestrator"]
    raw = payload.get("roles")
    if not raw:
        return orch.list_worker_roles()
    if not isinstance(raw, list):
        raise ValueError("roles must be a list")
    return [str(x) for x in raw]


def _want_async(payload: dict[str, Any]) -> bool:
    return bool(payload.get("async", True))

