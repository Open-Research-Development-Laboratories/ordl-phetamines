# ORDL Admin and Operations Runbook

This runbook defines operational procedures for platform administrators, operators, and security officers.

It is used for day-to-day control, incident management, continuity, and release operations.

## 1) Operating roles

- Platform Admin
- Fleet Operator
- Security Officer
- Compliance Auditor
- Release Manager
- Incident Commander

## 2) Daily operations checklist

### 2.1 Platform health

- Check API, worker, queue, DB, storage health.
- Confirm heartbeat freshness across gateways and nodes.
- Verify no uncontrolled reconnect storms.
- Validate queue backlog remains within SLO.

### 2.2 Security posture

- Review failed auth attempts.
- Review policy holds and denied critical actions.
- Review stale secrets and key rotation due list.
- Review extension trust and revocation queue.

### 2.3 Delivery and release status

- Check active deployment waves.
- Check approval queues and aging SLAs.
- Confirm no blocked releases without assigned owner.

### 2.4 Cost and capacity

- Monitor provider usage spikes.
- Monitor compute and storage saturation.
- Confirm budget alerts are acknowledged.

## 3) Weekly operations checklist

- Perform tenant access review.
- Validate high-privilege seat assignments.
- Validate backup job success and restore sample.
- Run fleet failover simulation in non-production.
- Review incident action items and closure status.

## 4) Monthly governance checklist

- Run policy drift scan against baseline.
- Export compliance evidence bundle.
- Execute control attestation workflow.
- Review protocol conformance runs.
- Review business continuity drill outcomes.

## 5) Standard procedures

## 5.1 User and seat lifecycle

Create user:

- Create account in identity provider.
- Create ORDL user record.
- Assign minimum required seat and role.
- Assign clearance tier and compartments.
- Confirm login and policy simulation passes.

Suspend user:

- Revoke active sessions.
- Suspend seat assignments.
- Revoke policy tokens.
- Log action in audit trail.

Terminate access:

- Revoke all seats and roles.
- Rotate any secrets accessible by user.
- trigger evidence export for access revocation.

## 5.2 Node onboarding workflow

- Candidate discovery created.
- Operator performs suitability review.
- Security officer approves trust zone assignment.
- Bootstrap profile assigned.
- Node added to staging gateway first.
- Health soak period completed.
- Promote to production mesh.

## 5.3 Gateway maintenance procedure

- Set gateway to draining.
- Ensure traffic redistributed.
- Confirm zero critical active sessions remain.
- Apply maintenance/update.
- Run post-update health probes.
- Return gateway to active and monitor.

## 5.4 Rolling update procedure

- Build release image and verify signatures.
- Run preflight checks.
- Execute canary wave.
- Evaluate canary metrics and policy outcomes.
- Roll remaining waves by region.
- Finalize rollout and close change record.

Rollback criteria:

- error rate breach
- latency regression breach
- policy decision latency breach
- elevated critical incident signal

## 6) Incident management

### 6.1 Incident severity levels

- Sev 1: platform-wide outage or major security event.
- Sev 2: major service degradation.
- Sev 3: partial service impact.
- Sev 4: minor issue with workaround.

### 6.2 Incident response flow

- detect and classify
- assign Incident Commander
- declare incident room
- contain impact
- recover service
- validate stability
- perform postmortem

### 6.3 Mandatory incident artifacts

- incident timeline
- affected scope
- root cause summary
- immediate remediation
- long-term corrective actions
- owner and due dates

## 7) Security operations

### 7.1 Secret rotation

- Rotate auth secrets and signing keys per policy period.
- Validate dependent services after rotation.
- Revoke old keys only after health validation.

### 7.2 Certificate and token management

- Validate token issuer and audience settings.
- Ensure short-lived token usage for critical actions.
- Revoke compromised signing material immediately.

### 7.3 Extension trust management

- Verify signature before enabling extension.
- Enforce per-project allowlists.
- Revoke extension on policy violation.

## 8) Compliance operations

### 8.1 Evidence export

- Run scheduled evidence export for defined control set.
- Validate chain integrity before export publication.
- Archive exports with retention tags.

### 8.2 Audit verification

- Run audit chain verification daily.
- Raise incident if chain mismatch is detected.

### 8.3 Control status maintenance

- Track pass/fail/partial per control.
- Link each control to fresh evidence.
- Assign owner for unresolved control gaps.

## 9) Reliability operations

### 9.1 Reconnect storm handling

- Detect node reconnect amplification.
- Temporarily widen retry jitter windows.
- Quarantine unstable nodes if required.
- Restore normal policy after stability returns.

### 9.2 Queue overload handling

- Identify queue class causing saturation.
- Apply backpressure policy.
- Scale worker pool where safe.
- pause non-critical jobs if thresholds exceed.

### 9.3 Data store degradation

- Trigger read-only mode for affected control surfaces if needed.
- prioritize control-plane writes over non-critical telemetry writes.
- initiate failover per storage and DB policies.

## 10) Business continuity and disaster recovery

### 10.1 Backup strategy

- Daily full backup for critical control-plane DB.
- Frequent incremental snapshots.
- Artifact store versioning and immutability.

### 10.2 Restore drill

- Monthly restore drill to isolated environment.
- Validate:
  - auth
  - policy decisions
  - dispatch workflow
  - audit chain continuity

### 10.3 DR failover

- Activate DR region.
- Restore latest validated state.
- Repoint ingress and control endpoints.
- Confirm policy gateway and auth are healthy before reopening writes.

## 11) Operational SLOs and thresholds

- API availability: >= 99.95%
- Fleet reconnect success in 5 min: >= 99%
- Dispatch acceptance latency p95: <= 2s
- Policy decision latency p95: <= 300ms
- Critical queue delay p95: <= 5s

## 12) Runbook automation hooks

All procedures should have automation entry points:

- `ops.health.check`
- `ops.fleet.reconcile`
- `ops.node.onboard`
- `ops.release.rollout`
- `ops.release.rollback`
- `ops.incident.declare`
- `ops.evidence.export`
- `ops.audit.verify`

## 13) Mandatory logging for every runbook action

Each action must log:

- actor
- timestamp
- tenant/project scope
- action type
- target resource
- result
- reason code

No silent admin actions are permitted.
