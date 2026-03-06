from __future__ import annotations

from tests.conftest import bearer, issue_token, setup_project


def test_audit_events_and_chain_verify(client):
    officer_token = issue_token(
        client,
        tenant='tenant-a',
        email='ceo@ordl.org',
        roles=['officer'],
        clearance='restricted',
    )
    architect_token = issue_token(
        client,
        tenant='tenant-a',
        email='architect@ordl.org',
        roles=['architect'],
        clearance='restricted',
    )
    _, _, project_id = setup_project(client, officer_token)

    me_arch = client.get('/v1/auth/me', headers=bearer(architect_token))
    assert me_arch.status_code == 200, me_arch.text
    architect_user_id = me_arch.json()['user_id']

    seat = client.post(
        '/v1/seats',
        headers=bearer(officer_token),
        json={
            'project_id': project_id,
            'user_id': architect_user_id,
            'role': 'architect',
            'rank': 'member',
            'position': 'system_architect',
            'group_name': 'r_and_d',
            'clearance_tier': 'restricted',
            'compartments': ['alpha', 'ops'],
            'status': 'active',
        },
    )
    assert seat.status_code == 200, seat.text

    created = client.post(
        '/v1/messages',
        headers=bearer(architect_token),
        json={
            'project_id': project_id,
            'title': 'Audit trail seed',
            'body': 'create deterministic audit event',
        },
    )
    assert created.status_code == 200, created.text
    message_id = created.json()['id']

    transitioned = client.post(
        f'/v1/messages/{message_id}/transition',
        headers=bearer(architect_token),
        json={'target_state': 'review', 'review_notes': 'ready for review'},
    )
    assert transitioned.status_code == 200, transitioned.text

    events = client.get(
        '/v1/audit/events',
        headers=bearer(officer_token),
        params={'project_id': project_id},
    )
    assert events.status_code == 200, events.text
    payload = events.json()
    assert isinstance(payload, list)
    assert len(payload) >= 2

    event_types = {row['event_type'] for row in payload}
    assert 'project.created' in event_types
    assert 'message.created' in event_types
    assert 'message.transitioned' in event_types

    first = payload[0]
    assert first['actor_type'] == 'user'
    assert first['actor_id']
    assert isinstance(first['actor'], dict)
    assert isinstance(first['payload'], dict)
    assert first['event_hash']
    assert first['hash_version'] == 'v2'

    verify = client.get(
        '/v1/audit/verify',
        headers=bearer(officer_token),
        params={'project_id': project_id},
    )
    assert verify.status_code == 200, verify.text
    verify_payload = verify.json()
    assert verify_payload['ok'] is True
    assert verify_payload['events_examined'] >= 2
    assert verify_payload['events_verified'] >= 2


def test_audit_event_actor_filter(client):
    officer_token = issue_token(
        client,
        tenant='tenant-b',
        email='lead@ordl.org',
        roles=['officer'],
        clearance='restricted',
    )
    engineer_token = issue_token(
        client,
        tenant='tenant-b',
        email='worker@ordl.org',
        roles=['engineer'],
        clearance='restricted',
    )
    _, _, project_id = setup_project(client, officer_token)

    me_engineer = client.get('/v1/auth/me', headers=bearer(engineer_token))
    assert me_engineer.status_code == 200, me_engineer.text
    engineer_user_id = me_engineer.json()['user_id']

    seat = client.post(
        '/v1/seats',
        headers=bearer(officer_token),
        json={
            'project_id': project_id,
            'user_id': engineer_user_id,
            'role': 'engineer',
            'rank': 'member',
            'position': 'developer',
            'group_name': 'delivery',
            'clearance_tier': 'restricted',
            'compartments': ['alpha', 'ops'],
            'status': 'active',
        },
    )
    assert seat.status_code == 200, seat.text

    msg = client.post(
        '/v1/messages',
        headers=bearer(engineer_token),
        json={'project_id': project_id, 'title': 'filter check', 'body': 'actor filter check'},
    )
    assert msg.status_code == 200, msg.text

    me = client.get('/v1/auth/me', headers=bearer(engineer_token))
    assert me.status_code == 200, me.text
    actor_id = me.json()['user_id']

    filtered = client.get(
        '/v1/audit/events',
        headers=bearer(officer_token),
        params={'project_id': project_id, 'actor_id': actor_id, 'event_type': 'message.created'},
    )
    assert filtered.status_code == 200, filtered.text
    rows = filtered.json()
    assert rows
    assert all(row['actor_id'] == actor_id for row in rows)
    assert all(row['event_type'] == 'message.created' for row in rows)
