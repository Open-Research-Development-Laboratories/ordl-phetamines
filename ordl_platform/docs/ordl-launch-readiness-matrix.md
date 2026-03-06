# ORDL Launch Readiness Matrix

This file is the release gate matrix for first production launch and subsequent major releases.

A release is blocked until all launch-critical controls are marked PASS with evidence.

## 1) Gate categories

- Product completeness
- Security and trust
- Fleet reliability
- Governance and authorization
- Model lifecycle safety
- Observability and operations
- Compliance evidence
- Migration and rollback safety

## 2) Product completeness gates

### 2.1 Route completeness

- PASS criteria:
  - All launch-critical routes exist.
  - All routes are wired to real data.
  - No placeholder view in production.

### 2.2 Role-based views

- PASS criteria:
  - Required role checks per route implemented.
  - Unauthorized access returns deterministic deny.
  - UI reflects least-privilege controls.

### 2.3 Workflow completeness

- PASS criteria:
  - Draft->Review->Rework->Approve->Dispatch works end-to-end.
  - Approval rationale required on all decisions.
  - Delivery status and retry behavior visible.

## 3) Security and trust gates

### 3.1 Identity and access

- PASS criteria:
  - OIDC/SAML config validated.
  - MFA policy enforced for privileged roles.
  - Session and token expiry behavior verified.

### 3.2 Secret management

- PASS criteria:
  - Secret backend configured and healthy.
  - no plaintext secrets in config or logs.
  - rotation and revocation workflows tested.

### 3.3 Outbound policy gateway

- PASS criteria:
  - critical outbound actions require valid policy token.
  - unsigned or stale tokens are blocked.
  - denial and hold behavior is auditable.

### 3.4 Extension trust

- PASS criteria:
  - extension signatures verified.
  - scope restrictions enforced.
  - revocation prevents execution immediately.

## 4) Fleet reliability gates

### 4.1 Pairing and trust

- PASS criteria:
  - pending pairing queue processes correctly.
  - approved devices receive only assigned scopes.
  - revoked devices lose access immediately.

### 4.2 Reconnect reliability

- PASS criteria:
  - nodes reconnect to last-known healthy gateway first.
  - fallback order works under gateway failure.
  - reconnect storm protection verified.

### 4.3 Probe and heartbeat

- PASS criteria:
  - gateway probe scheduler runs and records outputs.
  - heartbeat freshness thresholds enforced.
  - stale critical nodes trigger alerts.

### 4.4 Update resilience

- PASS criteria:
  - canary rollout works.
  - failed wave rollback works.
  - no node loss during standard update cycle.

## 5) Governance and authorization gates

### 5.1 Seat and clearance enforcement

- PASS criteria:
  - role, rank, clearance, and compartment checks enforced.
  - unauthorized operations blocked with reason codes.

### 5.2 Board and officer workflows

- PASS criteria:
  - designated approvals required where configured.
  - no bypass path for controlled actions.

### 5.3 Multi-tenant isolation

- PASS criteria:
  - data isolation between tenants confirmed.
  - queue and storage isolation confirmed.
  - audit query boundaries enforced.

## 6) Model lifecycle gates

### 6.1 Training controls

- PASS criteria:
  - training runs are reproducible.
  - artifacts are versioned and signed.
  - lineage links are complete.

### 6.2 Evaluation controls

- PASS criteria:
  - quality and safety suites run before promotion.
  - regression thresholds block promotion on failure.

### 6.3 Inference reliability

- PASS criteria:
  - latency/error SLOs met at expected load.
  - autoscaling and failover verified.

## 7) Observability and operations gates

### 7.1 Telemetry completeness

- PASS criteria:
  - traces, metrics, and logs are available.
  - correlation IDs connect cross-service events.

### 7.2 Alerting and paging

- PASS criteria:
  - critical alerts route to on-call.
  - acknowledgement and escalation flows verified.

### 7.3 Incident readiness

- PASS criteria:
  - incident declaration workflow tested.
  - postmortem template and closure workflow active.

## 8) Compliance and audit gates

### 8.1 Audit chain integrity

- PASS criteria:
  - hash-chain verification passes.
  - tamper detection paths tested.

### 8.2 Evidence export

- PASS criteria:
  - control evidence export works (json/csv/pdf where required).
  - exports are attributable and timestamped.

### 8.3 Control mapping

- PASS criteria:
  - baseline control map complete.
  - each control links to current evidence.

## 9) Migration and rollback gates

### 9.1 Schema migration safety

- PASS criteria:
  - forward migration tested.
  - rollback migration tested.
  - data integrity checks pass.

### 9.2 Release rollback safety

- PASS criteria:
  - service rollback script and process validated.
  - no orphaned long-running jobs after rollback.

### 9.3 Dual-run parity

- PASS criteria:
  - mirrored run behavior validated against baseline platform.
  - parity scenarios pass before final cutover.

## 10) Required launch evidence bundle

Bundle must include:

- release gate test report
- security validation report
- fleet resilience drill report
- audit verification report
- control evidence export
- rollback drill report

## 11) Gate decision policy

- PASS: all required launch gates pass.
- HOLD: one or more required gates unresolved.
- DENY: critical security, data integrity, or reliability gate failed.

Only designated release authorities can approve PASS.

## 12) Post-launch day-0 and day-7 checks

Day-0:

- confirm all critical service SLOs.
- monitor error and reconnect rates every 15 minutes.
- keep release rollback hot for immediate use.

Day-7:

- review first-week incidents and near-misses.
- validate cost and utilization against forecast.
- promote deferred non-critical features only after stability review.
