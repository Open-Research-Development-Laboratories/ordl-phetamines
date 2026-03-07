# ORDL API Endpoint Catalog

This catalog lists the control-plane API surface and expected contract behavior.

Each endpoint group defines:

- Purpose
- Required scopes
- Request/response patterns
- Audit requirements

## 1) Auth endpoints

### POST `/v1/auth/token`

- Purpose:
  - Issue scoped bearer tokens for platform access.
- Required scopes:
  - none (identity validated by auth flow)
- Request:
  - identity and tenant context fields
- Response:
  - `access_token`, `token_type`, `user_id`, `tenant_id`
- Audit:
  - emit `auth.token.issued`

### GET `/v1/auth/me`

- Purpose:
  - return principal and effective scopes.
- Required scopes:
  - authenticated
- Audit:
  - optional read audit by policy

## 2) Governance endpoints

### POST `/v1/orgs`
### GET `/v1/orgs`
### POST `/v1/teams`
### GET `/v1/teams`
### POST `/v1/projects`
### GET `/v1/projects`

- Purpose:
  - manage organization/team/project structure.
- Required scopes:
  - `governance.write` for create/update
  - `governance.read` for list/get
- Audit:
  - required on create/update/delete

### POST `/v1/seats`
### GET `/v1/seats`
### POST `/v1/clearance/assign`

- Purpose:
  - assign seats, roles, rank, and clearance.
- Required scopes:
  - `identity.admin`
- Audit:
  - required, with actor and rationale.

## 3) Dispatch and orchestration endpoints

### POST `/v1/dispatch/build`
### POST `/v1/dispatch/validate`
### POST `/v1/dispatch/submit`
### GET `/v1/dispatch/{id}`

- Purpose:
  - create and validate worker dispatch payloads.
- Required scopes:
  - `dispatch.write` for submit
  - `dispatch.read` for query
- Special rules:
  - policy token required for critical outbound actions.
- Audit:
  - dispatch submit and state transitions are auditable.

### POST `/v1/worker-groups`
### GET `/v1/worker-groups`
### POST `/v1/orchestration/profiles`
### GET `/v1/orchestration/profiles`

- Purpose:
  - define worker routing groups and orchestration profiles.
- Required scopes:
  - `orchestration.admin`

### POST `/v1/jobs/templates`
### GET `/v1/jobs/templates`
### POST `/v1/jobs/runs`
### GET `/v1/jobs/runs`
### POST `/v1/jobs/runs/{id}/state`
### POST `/v1/jobs/runs/{id}/cancel`
### GET `/v1/jobs/runs/{id}/artifacts`
### POST `/v1/jobs/runs/{id}/delivery`
### GET `/v1/jobs/runs/{id}/delivery`

- Purpose:
  - schedule, execute, and track orchestration jobs.
- Required scopes:
  - `jobs.write` for create/state/cancel
  - `jobs.read` for query
- Audit:
  - required for all state changes.

## 4) Collaboration endpoints

### POST `/v1/messages`
### GET `/v1/messages`
### POST `/v1/messages/{id}/review`
### POST `/v1/messages/{id}/approve`
### POST `/v1/messages/{id}/rework`
### POST `/v1/messages/{id}/dispatch`

- Purpose:
  - enforce governed collaboration workflow.
- Required scopes:
  - `collab.write`, `approvals.write`, `dispatch.write` as applicable.
- State machine:
  - `draft -> review -> approved -> dispatched -> superseded`
- Audit:
  - required for every transition.

### GET `/v1/approvals`
### POST `/v1/approvals/{id}/decision`

- Purpose:
  - list approval tasks and submit reviewer decisions.
- Required scopes:
  - `approvals.read`, `approvals.write`

## 5) Policy and authorization endpoints

### POST `/v1/policy/decide`
### POST `/v1/policy/token`
### POST `/v1/policy/verify`

- Purpose:
  - evaluate authz and issue/verify policy tokens.
- Required scopes:
  - `policy.read`, `policy.write`, `policy.admin`
- Audit:
  - required for decision and token issuance.

## 6) Provider and extension endpoints

### GET `/v1/providers`
### POST `/v1/providers`
### POST `/v1/providers/{id}/status`

- Purpose:
  - manage provider registry and health.
- Required scopes:
  - `providers.read`, `providers.admin`

### GET `/v1/extensions`
### POST `/v1/extensions/register`
### POST `/v1/extensions/{id}/status`

- Purpose:
  - signed extension lifecycle management.
- Required scopes:
  - `extensions.read`, `extensions.admin`
- Security:
  - signature verification before enable.

## 7) Worker and fleet endpoints

### GET `/v1/workers`
### POST `/v1/workers/register`
### POST `/v1/workers/{id}/heartbeat`
### POST `/v1/workers/{id}/probe`
### GET `/v1/workers/connectivity`

- Purpose:
  - register workers and maintain connectivity state.
- Required scopes:
  - `workers.read`, `workers.write`, `workers.admin`
- Audit:
  - heartbeats can be sampled; probes and admin actions audited.

## 8) Audit and evidence endpoints

### GET `/v1/audit/events`
### GET `/v1/audit/verify`
### GET `/v1/audit/export`

- Purpose:
  - read immutable audit stream, verify chain, export evidence.
- Required scopes:
  - `audit.read`
- Filters:
  - actor, event type, severity, trace id, run id, time range.

## 9) Digestion and coverage endpoints

### POST `/v1/digestion/scan`
### GET `/v1/digestion/coverage`
### GET `/v1/digestion/evidence`

- Purpose:
  - verify full-file and full-line corpus review coverage.
- Required scopes:
  - `digestion.write` for scan
  - `digestion.read` for reports.

## 10) Protocol governance endpoints

### POST `/v1/protocols/standards`
### GET `/v1/protocols/standards`
### POST `/v1/protocols/standards/{id}/versions`
### GET `/v1/protocols/standards/{id}/versions`
### POST `/v1/protocols/bootstrap/adopted`
### GET `/v1/protocols/compatibility`
### POST `/v1/protocols/validate`
### POST `/v1/protocols/conformance/runs`
### GET `/v1/protocols/conformance/runs`

- Purpose:
  - maintain protocol registry and conformance evidence.
- Required scopes:
  - `protocols.read`, `protocols.admin`
- Audit:
  - required for registry and conformance mutations.

## 11) Fleet API adjunct endpoints (external orchestrator service)

Representative endpoint family:

- `GET /v1/fleet/health`
- `POST /v1/fleet/restart`
- `POST /v1/fleet/ensure-connectivity`
- `POST /v1/fleet/discovery/scan`
- `POST /v1/fleet/stage-handoff`

Use cases:

- health and connectivity reconciliation
- multi-host restart and resync
- discovery and candidate evaluation
- worker handoff staging to chat/review pipelines

Security:

- bearer token required.
- high-risk actions require policy token where configured.

## 12) API-wide standards

- Versioning:
  - path-based major version (`/v1`).
- Error model:
  - deterministic error envelope with `code`, `message`, `details`.
- Idempotency:
  - required for create and state-change operations that can be retried.
- Pagination:
  - cursor-based pagination on list endpoints.
- Audit:
  - all write operations must emit audit events.

## 13) Endpoint implementation quality bars

- Every endpoint must include:
  - auth check
  - tenant/project scope validation
  - schema validation
  - policy evaluation for protected actions
  - structured error responses
- Every critical write endpoint must include:
  - idempotency support
  - audit write with actor/resource/reason
  - deterministic status transitions
