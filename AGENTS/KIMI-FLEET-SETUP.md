# KIMI Fleet Setup (Winsock)

## Topology

- Hub (Windows desktop): `hub-control` at `C:\development`
- Worker 1 (desktop Kimi): `worker-arch-desktop`
- Worker 2 (RHEL laptop Kimi): `worker-build-laptop`
- Worker 3 (RHEL server Kimi): `worker-batch-server`

## Core Goal

Run one coordinator plus multiple Kimi workers with deterministic startup context.
All workers consume the same injected corpus and follow the same output contract.

## Deterministic Startup Corpus

These files must exist on every machine's active workspace root before any new session:

- `AGENTS.md`
- `DIRECTIVES.md`
- `KIMI-FLEET-SETUP.md`
- `KIMI-RELAY-SOP.md`
- `KIMI-STARTUP-PROMPT.txt`
- `laws/KIMI.md`
- `laws/BOOK-MODE.md`
- `memory/YYYY-MM-DD.md` (today + yesterday)

Reference root:

- Windows hub: `C:\development`
- RHEL workers: `/development` (or override per host, but keep consistent on each host)

## Role Contract

### hub-control (hub)

- Split tasks and assign worker scope
- Enforce invariants and final acceptance
- Merge outputs into one publishable result

### worker-arch-desktop

- Architecture decisions
- Interface contracts
- Risk and failure-mode analysis

### worker-build-laptop

- Implementation
- Tests and benchmark evidence
- Migration notes

### worker-batch-server

- Long-running batch jobs
- Fallback worker when laptop is offline
- Large refactors and validation sweeps

## Dispatch Format (Mandatory)

Every worker task message must include:

1. Objective
2. Inputs (exact filenames)
3. Constraints/invariants
4. Required output format:
   - Summary
   - Risks
   - Action List
   - Open Questions

## Scheduling and Failover

1. Prefer `worker-build-laptop` for active coding loops.
2. Use `worker-batch-server` for long or heavy jobs.
3. If laptop is offline, fail over to server without blocking.
4. If workers disagree, hub resolves and logs rationale.

## Instance Identity Rules

- One unique `bridge.instanceId` and `bridge.deviceId` per machine.
- Never reuse a worker identity on another machine.
- Keep IDs stable to preserve pairing and audit continuity.

## Ops Notes

- Do not rename worker identities unless Winsock requests it.
- Keep full IDs in docs; short IDs are fine in chat.
- Treat laptop availability as intermittent by design.
