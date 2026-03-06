from conftest import bearer, issue_token, setup_project


def test_authorization_matrix(client):
    officer = issue_token(client, 'TenantA', 'officer@a.test', ['officer'], clearance='restricted')
    engineer = issue_token(client, 'TenantA', 'eng@a.test', ['engineer'], clearance='internal')

    _, _, project_id = setup_project(client, officer)

    # Engineer should not be able to assign seats.
    seat_attempt = client.post(
        '/v1/seats',
        headers=bearer(engineer),
        json={
            'project_id': project_id,
            'user_id': 'fake-user-id',
            'role': 'engineer',
            'clearance_tier': 'internal',
            'compartments': ['alpha'],
        },
    )
    assert seat_attempt.status_code == 403

    # Officer can evaluate high-risk dispatch as allow.
    decision = client.post(
        '/v1/clearance/evaluate',
        headers=bearer(officer),
        json={
            'action': 'dispatch',
            'required_clearance': 'internal',
            'required_compartments': ['alpha'],
            'high_risk': True,
        },
    )
    assert decision.status_code == 200
    assert decision.json()['decision'] == 'allow'

    # Engineer dispatch permission should be denied by role.
    engineer_decision = client.post(
        '/v1/clearance/evaluate',
        headers=bearer(engineer),
        json={
            'action': 'dispatch',
            'required_clearance': 'internal',
            'required_compartments': ['alpha'],
            'high_risk': False,
        },
    )
    assert engineer_decision.status_code == 200
    assert engineer_decision.json()['decision'] == 'deny'
