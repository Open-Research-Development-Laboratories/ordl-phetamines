from __future__ import annotations

from fastapi import APIRouter, Depends

from app.common import utc_now_iso
from app.config import get_settings
from app.security import Principal, get_current_principal

router = APIRouter(tags=['ops'])


@router.get('/info')
def info(principal: Principal = Depends(get_current_principal)) -> dict:
    settings = get_settings()
    return {
        'service': settings.app_name,
        'environment': settings.environment,
        'tenant_id': principal.tenant_id,
        'timestamp': utc_now_iso(),
    }
