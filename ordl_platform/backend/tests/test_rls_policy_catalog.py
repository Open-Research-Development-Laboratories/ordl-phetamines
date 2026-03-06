from app.rls import policy_expression_catalog


def test_rls_catalog_includes_core_tenant_tables():
    catalog = policy_expression_catalog()
    required = {
        'tenants',
        'users',
        'orgs',
        'projects',
        'worker_instances',
        'dispatch_requests',
        'dispatch_executions',
        'dispatch_events',
        'provider_credentials',
        'audit_events',
    }
    missing = sorted(required.difference(catalog))
    assert not missing, f'missing required rls policies: {missing}'


def test_rls_catalog_project_scope_uses_join_expression():
    catalog = policy_expression_catalog()
    project_expr = catalog['worker_instances']
    assert 'projects p' in project_expr
    assert 'orgs o' in project_expr
    assert 'current_setting' in project_expr
