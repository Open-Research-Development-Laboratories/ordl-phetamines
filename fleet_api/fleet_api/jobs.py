from __future__ import annotations

import json
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path
from threading import Lock
from typing import Any, Callable

from .utils import now_iso


@dataclass
class JobRecord:
    id: str
    name: str
    status: str
    created_at: str
    started_at: str | None = None
    completed_at: str | None = None
    duration_ms: int | None = None
    error: str | None = None
    result: Any = None


class JobManager:
    def __init__(self, max_workers: int, state_dir: Path) -> None:
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="fleet-api")
        self._jobs: dict[str, JobRecord] = {}
        self._lock = Lock()
        self._events_path = state_dir / "jobs-events.jsonl"
        self._events_path.parent.mkdir(parents=True, exist_ok=True)

    def submit(self, name: str, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> JobRecord:
        job_id = uuid.uuid4().hex
        rec = JobRecord(
            id=job_id,
            name=name,
            status="queued",
            created_at=now_iso(),
        )
        with self._lock:
            self._jobs[job_id] = rec
        self._event("queued", rec)
        self._executor.submit(self._run_job, rec.id, fn, args, kwargs)
        return rec

    def _run_job(self, job_id: str, fn: Callable[..., Any], args: tuple[Any, ...], kwargs: dict[str, Any]) -> None:
        with self._lock:
            rec = self._jobs[job_id]
            rec.status = "running"
            rec.started_at = now_iso()
        self._event("running", rec)

        started = rec.started_at
        try:
            result = fn(*args, **kwargs)
            with self._lock:
                rec.result = result
                rec.status = "succeeded"
                rec.completed_at = now_iso()
                rec.duration_ms = _duration_ms(started, rec.completed_at)
            self._event("succeeded", rec)
        except Exception as exc:  # noqa: BLE001
            with self._lock:
                rec.status = "failed"
                rec.error = f"{exc}\n{traceback.format_exc()}"
                rec.completed_at = now_iso()
                rec.duration_ms = _duration_ms(started, rec.completed_at)
            self._event("failed", rec)

    def get(self, job_id: str) -> JobRecord | None:
        with self._lock:
            return self._jobs.get(job_id)

    def list(self, limit: int = 50) -> list[JobRecord]:
        with self._lock:
            items = sorted(self._jobs.values(), key=lambda x: x.created_at, reverse=True)
        return items[: max(1, limit)]

    def _event(self, event: str, rec: JobRecord) -> None:
        payload = {
            "event": event,
            "at": now_iso(),
            "job": asdict(rec),
        }
        with self._events_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=True) + "\n")


def _duration_ms(started_at: str | None, ended_at: str | None) -> int | None:
    if not started_at or not ended_at:
        return None
    try:
        s = _parse_iso(started_at)
        e = _parse_iso(ended_at)
        return max(0, int((e - s).total_seconds() * 1000))
    except Exception:  # noqa: BLE001
        return None


def _parse_iso(value: str):
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    from datetime import datetime

    return datetime.fromisoformat(value)

