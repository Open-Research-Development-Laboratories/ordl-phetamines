Summary
- Add a new endpoint `POST /v1/fleet/execute` in `routes.py`, following the same auth + async job pattern already used by `/v1/fleet/restart`, `/v1/fleet/resync`, and `/v1/fleet/stage-handoff`.
- Back it with a new orchestrator method in `orchestrator.py` (e.g., `execute_worker_task(...)`) that:
  1) validates/normalizes role + task inputs,  
  2) runs a remote `openclaw agent ...` command via existing `_connect` + `_remote_run`,  
  3) resolves latest handoff via existing `latest_worker_handoff(...)`,  
  4) returns a machine-parseable payload containing execution status and artifact location.
- Reuse the current job system for persistence of result state: sync returns immediate result; async returns `job` record, and artifact path is stored inside job result payload (same integration surface already exposed via `/v1/jobs` and `/v1/jobs/{job_id}`).
- Keep request/response contract shape strict and explicit in dispatch validation + README so hub-control can integrate without guessing.

Risks
- Remote command contract risk: exact `openclaw agent` CLI flags may vary by host/version; command construction must be conservative and failure-transparent.
- Artifact ambiguity risk: `latest_worker_handoff` can return stale/old file if worker did not emit a new artifact for this run.
- Injection/escaping risk: task text passed to shell must be safely quoted (current code already uses `shlex.quote` patterns; keep that standard).
- Async observability risk: if endpoint returns 202 but result schema is inconsistent, hub integration will become brittle.
- Test coverage gap: current tests only cover helper functions; endpoint and execution-path tests need to be added.

Action List
- **File-touch implementation plan**
  1) **`fleet_api/fleet_api/orchestrator.py`**
     - Add `execute_worker_task(role, task, handoff_glob="/development/crew-handoff/*.md", timeout=..., metadata=None)` method.
     - Build remote command with strict quoting; run via `_remote_run`.
     - Capture timing fields (`started_at`, `finished_at` UTC ISO), `ok`, `returncode`, `stdout`, `stderr`.
     - Call `latest_worker_handoff(role, handoff_glob)` and include:
       - `handoff.ok`
       - `handoff.path` (artifact location)
       - `handoff.error` (if unresolved)
     - Return a stable dict contract, e.g.:
       - `{"ok","role","host","execution":{...},"handoff":{...}}`.
  2) **`fleet_api/fleet_api/routes.py`**
     - Add `@bp.post("/v1/fleet/execute")`.
     - Parse JSON: required `role`, required `task`, optional `handoff_glob`, `timeout`, `async`.
     - Reuse `_want_async(payload)` and `jobs.submit(...)`.
     - Sync response: `{"ok": result.ok, "result": ...}`.
     - Async response: `{"ok": True, "job": asdict(rec)}`, 202.
  3) **`fleet_api/fleet_api/dispatch.py`**
     - Add optional response validation checks for execution payload section keys (minimal contract checks only; no new framework).
     - Keep existing section-order behavior unchanged.
  4) **`fleet_api/tests/test_orchestrator_health_helpers.py`**
     - Add helper-level tests for new execution result normalization (timestamp/shape expectations) if helper funcs are introduced.
  5) **Add new tests file**: `fleet_api/tests/test_fleet_execute_endpoint.py`
     - Test 400 when `role` or `task` missing.
     - Test sync success path with orchestrator mock returning handoff path.
     - Test async path returns 202 + job envelope.
     - Test remote failure propagates machine-parseable error fields.
  6) **`fleet_api/README.md`**
     - Add endpoint to API list + example request/response for sync and async.
     - Document that artifact location is in `result.handoff.path` (sync) or job result payload (async).
  7) **`ordl_platform/docs/implementation-status.md`**
     - Add a short note under “Completed in this pass” once implemented: fleet execute endpoint added with machine-parseable artifact pointer.

- **Validation scope (batch worker only; separate from file touches)**
  - Run focused tests:
    - `pytest fleet_api/tests/test_orchestrator_health_helpers.py -q`
    - `pytest fleet_api/tests/test_fleet_execute_endpoint.py -q`
  - Smoke endpoint contract with local app:
    - `POST /v1/fleet/execute` sync + async.
    - `GET /v1/jobs/{job_id}` confirms artifact path persisted in result payload.
  - Negative-path checks:
    - invalid role
    - missing task
    - remote command non-zero exit
    - no handoff found (must still return parseable structure).

Open Questions
- What exact remote `openclaw agent` CLI invocation should be treated as canonical on workers (flags and JSON mode)?
- Should “artifact storage” mean only job-result persistence, or also writing a dedicated pointer record to `fleet_api/state/`?
- Do you want endpoint to support multi-role fanout now, or keep strict single-role execution for deterministic hub orchestration?
- For handoff freshness, should we enforce “artifact must be newer than execution start time” before returning success?