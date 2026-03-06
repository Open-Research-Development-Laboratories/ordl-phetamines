from __future__ import annotations

from datetime import datetime, timezone
import time

from sqlalchemy import select

from app.db import get_engine, get_session_local, init_engine
from app.models import Base, WorkerAction


def run_loop(poll_interval: float = 2.0) -> None:
    init_engine()
    Base.metadata.create_all(bind=get_engine())
    session_factory = get_session_local()

    while True:
        with session_factory() as db:
            pending = db.scalars(
                select(WorkerAction)
                .where(WorkerAction.status == 'queued')
                .order_by(WorkerAction.created_at.asc())
                .limit(50)
            ).all()
            for action in pending:
                action.status = 'completed'
                action.notes = f"{action.notes}\ncompleted_at={datetime.now(timezone.utc).isoformat()}"
            if pending:
                db.commit()
        time.sleep(poll_interval)


if __name__ == '__main__':
    run_loop()
