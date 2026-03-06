from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import ProviderCredential
from app.providers import PROVIDER_REGISTRY
from app.schemas import ProviderCredentialUpsert
from app.security import Principal, get_current_principal

router = APIRouter(prefix='/providers', tags=['providers'])


@router.get('')
def list_providers(principal: Principal = Depends(get_current_principal)) -> dict:
    return {'tenant_id': principal.tenant_id, 'providers': PROVIDER_REGISTRY}


@router.post('/credentials')
def upsert_credentials(
    payload: ProviderCredentialUpsert,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> dict:
    if payload.tenant_id != principal.tenant_id:
        raise HTTPException(status_code=403, detail='tenant scope denied')
    if payload.provider not in PROVIDER_REGISTRY:
        raise HTTPException(status_code=400, detail=f"unsupported provider: {payload.provider}")

    row = db.scalar(
        select(ProviderCredential).where(
            ProviderCredential.tenant_id == payload.tenant_id,
            ProviderCredential.provider == payload.provider,
        )
    )
    if row is None:
        row = ProviderCredential(tenant_id=payload.tenant_id, provider=payload.provider)
        db.add(row)

    row.auth_mode = payload.auth_mode
    row.configured = 'true' if payload.configured else 'false'
    row.metadata_json = json.dumps(payload.metadata, sort_keys=True)
    db.commit()

    return {
        'tenant_id': row.tenant_id,
        'provider': row.provider,
        'auth_mode': row.auth_mode,
        'configured': row.configured == 'true',
        'metadata': json.loads(row.metadata_json),
    }
