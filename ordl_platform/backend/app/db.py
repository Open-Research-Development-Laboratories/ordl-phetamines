from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings


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


def get_db() -> Generator[Session, None, None]:
    db = get_session_local()()
    try:
        yield db
    finally:
        db.close()

