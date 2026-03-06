# API Contracts (v1)

Base: `/v1`

- `POST /auth/token` issue bearer token for tenant user context.
- `GET /auth/me` read principal and tenant context.
- `GET /info` tenant-scoped service info.
- `POST /orgs`, `GET /orgs` org governance scope.
- `POST /teams`, `GET /teams` team management.
- `POST /projects`, `GET /projects`, `GET /projects/{id}` project management.
- `POST /seats`, `GET /seats` named seat lifecycle.
- `POST /clearance/evaluate` deterministic RBAC+ABAC decision.
- `POST /messages`, `GET /messages`, `GET /messages/{id}`, `PATCH /messages/{id}`, `DELETE /messages/{id}`, `POST /messages/{id}/transition`.
- `POST /approvals` reviewer approvals to gate dispatch.
- `POST /dispatch`, `GET /dispatch`, `GET /dispatch/results`.
- `POST /policy/decide`, `POST /policy/validate` signed policy token workflow.
- `GET /providers`, `POST /providers/credentials` provider auth metadata.
- `POST /extensions`, `GET /extensions`, `POST /extensions/{id}/status` signed extension governance.
- `POST /workers/register`, `GET /workers`, `POST /workers/{id}/action`.
- `POST /workers/{id}/heartbeat`, `POST /workers/{id}/probe`, `GET /workers/connectivity`.
- `POST /worker-groups`, `GET /worker-groups`.
- `POST /orchestration/profiles`, `GET /orchestration/profiles`.
- `POST /jobs/templates`, `GET /jobs/templates`.
- `POST /jobs/runs`, `GET /jobs/runs`, `POST /jobs/runs/{id}/state`, `POST /jobs/runs/{id}/cancel`.
- `GET /jobs/runs/{id}/artifacts`, `POST /jobs/runs/{id}/delivery`, `GET /jobs/runs/{id}/delivery`.
- `GET /audit` policy decision ledger view.
- `GET /audit/events`, `GET /audit/verify`, `GET /audit/export`.
- `POST /protocols/standards`, `GET /protocols/standards`, `POST /protocols/standards/{id}/versions`.
- `GET /protocols/standards/{id}/versions`.
- `POST /protocols/bootstrap/adopted`.
- `GET /protocols/compatibility`, `POST /protocols/validate`.
- `POST /protocols/conformance/runs`, `GET /protocols/conformance/runs`.
- `POST /digestion/run`, `GET /digestion/status/{project_id}`, `GET /digestion/gate/{project_id}`, `POST /digestion/export/{project_id}`.

Decision semantics:
- `allow`: action may proceed.
- `deny`: blocked.
- `hold`: requires privileged review path.

Message workflow states:
- `draft -> review -> approved -> dispatched -> superseded`.

Job run workflow states:
- `created -> queued -> dispatching -> running -> postback_pending -> delivered -> closed`.
- failure branches: `running -> retrying -> running`, `running -> failed -> escalated`, `postback_pending -> failed_visibility -> escalated`.

Connectivity control states:
- worker heartbeat updates `last_gateway_url`, ordered reconnect targets, and keepalive timing.
- probe failures force `connectivity_state=down` and set `reconnect_required=true`.
- reconnect policy always prefers last-known closest gateway first.

Clearance tiers:
- `public`, `internal`, `confidential`, `restricted`.
