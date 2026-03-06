from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import append_audit_event
from app.config import Settings, get_settings
from app.db import get_session_local
from app.models import (
    Org,
    Project,
    Team,
    WorkerAction,
    WorkerConnectivityMonitor,
    WorkerInstance,
)


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _json_list(value: str | None) -> list[str]:
    try:
        parsed = json.loads(value or "[]")
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    return [str(x) for x in parsed]


def _json_obj(value: str | None) -> dict[str, Any]:
    try:
        parsed = json.loads(value or "{}")
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _dump_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _reconnect_required(worker: WorkerInstance, stale_after_seconds: int) -> bool:
    now = datetime.now(timezone.utc)
    if worker.connectivity_state == "down":
        return True
    keepalive_at = _as_utc(worker.last_keepalive_at)
    if keepalive_at is None:
        return True
    age = (now - keepalive_at).total_seconds()
    return age > stale_after_seconds


def _resolve_reconnect_target(worker: WorkerInstance) -> str:
    if worker.last_gateway_url:
        return worker.last_gateway_url
    candidates = _json_list(worker.gateway_candidates_json)
    return candidates[0] if candidates else ""


def _has_recent_action(
    db: Session,
    *,
    worker_id: str,
    action: str,
    now: datetime,
    queue_throttle_seconds: int,
) -> bool:
    latest = db.scalar(
        select(WorkerAction)
        .where(
            WorkerAction.worker_id == worker_id,
            WorkerAction.action == action,
        )
        .order_by(WorkerAction.created_at.desc())
        .limit(1)
    )
    if latest is None:
        return False
    if latest.status == "queued":
        return True
    if queue_throttle_seconds <= 0:
        return False
    latest_created = _as_utc(latest.created_at)
    if latest_created is None:
        return False
    return latest_created >= (now - timedelta(seconds=queue_throttle_seconds))


def _queue_action_if_allowed(
    db: Session,
    *,
    worker: WorkerInstance,
    requested_by_user_id: str,
    action: str,
    notes_payload: dict[str, Any],
    now: datetime,
    queue_throttle_seconds: int,
) -> bool:
    if _has_recent_action(
        db,
        worker_id=worker.id,
        action=action,
        now=now,
        queue_throttle_seconds=queue_throttle_seconds,
    ):
        return False
    action_row = WorkerAction(
        worker_id=worker.id,
        action=action,
        requested_by_user_id=requested_by_user_id,
        status="queued",
        notes=_dump_json(notes_payload),
    )
    db.add(action_row)
    return True


def _resolve_tenant_id_for_project(db: Session, project_id: str) -> str | None:
    row = db.execute(
        select(Org.tenant_id)
        .select_from(Project)
        .join(Team, Team.id == Project.team_id)
        .join(Org, Org.id == Team.org_id)
        .where(Project.id == project_id)
        .limit(1)
    ).first()
    if row is None:
        return None
    return str(row[0]) if row[0] else None


def ensure_monitor_config(
    db: Session,
    *,
    project_id: str,
    actor_user_id: str,
    settings: Settings | None = None,
) -> WorkerConnectivityMonitor:
    cfg = settings or get_settings()
    row = db.scalar(
        select(WorkerConnectivityMonitor).where(WorkerConnectivityMonitor.project_id == project_id).limit(1)
    )
    if row is not None:
        return row
    row = WorkerConnectivityMonitor(
        project_id=project_id,
        enabled=1 if cfg.worker_monitor_default_enabled else 0,
        loop_interval_seconds=cfg.worker_monitor_loop_seconds,
        stale_after_seconds=cfg.worker_monitor_default_stale_after_seconds,
        queue_throttle_seconds=cfg.worker_monitor_default_queue_throttle_seconds,
        probe_action_enabled=1 if cfg.worker_monitor_default_probe_action_enabled else 0,
        reconnect_action_enabled=1 if cfg.worker_monitor_default_reconnect_action_enabled else 0,
        last_result_json="{}",
        created_by_user_id=actor_user_id,
    )
    db.add(row)
    db.flush()
    return row


def run_monitor_for_project(
    db: Session,
    *,
    monitor: WorkerConnectivityMonitor,
    actor_user_id: str,
    source: str,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    workers = db.scalars(select(WorkerInstance).where(WorkerInstance.project_id == monitor.project_id)).all()

    total_workers = len(workers)
    reconnect_required = 0
    probe_actions_queued = 0
    reconnect_actions_queued = 0
    stale_workers = 0
    healthy_workers = 0

    for worker in workers:
        needs_reconnect = _reconnect_required(worker, stale_after_seconds=monitor.stale_after_seconds)
        if not needs_reconnect:
            healthy_workers += 1
            continue

        reconnect_required += 1
        stale_workers += 1
        target_gateway = _resolve_reconnect_target(worker)
        if worker.connectivity_state != "down":
            worker.connectivity_state = "degraded"
        if worker.status == "online":
            worker.status = "degraded"

        notes_payload = {
            "source": "worker_connectivity_monitor",
            "monitor_id": monitor.id,
            "project_id": monitor.project_id,
            "worker_id": worker.id,
            "target_gateway": target_gateway,
            "stale_after_seconds": monitor.stale_after_seconds,
            "run_at": now.isoformat(),
        }
        if monitor.probe_action_enabled:
            queued = _queue_action_if_allowed(
                db,
                worker=worker,
                requested_by_user_id=actor_user_id,
                action="probe_gateway",
                notes_payload=notes_payload | {"intent": "probe"},
                now=now,
                queue_throttle_seconds=monitor.queue_throttle_seconds,
            )
            if queued:
                probe_actions_queued += 1

        if monitor.reconnect_action_enabled:
            queued = _queue_action_if_allowed(
                db,
                worker=worker,
                requested_by_user_id=actor_user_id,
                action="reconnect_gateway",
                notes_payload=notes_payload | {"intent": "reconnect"},
                now=now,
                queue_throttle_seconds=monitor.queue_throttle_seconds,
            )
            if queued:
                reconnect_actions_queued += 1

    result = {
        "monitor_id": monitor.id,
        "project_id": monitor.project_id,
        "source": source,
        "ran_at": now.isoformat(),
        "total_workers": total_workers,
        "healthy_workers": healthy_workers,
        "stale_workers": stale_workers,
        "reconnect_required_workers": reconnect_required,
        "probe_actions_queued": probe_actions_queued,
        "reconnect_actions_queued": reconnect_actions_queued,
        "queue_throttle_seconds": monitor.queue_throttle_seconds,
    }
    monitor.last_run_at = now
    monitor.last_result_json = _dump_json(result)
    return result


def run_monitor_once(
    db: Session,
    *,
    project_id: str,
    actor_user_id: str,
    tenant_id: str,
    force: bool = False,
    source: str = "api",
    settings: Settings | None = None,
) -> dict[str, Any]:
    monitor = ensure_monitor_config(db, project_id=project_id, actor_user_id=actor_user_id, settings=settings)

    if not monitor.enabled and not force:
        result = {
            "monitor_id": monitor.id,
            "project_id": project_id,
            "source": source,
            "skipped": True,
            "reason": "monitor_disabled",
        }
        monitor.last_result_json = _dump_json(result)
        return result

    result = run_monitor_for_project(
        db,
        monitor=monitor,
        actor_user_id=actor_user_id,
        source=source,
    )
    append_audit_event(
        db,
        tenant_id=tenant_id,
        project_id=project_id,
        event_type="worker.connectivity_monitor.run",
        payload=result,
        actor={
            "actor_type": "system" if source == "daemon" else "user",
            "actor_id": "system:worker-connectivity-monitor" if source == "daemon" else actor_user_id,
            "tenant_id": tenant_id,
            "roles": ["system"] if source == "daemon" else [],
            "clearance_tier": "restricted",
            "compartments": [],
        },
        resource={"resource_type": "worker_connectivity_monitor", "resource_id": monitor.id},
        source=source,
    )
    return result


def run_enabled_monitors_once(*, settings: Settings | None = None) -> int:
    cfg = settings or get_settings()
    session_factory = get_session_local()
    runs = 0
    with session_factory() as db:
        monitors = db.scalars(
            select(WorkerConnectivityMonitor).where(WorkerConnectivityMonitor.enabled == 1)
        ).all()
        for monitor in monitors:
            tenant_id = _resolve_tenant_id_for_project(db, monitor.project_id)
            if not tenant_id:
                continue
            run_monitor_once(
                db,
                project_id=monitor.project_id,
                actor_user_id=monitor.created_by_user_id,
                tenant_id=tenant_id,
                force=True,
                source="daemon",
                settings=cfg,
            )
            runs += 1
        db.commit()
    return runs


async def run_monitor_daemon(stop_event: asyncio.Event, *, settings: Settings | None = None) -> None:
    cfg = settings or get_settings()
    interval_seconds = max(5, int(cfg.worker_monitor_loop_seconds))
    while not stop_event.is_set():
        run_enabled_monitors_once(settings=cfg)
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval_seconds)
        except asyncio.TimeoutError:
            continue

