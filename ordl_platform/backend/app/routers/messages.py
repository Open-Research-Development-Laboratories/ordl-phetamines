from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import append_audit_event, build_actor_snapshot
from app.authz import evaluate_authorization
from app.common import ensure_project_scope, message_transition_allowed
from app.db import get_db
from app.models import CollabMessage
from app.schemas import MessageCreate, MessageOut, MessageTransition, MessageUpdate
from app.security import Principal, get_current_principal

router = APIRouter(prefix='/messages', tags=['messages'])


def _to_out(msg: CollabMessage) -> MessageOut:
    return MessageOut(
        id=msg.id,
        project_id=msg.project_id,
        author_user_id=msg.author_user_id,
        reviewer_user_id=msg.reviewer_user_id,
        title=msg.title,
        body=msg.body,
        state=msg.state,
        revision=msg.revision,
        parent_message_id=msg.parent_message_id,
        review_notes=msg.review_notes,
    )


@router.post('', response_model=MessageOut)
def create_message(
    payload: MessageCreate,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> MessageOut:
    ensure_project_scope(db, principal, payload.project_id)
    auth = evaluate_authorization(principal, action='write_message')
    if auth.decision != 'allow':
        raise HTTPException(status_code=403, detail=f'message creation denied: {auth.reason_codes}')

    msg = CollabMessage(
        project_id=payload.project_id,
        author_user_id=principal.user_id,
        reviewer_user_id=payload.reviewer_user_id,
        title=payload.title,
        body=payload.body,
        state='draft',
        parent_message_id=payload.parent_message_id,
    )
    db.add(msg)
    db.flush()
    append_audit_event(
        db,
        tenant_id=principal.tenant_id,
        project_id=payload.project_id,
        event_type='message.created',
        payload={'message_id': msg.id, 'title': msg.title},
        actor=build_actor_snapshot(db, principal, payload.project_id),
        resource={'resource_type': 'message', 'resource_id': msg.id},
    )
    db.commit()
    return _to_out(msg)


@router.get('', response_model=list[MessageOut])
def list_messages(
    project_id: str,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> list[MessageOut]:
    ensure_project_scope(db, principal, project_id)
    rows = db.scalars(
        select(CollabMessage)
        .where(CollabMessage.project_id == project_id)
        .order_by(CollabMessage.created_at.asc(), CollabMessage.id.asc())
    ).all()
    return [_to_out(row) for row in rows]


@router.get('/{message_id}', response_model=MessageOut)
def get_message(
    message_id: str,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> MessageOut:
    msg = db.get(CollabMessage, message_id)
    if msg is None:
        raise HTTPException(status_code=404, detail='message not found')
    ensure_project_scope(db, principal, msg.project_id)
    return _to_out(msg)


@router.patch('/{message_id}', response_model=MessageOut)
def update_message(
    message_id: str,
    payload: MessageUpdate,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> MessageOut:
    msg = db.get(CollabMessage, message_id)
    if msg is None:
        raise HTTPException(status_code=404, detail='message not found')
    ensure_project_scope(db, principal, msg.project_id)
    if msg.author_user_id != principal.user_id and principal.user_id != msg.reviewer_user_id:
        raise HTTPException(status_code=403, detail='message update denied')

    if payload.title is not None:
        msg.title = payload.title
    if payload.body is not None:
        msg.body = payload.body
    if payload.review_notes is not None:
        msg.review_notes = payload.review_notes
    msg.revision += 1
    msg.updated_at = datetime.now(timezone.utc)
    append_audit_event(
        db,
        tenant_id=principal.tenant_id,
        project_id=msg.project_id,
        event_type='message.updated',
        payload={'message_id': msg.id, 'revision': msg.revision},
        actor=build_actor_snapshot(db, principal, msg.project_id),
        resource={'resource_type': 'message', 'resource_id': msg.id},
    )

    db.commit()
    return _to_out(msg)


@router.delete('/{message_id}')
def delete_message(
    message_id: str,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> dict:
    msg = db.get(CollabMessage, message_id)
    if msg is None:
        return {'deleted': False}
    ensure_project_scope(db, principal, msg.project_id)
    if msg.author_user_id != principal.user_id and not any(role in {'officer', 'board_member'} for role in principal.roles):
        raise HTTPException(status_code=403, detail='message delete denied')
    append_audit_event(
        db,
        tenant_id=principal.tenant_id,
        project_id=msg.project_id,
        event_type='message.deleted',
        payload={'message_id': msg.id},
        actor=build_actor_snapshot(db, principal, msg.project_id),
        resource={'resource_type': 'message', 'resource_id': msg.id},
    )
    db.delete(msg)
    db.commit()
    return {'deleted': True}


@router.post('/{message_id}/transition', response_model=MessageOut)
def transition_message(
    message_id: str,
    payload: MessageTransition,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> MessageOut:
    msg = db.get(CollabMessage, message_id)
    if msg is None:
        raise HTTPException(status_code=404, detail='message not found')
    ensure_project_scope(db, principal, msg.project_id)

    if not message_transition_allowed(msg, principal, payload.target_state):
        raise HTTPException(status_code=400, detail='invalid transition or actor')

    msg.state = payload.target_state
    if payload.review_notes:
        msg.review_notes = payload.review_notes
    msg.updated_at = datetime.now(timezone.utc)
    append_audit_event(
        db,
        tenant_id=principal.tenant_id,
        project_id=msg.project_id,
        event_type='message.transitioned',
        payload={
            'message_id': msg.id,
            'target_state': payload.target_state,
            'review_notes': payload.review_notes or '',
        },
        actor=build_actor_snapshot(db, principal, msg.project_id),
        resource={'resource_type': 'message', 'resource_id': msg.id},
    )
    db.commit()
    return _to_out(msg)
