from __future__ import annotations

from tests.conftest import bearer, issue_token, setup_project


def test_worker_reconnect_policy_surface(client):
    officer = issue_token(client, 'Tenant-Conn', 'officer@conn.test', ['officer'], clearance='restricted')
    operator = issue_token(client, 'Tenant-Conn', 'operator@conn.test', ['operator'], clearance='restricted')
    _, _, project_id = setup_project(client, officer)

    me = client.get('/v1/auth/me', headers=bearer(operator))
    assert me.status_code == 200, me.text
    operator_user_id = me.json()['user_id']

    seat = client.post(
        '/v1/seats',
        headers=bearer(officer),
        json={
            'project_id': project_id,
            'user_id': operator_user_id,
            'role': 'operator',
            'rank': 'member',
            'position': 'gateway_operator',
            'group_name': 'ops',
            'clearance_tier': 'restricted',
            'compartments': ['alpha', 'ops'],
            'status': 'active',
        },
    )
    assert seat.status_code == 200, seat.text

    worker = client.post(
        '/v1/workers/register',
        headers=bearer(operator),
        json={
            'project_id': project_id,
            'name': 'worker-build-laptop',
            'role': 'builder',
            'host': '10.0.0.28',
            'device_id': 'device-build-laptop',
            'capabilities': ['python', 'tests'],
        },
    )
    assert worker.status_code == 200, worker.text
    worker_id = worker.json()['id']

    heartbeat = client.post(
        f'/v1/workers/{worker_id}/heartbeat',
        headers=bearer(operator),
        json={
            'gateway_url': 'ws://10.0.0.48:18789',
            'gateway_candidates': ['ws://10.0.0.48:18789', 'wss://flint.org.org'],
            'gateway_rtt_ms': 18,
            'keepalive_interval_seconds': 20,
            'keepalive_miss_threshold': 3,
            'connectivity_state': 'online',
        },
    )
    assert heartbeat.status_code == 200, heartbeat.text

    connectivity = client.get(
        '/v1/workers/connectivity',
        headers=bearer(operator),
        params={'project_id': project_id, 'stale_after_seconds': 120},
    )
    assert connectivity.status_code == 200, connectivity.text
    rows = connectivity.json()
    assert rows
    row = rows[0]
    assert row['reconnect_required'] is False
    assert row['reconnect_targets'][0] == 'ws://10.0.0.48:18789'

    probe_down = client.post(
        f'/v1/workers/{worker_id}/probe',
        headers=bearer(operator),
        json={'reachable': False, 'gateway_url': 'ws://10.0.0.48:18789', 'gateway_rtt_ms': -1, 'reason': 'probe_timeout'},
    )
    assert probe_down.status_code == 200, probe_down.text

    connectivity_after = client.get(
        '/v1/workers/connectivity',
        headers=bearer(operator),
        params={'project_id': project_id, 'stale_after_seconds': 120},
    )
    assert connectivity_after.status_code == 200, connectivity_after.text
    after = connectivity_after.json()[0]
    assert after['connectivity_state'] == 'down'
    assert after['reconnect_required'] is True
