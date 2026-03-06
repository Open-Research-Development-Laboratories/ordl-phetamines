# Orchestration Foundation Spec

Status: Draft v0.1  
Scope: ORDL platform control plane and worker runtime model

## 1) Objective

Design a provider-agnostic orchestration system that is plug-and-play, supports both group and individual task routing, and enforces explicit reporting chains for every job.

## 2) Design Principles

1. Provider-agnostic core: OpenAI, Anthropic, Kimi, and future providers share one orchestration contract.
2. Config-first behavior: orchestration behavior is controlled by profiles and policies, not hardcoded worker logic.
3. Fleet-by-default execution: non-trivial processes are delegated to worker fleet roles.
4. Deterministic governance: every job has owner, recipients, approval policy, and audit trail.
5. Composable routing: route by worker group, role, capability tag, or explicit worker id.
6. Fail-safe operation: retry/failover/escalation policy is declared per job class.

## 3) Core Domain Model

- `ProviderAdapter`
  - Standard provider plugin interface (`prepare`, `dispatch`, `poll`, `cancel`, `normalize_result`).
  - Adapter registration is signed and policy-gated.
- `WorkerIdentity`
  - Stable worker id, role, capability tags, health state, and trust metadata.
- `WorkerGroup`
  - Named collection of workers with routing strategy (`round_robin`, `least_loaded`, `priority`, `sticky`).
- `OrchestrationProfile`
  - Reusable execution policy pack (timeouts, retries, failover order, quality bar, output schema).
- `JobTemplate`
  - Versioned template for repeatable tasks with objective, required inputs, constraints, and recipients.
- `JobRun`
  - Runtime execution instance with state machine, artifacts, and timestamps.
- `ReportRoute`
  - Mapping of job outputs to designated recipients (person, team lead, board route, inbox).

## 4) Job Routing Modes

- Individual mode:
  - Target exactly one worker by id or role.
  - Useful for deterministic ownership.
- Group mode:
  - Target a worker group and apply strategy-based assignment.
  - Useful for high-throughput queues and resilience.
- Hybrid mode:
  - Planner on one worker/group, executor on another, validator on third.
  - Enforced by non-overlap file ownership policy.

## 5) Reporting Chain Requirements

Every `JobRun` must include:

1. `owner_principal_id` (who requested or owns the run)
2. `report_to` (one or more designated recipients)
3. `escalation_to` (fallback recipient route)
4. `visibility_mode` (`private`, `team`, `board`, `public-internal`)

Completion is valid only when:

- worker output is generated
- output is posted visibly to required chat/report channels
- recipient route delivery is recorded in audit

## 6) Orchestration Config Schema (Concept)

```json
{
  "profile_id": "prod-balanced-v1",
  "routing_mode": "group",
  "target_group": "implementation-core",
  "failover_group": "batch-fallback",
  "quality_bar": "strict",
  "max_parallel": 3,
  "retry_policy": { "max_attempts": 2, "backoff_seconds": 30 },
  "postback": {
    "required": true,
    "visible_body_required": true,
    "max_chunk_chars": 1800
  },
  "reporting": {
    "owner_principal_id": "user:winsock",
    "report_to": ["team:core-council", "user:null"],
    "escalation_to": ["board:ordl-board"]
  }
}
```

## 7) API Expansion (Planned)

New control endpoints:

- `POST /orchestration/profiles`
- `GET /orchestration/profiles`
- `POST /worker-groups`
- `GET /worker-groups`
- `POST /jobs/templates`
- `GET /jobs/templates`
- `POST /jobs/runs`
- `GET /jobs/runs`
- `POST /jobs/runs/{id}/cancel`
- `GET /jobs/runs/{id}/artifacts`
- `GET /jobs/runs/{id}/delivery`

## 8) Job State Machine

`created -> queued -> dispatching -> running -> postback_pending -> delivered -> closed`

Failure branches:

- `running -> retrying -> running`
- `running -> failed -> escalated`
- `postback_pending -> failed_visibility -> escalated`

## 9) Security and Governance

- Dispatch requires policy token and authorization decision (`allow`, `deny`, `hold`).
- Provider credentials are referenced by secret id, never copied into job payload.
- Every delivery/postback event is signed in audit chain.
- Jobs without explicit recipients are rejected.

## 10) Build Sequence

Phase 1:

- Profile + group + template models
- JobRun state machine in backend
- Visible postback enforcement checks

Phase 2:

- Adapter SDK for provider plugins
- Failover orchestration and retry policies
- Delivery receipts and escalation routing

Phase 3:

- UI configuration panels for profiles/groups/reporting chains
- Analytics for throughput, failure rate, and recipient SLA

