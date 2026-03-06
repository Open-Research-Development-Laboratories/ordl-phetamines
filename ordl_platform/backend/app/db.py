from __future__ import annotations

from collections.abc import Generator

from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.security import Principal, get_optional_principal


_ENGINE = None
_SESSION_LOCAL: sessionmaker[Session] | None = None


def init_engine(database_url: str | None = None) -> None:
    global _ENGINE
    global _SESSION_LOCAL

    settings = get_settings()
    db_url = database_url or settings.database_url
    connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}
    _ENGINE = create_engine(db_url, future=True, connect_args=connect_args)
    _SESSION_LOCAL = sessionmaker(autocommit=False, autoflush=False, bind=_ENGINE, expire_on_commit=False)


def get_engine():
    if _ENGINE is None:
        init_engine()
    return _ENGINE


def get_session_local() -> sessionmaker[Session]:
    if _SESSION_LOCAL is None:
        init_engine()
    assert _SESSION_LOCAL is not None
    return _SESSION_LOCAL


def _is_postgres_session(db: Session) -> bool:
    bind = db.get_bind()
    return bool(bind is not None and bind.dialect.name == 'postgresql')


def _set_session_scope(
    db: Session,
    *,
    tenant_id: str,
    user_id: str,
    bypass: bool,
) -> None:
    settings = get_settings()
    if not settings.db_rls_enabled or not _is_postgres_session(db):
        return
    db.execute(text("select set_config('app.current_tenant_id', :tenant_id, true)"), {'tenant_id': tenant_id})
    db.execute(text("select set_config('app.current_user_id', :user_id, true)"), {'user_id': user_id})
    db.execute(text("select set_config('app.rls_bypass', :bypass, true)"), {'bypass': '1' if bypass else '0'})


def bind_principal_scope(db: Session, principal: Principal) -> None:
    _set_session_scope(
        db,
        tenant_id=str(principal.tenant_id or ''),
        user_id=str(principal.user_id or ''),
        bypass=False,
    )


def bind_anonymous_scope(db: Session) -> None:
    _set_session_scope(db, tenant_id='', user_id='', bypass=False)


def enable_rls_bypass(db: Session) -> None:
    _set_session_scope(db, tenant_id='', user_id='system-bootstrap', bypass=True)


def get_db(
    principal: Principal | None = Depends(get_optional_principal),
) -> Generator[Session, None, None]:
    db = get_session_local()()
    try:
        if isinstance(principal, Principal):
            bind_principal_scope(db, principal)
        else:
            bind_anonymous_scope(db)
        yield db
    finally:
        db.close()
