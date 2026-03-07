# ORDL Flask BFF Implementation Change List
## Revision 10 - Backend API Adapter

**Date:** 2026-03-07  
**Source:** Revision 9 Fixed App → ORDL Backend /v1 API  
**Target:** `ordl_fixed/app/blueprints/api.py`  

---

## 1) SUMMARY

### 1.1 Objective
Transform the Revision 9 Flask BFF from an in-memory mock implementation to a thin proxy layer that delegates all data operations to the ORDL backend `/v1` API.

### 1.2 Current State (Revision 9)
| Component | Implementation | Issues |
|-----------|----------------|--------|
| Data Layer | In-memory Python dicts (`orgs_db`, `providers_db`, `extensions_db`, `evidence_db`) | No persistence, data loss on restart |
| Authorization | Local `evaluate_authorization()` with hardcoded clearance matrix | No JWT validation, mock auth |
| Audit Logging | Local `log_audit_event()` with no persistence | Compliance gap |
| API Coverage | 12 custom routes + 15 static mock routes | Incomplete vs /v1 contract |

### 1.3 Target State (Revision 10)
| Component | Implementation | Benefits |
|-----------|----------------|----------|
| Data Layer | HTTP proxy to `/v1/*` backend endpoints | Persistent storage, data integrity |
| Authorization | JWT extraction + backend delegation | Real auth, policy engine integration |
| Audit Logging | `POST /v1/audit/events` | Persistent audit trail |
| API Coverage | Full `/v1` contract alignment (47 routes) | Complete API surface |

### 1.4 Backend Contract Alignment
The `/v1` API contract defines 47 routes across 4 modules:
- **Foundation:** 5 routes (health, metrics, version)
- **Governance:** 24 routes (orgs, teams, projects, seats, clearance, policy)
- **Security:** 13 routes (audit, extensions, providers)
- **Control:** 5 routes (workers, incidents)

**Current api.py implements:** ~27 routes (12 dynamic + 15 static mocks)  
**Missing for full compliance:** 20 routes (mostly CRUD variations)

---

## 2) RISKS

### 2.1 Critical Risks (P0 - Block Release)

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| **Backend connectivity failure cascade** | Frontend becomes unusable if backend is down | Medium | Implement circuit breaker pattern; graceful degradation with cached read-only data |
| **JWT secret/key mismatch** | Auth failures across all endpoints | Medium | Ensure JWKS endpoint alignment; implement key rotation handling |
| **API contract drift** | 500 errors due to schema mismatches | High | Add Pydantic request/response validation; contract tests in CI |
| **Audit event loss on network partition** | Compliance violations | Low | Implement persistent retry queue (Redis/SQLite); graceful degradation |
| **Provider secret exposure in logs** | API keys leaked | Medium | Sanitize all request/response logging; use Vault references only |

### 2.2 High Risks (P1 - Must Address)

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| **Performance degradation (network hop)** | 2x-3x latency increase vs in-memory | High | Implement Redis caching for read-heavy endpoints (orgs, providers list); connection pooling |
| **Batch operation timeout** | Large batch ops fail partially | Medium | Implement async job pattern for >100 items; progress polling |
| **Circular audit logging** | Audit routes calling audit causes infinite loop | Low | Exclude `/v1/audit/*` routes from audit decorator; explicit audit bypass flag |
| **Token expiration during multi-step flows** | User loses work on token expiry | Medium | Implement silent refresh with refresh tokens; redirect with state preservation |
| **Backend rate limiting (429)** | Throttling disrupts operations | Medium | Implement exponential backoff; queue and retry with jitter |

### 2.3 Medium Risks (P2 - Should Address)

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| **Memory leak in backend client session** | Long-running frontend instability | Low | Use connection pooling with max connections; session recycling |
| **Large evidence package handling** | Memory exhaustion on download | Medium | Stream response for large files; redirect to signed S3 URLs |
| **CORS misconfiguration** | Browser blocks API calls | Low | Explicit CORS allowlist; preflight handling |
| **Region routing errors** | GDPR/compliance violations | Low | Region-aware backend URL selection based on org context |

---

## 3) ACTION LIST

### Phase 1: Infrastructure - Backend Client Module
**Priority:** CRITICAL | **ETA:** Day 1-2 | **Owner:** Backend Team

| # | Action | File | Description |
|---|--------|------|-------------|
| 1.1 | Create backend client module | `app/services/backend_client.py` | HTTP client with JWT handling, retry logic, circuit breaker |
| 1.2 | Create audit service module | `app/services/audit_service.py` | Async audit logging with retry queue |
| 1.3 | Add dependencies | `requirements.txt` | `requests>=2.31.0`, `PyJWT>=2.8.0`, `tenacity>=8.0` |
| 1.4 | Create config module | `app/config/settings.py` | Backend URL, timeouts, feature flags from env |
| 1.5 | Environment template | `.env.example` | Document all required environment variables |

### Phase 2: Authorization Migration
**Priority:** CRITICAL | **ETA:** Day 2-3 | **Owner:** Security Team

| # | Action | File | Description |
|---|--------|------|-------------|
| 2.1 | Remove mock auth | `app/blueprints/api.py` | Delete `evaluate_authorization()` function (lines ~19-65) |
| 2.2 | Implement JWT decorator | `app/services/backend_client.py` | `require_jwt` decorator for token extraction |
| 2.3 | Implement backend auth | `app/blueprints/api.py` | `require_backend_auth()` delegating to backend policy engine |
| 2.4 | Add auth alias | `app/blueprints/api.py` | `require_auth = require_backend_auth` for compatibility |
| 2.5 | Remove clearance matrix | `app/blueprints/api.py` | Delete hardcoded `clearance_requirements` dict |

### Phase 3: Data Store Removal
**Priority:** CRITICAL | **ETA:** Day 3 | **Owner:** Backend Team

| # | Action | File | Description |
|---|--------|------|-------------|
| 3.1 | Delete orgs_db | `app/blueprints/api.py` | Remove `orgs_db` dict (lines ~113-145) |
| 3.2 | Delete providers_db | `app/blueprints/api.py` | Remove `providers_db` dict (lines ~146-175) |
| 3.3 | Delete extensions_db | `app/blueprints/api.py` | Remove `extensions_db` dict (lines ~176-185) |
| 3.4 | Delete evidence_db | `app/blueprints/api.py` | Remove `evidence_db` dict (line ~186) |
| 3.5 | Add import | `app/blueprints/api.py` | `from ..services.backend_client import get_backend_client` |

### Phase 4: Organization Routes Migration
**Priority:** CRITICAL | **ETA:** Day 3-4 | **Owner:** Backend Team

| # | Action | Route | Change |
|---|--------|-------|--------|
| 4.1 | Refactor GET org | `/v1/orgs/<org_id>` | Proxy to `GET /v1/orgs/{org_id}` backend |
| 4.2 | Refactor PUT org | `/v1/orgs/<org_id>` | Proxy to `PUT /v1/orgs/{org_id}` backend |
| 4.3 | Refactor PUT defaults | `/v1/orgs/<org_id>/defaults` | Proxy to `PUT /v1/orgs/{org_id}/defaults` backend |
| 4.4 | Refactor POST member | `/v1/orgs/<org_id>/members` | Proxy to `POST /v1/orgs/{org_id}/members` backend |
| 4.5 | Refactor POST region | `/v1/orgs/<org_id>/regions` | Proxy to `POST /v1/orgs/{org_id}/regions` backend |
| 4.6 | Add GET orgs list | `/v1/governance/orgs` | Proxy to `GET /v1/orgs` backend |
| 4.7 | Add DELETE org | `/v1/orgs/<org_id>` | Proxy to `DELETE /v1/orgs/{org_id}` backend |
| 4.8 | Add GET members | `/v1/orgs/<org_id>/members` | Proxy to `GET /v1/orgs/{org_id}/members` backend |
| 4.9 | Add GET defaults | `/v1/orgs/<org_id>/defaults` | Proxy to `GET /v1/orgs/{org_id}/defaults` backend |
| 4.10 | Add GET regions | `/v1/orgs/<org_id>/regions` | Proxy to `GET /v1/orgs/{org_id}/regions` backend |

### Phase 5: Provider Routes Migration
**Priority:** HIGH | **ETA:** Day 4-5 | **Owner:** Backend Team

| # | Action | Route | Change |
|---|--------|-------|--------|
| 5.1 | Refactor POST test | `/v1/providers/<id>/test` | Proxy to `POST /v1/providers/{id}/test` backend |
| 5.2 | Refactor PUT config | `/v1/providers/<id>/config` | Proxy to `PUT /v1/providers/{id}/config` backend |
| 5.3 | Add GET providers | `/v1/security/providers` | Proxy to `GET /v1/providers` backend |
| 5.4 | Add POST provider | `/v1/providers` | Proxy to `POST /v1/providers` backend |
| 5.5 | Add GET provider | `/v1/providers/<id>` | Proxy to `GET /v1/providers/{id}` backend |
| 5.6 | Add PUT provider | `/v1/providers/<id>` | Proxy to `PUT /v1/providers/{id}` backend |
| 5.7 | Add DELETE provider | `/v1/providers/<id>` | Proxy to `DELETE /v1/providers/{id}` backend |
| 5.8 | Add PUT priority | `/v1/providers/priority` | Proxy to `PUT /v1/providers/priority` backend |
| 5.9 | Add GET probes | `/v1/providers/probes` | Proxy to `GET /v1/providers/probes` backend |
| 5.10 | Add PUT probes | `/v1/providers/probes` | Proxy to `PUT /v1/providers/probes` backend |

### Phase 6: Extension Routes Migration
**Priority:** MEDIUM | **ETA:** Day 5 | **Owner:** Backend Team

| # | Action | Route | Change |
|---|--------|-------|--------|
| 6.1 | Refactor POST verify | `/v1/extensions/verify` | Proxy to `POST /v1/extensions/verify` backend |
| 6.2 | Refactor POST batch | `/v1/extensions/batch` | Proxy to `POST /v1/extensions/batch` backend |
| 6.3 | Add GET extensions | `/v1/security/extensions` | Proxy to `GET /v1/extensions` backend |
| 6.4 | Add POST extension | `/v1/extensions` | Proxy to `POST /v1/extensions` backend |
| 6.5 | Add GET extension | `/v1/extensions/<ext_id>` | Proxy to `GET /v1/extensions/{ext_id}` backend |
| 6.6 | Add PUT extension | `/v1/extensions/<ext_id>` | Proxy to `PUT /v1/extensions/{ext_id}` backend |
| 6.7 | Add DELETE extension | `/v1/extensions/<ext_id>` | Proxy to `DELETE /v1/extensions/{ext_id}` backend |

### Phase 7: Audit Routes Migration
**Priority:** HIGH | **ETA:** Day 5 | **Owner:** Backend Team

| # | Action | Route | Change |
|---|--------|-------|--------|
| 7.1 | Refactor POST evidence | `/v1/audit/evidence` | Proxy to `POST /v1/audit/evidence` backend (no local audit logging) |
| 7.2 | Add GET events | `/v1/audit/events` | Proxy to `GET /v1/audit/events` backend |
| 7.3 | Add GET export | `/v1/audit/export` | Proxy to `GET /v1/audit/export` backend |

### Phase 8: Static Routes - Proxy or Remove
**Priority:** MEDIUM | **ETA:** Day 6 | **Owner:** Frontend Team

| # | Action | Route | Decision |
|---|--------|-------|----------|
| 8.1 | Proxy fleet routes | `/v1/fleet/*` | Proxy to backend; return empty if 404 |
| 8.2 | Proxy models routes | `/v1/models/*` | Proxy to backend; return empty if 404 |
| 8.3 | Proxy deployments | `/v1/deployments/*` | Proxy to backend; return empty if 404 |
| 8.4 | Proxy nodes routes | `/v1/nodes/*` | Proxy to backend; return empty if 404 |
| 8.5 | Proxy health routes | `/v1/health/*` | Proxy to backend; critical for k8s |
| 8.6 | Proxy incidents | `/v1/incidents/*` | Proxy to backend; return empty if 404 |
| 8.7 | Proxy messages | `/v1/messages/*` | **REMOVE** - Not in /v1 contract |
| 8.8 | Governance static | `/v1/governance/*` | Consolidate to proxy pattern |

### Phase 9: New Governance Routes (From Contract)
**Priority:** MEDIUM | **ETA:** Day 6-7 | **Owner:** Backend Team

| # | Action | Route | Backend Endpoint |
|---|--------|-------|------------------|
| 9.1 | Add teams CRUD | `/v1/teams`, `/v1/teams/<id>` | Proxy to `/v1/teams/*` |
| 9.2 | Add team scope | `/v1/teams/<id>/scope` | Proxy to `/v1/teams/{id}/scope` |
| 9.3 | Add projects CRUD | `/v1/projects`, `/v1/projects/<id>` | Proxy to `/v1/projects/*` |
| 9.4 | Add project defaults | `/v1/projects/<id>/defaults` | Proxy to `/v1/projects/{id}/defaults` |
| 9.5 | Add seats CRUD | `/v1/seats`, `/v1/seats/<id>` | Proxy to `/v1/seats/*` |
| 9.6 | Add seat assign | `/v1/seats/<id>/assign` | Proxy to `/v1/seats/{id}/assign` |
| 9.7 | Add seat vacate | `/v1/seats/<id>/vacate` | Proxy to `/v1/seats/{id}/vacate` |
| 9.8 | Add seat bulk | `/v1/seats/bulk` | Proxy to `/v1/seats/bulk` |
| 9.9 | Add seat matrix | `/v1/seats/matrix` | Proxy to `/v1/seats/matrix` |
| 9.10 | Add clearance tiers | `/v1/clearance/tiers` | Proxy to `/v1/clearance/tiers` |
| 9.11 | Add compartments | `/v1/clearance/compartments` | Proxy to `/v1/clearance/compartments` |
| 9.12 | Add clearance matrix | `/v1/clearance/matrix` | Proxy to `/v1/clearance/matrix` |
| 9.13 | Add policy decide | `/v1/policy/decide` | Proxy to `/v1/policy/decide` |

### Phase 10: Testing & Validation
**Priority:** CRITICAL | **ETA:** Day 7-8 | **Owner:** QA Team

| # | Action | Type | Description |
|---|--------|------|-------------|
| 10.1 | Unit tests | `tests/test_backend_client.py` | Backend client retry, error handling |
| 10.2 | Unit tests | `tests/test_auth.py` | JWT extraction, decorator behavior |
| 10.3 | Integration tests | `tests/integration/test_org_routes.py` | Full org CRUD with backend |
| 10.4 | Integration tests | `tests/integration/test_provider_routes.py` | Provider test/config flows |
| 10.5 | Contract tests | `tests/contract/test_api_contract.py` | Pact verification vs /v1 |
| 10.6 | Auth tests | `tests/security/test_authorization.py` | 401/403 handling, role access |
| 10.7 | Load tests | `tests/load/test_batch_ops.py` | Batch operations under load |
| 10.8 | Chaos tests | `tests/chaos/test_backend_failure.py` | Backend downtime behavior |

### Phase 11: Deployment & Rollout
**Priority:** HIGH | **ETA:** Day 9-10 | **Owner:** DevOps Team

| # | Action | Description |
|---|--------|-------------|
| 11.1 | Environment setup | Configure `ORDL_BACKEND_URL` in all environments |
| 11.2 | Feature flags | Add `USE_BACKEND_API` flag for gradual rollout |
| 11.3 | Blue-green deploy | Deploy new version alongside old; traffic switch |
| 11.4 | Monitoring | Add alerts for backend connectivity errors |
| 11.5 | Rollback plan | Document quick rollback to Rev9 if needed |

---

## 4) OPEN QUESTIONS

### 4.1 Backend Endpoint Availability (P0 - Blocking)

| # | Question | Impact | Resolution Path |
|---|----------|--------|-----------------|
| Q1 | **Does `/v1/auth/check` exist?** The adapter plan references this for auth delegation, but it's not in the contract. | Auth implementation | Confirm with backend team; fallback to JWT-only validation if not available |
| Q2 | **Are all 47 routes in the contract actually deployed?** Contract shows "implemented" but need runtime verification. | Route availability | Run contract test suite against staging backend |
| Q3 | **What's the backend base URL pattern?** Single endpoint or region-specific routing? | Client configuration | Document service discovery approach |
| Q4 | **Does backend support batch operations natively?** Some routes may need frontend-side batching. | Batch performance | Confirm batch route availability |

### 4.2 Authentication & Authorization (P1 - High Priority)

| # | Question | Impact | Resolution Path |
|---|----------|--------|-----------------|
| Q5 | **What's the JWT issuer and audience?** Need for token validation. | Token verification | Document JWT metadata from auth service |
| Q6 | **Is there a JWKS endpoint for key rotation?** | Key management | Implement JWKS fetch if available |
| Q7 | **What's the token expiry and refresh strategy?** | UX flows | Document token lifetime; implement refresh |
| Q8 | **Does backend support role-based or attribute-based access control?** | Auth delegation | Clarify policy engine integration |
| Q9 | **Are clearance levels L1-L5 or custom per tenant?** | Auth logic | Confirm clearance schema |

### 4.3 Data & Performance (P2 - Medium Priority)

| # | Question | Impact | Resolution Path |
|---|----------|--------|-----------------|
| Q10 | **What's the expected QPS for org/provider lists?** | Caching strategy | Gather traffic estimates |
| Q11 | **Are there backend rate limits?** | Error handling | Document rate limit headers |
| Q12 | **What's the max batch size for extensions?** | Batch validation | Confirm limits vs current 100 |
| Q13 | **Does backend support pagination for large lists?** | List performance | Implement cursor/offset pagination |
| Q14 | **How are file uploads/downloads handled?** | Evidence packages | Confirm streaming vs redirect approach |

### 4.4 Operational (P2 - Medium Priority)

| # | Question | Impact | Resolution Path |
|---|----------|--------|-----------------|
| Q15 | **What's the SLA for backend availability?** | SLO definition | Document uptime commitment |
| Q16 | **Is there a webhook for async job completion?** | Batch UX | Implement polling vs webhook |
| Q17 | **How do we handle backend version upgrades?** | Forward compatibility | Document versioning policy |
| Q18 | **What's the audit log retention policy?** | Compliance | Align with backend retention |
| Q19 | **Is there a staging environment for integration testing?** | Testing | Confirm test environment availability |

### 4.5 Frontend Compatibility (P3 - Low Priority)

| # | Question | Impact | Resolution Path |
|---|----------|--------|-----------------|
| Q20 | **Does frontend need any schema changes for backend responses?** | UI compatibility | Test all routes with real backend data |
| Q21 | **Are there any field name changes in backend vs mock?** | Data mapping | Document schema diffs |
| Q22 | **Does frontend handle 202 Accepted for async operations?** | Async UX | Update UI for pending states |

---

## Appendix A: Route Mapping Matrix

| Route | Current | Backend | Status | Priority |
|-------|---------|---------|--------|----------|
| `GET /v1/orgs/{id}` | In-memory | `/v1/orgs/{id}` | ✅ | P0 |
| `PUT /v1/orgs/{id}` | In-memory | `/v1/orgs/{id}` | ✅ | P0 |
| `PUT /v1/orgs/{id}/defaults` | In-memory | `/v1/orgs/{id}/defaults` | ✅ | P0 |
| `POST /v1/orgs/{id}/members` | In-memory | `/v1/orgs/{id}/members` | ✅ | P0 |
| `POST /v1/orgs/{id}/regions` | In-memory | `/v1/orgs/{id}/regions` | ✅ | P0 |
| `POST /v1/providers/{id}/test` | Simulated | `/v1/providers/{id}/test` | ✅ | P0 |
| `PUT /v1/providers/{id}/config` | In-memory | `/v1/providers/{id}/config` | ✅ | P0 |
| `POST /v1/extensions/verify` | Simulated | `/v1/extensions/verify` | ✅ | P1 |
| `POST /v1/extensions/batch` | In-memory | `/v1/extensions/batch` | ✅ | P1 |
| `POST /v1/audit/evidence` | In-memory | `/v1/audit/evidence` | ✅ | P0 |
| `GET /v1/audit/events` | Static mock | `/v1/audit/events` | ✅ | P1 |
| `GET /v1/audit/export` | Static mock | `/v1/audit/export` | ✅ | P1 |
| `GET /v1/orgs` | Static mock | `/v1/orgs` | ✅ | P1 |
| `DELETE /v1/orgs/{id}` | Missing | `/v1/orgs/{id}` | ⚠️ New | P1 |
| `GET /v1/orgs/{id}/members` | Missing | `/v1/orgs/{id}/members` | ⚠️ New | P2 |
| `GET /v1/providers` | Static mock | `/v1/providers` | ✅ | P1 |
| `POST /v1/providers` | Missing | `/v1/providers` | ⚠️ New | P1 |
| `GET /v1/providers/{id}` | Missing | `/v1/providers/{id}` | ⚠️ New | P1 |
| `PUT /v1/providers/{id}` | Missing | `/v1/providers/{id}` | ⚠️ New | P1 |
| `DELETE /v1/providers/{id}` | Missing | `/v1/providers/{id}` | ⚠️ New | P1 |
| `PUT /v1/providers/priority` | Missing | `/v1/providers/priority` | ⚠️ New | P2 |
| `GET /v1/extensions` | Static mock | `/v1/extensions` | ✅ | P1 |
| `POST /v1/extensions` | Missing | `/v1/extensions` | ⚠️ New | P2 |
| `GET /v1/extensions/{id}` | Missing | `/v1/extensions/{id}` | ⚠️ New | P2 |
| `PUT /v1/extensions/{id}` | Missing | `/v1/extensions/{id}` | ⚠️ New | P2 |
| `DELETE /v1/extensions/{id}` | Missing | `/v1/extensions/{id}` | ⚠️ New | P2 |
| `GET /v1/teams` | Missing | `/v1/teams` | ⚠️ New | P2 |
| `GET /v1/projects` | Missing | `/v1/projects` | ⚠️ New | P2 |
| `GET /v1/seats` | Missing | `/v1/seats` | ⚠️ New | P2 |
| `GET /v1/clearance/tiers` | Missing | `/v1/clearance/tiers` | ⚠️ New | P3 |
| `GET /v1/policy/decide` | Missing | `/v1/policy/decide` | ⚠️ New | P3 |

---

## Appendix B: Code Size Estimate

| Component | Lines | Complexity |
|-----------|-------|------------|
| `backend_client.py` | ~180 | Medium |
| `audit_service.py` | ~90 | Low |
| `api.py` changes | ~400 modified, ~200 new | High |
| Tests | ~500 | Medium |
| **Total** | **~1400** | **Medium-High** |

---

**End of Change List**
