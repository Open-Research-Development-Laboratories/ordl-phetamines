from __future__ import annotations

from datetime import datetime, timezone
from threading import Event, Lock, Thread
from typing import Any

from .config import AppConfig
from .orchestrator import FleetOrchestrator


class FleetConnectivityMonitor:
    def __init__(self, cfg: AppConfig, orchestrator: FleetOrchestrator) -> None:
        self.cfg = cfg
        self.orchestrator = orchestrator
        self._stop = Event()
        self._thread: Thread | None = None
        self._lock = Lock()
        self._last_run_at: str | None = None
        self._last_result: dict[str, Any] | None = None
        self._last_error: str | None = None

    def start(self) -> None:
        if not self.cfg.connectivity_monitor_enabled:
            return
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = Thread(target=self._loop, name="fleet-connectivity-monitor", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "enabled": self.cfg.connectivity_monitor_enabled,
                "interval_seconds": self.cfg.connectivity_monitor_interval_seconds,
                "running": bool(self._thread and self._thread.is_alive()),
                "last_run_at": self._last_run_at,
                "last_error": self._last_error,
                "last_result": self._last_result,
            }

    def run_once(self) -> dict[str, Any]:
        result = self.orchestrator.ensure_connectivity(
            recency_minutes=self.cfg.health_signal_recency_minutes,
            reconnect_attempts=self.cfg.connectivity_reconnect_attempts,
        )
        with self._lock:
            self._last_run_at = datetime.now(timezone.utc).isoformat()
            self._last_result = result
            self._last_error = None
        return result

    def _loop(self) -> None:
        interval = max(15, self.cfg.connectivity_monitor_interval_seconds)
        while not self._stop.is_set():
            try:
                self.run_once()
            except Exception as exc:  # noqa: BLE001
                with self._lock:
                    self._last_run_at = datetime.now(timezone.utc).isoformat()
                    self._last_error = str(exc)
            self._stop.wait(interval)
