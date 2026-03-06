from __future__ import annotations

from tests.conftest import bearer, issue_token, setup_project


def _add_project_member(client, officer_token: str, member_token: str, role: str) -> None:
    _, _, project_id = setup_project(client, officer_token)
    me = client.get('/v1/auth/me', headers=bearer(member_token))
    assert me.status_code == 200, me.text
    user_id = me.json()['user_id']
    seat = client.post(
        '/v1/seats',
        headers=bearer(officer_token),
        json={
            'project_id': project_id,
            'user_id': user_id,
            'role': role,
            'rank': 'member',
            'position': role,
            'group_name': 'delivery',
            'clearance_tier': 'restricted',
            'compartments': ['alpha', 'ops'],
            'status': 'active',
        },
    )
    assert seat.status_code == 200, seat.text
    return project_id


def test_orchestration_job_lifecycle(client):
    officer = issue_token(client, 'Tenant-Orch', 'officer@orch.test', ['officer'], clearance='restricted')
    architect = issue_token(client, 'Tenant-Orch', 'architect@orch.test', ['architect'], clearance='restricted')
    project_id = _add_project_member(client, officer, architect, 'architect')

    group = client.post(
        '/v1/worker-groups',
        headers=bearer(officer),
        json={
            'project_id': project_id,
            'name': 'implementation-core',
            'routing_strategy': 'round_robin',
            'selection_mode': 'explicit',
            'worker_ids': ['worker-build-laptop'],
            'capability_tags': ['python', 'api'],
        },
    )
    assert group.status_code == 200, group.text
    group_id = group.json()['id']

    profile = client.post(
        '/v1/orchestration/profiles',
        headers=bearer(officer),
        json={
            'project_id': project_id,
            'name': 'prod-balanced-v1',
            'routing_mode': 'group',
            'target_group_id': group_id,
            'quality_bar': 'strict',
            'max_parallel': 3,
            'retry_max_attempts': 2,
            'retry_backoff_seconds': 30,
            'postback_required': True,
            'visible_body_required': True,
            'max_chunk_chars': 1800,
            'owner_principal_id': 'user:winsock',
            'report_to': ['team:core-council'],
            'escalation_to': ['board:ordl-board'],
            'visibility_mode': 'team',
        },
    )
    assert profile.status_code == 200, profile.text
    profile_id = profile.json()['id']

    template = client.post(
        '/v1/jobs/templates',
        headers=bearer(officer),
        json={
            'project_id': project_id,
            'name': 'api-hardening',
            'version': 'v1',
            'objective': 'Harden API retry controls',
            'required_inputs': ['/docs/orchestration-foundation-spec.md'],
            'constraints': {'no_upstream_code_copy': True},
            'output_schema': {'sections': ['Summary', 'Risks', 'Action List', 'Open Questions']},
            'default_profile_id': profile_id,
            'report_to': ['team:core-council'],
            'escalation_to': ['board:ordl-board'],
            'visibility_mode': 'team',
        },
    )
    assert template.status_code == 200, template.text
    template_id = template.json()['id']

    run = client.post(
        '/v1/jobs/runs',
        headers=bearer(architect),
        json={
            'project_id': project_id,
            'template_id': template_id,
            'owner_principal_id': 'user:winsock',
            'report_to': [],
            'escalation_to': [],
            'routing_mode': 'group',
            'target_group_id': group_id,
            'input_payload': {'task': 'implement health gateway checks'},
        },
    )
    assert run.status_code == 200, run.text
    run_id = run.json()['id']
    assert run.json()['state'] == 'created'

    for state in ['queued', 'dispatching', 'running', 'postback_pending']:
        moved = client.post(
            f'/v1/jobs/runs/{run_id}/state',
            headers=bearer(architect),
            json={'target_state': state, 'state_reason': f'to {state}'},
        )
        assert moved.status_code == 200, moved.text
        assert moved.json()['state'] == state

    delivered = client.post(
        f'/v1/jobs/runs/{run_id}/delivery',
        headers=bearer(architect),
        json={
            'recipient': 'team:core-council',
            'channel': 'ordlctl_chat',
            'status': 'delivered',
            'detail': {'message_id': 'abc123'},
        },
    )
    assert delivered.status_code == 200, delivered.text

    delivery_list = client.get(f'/v1/jobs/runs/{run_id}/delivery', headers=bearer(architect))
    assert delivery_list.status_code == 200, delivery_list.text
    assert len(delivery_list.json()) == 1

    artifacts = client.get(f'/v1/jobs/runs/{run_id}/artifacts', headers=bearer(architect))
    assert artifacts.status_code == 200, artifacts.text
    assert artifacts.json()['artifact_count'] == 1

    closed = client.post(
        f'/v1/jobs/runs/{run_id}/state',
        headers=bearer(architect),
        json={'target_state': 'closed', 'state_reason': 'done'},
    )
    assert closed.status_code == 200, closed.text
    assert closed.json()['state'] == 'closed'

    invalid = client.post(
        f'/v1/jobs/runs/{run_id}/state',
        headers=bearer(architect),
        json={'target_state': 'running', 'state_reason': 'invalid'},
    )
    assert invalid.status_code == 400, invalid.text

    cancel_after_close = client.post(f'/v1/jobs/runs/{run_id}/cancel', headers=bearer(architect))
    assert cancel_after_close.status_code == 400, cancel_after_close.text


def test_job_run_requires_report_recipients(client):
    officer = issue_token(client, 'Tenant-Orch-2', 'officer2@orch.test', ['officer'], clearance='restricted')
    architect = issue_token(client, 'Tenant-Orch-2', 'architect2@orch.test', ['architect'], clearance='restricted')
    project_id = _add_project_member(client, officer, architect, 'architect')

    run = client.post(
        '/v1/jobs/runs',
        headers=bearer(architect),
        json={
            'project_id': project_id,
            'owner_principal_id': 'user:winsock',
            'report_to': [],
            'escalation_to': [],
            'routing_mode': 'group',
            'input_payload': {'task': 'should fail without recipients'},
        },
    )
    assert run.status_code == 400, run.text
    assert 'report_to' in run.text
