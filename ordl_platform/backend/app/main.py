from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.common import utc_now_iso
from app.config import get_settings
from app.connectivity_monitor import run_monitor_daemon
from app.db import get_engine, init_engine
from app.models import Base
from app.routers import (
    approvals,
    audit,
    auth,
    clearance,
    digestion,
    dispatch,
    extensions,
    governance,
    messages,
    orchestration,
    ops,
    policy,
    programs,
    protocols,
    providers,
    seats,
    workers,
)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    daemon_stop: asyncio.Event | None = None
    daemon_task: asyncio.Task | None = None
    if settings.worker_monitor_daemon_enabled:
        daemon_stop = asyncio.Event()
        daemon_task = asyncio.create_task(run_monitor_daemon(daemon_stop, settings=settings))
    try:
        yield
    finally:
        if daemon_stop is not None:
            daemon_stop.set()
        if daemon_task is not None:
            try:
                await asyncio.wait_for(daemon_task, timeout=5)
            except asyncio.TimeoutError:
                daemon_task.cancel()
                await asyncio.gather(daemon_task, return_exceptions=True)


def create_app() -> FastAPI:
    init_engine(settings.database_url)
    Base.metadata.create_all(bind=get_engine())

    app = FastAPI(title=settings.app_name, lifespan=lifespan)

    @app.get('/health')
    def health() -> dict:
        return {
            'status': 'ok',
            'service': settings.app_name,
            'timestamp': utc_now_iso(),
        }

    app.include_router(auth.router, prefix=settings.api_prefix)
    app.include_router(ops.router, prefix=settings.api_prefix)
    app.include_router(governance.router, prefix=settings.api_prefix)
    app.include_router(seats.router, prefix=settings.api_prefix)
    app.include_router(clearance.router, prefix=settings.api_prefix)
    app.include_router(messages.router, prefix=settings.api_prefix)
    app.include_router(approvals.router, prefix=settings.api_prefix)
    app.include_router(dispatch.router, prefix=settings.api_prefix)
    app.include_router(policy.router, prefix=settings.api_prefix)
    app.include_router(providers.router, prefix=settings.api_prefix)
    app.include_router(extensions.router, prefix=settings.api_prefix)
    app.include_router(workers.router, prefix=settings.api_prefix)
    app.include_router(orchestration.router, prefix=settings.api_prefix)
    app.include_router(programs.router, prefix=settings.api_prefix)
    app.include_router(audit.router, prefix=settings.api_prefix)
    app.include_router(protocols.router, prefix=settings.api_prefix)
    app.include_router(digestion.router, prefix=settings.api_prefix)
    return app


app = create_app()
