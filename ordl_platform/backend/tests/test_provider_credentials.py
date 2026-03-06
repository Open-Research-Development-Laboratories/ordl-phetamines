from __future__ import annotations

from tests.conftest import bearer, issue_token


def test_provider_credentials_list_and_get(client):
    officer = issue_token(client, 'Tenant-Prov', 'officer@prov.test', ['officer'], clearance='restricted')
    me = client.get('/v1/auth/me', headers=bearer(officer))
    assert me.status_code == 200, me.text
    tenant_id = me.json()['tenant_id']

    upsert = client.post(
        '/v1/providers/credentials',
        headers=bearer(officer),
        json={
            'tenant_id': tenant_id,
            'provider': 'openai_codex',
            'auth_mode': 'managed_secret',
            'configured': True,
            'metadata': {'live_enabled': False, 'default_model': 'gpt-5.4'},
        },
    )
    assert upsert.status_code == 200, upsert.text

    listed = client.get('/v1/providers/credentials', headers=bearer(officer))
    assert listed.status_code == 200, listed.text
    creds = listed.json()['credentials']
    assert any(item['provider'] == 'openai_codex' for item in creds)

    fetched = client.get('/v1/providers/credentials/openai_codex', headers=bearer(officer))
    assert fetched.status_code == 200, fetched.text
    assert fetched.json()['provider'] == 'openai_codex'
    assert fetched.json()['configured'] is True


def test_provider_credentials_tenant_scope_isolation(client):
    officer_a = issue_token(client, 'Tenant-Prov-A', 'officer-a@prov.test', ['officer'], clearance='restricted')
    officer_b = issue_token(client, 'Tenant-Prov-B', 'officer-b@prov.test', ['officer'], clearance='restricted')
    me_a = client.get('/v1/auth/me', headers=bearer(officer_a))
    me_b = client.get('/v1/auth/me', headers=bearer(officer_b))
    assert me_a.status_code == 200 and me_b.status_code == 200
    tenant_a = me_a.json()['tenant_id']
    tenant_b = me_b.json()['tenant_id']

    upsert_a = client.post(
        '/v1/providers/credentials',
        headers=bearer(officer_a),
        json={
            'tenant_id': tenant_a,
            'provider': 'kimi',
            'auth_mode': 'managed_secret',
            'configured': True,
            'metadata': {'live_enabled': False},
        },
    )
    assert upsert_a.status_code == 200, upsert_a.text

    denied_cross = client.post(
        '/v1/providers/credentials',
        headers=bearer(officer_b),
        json={
            'tenant_id': tenant_a,
            'provider': 'kimi',
            'auth_mode': 'managed_secret',
            'configured': True,
            'metadata': {'live_enabled': True},
        },
    )
    assert denied_cross.status_code == 403

    not_found_b = client.get('/v1/providers/credentials/kimi', headers=bearer(officer_b))
    assert not_found_b.status_code == 404

    list_b = client.get('/v1/providers/credentials', headers=bearer(officer_b))
    assert list_b.status_code == 200
    assert all(item['tenant_id'] == tenant_b for item in list_b.json()['credentials'])

