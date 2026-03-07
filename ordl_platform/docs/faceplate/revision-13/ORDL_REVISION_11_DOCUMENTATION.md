# ORDL Revision 11 Documentation

**Date:** 2026-03-07  
**Source of Truth:** Current ORDL repository (`ordl_platform/`, `ordl_fixed/`, `static/js/api/`)

---

## 1) SUMMARY

### Analysis Overview
Rewrote Revision 11 documentation to align with actual repository state. Previous revisions contained significant discrepancies between documented claims and implemented reality.

### Key Corrections from Previous Revisions

| Previous Claim | Current Reality | Correction |
|----------------|-----------------|------------|
| 47 routes implemented | **51 HTTP routes + 1 WebSocket** | Updated route inventory; contract undercounted |
| `/v1/metrics` exists | **DOES NOT EXIST** | Removed from foundation routes |
| `/v1/policy/decide` exists | **DOES NOT EXIST** | Actual endpoint is `/v1/models/policy/evaluate` |
| `/v1/workers/*` routes | **NOT IMPLEMENTED** | Worker routes are under `/v1/dispatch/workers/*` |
| `/v1/incidents/*` routes | **NOT IMPLEMENTED** | No incident routes exist |
| Teams, projects, seats, clearance routes | **NOT IMPLEMENTED** | Removed 17 claimed routes from governance |
| `api-v1-routes.md` exists | **DOES NOT EXIST** | Removed from input file list |
| `ordl_fixed/` path does not exist | **EXISTS** | Path verified: contains Flask blueprints |
| `js/api/*.js` files don't exist | **EXIST** | Located at `static/js/api/` |

### Actual Repository Topology

```
ordl_platform/                    # FastAPI backend (source of truth)
├── backend/
│   ├── app/
│   │   ├── main.py               # Health, version endpoints
│   │   ├── models.py             # SQLAlchemy models
│   │   ├── schemas.py            # Pydantic schemas
│   │   ├── database.py           # DB connection
│   │   ├── core/auth.py          # Auth + audit utilities
│   │   └── routers/
│   │       ├── governance.py     # /v1/orgs/* (7 routes)
│   │       ├── providers.py      # /v1/providers/* (9 routes)
│   │       ├── extensions.py     # /v1/extensions/* (7 routes)
│   │       ├── audit.py          # /v1/audit/* (6 routes)
│   │       ├── dispatch.py       # /v1/dispatch/* (10 HTTP + 1 WS)
│   │       └── models_governance.py  # /v1/models/* (8 routes)
│   └── tests/
└── docs/
    └── contracts/
        └── api-v1-contract.json  # PARTIALLY INACCURATE (see Section 4)

ordl_fixed/                       # Flask BFF (legacy/adapter layer)
├── app/
│   ├── blueprints/
│   │   ├── api.py                # Referenced in Rev10 docs
│   │   ├── governance.py
│   │   ├── security.py
│   │   ├── control.py
│   │   └── ...
│   ├── static/
│   └── templates/

static/js/api/                    # Frontend API clients
├── governance.js                 # Referenced in docs
├── security.js
├── audit.js
├── models.js
├── fleet.js
├── deployments.js
├── messages.js
└── client.js
```

### Verified Route Inventory (51 HTTP + 1 WebSocket)

#### Foundation (4 routes) - main.py
| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/health` | ✅ Implemented |
| GET | `/v1/health/ready` | ✅ Implemented |
| GET | `/v1/health/live` | ✅ Implemented |
| GET | `/v1/version` | ✅ Implemented |
| GET | `/v1/metrics` | ❌ **NOT IMPLEMENTED** |

#### Governance (7 routes) - governance.py
| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/orgs` | ✅ Implemented |
| POST | `/v1/orgs` | ✅ Implemented |
| GET | `/v1/orgs/{org_id}` | ✅ Implemented |
| PUT | `/v1/orgs/{org_id}` | ✅ Implemented |
| PUT | `/v1/orgs/{org_id}/defaults` | ✅ Implemented |
| POST | `/v1/orgs/{org_id}/members` | ✅ Implemented |
| POST | `/v1/orgs/{org_id}/regions` | ✅ Implemented |
| DELETE | `/v1/orgs/{org_id}` | ❌ **NOT IMPLEMENTED** |
| GET | `/v1/orgs/{org_id}/members` | ❌ **NOT IMPLEMENTED** |
| GET | `/v1/orgs/{org_id}/defaults` | ❌ **NOT IMPLEMENTED** |
| GET | `/v1/orgs/{org_id}/regions` | ❌ **NOT IMPLEMENTED** |
| GET | `/v1/teams` | ❌ **NOT IMPLEMENTED** |
| GET | `/v1/projects` | ❌ **NOT IMPLEMENTED** |
| GET | `/v1/seats` | ❌ **NOT IMPLEMENTED** |
| GET | `/v1/clearance/tiers` | ❌ **NOT IMPLEMENTED** |
| GET | `/v1/clearance/compartments` | ❌ **NOT IMPLEMENTED** |
| GET | `/v1/clearance/matrix` | ❌ **NOT IMPLEMENTED** |

#### Security - Providers (9 routes) - providers.py
| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/providers` | ✅ Implemented |
| POST | `/v1/providers` | ✅ Implemented |
| GET | `/v1/providers/{provider_id}` | ✅ Implemented |
| PUT | `/v1/providers/{provider_id}` | ✅ Implemented |
| DELETE | `/v1/providers/{provider_id}` | ✅ Implemented |
| POST | `/v1/providers/{provider_id}/test` | ✅ Implemented |
| PUT | `/v1/providers/{provider_id}/config` | ✅ Implemented |
| PUT | `/v1/providers/priority` | ✅ Implemented |
| PUT | `/v1/providers/probes` | ✅ Implemented |

#### Security - Extensions (7 routes) - extensions.py
| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/extensions` | ✅ Implemented |
| POST | `/v1/extensions` | ✅ Implemented |
| GET | `/v1/extensions/{ext_id}` | ✅ Implemented |
| PUT | `/v1/extensions/{ext_id}` | ✅ Implemented |
| DELETE | `/v1/extensions/{ext_id}` | ✅ Implemented |
| POST | `/v1/extensions/verify` | ✅ Implemented |
| POST | `/v1/extensions/batch` | ✅ Implemented |

#### Security - Audit (6 routes) - audit.py
| Method | Path | Status |
|--------|------|--------|
| GET | `/v1/audit/events` | ✅ Implemented |
| GET | `/v1/audit/export` | ✅ Implemented |
| POST | `/v1/audit/evidence` | ✅ Implemented |
| GET | `/v1/audit/evidence/{evidence_id}` | ✅ Implemented |
| GET | `/v1/audit/evidence/{evidence_id}/chain` | ✅ Implemented |
| GET | `/v1/audit/evidence/{evidence_id}/download` | ✅ Implemented |

#### Models Governance (8 routes) - models_governance.py
**Note:** These routes are NOT in the api-v1-contract.json

| Method | Path | Status |
|--------|------|--------|
| POST | `/v1/models/policy/evaluate` | ✅ Implemented |
| POST | `/v1/models/policy` | ✅ Implemented |
| GET | `/v1/models/policy/{model_id}/{org_id}` | ✅ Implemented |
| PUT | `/v1/models/policy/{model_id}/{org_id}` | ✅ Implemented |
| POST | `/v1/models/policy/validate-fail-closed` | ✅ Implemented |
| POST | `/v1/models/policy/emergency-deny` | ✅ Implemented |
| GET | `/v1/models/policy/token/{token}/validate` | ✅ Implemented |
| GET | `/v1/models/access-logs` | ✅ Implemented |

#### Control - Dispatch (10 HTTP + 1 WebSocket) - dispatch.py
**Note:** Routes are under `/v1/dispatch/` prefix, NOT `/v1/workers/` or `/v1/incidents/`

| Method | Path | Status |
|--------|------|--------|
| POST | `/v1/dispatch/workers/register` | ✅ Implemented |
| POST | `/v1/dispatch/workers/{worker_id}/keepalive` | ✅ Implemented |
| POST | `/v1/dispatch/workers/{worker_id}/reconnect` | ✅ Implemented |
| POST | `/v1/dispatch/workers/{worker_id}/restart` | ✅ Implemented |
| GET | `/v1/dispatch/workers/{worker_id}/recovery` | ✅ Implemented |
| POST | `/v1/dispatch/gateway/failover` | ✅ Implemented |
| POST | `/v1/dispatch/tasks/dispatch` | ✅ Implemented |
| GET | `/v1/dispatch/workers` | ✅ Implemented |
| GET | `/v1/dispatch/gateways` | ✅ Implemented |
| POST | `/v1/dispatch/workers/check-timeouts` | ✅ Implemented |
| WS | `/v1/dispatch/ws/workers/{worker_id}` | ✅ Implemented |
| GET | `/v1/workers` | ❌ **NOT IMPLEMENTED** (contract claims exists) |
| GET | `/v1/workers/{worker_id}` | ❌ **NOT IMPLEMENTED** (contract claims exists) |
| PUT | `/v1/workers/{worker_id}` | ❌ **NOT IMPLEMENTED** (contract claims exists) |
| DELETE | `/v1/workers/{worker_id}` | ❌ **NOT IMPLEMENTED** (contract claims exists) |
| GET | `/v1/workers/{worker_id}/status` | ❌ **NOT IMPLEMENTED** (contract claims exists) |
| PUT | `/v1/workers/{worker_id}/status` | ❌ **NOT IMPLEMENTED** (contract claims exists) |
| GET | `/v1/incidents` | ❌ **NOT IMPLEMENTED** (contract claims exists) |
| POST | `/v1/incidents` | ❌ **NOT IMPLEMENTED** (contract claims exists) |
| GET | `/v1/incidents/{incident_id}` | ❌ **NOT IMPLEMENTED** (contract claims exists) |
| PUT | `/v1/incidents/{incident_id}` | ❌ **NOT IMPLEMENTED** (contract claims exists) |

---

## 2) RISKS

| Risk | Severity | Likelihood | Impact | Evidence |
|------|----------|------------|--------|----------|
| **Contract-Implementation Drift** | CRITICAL | CONFIRMED | API consumers using wrong endpoints | 17 governance routes claimed but missing; worker/incident paths wrong |
| **Missing Metrics Endpoint** | HIGH | CONFIRMED | Monitoring/observability gap | `/v1/metrics` referenced in docs but not implemented |
| **Policy Endpoint Mismatch** | HIGH | CONFIRMED | Authorization failures | Docs reference `/v1/policy/decide`; actual is `/v1/models/policy/evaluate` |
| **Stale Documentation Referenced** | MEDIUM | CONFIRMED | Developers working from incorrect specs | `api-v1-routes.md` listed as input but doesn't exist |
| **Path Prefix Confusion** | MEDIUM | CONFIRMED | Routing errors in client code | Workers under `/v1/dispatch/` not `/v1/workers/` |
| **Undocumented Routes** | MEDIUM | CONFIRMED | Security audit gaps | 8 models governance routes not in contract |
| **Dual Codebase Maintenance** | MEDIUM | LIKELY | Divergence between Flask and FastAPI | Both `ordl_fixed/` and `ordl_platform/` exist and are active |

---

## 3) ACTION LIST

### Immediate Actions (Blockers)

| # | Action | Priority | Owner | Evidence |
|---|--------|----------|-------|----------|
| 3.1 | **Update api-v1-contract.json** to reflect actual routes | CRITICAL | Backend | Contract claims 47 routes; actual is 51+ |
| 3.2 | **Remove `/v1/metrics` from contract** or implement it | CRITICAL | Backend | Endpoint does not exist |
| 3.3 | **Update worker route paths** in contract to `/v1/dispatch/workers/*` | CRITICAL | Backend | Current paths are misleading |
| 3.4 | **Remove incident routes** from contract or implement them | CRITICAL | Backend | No incident routes exist |
| 3.5 | **Add models governance routes** to contract (8 routes) | HIGH | Backend | Currently undocumented |
| 3.6 | **Update policy endpoint** references from `/v1/policy/decide` to `/v1/models/policy/evaluate` | HIGH | Documentation | Endpoint path changed |
| 3.7 | **Generate api-v1-routes.md** from actual code or remove reference | MEDIUM | Documentation | Listed as input but doesn't exist |
| 3.8 | **Clarify ordl_fixed vs ordl_platform** relationship | MEDIUM | Architecture | Both directories exist; roles unclear |

### Documentation Corrections

| # | Action | Current State | Correct State |
|---|--------|---------------|---------------|
| 3.9 | Fix route count claims | "47 routes" | "51 HTTP routes + 1 WebSocket" |
| 3.10 | Fix foundation route count | "5 routes" | "4 routes (/v1/metrics missing)" |
| 3.11 | Fix governance route count | "24 routes" | "7 routes (17 missing)" |
| 3.12 | Fix control route count | "5 routes" | "10 HTTP + 1 WS under /v1/dispatch/" |
| 3.13 | Update file path references | `ordl_fixed/app/blueprints/api.py` | Clarify Flask vs FastAPI structure |
| 3.14 | Fix js/api path references | Claimed missing | `static/js/api/*.js` exists |

### Contract Alignment

| # | Action | Contract Claim | Implementation |
|---|--------|----------------|----------------|
| 3.15 | Remove unimplemented teams routes | 5 routes | 0 implemented |
| 3.16 | Remove unimplemented projects routes | 5 routes | 0 implemented |
| 3.17 | Remove unimplemented seats routes | 9 routes | 0 implemented |
| 3.18 | Remove unimplemented clearance routes | 5 routes | 0 implemented |
| 3.19 | Remove unimplemented incident routes | 5 routes | 0 implemented |
| 3.20 | Fix worker route prefixes | `/v1/workers/*` | `/v1/dispatch/workers/*` |

---

## 4) OPEN QUESTIONS

| # | Question | Impact | Suggested Resolution |
|---|----------|--------|---------------------|
| 4.1 | **Should `/v1/metrics` be implemented?** It's in the contract but not the code. Prometheus/OpenMetrics compatibility needed? | MEDIUM | Decision: implement OR remove from contract |
| 4.2 | **What is the relationship between `ordl_fixed/` and `ordl_platform/`?** Both have active code. Is `ordl_fixed` the Flask BFF and `ordl_platform` the backend? | HIGH | Document architecture decision; clarify migration status |
| 4.3 | **Should the 17 missing governance routes be implemented?** (teams, projects, seats, clearance) | HIGH | Decision: implement missing routes OR update contract |
| 4.4 | **Should incident routes be implemented?** Contract claims 5 routes but none exist. | MEDIUM | Decision: implement OR remove from contract |
| 4.5 | **Should worker routes be moved from `/v1/dispatch/` to `/v1/workers/`?** Contract expects latter. | MEDIUM | Decision: update contract OR refactor code |
| 4.6 | **Is the policy endpoint at `/v1/policy/decide` or `/v1/models/policy/evaluate`?** Both referenced. | HIGH | Standardize on one path; update all docs |
| 4.7 | **Should `api-v1-routes.md` be generated?** It was listed as input but never created. | LOW | Generate from code OR remove from file list |
| 4.8 | **Are the 8 models governance routes intentionally omitted from the contract?** They exist in code but not contract. | MEDIUM | Add to contract OR document why excluded |

---

## Appendix A: Corrected Route Count Summary

| Module | Contract Claim | Actual Implemented | Discrepancy |
|--------|----------------|-------------------|-------------|
| Foundation | 5 | 4 | -1 (missing metrics) |
| Governance | 24 | 7 | -17 (teams, projects, seats, clearance) |
| Security - Providers | 9 | 9 | 0 ✅ |
| Security - Extensions | 7 | 7 | 0 ✅ |
| Security - Audit | 3 | 6 | +3 (bonus routes) |
| Security - Models Gov | 0 | 8 | +8 (not in contract) |
| Control - Workers | 5 | 10 | +5 (different paths) |
| Control - Incidents | 5 | 0 | -5 (not implemented) |
| **TOTAL HTTP** | **47** | **51** | **+4** |
| **WebSocket** | **0** | **1** | **+1** |

---

## Appendix B: Input File Status

| Input File | Previous Claim | Current Status | Action |
|------------|----------------|----------------|--------|
| `ORDL_REV10_IMPLEMENTATION_CHANGE_LIST.md` | Existed | ✅ Verified | Superseded by this document |
| `ORDL_REVISION_10_NORMALIZATION_REPORT.md` | Existed | ✅ Verified | Partially incorrect; see corrections above |
| `api-v1-contract.json` | Existed | ✅ Verified | **INACCURATE - requires update** |
| `api-v1-routes.md` | Claimed missing | ❌ **ACTUALLY MISSING** | Generate OR remove from requirements |

---

**End of Revision 11 Documentation**
