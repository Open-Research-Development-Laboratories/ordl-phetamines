from __future__ import annotations

from sqlalchemy import select

from app.models import WorkerAction
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


def test_worker_monitor_run_once_queues_actions_and_throttles(client):
    officer = issue_token(client, 'Tenant-Monitor', 'officer@monitor.test', ['officer'], clearance='restricted')
    operator = issue_token(client, 'Tenant-Monitor', 'operator@monitor.test', ['operator'], clearance='restricted')
    _, _, project_id = setup_project(client, officer)
    _add_operator_seat(client, officer, operator, project_id)

    worker_id = _register_worker(
        client,
        operator,
        project_id,
        'worker-build-laptop',
        '10.0.0.28',
        'device-build-laptop',
    )

    config = client.post(
        '/v1/workers/monitor/config',
        headers=bearer(operator),
        json={
            'project_id': project_id,
            'enabled': True,
            'loop_interval_seconds': 20,
            'stale_after_seconds': 45,
            'queue_throttle_seconds': 600,
            'probe_action_enabled': True,
            'reconnect_action_enabled': True,
        },
    )
    assert config.status_code == 200, config.text

    first = client.post(
        '/v1/workers/monitor/run-once',
        headers=bearer(operator),
        json={'project_id': project_id, 'force': False},
    )
    assert first.status_code == 200, first.text
    body = first.json()
    assert body['total_workers'] == 1
    assert body['stale_workers'] == 1
    assert body['probe_actions_queued'] == 1
    assert body['reconnect_actions_queued'] == 1

    second = client.post(
        '/v1/workers/monitor/run-once',
        headers=bearer(operator),
        json={'project_id': project_id, 'force': False},
    )
    assert second.status_code == 200, second.text
    body2 = second.json()
    assert body2['probe_actions_queued'] == 0
    assert body2['reconnect_actions_queued'] == 0

    from app.db import get_session_local

    with get_session_local()() as db:
        actions = db.scalars(
            select(WorkerAction)
            .where(WorkerAction.worker_id == worker_id)
            .order_by(WorkerAction.created_at.asc())
        ).all()
        assert len(actions) == 2
        assert {row.action for row in actions} == {'probe_gateway', 'reconnect_gateway'}


def test_worker_monitor_disabled_requires_force(client):
    officer = issue_token(client, 'Tenant-Monitor-2', 'officer2@monitor.test', ['officer'], clearance='restricted')
    operator = issue_token(client, 'Tenant-Monitor-2', 'operator2@monitor.test', ['operator'], clearance='restricted')
    _, _, project_id = setup_project(client, officer)
    _add_operator_seat(client, officer, operator, project_id)

    _register_worker(
        client,
        operator,
        project_id,
        'worker-batch-server',
        '10.0.0.27',
        'device-batch-server',
    )

    disable = client.post(
        '/v1/workers/monitor/config',
        headers=bearer(operator),
        json={
            'project_id': project_id,
            'enabled': False,
            'loop_interval_seconds': 20,
            'stale_after_seconds': 45,
            'queue_throttle_seconds': 0,
            'probe_action_enabled': True,
            'reconnect_action_enabled': True,
        },
    )
    assert disable.status_code == 200, disable.text
    assert disable.json()['enabled'] is False

    skipped = client.post(
        '/v1/workers/monitor/run-once',
        headers=bearer(operator),
        json={'project_id': project_id, 'force': False},
    )
    assert skipped.status_code == 200, skipped.text
    assert skipped.json()['skipped'] is True
    assert skipped.json()['reason'] == 'monitor_disabled'

    forced = client.post(
        '/v1/workers/monitor/run-once',
        headers=bearer(operator),
        json={'project_id': project_id, 'force': True},
    )
    assert forced.status_code == 200, forced.text
    assert forced.json().get('skipped') is None
    assert forced.json()['total_workers'] == 1

