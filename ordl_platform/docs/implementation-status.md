# Implementation Status

## Completed in this pass

- New clean-room module scaffold under `ordl_platform/`.
- FastAPI backend with required v1 API surface and contracts:
  - `/auth`, `/orgs`, `/teams`, `/projects`, `/seats`, `/clearance`, `/messages`, `/approvals`, `/dispatch`, `/policy`, `/providers`, `/extensions`, `/workers`, `/audit`, `/digestion`.
- RBAC + ABAC authorization decisions with deterministic allow/deny/hold semantics.
- Signed policy-token issuance and validation for dispatch no-bypass control.
- Signed extension registration and status lifecycle update endpoint.
- Worker inventory/registration and queued worker action records.
- Tamper-evident audit event chaining.
- Code digestion engine with file/line/chunk hashing and coverage gate endpoints.
- React TypeScript control UI shell.
- Podman Compose runtime for Postgres, Valkey, MinIO, backend, worker, and frontend.
- Test suite: 6 tests passing.
- Added orchestration foundation spec for provider-agnostic routing, worker groups, job templates/runs, and designated reporting chains:
  - `ordl_platform/docs/orchestration-foundation-spec.md`
- Added AI Control IDE platform spec:
  - `ordl_platform/docs/ai-control-ide-spec.md`
- Added protocol/standards program spec:
  - `ordl_platform/docs/protocol-standards-program.md`
- Added full audit trail spec:
  - `ordl_platform/docs/audit-trail-spec.md`
- Expanded backend audit trail event model and API:
  - `GET /v1/audit/events`
  - `GET /v1/audit/verify`
- Implemented orchestration control-plane APIs:
  - `POST/GET /v1/worker-groups`
  - `POST/GET /v1/orchestration/profiles`
  - `POST/GET /v1/jobs/templates`
  - `POST/GET /v1/jobs/runs`
  - `POST /v1/jobs/runs/{id}/state`
  - `POST /v1/jobs/runs/{id}/cancel`
  - `GET /v1/jobs/runs/{id}/artifacts`
  - `POST/GET /v1/jobs/runs/{id}/delivery`
- Implemented audit export API and expanded query filters:
  - `GET /v1/audit/export`
  - added filtering dimensions: `actor_id`, `event_type`, `trace_id`, `run_id`, `severity`, `start_time`, `end_time`
- Implemented worker connectivity enforcement contracts:
  - `POST /v1/workers/{id}/heartbeat`
  - `POST /v1/workers/{id}/probe`
  - `GET /v1/workers/connectivity`
  - deterministic reconnect target ordering (last-known gateway first)
  - keepalive/probe timestamps and reconnect-required evaluation

## Remaining major implementation items

- OIDC/SAML identity federation with break-glass flow.
- Full provider execution adapters (real outbound provider calls with secret vault integration).
- Protocol registry and conformance runtime (`protocols/standards`, `protocols/validate`, `protocols/conformance`).
- High-volume audit retention and archival tiering strategy.
- Approval queue UX depth (parallel reviewers, SLA timers, escalations).
- Signed extension package verification with asymmetric keys (Sigstore/cert chain).
- Advanced multi-tenant guardrails and row-level security at database level.
- Kubernetes manifests/Helm baseline.
- Formal control evidence pack generation automation.
- Active gateway daemon for continuous worker probe scheduling and autonomous reconnect execution.
