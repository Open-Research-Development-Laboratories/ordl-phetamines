import hashlib
import hmac

from conftest import bearer, issue_token


def test_extension_signature_verification(client):
    officer = issue_token(client, 'TenantE', 'officer@e.test', ['officer'])
    me = client.get('/v1/auth/me', headers=bearer(officer)).json()

    bad = client.post(
        '/v1/extensions',
        headers=bearer(officer),
        json={
            'tenant_id': me['tenant_id'],
            'name': 'mcp.bridge',
            'version': '1.0.0',
            'scopes': ['dispatch.read', 'dispatch.write'],
            'signature': 'invalid',
        },
    )
    assert bad.status_code == 400

    canonical = 'mcp.bridge:1.0.0:dispatch.read,dispatch.write'
    signature = hmac.new(
        b'ordl-dev-extension-secret-please-change-this-32b',
        canonical.encode('utf-8'),
        hashlib.sha256,
    ).hexdigest()

    good = client.post(
        '/v1/extensions',
        headers=bearer(officer),
        json={
            'tenant_id': me['tenant_id'],
            'name': 'mcp.bridge',
            'version': '1.0.0',
            'scopes': ['dispatch.read', 'dispatch.write'],
            'signature': signature,
        },
    )
    assert good.status_code == 200, good.text
    assert good.json()['name'] == 'mcp.bridge'
