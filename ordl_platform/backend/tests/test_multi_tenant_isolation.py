from conftest import bearer, issue_token, setup_project


def test_multi_tenant_isolation(client):
    tenant_a_officer = issue_token(client, 'TenantD-A', 'officer-a@d.test', ['officer'])
    tenant_b_officer = issue_token(client, 'TenantD-B', 'officer-b@d.test', ['officer'])

    _, _, project_id = setup_project(client, tenant_a_officer)

    visible_b = client.get('/v1/projects', headers=bearer(tenant_b_officer))
    assert visible_b.status_code == 200
    assert all(item['id'] != project_id for item in visible_b.json())

    denied = client.get(f'/v1/projects/{project_id}', headers=bearer(tenant_b_officer))
    assert denied.status_code in {403, 404}
