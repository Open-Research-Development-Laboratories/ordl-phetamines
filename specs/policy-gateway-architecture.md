# Policy Gateway Architecture (Universal Outbound Control Plane)

## Goal
Enforce deterministic, non-bypass outbound policy across all channels and providers.

## Security Objectives
- Fail-closed on any uncertainty or outage.
- No direct provider sends from agent runtime.
- Deterministic policy as final authority.
- Full auditability with tamper-evident records.

## High-Level Design

```text
Agent Runtime
  -> Outbound Request API
    -> Policy Gateway (authn/authz + normalization)
      -> Deterministic Policy Engine (OPA/Cedar)
      -> Optional Model Judge (advisory only)
      -> Decision Broker (allow|deny|hold)
      -> Signed Decision Token
        -> Provider Adapter (Discord/Telegram/SMS/Email/etc.)
          -> Provider API

Audit Log Sink (append-only/WORM)
Approval Queue + UI
State Store (quiet mode, allowlists, freeze flags)
```

## Trust Boundaries
1. Agent Runtime (untrusted for enforcement).
2. Policy Gateway + Engine (trusted enforcement domain).
3. Provider Adapters (trusted transmitters, require signed policy token).
4. Audit Sink (immutable evidence).

## Non-Bypass Guarantees
- Provider credentials are only available to Provider Adapters.
- Adapters reject transmissions without valid signed decision token.
- Token contains request hash, destination, decision, policy version, TTL, nonce.
- Replay protection on nonce + short TTL.

## Core Components

### 1) Outbound Request API
- Single ingress for all outbound actions.
- Accepts canonical request schema.
- Authenticates actor/session.

### 2) Normalizer
- Maps channel-specific payloads into canonical policy event format.
- Derives metadata: destination class, sensitivity, intent, risk hints.

### 3) Deterministic Policy Engine
- Rule evaluation order:
  1. Global hard-deny rules
  2. Runtime freeze/quiet rules
  3. Data leakage and sensitivity rules
  4. Channel and destination rules
  5. Role-based approval rules
  6. Rate-limit and anti-spam rules
- Produces `allow`, `deny`, or `hold_for_approval` with rule IDs.

### 4) Optional Model Judge (Secondary)
- Receives normalized request + context snippets.
- Returns risk annotations and recommendation.
- Cannot override deterministic decision.

### 5) Decision Broker
- Merges deterministic decision + optional annotations.
- Signs decision token when `allow`.
- Sends `hold` to approval queue.

### 6) Provider Adapters
- Validate signed token before send.
- Verify hash(payload) equals hash in token.
- Enforce token TTL and nonce uniqueness.

### 7) Approval Service
- Human review for `hold_for_approval`.
- Scoped approvals only (destination, intent, expiration).

### 8) Audit and Observability
- Append-only logs with:
  - request hash
  - actor/session
  - policy version
  - decision + rule IDs
  - approval metadata (if any)
- Metrics: deny rate, hold rate, false holds, latency.

## Decision Semantics
- `allow`: transmit permitted.
- `deny`: blocked, no provider call.
- `hold_for_approval`: queue and await explicit approval.

## Fail-Closed Behavior
- Policy engine unavailable -> deny.
- State store unavailable -> deny.
- Audit sink unavailable -> deny (or emergency local append-only fallback with immediate alert).
- Signature service unavailable -> deny.

## Runtime States
- `normal`
- `quiet` (restrict proactive sends)
- `frozen` (deny all outbound except emergency allowlist)
- `incident` (tightened policies + elevated logging)

## Deployment Pattern
- Run gateway as independent service.
- Sidecar or proxy mode for provider adapters.
- Blue/green policy rollouts with version pinning.

## Minimum SLA Targets
- Decision latency p95 < 150ms (without hold)
- Availability 99.9%+ for enforcement path
- Zero unaudited outbound transmissions

## Hardening Checklist
- mTLS between components
- Signed configs and policy bundles
- Secret management via vault/HSM
- Principle of least privilege IAM
- Regular policy regression and adversarial tests
- Tamper alerts on log chain integrity
