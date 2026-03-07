from __future__ import annotations

from tests.conftest import bearer, issue_token, setup_project


def _add_operator_seat(client, officer_token: str, operator_token: str, project_id: str) -> str:
    me = client.get('/v1/auth/me', headers=bearer(operator_token))
    assert me.status_code == 200, me.text
    operator_user_id = me.json()['user_id']
    seat = client.post(
        '/v1/seats',
        headers=bearer(officer_token),
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
    return operator_user_id


def _register_worker(client, operator_token: str, project_id: str, name: str, host: str, device_id: str) -> str:
    worker = client.post(
        '/v1/workers/register',
        headers=bearer(operator_token),
        json={
            'project_id': project_id,
            'name': name,
            'role': 'builder',
            'host': host,
            'device_id': device_id,
            'capabilities': ['python'],
        },
    )
    assert worker.status_code == 200, worker.text
    return worker.json()['id']


def test_worker_action_pending_and_ack_flow(client):
    officer = issue_token(client, 'Tenant-Action', 'officer@action.test', ['officer'], clearance='restricted')
    operator = issue_token(client, 'Tenant-Action', 'operator@action.test', ['operator'], clearance='restricted')
    _, _, project_id = setup_project(client, officer)
    _add_operator_seat(client, officer, operator, project_id)

    worker_id = _register_worker(
        client,
        operator,
        project_id,
        'worker-build-laptop',
        '198.51.100.28',
        'device-build-laptop',
    )

    queued = client.post(
        f'/v1/workers/{worker_id}/action',
        headers=bearer(operator),
        json={'action': 'reconnect_gateway', 'notes': 'queued-by-test'},
    )
    assert queued.status_code == 200, queued.text
    action_id = queued.json()['worker_action_id']

    pending = client.get(
        f'/v1/workers/{worker_id}/actions/pending',
        headers=bearer(operator),
    )
    assert pending.status_code == 200, pending.text
    rows = pending.json()
    assert len(rows) == 1
    assert rows[0]['id'] == action_id
    assert rows[0]['status'] == 'queued'

    in_progress = client.post(
        f'/v1/workers/actions/{action_id}/ack',
        headers=bearer(operator),
        json={'status': 'in_progress', 'result': {'step': 'connecting'}, 'error': '', 'notes': 'started'},
    )
    assert in_progress.status_code == 200, in_progress.text
    assert in_progress.json()['status'] == 'in_progress'

    completed = client.post(
        f'/v1/workers/actions/{action_id}/ack',
        headers=bearer(operator),
        json={'status': 'completed', 'result': {'gateway': 'ws://198.51.100.48:18789'}, 'error': '', 'notes': 'done'},
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()['status'] == 'completed'
    assert 'gateway' in completed.json()['notes']

    pending_after = client.get(
        f'/v1/workers/{worker_id}/actions/pending',
        headers=bearer(operator),
    )
    assert pending_after.status_code == 200, pending_after.text
    assert pending_after.json() == []

    invalid = client.post(
        f'/v1/workers/actions/{action_id}/ack',
        headers=bearer(operator),
        json={'status': 'failed', 'result': {}, 'error': 'late-failure', 'notes': 'invalid transition'},
    )
    assert invalid.status_code == 400, invalid.text


def test_worker_action_tenant_isolation(client):
    officer_a = issue_token(client, 'Tenant-Action-A', 'officer-a@action.test', ['officer'], clearance='restricted')
    operator_a = issue_token(client, 'Tenant-Action-A', 'operator-a@action.test', ['operator'], clearance='restricted')
    officer_b = issue_token(client, 'Tenant-Action-B', 'officer-b@action.test', ['officer'], clearance='restricted')
    operator_b = issue_token(client, 'Tenant-Action-B', 'operator-b@action.test', ['operator'], clearance='restricted')

    _, _, project_a = setup_project(client, officer_a)
    _add_operator_seat(client, officer_a, operator_a, project_a)
    worker_a = _register_worker(
        client,
        operator_a,
        project_a,
        'worker-a',
        '198.51.100.31',
        'device-worker-a',
    )
    queued = client.post(
        f'/v1/workers/{worker_a}/action',
        headers=bearer(operator_a),
        json={'action': 'probe_gateway', 'notes': 'tenant-a'},
    )
    assert queued.status_code == 200, queued.text
    action_id = queued.json()['worker_action_id']

    _, _, project_b = setup_project(client, officer_b)
    _add_operator_seat(client, officer_b, operator_b, project_b)

    denied_pending = client.get(
        f'/v1/workers/{worker_a}/actions/pending',
        headers=bearer(operator_b),
    )
    assert denied_pending.status_code in {403, 404}

    denied_ack = client.post(
        f'/v1/workers/actions/{action_id}/ack',
        headers=bearer(operator_b),
        json={'status': 'failed', 'result': {}, 'error': 'unauthorized', 'notes': ''},
    )
    assert denied_ack.status_code in {403, 404}

