from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path: Path):
    db_path = tmp_path / 'test.db'
    os.environ['ORDL_DATABASE_URL'] = f"sqlite:///{db_path.as_posix()}"

    from app.config import get_settings

    get_settings.cache_clear()

    from app.main import create_app

    app = create_app()
    with TestClient(app) as c:
        yield c


def issue_token(client: TestClient, tenant: str, email: str, roles: list[str], clearance: str = 'restricted') -> str:
    res = client.post(
        '/v1/auth/token',
        json={
            'tenant_name': tenant,
            'email': email,
            'display_name': email.split('@')[0],
            'roles': roles,
            'clearance_tier': clearance,
            'compartments': ['alpha', 'ops'],
        },
    )
    assert res.status_code == 200, res.text
    return res.json()['access_token']


def bearer(token: str) -> dict[str, str]:
    return {'Authorization': f'Bearer {token}'}


def setup_project(client: TestClient, officer_token: str) -> tuple[str, str, str]:
    org = client.post('/v1/orgs', headers=bearer(officer_token), json={'tenant_id': _tenant_id(client, officer_token), 'name': 'OrgA'})
    assert org.status_code == 200, org.text
    org_id = org.json()['id']

    team = client.post('/v1/teams', headers=bearer(officer_token), json={'org_id': org_id, 'name': 'TeamA'})
    assert team.status_code == 200, team.text
    team_id = team.json()['id']

    project = client.post(
        '/v1/projects',
        headers=bearer(officer_token),
        json={'team_id': team_id, 'code': 'PRJ1', 'name': 'Project One', 'ingress_mode': 'zero_trust', 'visibility_mode': 'scoped'},
    )
    assert project.status_code == 200, project.text
    return org_id, team_id, project.json()['id']


def _tenant_id(client: TestClient, token: str) -> str:
    me = client.get('/v1/auth/me', headers=bearer(token))
    assert me.status_code == 200, me.text
    return me.json()['tenant_id']
