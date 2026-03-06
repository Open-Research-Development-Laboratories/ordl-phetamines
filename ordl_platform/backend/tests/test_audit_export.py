from __future__ import annotations

from tests.conftest import bearer, issue_token, setup_project


def test_audit_export_filters_and_csv(client):
    officer = issue_token(client, 'Tenant-Audit-Export', 'officer@audit-export.test', ['officer'], clearance='restricted')
    architect = issue_token(client, 'Tenant-Audit-Export', 'architect@audit-export.test', ['architect'], clearance='restricted')
    _, _, project_id = setup_project(client, officer)

    me = client.get('/v1/auth/me', headers=bearer(architect))
    assert me.status_code == 200, me.text
    user_id = me.json()['user_id']

    seat = client.post(
        '/v1/seats',
        headers=bearer(officer),
        json={
            'project_id': project_id,
            'user_id': user_id,
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

    group = client.post(
        '/v1/worker-groups',
        headers=bearer(officer),
        json={
            'project_id': project_id,
            'name': 'audit-group',
            'routing_strategy': 'round_robin',
            'selection_mode': 'explicit',
            'worker_ids': ['worker-build-laptop'],
            'capability_tags': ['audit'],
        },
    )
    assert group.status_code == 200, group.text
    group_id = group.json()['id']

    run = client.post(
        '/v1/jobs/runs',
        headers=bearer(architect),
        json={
            'project_id': project_id,
            'owner_principal_id': 'user:winsock',
            'report_to': ['team:audit'],
            'escalation_to': ['board:ordl'],
            'routing_mode': 'group',
            'target_group_id': group_id,
            'objective': 'Generate audit export test events',
            'input_payload': {'scope': 'audit'},
        },
    )
    assert run.status_code == 200, run.text
    run_id = run.json()['id']

    events = client.get(
        '/v1/audit/events',
        headers=bearer(officer),
        params={
            'project_id': project_id,
            'run_id': run_id,
            'event_type': 'job_run.created',
            'severity': 'info',
        },
    )
    assert events.status_code == 200, events.text
    rows = events.json()
    assert rows
    assert all(row['run_id'] == run_id for row in rows)
    assert all(row['event_type'] == 'job_run.created' for row in rows)

    export_json = client.get(
        '/v1/audit/export',
        headers=bearer(officer),
        params={'project_id': project_id, 'format': 'json', 'run_id': run_id},
    )
    assert export_json.status_code == 200, export_json.text
    payload = export_json.json()
    assert payload['format'] == 'json'
    assert payload['count'] >= 1
    assert all(row['run_id'] == run_id for row in payload['events'])

    export_csv = client.get(
        '/v1/audit/export',
        headers=bearer(officer),
        params={'project_id': project_id, 'format': 'csv', 'run_id': run_id},
    )
    assert export_csv.status_code == 200, export_csv.text
    assert 'text/csv' in export_csv.headers.get('content-type', '')
    body = export_csv.text
    assert 'event_type' in body
    assert run_id in body
