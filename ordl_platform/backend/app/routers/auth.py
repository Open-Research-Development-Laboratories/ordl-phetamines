from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common import ensure_user_scope
from app.db import enable_rls_bypass, get_db
from app.models import Tenant, User
from app.schemas import TokenRequest, TokenResponse
from app.security import Principal, create_access_token, get_current_principal

router = APIRouter(prefix='/auth', tags=['auth'])


@router.post('/token', response_model=TokenResponse)
def issue_token(payload: TokenRequest, db: Session = Depends(get_db)) -> TokenResponse:
    from app.config import get_settings

    settings = get_settings()
    if settings.oidc_required and not settings.allow_local_token_issuer:
        raise HTTPException(status_code=403, detail="local token issuance disabled in oidc-required mode")

    # Token issuance runs before a tenant-scoped identity exists.
    enable_rls_bypass(db)

    tenant = db.scalar(select(Tenant).where(Tenant.name == payload.tenant_name))
    if tenant is None:
        tenant = Tenant(name=payload.tenant_name, tenant_type='organization')
        db.add(tenant)
        db.flush()

    user = db.scalar(select(User).where(User.email == payload.email))
    if user is None:
        user = User(
            tenant_id=tenant.id,
            email=payload.email,
            display_name=payload.display_name,
            roles_json=json.dumps(payload.roles, sort_keys=True),
        )
        db.add(user)
        db.flush()
    else:
        user.tenant_id = tenant.id
        user.display_name = payload.display_name or user.display_name
        user.roles_json = json.dumps(payload.roles, sort_keys=True)

    token = create_access_token(
        user_id=user.id,
        tenant_id=tenant.id,
        roles=payload.roles,
        clearance_tier=payload.clearance_tier,
        compartments=payload.compartments,
        settings=settings,
    )
    db.commit()
    return TokenResponse(access_token=token, user_id=user.id, tenant_id=tenant.id)


@router.get('/me')
def auth_me(principal: Principal = Depends(get_current_principal), db: Session = Depends(get_db)) -> dict:
    user = ensure_user_scope(db, principal)
    return {
        'user_id': principal.user_id,
        'tenant_id': principal.tenant_id,
        'roles': principal.roles,
        'clearance_tier': principal.clearance_tier,
        'compartments': principal.compartments,
        'email': user.email,
        'display_name': user.display_name,
    }
