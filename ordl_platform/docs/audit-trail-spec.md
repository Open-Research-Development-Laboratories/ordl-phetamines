# Full Audit Trail Spec

Status: Draft v0.1  
Goal: immutable, actor-complete, chain-verifiable audit for every human and AI action.

## 1) Coverage Requirement

Audit must include:

- human actions (board, officer, manager, worker, contractor)
- agent actions (single model, fleet, swarm)
- worker runtime actions
- tool execution and side effects
- provider dispatch attempts and outcomes
- delivery/postback actions and recipient routing
- policy decisions and overrides

## 2) Event Envelope

Each event must carry:

- `event_index` (project-scoped monotonic counter)
- `event_type`
- `actor_type`, `actor_id`
- seat snapshot (`role`, `rank`, `position`, `group_name`) when available
- `resource` object (`resource_type`, `resource_id`)
- `payload` object (action details)
- `context` object (optional runtime context)
- `source`, `classification`, `severity`
- `trace_id`, `run_id`, `session_id`
- hash chain fields (`prev_hash`, `event_hash`, `hash_version`)
- `created_at`

## 3) Chain Integrity

- Every event links to previous hash.
- Hash seed includes canonical JSON of actor/resource/payload/context and event metadata.
- Verification endpoint must detect broken links and modified payloads.

## 4) Completeness Rules

Run is not considered complete unless all are true:

1. dispatch decision recorded
2. execution attempt recorded
3. output artifact recorded
4. postback/delivery recorded
5. recipient delivery receipt recorded

## 5) Query and Evidence

Required query dimensions:

- by project
- by actor
- by event type
- by run id / trace id
- by severity
- by time range

Evidence outputs:

- timeline export (`json`, `csv`)
- chain verification result
- recipient delivery proof report

## 6) API Targets

- `GET /audit/events`
- `GET /audit/verify`
- `GET /audit/export`
- `GET /audit/events?actor_id=...&event_type=...`

## 7) R&D Validation

Protocol acceptance for audit subsystem requires:

- deterministic serialization tests
- hash chain break detection tests
- actor coverage tests across roles and agent types
- throughput test for high event volumes
