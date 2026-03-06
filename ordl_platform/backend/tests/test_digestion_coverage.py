from pathlib import Path

from conftest import bearer, issue_token, setup_project


def test_digestion_full_coverage(client, tmp_path: Path):
    officer = issue_token(client, 'TenantF', 'officer@f.test', ['officer'], clearance='restricted')
    _, _, project_id = setup_project(client, officer)

    repo_root = tmp_path / 'repo'
    repo_root.mkdir(parents=True, exist_ok=True)
    (repo_root / 'a.py').write_text('line1\nline2\nline3\n', encoding='utf-8')
    (repo_root / 'b.md').write_text('# title\ntext\n', encoding='utf-8')

    run = client.post(
        '/v1/digestion/run',
        headers=bearer(officer),
        json={'project_id': project_id, 'repo_root': str(repo_root), 'chunk_size': 2},
    )
    assert run.status_code == 200, run.text
    assert run.json()['total_files'] >= 2

    status = client.get(f'/v1/digestion/status/{project_id}', headers=bearer(officer))
    assert status.status_code == 200
    status_payload = status.json()
    assert status_payload['full_coverage'] is True
    assert status_payload['coverage_percent'] == 100.0

    gate = client.get(f'/v1/digestion/gate/{project_id}', headers=bearer(officer))
    assert gate.status_code == 200
    assert gate.json()['gate'] == 'pass'
