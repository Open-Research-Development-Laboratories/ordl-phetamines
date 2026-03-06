from conftest import bearer, issue_token, setup_project


def test_message_state_machine_and_dispatch_gate(client):
    officer = issue_token(client, 'TenantB', 'officer@b.test', ['officer'], clearance='restricted')
    engineer = issue_token(client, 'TenantB', 'eng@b.test', ['engineer'], clearance='internal')

    _, _, project_id = setup_project(client, officer)

    me = client.get('/v1/auth/me', headers=bearer(engineer)).json()
    add_engineer = client.post(
        '/v1/seats',
        headers=bearer(officer),
        json={
            'project_id': project_id,
            'user_id': me['user_id'],
            'role': 'engineer',
            'rank': 'member',
            'position': 'developer',
            'group_name': 'builders',
            'clearance_tier': 'internal',
            'compartments': ['alpha'],
            'status': 'active',
        },
    )
    assert add_engineer.status_code == 200, add_engineer.text

    msg = client.post(
        '/v1/messages',
        headers=bearer(engineer),
        json={'project_id': project_id, 'title': 'Draft', 'body': 'Body', 'reviewer_user_id': client.get('/v1/auth/me', headers=bearer(officer)).json()['user_id']},
    )
    assert msg.status_code == 200, msg.text
    msg_id = msg.json()['id']

    invalid = client.post(
        f'/v1/messages/{msg_id}/transition',
        headers=bearer(engineer),
        json={'target_state': 'approved', 'review_notes': 'skip'},
    )
    assert invalid.status_code == 400

    to_review = client.post(
        f'/v1/messages/{msg_id}/transition',
        headers=bearer(engineer),
        json={'target_state': 'review', 'review_notes': ''},
    )
    assert to_review.status_code == 200
    assert to_review.json()['state'] == 'review'

    approval = client.post(
        '/v1/approvals',
        headers=bearer(officer),
        json={'project_id': project_id, 'message_id': msg_id, 'decision': 'approved', 'rationale': 'ok'},
    )
    assert approval.status_code == 200

    dispatch = client.post(
        '/v1/dispatch',
        headers=bearer(officer),
        json={
            'project_id': project_id,
            'message_id': msg_id,
            'target_scope': 'group',
            'target_value': 'engineers',
            'provider': 'openai_codex',
            'model': 'gpt-5.3-codex',
            'payload': {'task': 'implement changes'},
        },
    )
    assert dispatch.status_code == 200, dispatch.text
    assert dispatch.json()['state'] == 'dispatched'
