from __future__ import annotations

import hashlib
import hmac
import json

from app.config import get_settings
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


def _register_worker(client, operator_token: str, project_id: str, name: str, role: str, host: str, device_id: str) -> str:
    res = client.post(
        '/v1/workers/register',
        headers=bearer(operator_token),
        json={
            'project_id': project_id,
            'name': name,
            'role': role,
            'host': host,
            'device_id': device_id,
            'capabilities': ['python', 'tests'],
        },
    )
    assert res.status_code == 200, res.text
    return res.json()['id']


def _bundle_signature_payload(*, project_id: str, name: str, version: str, digest: str, signer: str, artifact_uri: str) -> str:
    payload = {
        'project_id': project_id,
        'name': name,
        'version': version,
        'digest': digest,
        'signer': signer,
        'artifact_uri': artifact_uri,
    }
    return json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def _bundle_signature(*, payload: str) -> str:
    secret = get_settings().extension_signing_secret
    return hmac.new(secret.encode('utf-8'), payload.encode('utf-8'), hashlib.sha256).hexdigest()


def _issue_start_policy_token(client, operator_token: str, project_id: str, campaign_id: str, desired_version: str, worker_ids: list[str]) -> str:
    request_payload = {
        'campaign_id': campaign_id,
        'project_id': project_id,
        'desired_version': desired_version,
        'requested_worker_ids': sorted(worker_ids),
    }
    decide = client.post(
        '/v1/policy/decide',
        headers=bearer(operator_token),
        json={
            'project_id': project_id,
            'action': 'worker_action',
            'resource_type': 'worker_update_campaign',
            'resource_id': campaign_id,
            'payload': request_payload,
            'required_clearance': 'internal',
            'required_compartments': [],
            'high_risk': False,
            'destination_scope': 'project',
        },
    )
    assert decide.status_code == 200, decide.text
    token = decide.json().get('policy_token')
    assert token
    return token


def test_worker_update_campaign_and_discovery_workflow(client):
    officer = issue_token(client, 'Tenant-Update', 'officer@update.test', ['officer'], clearance='restricted')
    operator = issue_token(client, 'Tenant-Update', 'operator@update.test', ['operator'], clearance='restricted')
    _, _, project_id = setup_project(client, officer)
    _add_operator_seat(client, officer, operator, project_id)

    worker_build = _register_worker(
        client,
        operator,
        project_id,
        'worker-build-laptop',
        'builder',
        '10.0.0.28',
        'device-build-laptop',
    )
    _register_worker(
        client,
        operator,
        project_id,
        'worker-batch-server',
        'batch',
        '10.0.0.27',
        'device-batch-server',
    )

    bundle_name = 'worker-runtime'
    bundle_version = '2026.03.1'
    bundle_digest = 'sha256:abc123'
    bundle_signer = 'ordl-release'
    bundle_uri = 's3://ordl-artifacts/worker-runtime-2026.03.1.tgz'
    signature_payload = _bundle_signature_payload(
        project_id=project_id,
        name=bundle_name,
        version=bundle_version,
        digest=bundle_digest,
        signer=bundle_signer,
        artifact_uri=bundle_uri,
    )
    bundle_signature = _bundle_signature(payload=signature_payload)
    bundle = client.post(
        '/v1/workers/update-bundles',
        headers=bearer(operator),
        json={
            'project_id': project_id,
            'name': bundle_name,
            'version': bundle_version,
            'digest': bundle_digest,
            'signature': bundle_signature,
            'signer': bundle_signer,
            'artifact_uri': bundle_uri,
            'metadata': {'channel': 'stable'},
        },
    )
    assert bundle.status_code == 200, bundle.text
    bundle_id = bundle.json()['id']

    campaign = client.post(
        '/v1/workers/update-campaigns',
        headers=bearer(operator),
        json={
            'project_id': project_id,
            'name': 'rollout-2026-03',
            'bundle_id': bundle_id,
            'target_selector': {'role': 'builder'},
            'desired_version': '2026.03.1',
            'rollout_strategy': 'rolling',
            'preflight_required': True,
            'backup_required': True,
            'canary_batch_size': 1,
            'max_allowed_failures': 0,
            'auto_rollback_on_halt': True,
        },
    )
    assert campaign.status_code == 200, campaign.text
    campaign_id = campaign.json()['id']
    assert campaign.json()['state'] == 'draft'

    started = client.post(
        f'/v1/workers/update-campaigns/{campaign_id}/start',
        headers=bearer(operator),
        json={
            'worker_ids': [],
            'policy_token': _issue_start_policy_token(
                client,
                operator,
                project_id,
                campaign_id,
                '2026.03.1',
                [],
            ),
        },
    )
    assert started.status_code == 200, started.text
    assert started.json()['campaign']['state'] == 'completed'
    assert started.json()['selected_workers'] == 1

    executions = client.get(
        f'/v1/workers/update-campaigns/{campaign_id}/executions',
        headers=bearer(operator),
    )
    assert executions.status_code == 200, executions.text
    rows = executions.json()
    assert len(rows) == 1
    assert rows[0]['worker_id'] == worker_build
    assert rows[0]['applied_version'] == '2026.03.1'
    assert rows[0]['rollback_state'] == 'not_requested'

    rolled_back = client.post(
        f'/v1/workers/update-campaigns/{campaign_id}/rollback',
        headers=bearer(operator),
        json={'reason': 'post-deploy smoke mismatch'},
    )
    assert rolled_back.status_code == 200, rolled_back.text
    assert rolled_back.json()['state'] == 'rolled_back'

    executions_after = client.get(
        f'/v1/workers/update-campaigns/{campaign_id}/executions',
        headers=bearer(operator),
    )
    assert executions_after.status_code == 200, executions_after.text
    assert executions_after.json()[0]['rollback_state'] == 'rolled_back'

    discovery = client.post(
        '/v1/workers/discovery/scans',
        headers=bearer(operator),
        json={
            'project_id': project_id,
            'network_scope': 'lan-segment-a',
            'candidate_hosts': ['10.0.0.50', '10.0.0.28'],
            'auto_enroll': False,
            'notes': 'nightly discovery run',
        },
    )
    assert discovery.status_code == 200, discovery.text
    scan_id = discovery.json()['id']
    findings = discovery.json()['findings']
    assert len(findings) >= 2

    listed_scans = client.get(
        '/v1/workers/discovery/scans',
        headers=bearer(operator),
        params={'project_id': project_id},
    )
    assert listed_scans.status_code == 200, listed_scans.text
    assert any(item['id'] == scan_id for item in listed_scans.json())

    fetched_scan = client.get(
        f'/v1/workers/discovery/scans/{scan_id}',
        headers=bearer(operator),
    )
    assert fetched_scan.status_code == 200, fetched_scan.text
    assert fetched_scan.json()['id'] == scan_id


def test_update_campaign_tenant_isolation(client):
    officer_a = issue_token(client, 'Tenant-Update-A', 'officer-a@update.test', ['officer'], clearance='restricted')
    operator_a = issue_token(client, 'Tenant-Update-A', 'operator-a@update.test', ['operator'], clearance='restricted')
    officer_b = issue_token(client, 'Tenant-Update-B', 'officer-b@update.test', ['officer'], clearance='restricted')
    operator_b = issue_token(client, 'Tenant-Update-B', 'operator-b@update.test', ['operator'], clearance='restricted')

    _, _, project_a = setup_project(client, officer_a)
    _add_operator_seat(client, officer_a, operator_a, project_a)
    worker_a = _register_worker(
        client,
        operator_a,
        project_a,
        'worker-a',
        'builder',
        '10.0.0.31',
        'device-worker-a',
    )

    bundle_name = 'worker-runtime'
    bundle_version = '2026.03.2'
    bundle_digest = 'sha256:tenanta'
    bundle_signer = 'ordl-release'
    bundle_uri = 's3://ordl-artifacts/worker-runtime-2026.03.2.tgz'
    signature_payload = _bundle_signature_payload(
        project_id=project_a,
        name=bundle_name,
        version=bundle_version,
        digest=bundle_digest,
        signer=bundle_signer,
        artifact_uri=bundle_uri,
    )
    bundle_signature = _bundle_signature(payload=signature_payload)
    bundle = client.post(
        '/v1/workers/update-bundles',
        headers=bearer(operator_a),
        json={
            'project_id': project_a,
            'name': bundle_name,
            'version': bundle_version,
            'digest': bundle_digest,
            'signature': bundle_signature,
            'signer': bundle_signer,
            'artifact_uri': bundle_uri,
            'metadata': {},
        },
    )
    assert bundle.status_code == 200, bundle.text
    bundle_id = bundle.json()['id']

    campaign = client.post(
        '/v1/workers/update-campaigns',
        headers=bearer(operator_a),
        json={
            'project_id': project_a,
            'name': 'tenant-a-rollout',
            'bundle_id': bundle_id,
            'target_selector': {'role': 'builder'},
            'desired_version': '2026.03.2',
        },
    )
    assert campaign.status_code == 200, campaign.text
    campaign_id = campaign.json()['id']

    _, _, project_b = setup_project(client, officer_b)
    _add_operator_seat(client, officer_b, operator_b, project_b)

    denied = client.get(
        f'/v1/workers/update-campaigns/{campaign_id}/executions',
        headers=bearer(operator_b),
    )
    assert denied.status_code in {403, 404}

    denied_start = client.post(
        f'/v1/workers/update-campaigns/{campaign_id}/start',
        headers=bearer(operator_b),
        json={
            'worker_ids': [worker_a],
            'policy_token': 'invalid',
        },
    )
    assert denied_start.status_code in {403, 404}


def test_canary_halt_and_auto_rollback(client):
    officer = issue_token(client, 'Tenant-Canary', 'officer@canary.test', ['officer'], clearance='restricted')
    operator = issue_token(client, 'Tenant-Canary', 'operator@canary.test', ['operator'], clearance='restricted')
    _, _, project_id = setup_project(client, officer)
    _add_operator_seat(client, officer, operator, project_id)

    worker_down = _register_worker(
        client,
        operator,
        project_id,
        'worker-down',
        'builder',
        '10.0.0.61',
        'device-worker-down',
    )
    _register_worker(
        client,
        operator,
        project_id,
        'worker-up',
        'builder',
        '10.0.0.62',
        'device-worker-up',
    )
    probe_down = client.post(
        f'/v1/workers/{worker_down}/probe',
        headers=bearer(operator),
        json={'reachable': False, 'gateway_url': 'ws://10.0.0.48:18789', 'gateway_rtt_ms': -1, 'reason': 'canary test'},
    )
    assert probe_down.status_code == 200, probe_down.text

    bundle_name = 'worker-runtime'
    bundle_version = '2026.04.0'
    bundle_digest = 'sha256:canary'
    bundle_signer = 'ordl-release'
    bundle_uri = 's3://ordl-artifacts/worker-runtime-2026.04.0.tgz'
    signature_payload = _bundle_signature_payload(
        project_id=project_id,
        name=bundle_name,
        version=bundle_version,
        digest=bundle_digest,
        signer=bundle_signer,
        artifact_uri=bundle_uri,
    )
    bundle_signature = _bundle_signature(payload=signature_payload)
    bundle = client.post(
        '/v1/workers/update-bundles',
        headers=bearer(operator),
        json={
            'project_id': project_id,
            'name': bundle_name,
            'version': bundle_version,
            'digest': bundle_digest,
            'signature': bundle_signature,
            'signer': bundle_signer,
            'artifact_uri': bundle_uri,
            'metadata': {},
        },
    )
    assert bundle.status_code == 200, bundle.text
    bundle_id = bundle.json()['id']

    campaign = client.post(
        '/v1/workers/update-campaigns',
        headers=bearer(operator),
        json={
            'project_id': project_id,
            'name': 'canary-fail-rollout',
            'bundle_id': bundle_id,
            'target_selector': {'role': 'builder'},
            'desired_version': bundle_version,
            'rollout_strategy': 'canary',
            'preflight_required': True,
            'backup_required': True,
            'canary_batch_size': 1,
            'max_allowed_failures': 0,
            'auto_rollback_on_halt': True,
        },
    )
    assert campaign.status_code == 200, campaign.text
    campaign_id = campaign.json()['id']

    start = client.post(
        f'/v1/workers/update-campaigns/{campaign_id}/start',
        headers=bearer(operator),
        json={
            'worker_ids': [],
            'policy_token': _issue_start_policy_token(
                client,
                operator,
                project_id,
                campaign_id,
                bundle_version,
                [],
            ),
        },
    )
    assert start.status_code == 200, start.text
    assert start.json()['halted'] is True
    assert start.json()['campaign']['state'] == 'halted_rolled_back'

    executions = client.get(
        f'/v1/workers/update-campaigns/{campaign_id}/executions',
        headers=bearer(operator),
    )
    assert executions.status_code == 200, executions.text
    assert any(item['state'] in {'failed', 'rolled_back'} for item in executions.json())
