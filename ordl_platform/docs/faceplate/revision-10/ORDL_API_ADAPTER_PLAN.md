# ORDL Frontend API Adapter Implementation Plan
## Revision 9 to Backend /v1 Migration

**Date:** 2026-03-07  
**Target:** `C:/Users/Winsock/Documents/GitHub/ordl-phetamines/ordl_platform/docs/faceplate/revision-9-fixed-app/ordl_fixed/app/blueprints/api.py`  
**Backend Contract:** `/v1` API (119 paths in current contract export)

---

# 1) SUMMARY

The current Revision 9 Flask blueprint (`api.py`) uses in-memory dictionaries (`orgs_db`, `providers_db`, `extensions_db`, `evidence_db`) with mock authorization and audit logging. This adapter plan treats Flask as a thin BFF layer that proxies requests to the ORDL backend `/v1` API and removes local stateful business logic from the UI-side blueprint.

## Key Changes Overview

| Component | Current State | New State |
|-----------|--------------|-----------|
| Data Stores | In-memory dicts (`orgs_db`, etc.) | HTTP calls to backend `/v1/*` |
| Authorization | Local `evaluate_authorization()` with mock clearance levels | JWT validation + backend-enforced authn/authz |
| Audit Logging | Local `log_audit_event()` (no persistence) | `POST /v1/audit/events` and `POST /v1/audit/evidence` to backend |
| Auth Tokens | Mock user context from `g` object | Real JWT extraction from `Authorization` header |
| Business Logic | Embedded in Flask routes | Backend is source of truth, Flask is proxy/orchestration layer |

## Backend Endpoint Mapping

| Local Route | Backend Endpoint | Status |
|-------------|------------------|--------|
| `GET /v1/orgs/{id}` | `/v1/orgs/{org_id}` | Implemented |
| `PUT /v1/orgs/{id}` | `/v1/orgs/{org_id}` | Implemented |
| `PUT /v1/orgs/{id}/defaults` | `/v1/orgs/{org_id}/defaults` | Implemented |
| `POST /v1/orgs/{id}/members` | `/v1/orgs/{org_id}/members` | Implemented |
| `POST /v1/orgs/{id}/regions` | `/v1/orgs/{org_id}/regions` | Implemented |
| `POST /v1/providers/{id}/test` | `/v1/providers/{provider_id}/test` | Implemented |
| `PUT /v1/providers/{id}/config` | `/v1/providers/{provider_id}/config` | Implemented |
| `POST /v1/extensions/verify` | `/v1/extensions/verify` | Implemented |
| `POST /v1/extensions/batch` | `/v1/extensions/batch` | Implemented |
| `POST /v1/audit/evidence` | `/v1/audit/evidence` | Implemented |
| `GET /v1/audit/events` | `/v1/audit/events` | Implemented |
| `GET /v1/audit/export` | `/v1/audit/export` | Implemented |

## Current Workspace Validation Baseline

- Current contract export: `ordl_platform/docs/contracts/api-v1-contract.json`
- Current contract path count: `119`
- Current Rev8 contract parity review: `37 required, 37 present, 0 missing`
- Current backend suite baseline in this workspace: `38 passed`

---

# 2) RISKS

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Backend connectivity failures | High | Medium | Add circuit breaker behavior and normalized 5xx/timeout proxy responses |
| JWT token expiration during requests | Medium | Low | Return 401 cleanly and centralize auth refresh policy outside the BFF |
| Backend API contract drift | High | Medium | Validate against `api-v1-contract.json` and pin adapter behavior to generated schemas |
| Performance degradation from extra hop | Medium | Medium | Cache selected read-heavy views and collapse redundant calls |
| Audit event loss on network failure | High | Low | Queue and retry audit writes or fail closed for regulated actions |
| Backend authz vs frontend assumptions mismatch | Critical | Medium | Keep all authorization decisions backend-driven and integration-tested |

---

# 3) ACTION LIST

## Phase 1: Core Infrastructure

1. Create a dedicated Flask backend client module for `/v1` communication.
2. Centralize JWT extraction and header forwarding.
3. Replace all direct dict reads/writes with backend proxy calls.
4. Remove mock authorization logic from the Flask layer.
5. Route audit writes to backend audit endpoints.

## Phase 2: Endpoint Migration

1. Migrate org, provider, extension, and audit flows first.
2. Add response normalization for backend 401/403/404/409/422 paths.
3. Add adapter-level error handling for timeout and connection failures.
4. Add a contract check against the generated `/v1` route set before each major frontend revision.

## Phase 3: Verification

1. Validate every mapped endpoint against the current contract export.
2. Add integration tests for JWT forwarding and backend denial propagation.
3. Reject any remaining Revision 9 paths that still depend on local in-memory state.

---

# 4) OPEN QUESTIONS

1. Should the Flask BFF perform any response shaping, or should it remain a near-transparent proxy?
2. Which read endpoints are acceptable to cache in the BFF without weakening governance guarantees?
3. Should audit writes fail closed for all privileged actions, or only for regulated evidence flows?
