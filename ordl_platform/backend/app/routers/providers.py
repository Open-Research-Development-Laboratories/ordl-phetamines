from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import append_audit_event, build_actor_snapshot
from app.db import get_db
from app.models import ProviderCredential
from app.providers import PROVIDER_REGISTRY
from app.schemas import ProviderCredentialUpsert
from app.security import Principal, get_current_principal

router = APIRouter(prefix='/providers', tags=['providers'])


def _require_provider_admin(principal: Principal) -> None:
    if not any(role in {'officer', 'board_member'} for role in principal.roles):
        raise HTTPException(status_code=403, detail='provider admin role required')


def _metadata(value: str | None) -> dict[str, Any]:
    try:
        loaded = json.loads(value or '{}')
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


@router.get('')
def list_providers(principal: Principal = Depends(get_current_principal)) -> dict:
    return {'tenant_id': principal.tenant_id, 'providers': PROVIDER_REGISTRY}


@router.post('')
def create_provider_profile(
    payload: dict,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> dict:
    _require_provider_admin(principal)
    provider = str(payload.get('provider') or payload.get('id') or '').strip()
    if not provider:
        raise HTTPException(status_code=400, detail='provider is required')
    row = db.scalar(
        select(ProviderCredential).where(
            ProviderCredential.tenant_id == principal.tenant_id,
            ProviderCredential.provider == provider,
        )
    )
    if row is not None:
        raise HTTPException(status_code=409, detail='provider already exists')
    metadata = payload.get('metadata') if isinstance(payload.get('metadata'), dict) else {}
    row = ProviderCredential(
        tenant_id=principal.tenant_id,
        provider=provider,
        auth_mode=str(payload.get('auth_mode') or 'managed_secret'),
        configured='true' if bool(payload.get('configured', True)) else 'false',
        metadata_json=json.dumps(metadata, sort_keys=True),
    )
    db.add(row)
    append_audit_event(
        db,
        tenant_id=principal.tenant_id,
        project_id=None,
        event_type='provider.created',
        payload={'provider': provider},
        actor=build_actor_snapshot(db, principal),
        resource={'resource_type': 'provider', 'resource_id': provider},
    )
    db.commit()
    return {
        'tenant_id': row.tenant_id,
        'provider': row.provider,
        'auth_mode': row.auth_mode,
        'configured': row.configured == 'true',
        'metadata': json.loads(row.metadata_json),
    }


@router.post('/credentials')
def upsert_credentials(
    payload: ProviderCredentialUpsert,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> dict:
    _require_provider_admin(principal)
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


@router.get('/credentials')
def list_credentials(
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> dict:
    rows = db.scalars(
        select(ProviderCredential)
        .where(ProviderCredential.tenant_id == principal.tenant_id)
        .order_by(ProviderCredential.provider.asc())
    ).all()
    items = []
    for row in rows:
        items.append(
            {
                'tenant_id': row.tenant_id,
                'provider': row.provider,
                'auth_mode': row.auth_mode,
                'configured': row.configured == 'true',
                'metadata': json.loads(row.metadata_json),
            }
        )
    return {'tenant_id': principal.tenant_id, 'credentials': items}


@router.get('/{provider}')
def get_provider_profile(
    provider: str,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> dict:
    return get_credential(provider=provider, principal=principal, db=db)


@router.patch('/{provider}')
def patch_provider_profile(
    provider: str,
    payload: dict,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> dict:
    _require_provider_admin(principal)
    row = db.scalar(
        select(ProviderCredential).where(
            ProviderCredential.tenant_id == principal.tenant_id,
            ProviderCredential.provider == provider,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail='provider not found')
    if 'auth_mode' in payload:
        row.auth_mode = str(payload['auth_mode'])
    if 'configured' in payload:
        row.configured = 'true' if bool(payload['configured']) else 'false'
    meta = _metadata(row.metadata_json)
    if isinstance(payload.get('metadata'), dict):
        meta.update(payload['metadata'])
    row.metadata_json = json.dumps(meta, sort_keys=True)
    db.commit()
    return {
        'tenant_id': row.tenant_id,
        'provider': row.provider,
        'auth_mode': row.auth_mode,
        'configured': row.configured == 'true',
        'metadata': meta,
    }


@router.delete('/{provider}')
def delete_provider_profile(
    provider: str,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> dict:
    _require_provider_admin(principal)
    row = db.scalar(
        select(ProviderCredential).where(
            ProviderCredential.tenant_id == principal.tenant_id,
            ProviderCredential.provider == provider,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail='provider not found')
    db.delete(row)
    db.commit()
    return {'status': 'deleted', 'provider': provider}


@router.post('/{provider}/test')
def test_provider(
    provider: str,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> dict:
    row = db.scalar(
        select(ProviderCredential).where(
            ProviderCredential.tenant_id == principal.tenant_id,
            ProviderCredential.provider == provider,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail='provider not found')
    configured = row.configured == 'true'
    return {'provider': provider, 'status': 'healthy' if configured else 'not_configured', 'configured': configured}


@router.post('/{id}/test')
def test_provider_alias(
    id: str,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> dict:
    return test_provider(provider=id, principal=principal, db=db)


@router.get('/{provider}/logs')
def provider_logs(
    provider: str,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> list[dict]:
    row = db.scalar(
        select(ProviderCredential).where(
            ProviderCredential.tenant_id == principal.tenant_id,
            ProviderCredential.provider == provider,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail='provider not found')
    meta = _metadata(row.metadata_json)
    logs = meta.get('logs', [])
    return logs if isinstance(logs, list) else []


@router.post('/failover')
def force_failover(
    payload: dict,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> dict:
    _require_provider_admin(principal)
    source = str(payload.get('from') or '').strip()
    target = str(payload.get('to') or '').strip()
    if not source or not target:
        raise HTTPException(status_code=400, detail='from and to are required')
    append_audit_event(
        db,
        tenant_id=principal.tenant_id,
        project_id=None,
        event_type='provider.failover',
        payload={'from': source, 'to': target},
        actor=build_actor_snapshot(db, principal),
        resource={'resource_type': 'provider_failover', 'resource_id': f'{source}->{target}'},
    )
    db.commit()
    return {'status': 'accepted', 'from': source, 'to': target}


@router.get('/priority')
def get_provider_priority(
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> list[dict]:
    rows = db.scalars(
        select(ProviderCredential).where(ProviderCredential.tenant_id == principal.tenant_id)
    ).all()
    ordered: list[dict] = []
    for row in rows:
        meta = _metadata(row.metadata_json)
        ordered.append({'provider': row.provider, 'priority': int(meta.get('priority', 100))})
    return sorted(ordered, key=lambda item: item['priority'])


@router.put('/priority')
@router.patch('/priority')
def put_provider_priority(
    payload: dict,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> dict:
    _require_provider_admin(principal)
    order = payload.get('order') or payload.get('providers') or []
    provider_order: list[str] = []
    if isinstance(order, list):
        for item in order:
            if isinstance(item, str):
                provider_order.append(item)
            elif isinstance(item, dict) and item.get('provider'):
                provider_order.append(str(item['provider']))
    for idx, provider in enumerate(provider_order):
        row = db.scalar(
            select(ProviderCredential).where(
                ProviderCredential.tenant_id == principal.tenant_id,
                ProviderCredential.provider == provider,
            )
        )
        if row is None:
            continue
        meta = _metadata(row.metadata_json)
        meta['priority'] = idx + 1
        row.metadata_json = json.dumps(meta, sort_keys=True)
    db.commit()
    return {'updated': provider_order}


@router.get('/{provider}/probes')
def get_provider_probes(
    provider: str,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> list[dict]:
    row = db.scalar(
        select(ProviderCredential).where(
            ProviderCredential.tenant_id == principal.tenant_id,
            ProviderCredential.provider == provider,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail='provider not found')
    probes = _metadata(row.metadata_json).get('probes', [])
    return probes if isinstance(probes, list) else []


@router.post('/{provider}/probes')
def create_provider_probe(
    provider: str,
    payload: dict,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> dict:
    _require_provider_admin(principal)
    row = db.scalar(
        select(ProviderCredential).where(
            ProviderCredential.tenant_id == principal.tenant_id,
            ProviderCredential.provider == provider,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail='provider not found')
    meta = _metadata(row.metadata_json)
    probes = meta.get('probes', [])
    if not isinstance(probes, list):
        probes = []
    probe = {'id': str(payload.get('id') or f'probe-{len(probes)+1}'), **payload}
    probes.append(probe)
    meta['probes'] = probes
    row.metadata_json = json.dumps(meta, sort_keys=True)
    db.commit()
    return probe


@router.patch('/{provider}/probes/{probe_id}')
def patch_provider_probe(
    provider: str,
    probe_id: str,
    payload: dict,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> dict:
    _require_provider_admin(principal)
    row = db.scalar(
        select(ProviderCredential).where(
            ProviderCredential.tenant_id == principal.tenant_id,
            ProviderCredential.provider == provider,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail='provider not found')
    meta = _metadata(row.metadata_json)
    probes = meta.get('probes', [])
    if not isinstance(probes, list):
        probes = []
    target = next((item for item in probes if str(item.get('id')) == probe_id), None)
    if target is None:
        raise HTTPException(status_code=404, detail='probe not found')
    if isinstance(payload, dict):
        target.update(payload)
    meta['probes'] = probes
    row.metadata_json = json.dumps(meta, sort_keys=True)
    db.commit()
    return target


@router.put('/probes')
def put_provider_probes(
    payload: dict,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> dict:
    _require_provider_admin(principal)
    provider = str(payload.get('provider') or '').strip()
    if not provider:
        raise HTTPException(status_code=400, detail='provider is required')
    row = db.scalar(
        select(ProviderCredential).where(
            ProviderCredential.tenant_id == principal.tenant_id,
            ProviderCredential.provider == provider,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail='provider not found')
    probes = payload.get('probes', [])
    if not isinstance(probes, list):
        raise HTTPException(status_code=400, detail='probes must be a list')
    meta = _metadata(row.metadata_json)
    meta['probes'] = probes
    row.metadata_json = json.dumps(meta, sort_keys=True)
    db.commit()
    return {'provider': provider, 'probe_count': len(probes)}


@router.put('/{provider}/config')
def put_provider_config(
    provider: str,
    payload: dict,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> dict:
    return patch_provider_profile(provider=provider, payload={'metadata': payload}, principal=principal, db=db)


@router.put('/{id}/config')
def put_provider_config_alias(
    id: str,
    payload: dict,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> dict:
    return put_provider_config(provider=id, payload=payload, principal=principal, db=db)


@router.get('/credentials/{provider}')
def get_credential(
    provider: str,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> dict:
    row = db.scalar(
        select(ProviderCredential).where(
            ProviderCredential.tenant_id == principal.tenant_id,
            ProviderCredential.provider == provider,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail='provider credential not found')
    return {
        'tenant_id': row.tenant_id,
        'provider': row.provider,
        'auth_mode': row.auth_mode,
        'configured': row.configured == 'true',
        'metadata': json.loads(row.metadata_json),
    }
