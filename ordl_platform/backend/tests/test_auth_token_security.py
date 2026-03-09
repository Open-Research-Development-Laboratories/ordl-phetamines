from __future__ import annotations

import os
from pathlib import Path

from fastapi.testclient import TestClient


def test_auth_token_issuer_disabled_by_default(tmp_path: Path) -> None:
    db_path = tmp_path / 'security.db'
    os.environ['ORDL_DATABASE_URL'] = f"sqlite:///{db_path.as_posix()}"
    os.environ.pop('ORDL_ALLOW_LOCAL_TOKEN_ISSUER', None)

    from app.config import get_settings

    get_settings.cache_clear()

    from app.main import create_app

    app = create_app()
    with TestClient(app) as client:
        res = client.post(
            '/v1/auth/token',
            json={
                'tenant_name': 'Tenant-Sec',
                'email': 'attacker@sec.test',
                'display_name': 'attacker',
                'roles': ['board_member'],
                'clearance_tier': 'restricted',
                'compartments': ['ops'],
            },
        )

    assert res.status_code == 403
    assert res.json()['detail'] == 'local token issuance disabled'
