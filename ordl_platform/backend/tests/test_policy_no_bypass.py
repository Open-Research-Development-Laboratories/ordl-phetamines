from conftest import bearer, issue_token, setup_project


def test_policy_token_no_bypass(client):
    officer = issue_token(client, 'TenantC', 'officer@c.test', ['officer'], clearance='restricted')
    _, _, project_id = setup_project(client, officer)

    decide = client.post(
        '/v1/policy/decide',
        headers=bearer(officer),
        json={
            'project_id': project_id,
            'action': 'dispatch',
            'resource_type': 'dispatch_request',
            'resource_id': 'r1',
            'payload': {'x': 1},
            'required_clearance': 'internal',
            'required_compartments': ['alpha'],
            'high_risk': False,
            'destination_scope': 'group',
        },
    )
    assert decide.status_code == 200, decide.text
    payload = decide.json()
    assert payload['decision'] == 'allow'
    assert payload['policy_token']

    invalid = client.post(
        '/v1/policy/validate',
        headers=bearer(officer),
        json={
            'token': payload['policy_token'],
            'request_hash': 'bad-hash',
            'destination_scope': 'group',
        },
    )
    assert invalid.status_code == 403

    valid = client.post(
        '/v1/policy/validate',
        headers=bearer(officer),
        json={
            'token': payload['policy_token'],
            'request_hash': payload['request_hash'],
            'destination_scope': 'group',
        },
    )
    assert valid.status_code == 200
    assert valid.json()['valid'] is True
