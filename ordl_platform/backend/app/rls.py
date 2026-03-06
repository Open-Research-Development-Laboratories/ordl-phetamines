from __future__ import annotations

import logging

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from app.config import Settings

logger = logging.getLogger(__name__)

POLICY_NAME = 'ordl_tenant_guard_v1'

_TENANT_SETTING = "nullif(current_setting('app.current_tenant_id', true), '')"
_BYPASS_SETTING = "current_setting('app.rls_bypass', true) = '1'"

_PROJECT_SCOPE_EXISTS = (
    "exists ("
    "select 1 from projects p "
    "join teams t on t.id = p.team_id "
    "join orgs o on o.id = t.org_id "
    f"where p.id = project_id and o.tenant_id = {_TENANT_SETTING}"
    ")"
)

_POLICY_EXPRESSIONS: dict[str, str] = {
    'tenants': f"id = {_TENANT_SETTING}",
    'users': f"tenant_id = {_TENANT_SETTING}",
    'orgs': f"tenant_id = {_TENANT_SETTING}",
    'teams': (
        "exists ("
        "select 1 from orgs o "
        f"where o.id = org_id and o.tenant_id = {_TENANT_SETTING}"
        ")"
    ),
    'projects': (
        "exists ("
        "select 1 from teams t "
        "join orgs o on o.id = t.org_id "
        f"where t.id = team_id and o.tenant_id = {_TENANT_SETTING}"
        ")"
    ),
    'seat_assignments': _PROJECT_SCOPE_EXISTS,
    'worker_instances': _PROJECT_SCOPE_EXISTS,
    'worker_update_bundles': _PROJECT_SCOPE_EXISTS,
    'worker_update_campaigns': _PROJECT_SCOPE_EXISTS,
    'worker_discovery_scans': _PROJECT_SCOPE_EXISTS,
    'worker_connectivity_monitors': _PROJECT_SCOPE_EXISTS,
    'worker_groups': _PROJECT_SCOPE_EXISTS,
    'orchestration_profiles': _PROJECT_SCOPE_EXISTS,
    'job_templates': _PROJECT_SCOPE_EXISTS,
    'job_runs': _PROJECT_SCOPE_EXISTS,
    'job_delivery_receipts': _PROJECT_SCOPE_EXISTS,
    'collab_messages': _PROJECT_SCOPE_EXISTS,
    'approvals': _PROJECT_SCOPE_EXISTS,
    'dispatch_requests': _PROJECT_SCOPE_EXISTS,
    'policy_decisions': _PROJECT_SCOPE_EXISTS,
    'code_digest_runs': _PROJECT_SCOPE_EXISTS,
    'change_requests': _PROJECT_SCOPE_EXISTS,
    'protocol_conformance_runs': _PROJECT_SCOPE_EXISTS,
    'worker_actions': (
        "exists ("
        "select 1 from worker_instances w "
        "join projects p on p.id = w.project_id "
        "join teams t on t.id = p.team_id "
        "join orgs o on o.id = t.org_id "
        f"where w.id = worker_id and o.tenant_id = {_TENANT_SETTING}"
        ")"
    ),
    'worker_update_executions': (
        "exists ("
        "select 1 from worker_update_campaigns c "
        "join projects p on p.id = c.project_id "
        "join teams t on t.id = p.team_id "
        "join orgs o on o.id = t.org_id "
        f"where c.id = campaign_id and o.tenant_id = {_TENANT_SETTING}"
        ")"
    ),
    'dispatch_results': (
        "exists ("
        "select 1 from dispatch_requests d "
        "join projects p on p.id = d.project_id "
        "join teams t on t.id = p.team_id "
        "join orgs o on o.id = t.org_id "
        f"where d.id = dispatch_request_id and o.tenant_id = {_TENANT_SETTING}"
        ")"
    ),
    'dispatch_executions': (
        "exists ("
        "select 1 from dispatch_requests d "
        "join projects p on p.id = d.project_id "
        "join teams t on t.id = p.team_id "
        "join orgs o on o.id = t.org_id "
        f"where d.id = dispatch_request_id and o.tenant_id = {_TENANT_SETTING}"
        ")"
    ),
    'dispatch_events': (
        "exists ("
        "select 1 from dispatch_executions e "
        "join dispatch_requests d on d.id = e.dispatch_request_id "
        "join projects p on p.id = d.project_id "
        "join teams t on t.id = p.team_id "
        "join orgs o on o.id = t.org_id "
        f"where e.id = execution_id and o.tenant_id = {_TENANT_SETTING}"
        ")"
    ),
    'extensions': f"tenant_id = {_TENANT_SETTING}",
    'provider_credentials': f"tenant_id = {_TENANT_SETTING}",
    'config_states': f"tenant_id = {_TENANT_SETTING}",
    'protocol_standards': f"tenant_id = {_TENANT_SETTING}",
    'protocol_standard_versions': (
        "exists ("
        "select 1 from protocol_standards s "
        f"where s.id = standard_id and s.tenant_id = {_TENANT_SETTING}"
        ")"
    ),
    'audit_events': f"tenant_id = {_TENANT_SETTING}",
    'code_digest_files': (
        "exists ("
        "select 1 from code_digest_runs r "
        "join projects p on p.id = r.project_id "
        "join teams t on t.id = p.team_id "
        "join orgs o on o.id = t.org_id "
        f"where r.id = run_id and o.tenant_id = {_TENANT_SETTING}"
        ")"
    ),
    'code_digest_chunks': (
        "exists ("
        "select 1 from code_digest_files f "
        "join code_digest_runs r on r.id = f.run_id "
        "join projects p on p.id = r.project_id "
        "join teams t on t.id = p.team_id "
        "join orgs o on o.id = t.org_id "
        f"where f.id = file_id and o.tenant_id = {_TENANT_SETTING}"
        ")"
    ),
    'programs': (
        "exists ("
        "select 1 from orgs o "
        f"where o.id = org_id and o.tenant_id = {_TENANT_SETTING}"
        ")"
    ),
    'program_milestones': (
        "exists ("
        "select 1 from programs g "
        "join orgs o on o.id = g.org_id "
        f"where g.id = program_id and o.tenant_id = {_TENANT_SETTING}"
        ")"
    ),
    'program_risks': (
        "exists ("
        "select 1 from programs g "
        "join orgs o on o.id = g.org_id "
        f"where g.id = program_id and o.tenant_id = {_TENANT_SETTING}"
        ")"
    ),
    'model_eval_runs': _PROJECT_SCOPE_EXISTS,
    'model_fine_tune_runs': _PROJECT_SCOPE_EXISTS,
    'model_promotions': _PROJECT_SCOPE_EXISTS,
}


def policy_expression_catalog() -> dict[str, str]:
    return dict(_POLICY_EXPRESSIONS)


def _guard_expression(expr: str) -> str:
    return f"(({_BYPASS_SETTING}) OR (({_TENANT_SETTING}) IS NOT NULL AND ({expr})))"


def ensure_postgres_rls(engine: Engine, settings: Settings) -> None:
    if not settings.db_rls_enabled:
        return
    if engine.dialect.name != 'postgresql':
        return

    existing_tables = set(inspect(engine).get_table_names())
    if not existing_tables:
        return

    with engine.begin() as conn:
        for table_name, expr in _POLICY_EXPRESSIONS.items():
            if table_name not in existing_tables:
                continue
            guarded = _guard_expression(expr)
            conn.execute(text(f'ALTER TABLE "{table_name}" ENABLE ROW LEVEL SECURITY'))
            conn.execute(text(f'ALTER TABLE "{table_name}" FORCE ROW LEVEL SECURITY'))
            conn.execute(text(f'DROP POLICY IF EXISTS {POLICY_NAME} ON "{table_name}"'))
            conn.execute(
                text(
                    f'CREATE POLICY {POLICY_NAME} ON "{table_name}" '
                    f'USING ({guarded}) WITH CHECK ({guarded})'
                )
            )
    logger.info('postgres rls policies applied to %s tables', len(existing_tables.intersection(_POLICY_EXPRESSIONS)))
