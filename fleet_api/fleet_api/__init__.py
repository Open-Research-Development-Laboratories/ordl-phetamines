from __future__ import annotations

from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

from .config import load_config
from .jobs import JobManager
from .monitor import FleetConnectivityMonitor
from .orchestrator import FleetOrchestrator
from .policy_ops import PolicyOps
from .routes import bp


def create_app() -> Flask:
    cfg = load_config()
    cfg.state_dir.mkdir(parents=True, exist_ok=True)

    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )

    app.config.update(
        FLEET_API_BIND=cfg.bind,
        FLEET_API_PORT=cfg.port,
        FLEET_API_KEY=cfg.api_key,
    )

    app.extensions["fleet.config"] = cfg
    app.extensions["fleet.jobs"] = JobManager(max_workers=cfg.jobs_max_workers, state_dir=cfg.state_dir)
    app.extensions["fleet.orchestrator"] = FleetOrchestrator(cfg)
    app.extensions["fleet.monitor"] = FleetConnectivityMonitor(cfg, app.extensions["fleet.orchestrator"])
    app.extensions["fleet.policy"] = PolicyOps(workspace_root=cfg.workspace_root)

    @app.errorhandler(Exception)
    def _handle_error(exc: Exception):
        # Preserve intended HTTP status codes (404/401/etc.) instead of coercing to 500.
        if isinstance(exc, HTTPException):
            return exc
        return jsonify({"ok": False, "error": str(exc)}), 500

    app.register_blueprint(bp)
    app.extensions["fleet.monitor"].start()
    return app
