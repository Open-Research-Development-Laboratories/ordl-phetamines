from __future__ import annotations

import hashlib
import hmac
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.authz import evaluate_authorization
from app.common import json_list
from app.config import get_settings
from app.db import get_db
from app.models import Extension
from app.schemas import ExtensionBatchRequest, ExtensionCreate, ExtensionOut, ExtensionVerifyRequest
from app.security import Principal, get_current_principal

router = APIRouter(prefix='/extensions', tags=['extensions'])


def _canonical_signature_input(name: str, version: str, scopes: list[str]) -> str:
    return f"{name}:{version}:{','.join(sorted(scopes))}"


@router.post('', response_model=ExtensionOut)
def register_extension(
    payload: ExtensionCreate,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> ExtensionOut:
    if payload.tenant_id != principal.tenant_id:
        raise HTTPException(status_code=403, detail='tenant scope denied')

    auth = evaluate_authorization(principal, action='manage_extensions')
    if auth.decision != 'allow':
        raise HTTPException(status_code=403, detail=f'extension registration denied: {auth.reason_codes}')

    settings = get_settings()
    canonical = _canonical_signature_input(payload.name, payload.version, payload.scopes)
    expected = hmac.new(
        settings.extension_signing_secret.encode('utf-8'),
        canonical.encode('utf-8'),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, payload.signature):
        raise HTTPException(status_code=400, detail='invalid extension signature')

    row = Extension(
        tenant_id=payload.tenant_id,
        name=payload.name,
        version=payload.version,
        signature=payload.signature,
        scopes_json=json.dumps(payload.scopes, sort_keys=True),
        status='active',
    )
    db.add(row)
    db.commit()
    return ExtensionOut(
        id=row.id,
        tenant_id=row.tenant_id,
        name=row.name,
        version=row.version,
        scopes=json_list(row.scopes_json),
        status=row.status,
    )


@router.get('', response_model=list[ExtensionOut])
def list_extensions(
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> list[ExtensionOut]:
    rows = db.scalars(select(Extension).where(Extension.tenant_id == principal.tenant_id)).all()
    return [
        ExtensionOut(
            id=row.id,
            tenant_id=row.tenant_id,
            name=row.name,
            version=row.version,
            scopes=json_list(row.scopes_json),
            status=row.status,
        )
        for row in rows
    ]


@router.post('/{extension_id}/status', response_model=ExtensionOut)
def set_extension_status(
    extension_id: str,
    status: str,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> ExtensionOut:
    row = db.get(Extension, extension_id)
    if row is None:
        raise HTTPException(status_code=404, detail='extension not found')
    if row.tenant_id != principal.tenant_id:
        raise HTTPException(status_code=403, detail='tenant scope denied')
    auth = evaluate_authorization(principal, action='manage_extensions')
    if auth.decision != 'allow':
        raise HTTPException(status_code=403, detail=f'extension update denied: {auth.reason_codes}')

    row.status = status
    db.commit()
    return ExtensionOut(
        id=row.id,
        tenant_id=row.tenant_id,
        name=row.name,
        version=row.version,
        scopes=json_list(row.scopes_json),
        status=row.status,
    )


@router.post('/verify')
def verify_extensions(
    payload: ExtensionVerifyRequest,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> dict:
    auth = evaluate_authorization(principal, action='manage_extensions')
    if auth.decision != 'allow':
        raise HTTPException(status_code=403, detail=f'extension verify denied: {auth.reason_codes}')

    settings = get_settings()
    stmt = select(Extension).where(Extension.tenant_id == principal.tenant_id)
    if payload.extension_ids:
        stmt = stmt.where(Extension.id.in_(payload.extension_ids))
    rows = db.scalars(stmt).all()

    results: list[dict] = []
    for row in rows:
        scopes = json_list(row.scopes_json)
        canonical = _canonical_signature_input(row.name, row.version, scopes)
        expected = hmac.new(
            settings.extension_signing_secret.encode('utf-8'),
            canonical.encode('utf-8'),
            hashlib.sha256,
        ).hexdigest()
        results.append(
            {
                'extension_id': row.id,
                'name': row.name,
                'version': row.version,
                'status': row.status,
                'signature_valid': hmac.compare_digest(expected, row.signature),
            }
        )
    return {'count': len(results), 'results': results}


@router.post('/batch')
def batch_extensions(
    payload: ExtensionBatchRequest,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> dict:
    auth = evaluate_authorization(principal, action='manage_extensions')
    if auth.decision != 'allow':
        raise HTTPException(status_code=403, detail=f'extension batch denied: {auth.reason_codes}')
    if not payload.extension_ids:
        raise HTTPException(status_code=400, detail='extension_ids is required')

    rows = db.scalars(
        select(Extension).where(
            Extension.tenant_id == principal.tenant_id,
            Extension.id.in_(payload.extension_ids),
        )
    ).all()
    found = {row.id for row in rows}
    missing = [eid for eid in payload.extension_ids if eid not in found]

    updated = 0
    deleted = 0
    for row in rows:
        if payload.operation == 'activate':
            row.status = 'active'
            updated += 1
        elif payload.operation == 'disable':
            row.status = 'disabled'
            updated += 1
        elif payload.operation == 'revoke':
            row.status = 'revoked'
            updated += 1
        elif payload.operation == 'delete':
            db.delete(row)
            deleted += 1

    db.commit()
    return {
        'operation': payload.operation,
        'updated': updated,
        'deleted': deleted,
        'missing_extension_ids': missing,
        'reason': payload.reason,
    }
