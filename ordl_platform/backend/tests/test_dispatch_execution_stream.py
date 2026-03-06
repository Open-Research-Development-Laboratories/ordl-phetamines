from __future__ import annotations

from tests.conftest import bearer, issue_token, setup_project


def test_dispatch_execution_events_and_stream(client):
    officer = issue_token(client, 'Tenant-Dispatch', 'officer@dispatch.test', ['officer'], clearance='restricted')
    _, _, project_id = setup_project(client, officer)

    created = client.post(
        '/v1/dispatch',
        headers=bearer(officer),
        json={
            'project_id': project_id,
            'target_scope': 'group',
            'target_value': 'workers',
            'provider': 'openai_codex',
            'model': 'gpt-5.4',
            'payload': {'prompt': 'Write a short health report.'},
        },
    )
    assert created.status_code == 200, created.text
    dispatch_id = created.json()['id']
    assert created.json()['state'] == 'dispatched'

    executions = client.get(
        f'/v1/dispatch/{dispatch_id}/executions',
        headers=bearer(officer),
    )
    assert executions.status_code == 200, executions.text
    rows = executions.json()
    assert len(rows) >= 1
    execution_id = rows[0]['id']
    assert rows[0]['status'] in {'completed', 'failed'}

    events = client.get(
        f'/v1/dispatch/executions/{execution_id}/events',
        headers=bearer(officer),
    )
    assert events.status_code == 200, events.text
    event_rows = events.json()
    assert len(event_rows) >= 1
    event_types = {row['event_type'] for row in event_rows}
    assert 'execution.started' in event_types

    stream = client.get(
        f'/v1/dispatch/executions/{execution_id}/stream',
        headers=bearer(officer),
    )
    assert stream.status_code == 200, stream.text
    assert 'event:' in stream.text
    assert 'data:' in stream.text

    rerun = client.post(
        f'/v1/dispatch/{dispatch_id}/execute',
        headers=bearer(officer),
        json={'force': True},
    )
    assert rerun.status_code == 200, rerun.text
    assert rerun.json()['status'] in {'completed', 'failed'}


def test_dispatch_execution_tenant_isolation(client):
    officer_a = issue_token(client, 'Tenant-Dispatch-A', 'officer-a@dispatch.test', ['officer'], clearance='restricted')
    officer_b = issue_token(client, 'Tenant-Dispatch-B', 'officer-b@dispatch.test', ['officer'], clearance='restricted')
    _, _, project_a = setup_project(client, officer_a)
    _, _, _ = setup_project(client, officer_b)

    created = client.post(
        '/v1/dispatch',
        headers=bearer(officer_a),
        json={
            'project_id': project_a,
            'target_scope': 'group',
            'target_value': 'workers',
            'provider': 'openai_codex',
            'model': 'gpt-5.4',
            'payload': {'prompt': 'A-only report'},
        },
    )
    assert created.status_code == 200, created.text
    dispatch_id = created.json()['id']

    denied_execs = client.get(
        f'/v1/dispatch/{dispatch_id}/executions',
        headers=bearer(officer_b),
    )
    assert denied_execs.status_code in {403, 404}

