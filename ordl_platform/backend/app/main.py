from __future__ import annotations

from fastapi import FastAPI

from app.common import utc_now_iso
from app.config import get_settings
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
    protocols,
    providers,
    seats,
    workers,
)

settings = get_settings()


def create_app() -> FastAPI:
    init_engine(settings.database_url)
    Base.metadata.create_all(bind=get_engine())

    app = FastAPI(title=settings.app_name)

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
    app.include_router(audit.router, prefix=settings.api_prefix)
    app.include_router(protocols.router, prefix=settings.api_prefix)
    app.include_router(digestion.router, prefix=settings.api_prefix)
    return app


app = create_app()
