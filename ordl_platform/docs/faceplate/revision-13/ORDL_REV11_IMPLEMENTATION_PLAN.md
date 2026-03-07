# ORDL Revision 11 Flask BFF Implementation Plan
## File-Accurate Plan for `/root/.openclaw/workspace/ordl_fixed/app/blueprints/api.py`

**Date:** 2026-03-07  
**Target File:** `/root/.openclaw/workspace/ordl_fixed/app/blueprints/api.py`  
**Backend Contract:** `/root/.openclaw/workspace/ordl_platform/docs/contracts/api-v1-contract.json`  
**Source of Truth:** Backend `/v1` API (47 routes across 4 modules)

---

## 1) SUMMARY

### Current State (Revision 9)
The Flask BFF at `/root/.openclaw/workspace/ordl_fixed/app/blueprints/api.py` currently contains:

| Component | Lines | Implementation |
|-----------|-------|----------------|
| `evaluate_authorization()` | ~19-65 | Mock auth with hardcoded clearance matrix |
| `require_auth` decorator | ~68-89 | Local authorization checks |
| `log_audit_event()` | ~92-106 | No-op audit logging (no persistence) |
| `orgs_db` | ~113-145 | In-memory dict with 1 mock org |
| `providers_db` | ~146-175 | In-memory dict with 2 mock providers |
| `extensions_db` | ~176-185 | In-memory dict with 2 mock extensions |
| `evidence_db` | ~186 | Empty dict for evidence packages |
| **Total Routes** | ~27 | 12 dynamic + 15 static mocks |

### Target State (Revision 11)
Transform the Flask BFF into a thin HTTP proxy layer delegating all data operations to the backend `/v1` API:

| Component | Target Implementation |
|-----------|----------------------|
| Authorization | JWT extraction + backend delegation |
| Data Layer | HTTP proxy to `/v1/*` endpoints |
| Audit Logging | `POST /v1/audit/events` backend call |
| **Total Routes** | 47 (full contract alignment) |

### Backend Contract Alignment
Per `/root/.openclaw/workspace/ordl_platform/docs/contracts/api-v1-contract.json`:
- **Foundation:** 5 routes (health, metrics, version)
- **Governance:** 24 routes (orgs, teams, projects, seats, clearance, policy)
- **Security:** 13 routes (audit, extensions, providers)
- **Control:** 5 routes (workers, incidents)

### Directory Structure Changes
```
ordl_fixed/
├── app/
│   ├── blueprints/
│   │   └── api.py              # MODIFY: Remove mocks, add proxy logic
│   └── services/               # CREATE: New directory
│       ├── __init__.py         # CREATE: Package init
│       ├── backend_client.py   # CREATE: HTTP client with JWT/retry
│       └── audit_service.py    # CREATE: Async audit logging
├── requirements.txt            # MODIFY: Add requests, PyJWT, tenacity
└── .env.example                # CREATE: Environment template
```

---

## 2) RISKS

### P0 - Critical (Block Release)

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Backend connectivity cascade** | Frontend unusable if backend down | Implement circuit breaker in `backend_client.py`; return 503 with retry-after header |
| **JWT secret mismatch** | Auth failures across all endpoints | Validate JWKS endpoint availability before deployment; implement key rotation handler |
| **API contract drift** | 500 errors from schema mismatches | Add response validation layer; backend contract is source of truth per requirements |
| **Circular audit logging** | Audit routes calling audit causes infinite loop | Exclude `/v1/audit/*` from audit decorator; add `skip_audit=True` flag |
| **Provider secret exposure** | API keys in logs | Sanitize `config.api_key_ref` fields in `backend_client.py` before logging |

### P1 - High (Must Address)

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Network hop latency** | 2x-3x latency vs in-memory | Connection pooling in `backend_client.py`; 30s default timeout |
| **Token expiration mid-flow** | User loses work | Implement 401→401 passthrough; frontend handles refresh |
| **Backend 429 rate limiting** | Throttling disrupts ops | Exponential backoff with jitter in `backend_client.py` |
| **Batch operation timeouts** | Large batches fail | Backend handles batching; proxy passes through with 120s timeout |

### P2 - Medium (Should Address)

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Directory creation failure** | `app/services/` may not exist | Create directory as part of Phase 1 |
| **Import path errors** | Relative imports breaking | Use `from ..services.backend_client import ...` pattern |
| **Missing requirements** | New dependencies not installed | Pin versions: `requests>=2.31.0`, `PyJWT>=2.8.0`, `tenacity>=8.0` |

---

## 3) ACTION LIST

### Phase 1: Infrastructure Setup
**Priority:** P0 | **Files to Create/Modify:**

| # | Action | File Path | Description |
|---|--------|-----------|-------------|
| 1.1 | Create services directory | `ordl_fixed/app/services/` | New directory for backend client modules |
| 1.2 | Create package init | `ordl_fixed/app/services/__init__.py` | Empty init file for Python package |
| 1.3 | Create backend client | `ordl_fixed/app/services/backend_client.py` | HTTP client with JWT handling, retry logic, circuit breaker pattern |
| 1.4 | Create audit service | `ordl_fixed/app/services/audit_service.py` | Async audit logging with in-memory retry queue |
| 1.5 | Add dependencies | `ordl_fixed/requirements.txt` | Add: `requests>=2.31.0`, `PyJWT>=2.8.0`, `tenacity>=8.0` |
| 1.6 | Create env template | `ordl_fixed/.env.example` | Document: `ORDL_BACKEND_URL`, `ORDL_BACKEND_TIMEOUT`, `ORDL_JWKS_URL` |

### Phase 2: Authorization Migration
**Priority:** P0 | **File:** `ordl_fixed/app/blueprints/api.py`

| # | Action | Line Range | Description |
|---|--------|------------|-------------|
| 2.1 | Import backend client | Top of file | Add: `from ..services.backend_client import get_backend_client, require_jwt` |
| 2.2 | Remove mock auth | ~19-65 | Delete entire `evaluate_authorization()` function |
| 2.3 | Remove clearance matrix | ~55-63 | Delete `clearance_requirements` dict within auth function |
| 2.4 | Update decorator | ~68-89 | Replace `require_auth` body to call backend `/v1/policy/decide` |
| 2.5 | Add auth alias | After decorator | Add: `require_auth = require_backend_auth` for route compatibility |
| 2.6 | Update audit logger | ~92-106 | Modify `log_audit_event()` to POST to `/v1/audit/events` via backend client |

### Phase 3: Data Store Removal
**Priority:** P0 | **File:** `ordl_fixed/app/blueprints/api.py`

| # | Action | Line Range | Description |
|---|--------|------------|-------------|
| 3.1 | Delete orgs_db | ~113-145 | Remove entire `orgs_db` dict definition |
| 3.2 | Delete providers_db | ~146-175 | Remove entire `providers_db` dict definition |
| 3.3 | Delete extensions_db | ~176-185 | Remove entire `extensions_db` dict definition |
| 3.4 | Delete evidence_db | ~186 | Remove `evidence_db = {}` line |

### Phase 4: Organization Routes Migration
**Priority:** P0 | **File:** `ordl_fixed/app/blueprints/api.py`

| # | Action | Route | Current | Target |
|---|--------|-------|---------|--------|
| 4.1 | Refactor | `GET /v1/orgs/<org_id>` | In-memory lookup | Proxy to `GET /v1/orgs/{org_id}` |
| 4.2 | Refactor | `PUT /v1/orgs/<org_id>` | In-memory update | Proxy to `PUT /v1/orgs/{org_id}` |
| 4.3 | Refactor | `PUT /v1/orgs/<org_id>/defaults` | In-memory settings | Proxy to `PUT /v1/orgs/{org_id}/defaults` |
| 4.4 | Refactor | `POST /v1/orgs/<org_id>/members` | In-memory append | Proxy to `POST /v1/orgs/{org_id}/members` |
| 4.5 | Refactor | `POST /v1/orgs/<org_id>/regions` | In-memory append | Proxy to `POST /v1/orgs/{org_id}/regions` |
| 4.6 | Add | `GET /v1/governance/orgs` | Static mock | Proxy to `GET /v1/orgs` |
| 4.7 | Add | `DELETE /v1/orgs/<org_id>` | Missing | Proxy to `DELETE /v1/orgs/{org_id}` |
| 4.8 | Add | `GET /v1/orgs/<org_id>/members` | Missing | Proxy to `GET /v1/orgs/{org_id}/members` |
| 4.9 | Add | `GET /v1/orgs/<org_id>/defaults` | Missing | Proxy to `GET /v1/orgs/{org_id}/defaults` |
| 4.10 | Add | `GET /v1/orgs/<org_id>/regions` | Missing | Proxy to `GET /v1/orgs/{org_id}/regions` |

### Phase 5: Provider Routes Migration
**Priority:** P0 | **File:** `ordl_fixed/app/blueprints/api.py`

| # | Action | Route | Current | Target |
|---|--------|-------|---------|--------|
| 5.1 | Refactor | `POST /v1/providers/<id>/test` | Simulated random latency | Proxy to `POST /v1/providers/{id}/test` |
| 5.2 | Refactor | `PUT /v1/providers/<id>/config` | In-memory update | Proxy to `PUT /v1/providers/{id}/config` |
| 5.3 | Refactor | `GET /v1/security/providers` | List from providers_db | Proxy to `GET /v1/providers` |
| 5.4 | Add | `POST /v1/providers` | Missing | Proxy to `POST /v1/providers` |
| 5.5 | Add | `GET /v1/providers/<id>` | Missing | Proxy to `GET /v1/providers/{id}` |
| 5.6 | Add | `PUT /v1/providers/<id>` | Missing | Proxy to `PUT /v1/providers/{id}` |
| 5.7 | Add | `DELETE /v1/providers/<id>` | Missing | Proxy to `DELETE /v1/providers/{id}` |
| 5.8 | Add | `PUT /v1/providers/priority` | Missing | Proxy to `PUT /v1/providers/priority` |
| 5.9 | Add | `GET /v1/providers/probes` | Missing | Proxy to `GET /v1/providers/probes` |
| 5.10 | Add | `PUT /v1/providers/probes` | Missing | Proxy to `PUT /v1/providers/probes` |

### Phase 6: Extension Routes Migration
**Priority:** P1 | **File:** `ordl_fixed/app/blueprints/api.py`

| # | Action | Route | Current | Target |
|---|--------|-------|---------|--------|
| 6.1 | Refactor | `POST /v1/extensions/verify` | Simulated signature check | Proxy to `POST /v1/extensions/verify` |
| 6.2 | Refactor | `POST /v1/extensions/batch` | In-memory batch | Proxy to `POST /v1/extensions/batch` |
| 6.3 | Refactor | `GET /v1/security/extensions` | List from extensions_db | Proxy to `GET /v1/extensions` |
| 6.4 | Add | `POST /v1/extensions` | Missing | Proxy to `POST /v1/extensions` |
| 6.5 | Add | `GET /v1/extensions/<ext_id>` | Missing | Proxy to `GET /v1/extensions/{ext_id}` |
| 6.6 | Add | `PUT /v1/extensions/<ext_id>` | Missing | Proxy to `PUT /v1/extensions/{ext_id}` |
| 6.7 | Add | `DELETE /v1/extensions/<ext_id>` | Missing | Proxy to `DELETE /v1/extensions/{ext_id}` |

### Phase 7: Audit Routes Migration
**Priority:** P0 | **File:** `ordl_fixed/app/blueprints/api.py`

| # | Action | Route | Current | Target |
|---|--------|-------|---------|--------|
| 7.1 | Refactor | `POST /v1/audit/evidence` | In-memory evidence creation | Proxy to `POST /v1/audit/evidence` with `skip_audit=True` |
| 7.2 | Refactor | `GET /v1/audit/events` | Static mock events | Proxy to `GET /v1/audit/events` with `skip_audit=True` |
| 7.3 | Refactor | `GET /v1/audit/export` | Static mock | Proxy to `GET /v1/audit/export` with `skip_audit=True` |

### Phase 8: Static Routes Decision
**Priority:** P1 | **File:** `ordl_fixed/app/blueprints/api.py`

| # | Action | Route | Decision |
|---|--------|-------|----------|
| 8.1 | Proxy | `/v1/fleet/*` (4 routes) | Pass-through to backend; return empty array if 404 |
| 8.2 | Proxy | `/v1/models/*` (4 routes) | Pass-through to backend; return empty array if 404 |
| 8.3 | Proxy | `/v1/deployments/*` (3 routes) | Pass-through to backend; return empty array if 404 |
| 8.4 | Proxy | `/v1/nodes/*` (2 routes) | Pass-through to backend; return empty array if 404 |
| 8.5 | Proxy | `/v1/health/*` (3 routes) | Pass-through to backend; critical for health checks |
| 8.6 | Proxy | `/v1/incidents/*` (2 routes) | Pass-through to backend; return empty array if 404 |
| 8.7 | **REMOVE** | `/v1/messages/*` (2 routes) | Not in `/v1` contract - delete routes |
| 8.8 | Proxy | `/v1/governance/*` (4 routes) | Consolidate to pass-through pattern |

### Phase 9: New Governance Routes (Per Contract)
**Priority:** P2 | **File:** `ordl_fixed/app/blueprints/api.py`

| # | Action | Route | Backend Endpoint |
|---|--------|-------|------------------|
| 9.1 | Add | `GET /v1/teams`, `POST /v1/teams` | Proxy to `/v1/teams` |
| 9.2 | Add | `GET /v1/teams/<id>`, `PUT /v1/teams/<id>`, `DELETE /v1/teams/<id>` | Proxy to `/v1/teams/{id}` |
| 9.3 | Add | `GET /v1/teams/<id>/scope`, `PUT /v1/teams/<id>/scope` | Proxy to `/v1/teams/{id}/scope` |
| 9.4 | Add | `GET /v1/projects`, `POST /v1/projects` | Proxy to `/v1/projects` |
| 9.5 | Add | `GET /v1/projects/<id>`, `PUT /v1/projects/<id>`, `DELETE /v1/projects/<id>` | Proxy to `/v1/projects/{id}` |
| 9.6 | Add | `GET /v1/projects/<id>/defaults`, `PUT /v1/projects/<id>/defaults` | Proxy to `/v1/projects/{id}/defaults` |
| 9.7 | Add | `GET /v1/seats`, `POST /v1/seats` | Proxy to `/v1/seats` |
| 9.8 | Add | `GET /v1/seats/<id>`, `PUT /v1/seats/<id>`, `DELETE /v1/seats/<id>` | Proxy to `/v1/seats/{id}` |
| 9.9 | Add | `POST /v1/seats/<id>/assign`, `POST /v1/seats/<id>/vacate` | Proxy to `/v1/seats/{id}/assign|vacate` |
| 9.10 | Add | `POST /v1/seats/bulk` | Proxy to `/v1/seats/bulk` |
| 9.11 | Add | `GET /v1/seats/matrix`, `PUT /v1/seats/matrix` | Proxy to `/v1/seats/matrix` |
| 9.12 | Add | `GET /v1/clearance/tiers`, `PUT /v1/clearance/tiers` | Proxy to `/v1/clearance/tiers` |
| 9.13 | Add | `GET /v1/clearance/tiers/<tier_id>` | Proxy to `/v1/clearance/tiers/{tier_id}` |
| 9.14 | Add | `GET /v1/clearance/compartments`, `POST /v1/clearance/compartments` | Proxy to `/v1/clearance/compartments` |
| 9.15 | Add | `GET /v1/clearance/compartments/<id>`, `PUT /v1/clearance/compartments/<id>` | Proxy to `/v1/clearance/compartments/{id}` |
| 9.16 | Add | `GET /v1/clearance/matrix`, `PUT /v1/clearance/matrix` | Proxy to `/v1/clearance/matrix` |
| 9.17 | Add | `GET /v1/clearance/matrix/export` | Proxy to `/v1/clearance/matrix/export` |
| 9.18 | Add | `POST /v1/policy/decide` | Proxy to `/v1/policy/decide` |

### Phase 10: Control Routes (Workers/Incidents)
**Priority:** P2 | **File:** `ordl_fixed/app/blueprints/api.py`

| # | Action | Route | Backend Endpoint |
|---|--------|-------|------------------|
| 10.1 | Add | `GET /v1/workers`, `POST /v1/workers` | Proxy to `/v1/workers` |
| 10.2 | Add | `GET /v1/workers/<id>`, `PUT /v1/workers/<id>`, `DELETE /v1/workers/<id>` | Proxy to `/v1/workers/{id}` |
| 10.3 | Add | `GET /v1/workers/<id>/status`, `PUT /v1/workers/<id>/status` | Proxy to `/v1/workers/{id}/status` |
| 10.4 | Add | `GET /v1/incidents`, `POST /v1/incidents` | Proxy to `/v1/incidents` |
| 10.5 | Add | `GET /v1/incidents/<id>`, `PUT /v1/incidents/<id>` | Proxy to `/v1/incidents/{id}` |

---

## 4) OPEN QUESTIONS

### P0 - Blocking Implementation

| # | Question | Context | Resolution Required |
|---|----------|---------|---------------------|
| Q1 | **What is the backend base URL?** | Need `ORDL_BACKEND_URL` value for `backend_client.py` | Provide staging/production endpoint |
| Q2 | **Is `/v1/policy/decide` the correct auth endpoint?** | Change list references auth delegation but contract shows `/v1/policy/decide` | Confirm auth delegation approach |
| Q3 | **Are all 47 contract routes deployed?** | Contract shows "implemented" status but need runtime verification | Test against actual backend |
| Q4 | **Does backend have staging environment?** | Required for integration testing | Provide staging URL or confirm prod testing OK |

### P1 - High Priority

| # | Question | Context | Resolution Required |
|---|----------|---------|---------------------|
| Q5 | **JWT issuer/audience values?** | Required for token validation in `backend_client.py` | Document JWT metadata |
| Q6 | **JWKS endpoint URL?** | For key rotation support | Provide URL or confirm static secret |
| Q7 | **Token expiry duration?** | For refresh strategy | Document access/refresh token lifetimes |
| Q8 | **Backend rate limits?** | For retry/backoff configuration | Document rate limit headers |
| Q9 | **Max batch size for extensions?** | Current code limits to 100 items | Confirm backend limit |

### P2 - Medium Priority

| # | Question | Context | Resolution Required |
|---|----------|---------|---------------------|
| Q10 | **Does `app/services/` directory structure work?** | Current repo only has `app/blueprints/` | Confirm directory creation OK |
| Q11 | **Backend timeout expectations?** | Default 30s vs longer for batch ops | Confirm timeout values |
| Q12 | **How are file uploads handled?** | Evidence packages may be large | Confirm streaming vs redirect approach |
| Q13 | **Backend availability SLA?** | For circuit breaker configuration | Document uptime commitment |

---

## Appendix A: Route Implementation Matrix

| Route | Method | Current | Target | Priority |
|-------|--------|---------|--------|----------|
| `/v1/health` | GET | Static mock | Proxy | P0 |
| `/v1/health/ready` | GET | Missing | Proxy | P0 |
| `/v1/health/live` | GET | Missing | Proxy | P0 |
| `/v1/orgs` | GET | Static mock | Proxy | P0 |
| `/v1/orgs` | POST | Missing | Proxy | P1 |
| `/v1/orgs/{id}` | GET | In-memory | Proxy | P0 |
| `/v1/orgs/{id}` | PUT | In-memory | Proxy | P0 |
| `/v1/orgs/{id}` | DELETE | Missing | Proxy | P1 |
| `/v1/orgs/{id}/members` | GET | Missing | Proxy | P2 |
| `/v1/orgs/{id}/members` | POST | In-memory | Proxy | P0 |
| `/v1/orgs/{id}/defaults` | GET | Missing | Proxy | P2 |
| `/v1/orgs/{id}/defaults` | PUT | In-memory | Proxy | P0 |
| `/v1/orgs/{id}/regions` | GET | Missing | Proxy | P2 |
| `/v1/orgs/{id}/regions` | POST | In-memory | Proxy | P0 |
| `/v1/providers` | GET | Static mock | Proxy | P1 |
| `/v1/providers` | POST | Missing | Proxy | P1 |
| `/v1/providers/{id}` | GET | Missing | Proxy | P1 |
| `/v1/providers/{id}` | PUT | Missing | Proxy | P1 |
| `/v1/providers/{id}` | DELETE | Missing | Proxy | P1 |
| `/v1/providers/{id}/test` | POST | Simulated | Proxy | P0 |
| `/v1/providers/{id}/config` | PUT | In-memory | Proxy | P0 |
| `/v1/providers/priority` | PUT | Missing | Proxy | P2 |
| `/v1/providers/probes` | GET/PUT | Missing | Proxy | P2 |
| `/v1/extensions` | GET | Static mock | Proxy | P1 |
| `/v1/extensions` | POST | Missing | Proxy | P2 |
| `/v1/extensions/{id}` | GET/PUT/DELETE | Missing | Proxy | P2 |
| `/v1/extensions/verify` | POST | Simulated | Proxy | P1 |
| `/v1/extensions/batch` | POST | In-memory | Proxy | P1 |
| `/v1/audit/events` | GET | Static mock | Proxy | P1 |
| `/v1/audit/export` | GET | Static mock | Proxy | P1 |
| `/v1/audit/evidence` | POST | In-memory | Proxy | P0 |
| `/v1/teams/*` | ALL | Missing | Proxy | P2 |
| `/v1/projects/*` | ALL | Missing | Proxy | P2 |
| `/v1/seats/*` | ALL | Missing | Proxy | P2 |
| `/v1/clearance/*` | ALL | Missing | Proxy | P2 |
| `/v1/policy/decide` | POST | Missing | Proxy | P2 |
| `/v1/workers/*` | ALL | Missing | Proxy | P2 |
| `/v1/incidents/*` | ALL | Static mock | Proxy | P1 |
| `/v1/messages/*` | ALL | Static mock | **REMOVE** | P1 |

---

**End of Implementation Plan**
