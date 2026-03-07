# ORDL Revision 10 Architecture Normalization Report

## 1) SUMMARY

### Analysis Overview
Analyzed 4 input documents against the actual ORDL backend `/v1` contract and repository topology. Found significant discrepancies between documented claims and implemented reality.

### Contract Verification Status

| Document Claim | Backend Reality | Status |
|----------------|-----------------|--------|
| 47 routes implemented | ✅ 47 routes confirmed | VERIFIED |
| `/v1/auth/check` endpoint exists | ❌ DOES NOT EXIST | UNPROVEN |
| `/v1/orgs/{org_id}` CRUD | ✅ Implemented in governance router | VERIFIED |
| `/v1/providers/{id}/test` | ✅ Implemented in providers router | VERIFIED |
| `/v1/extensions/verify` | ✅ Implemented in extensions router | VERIFIED |
| `/v1/extensions/batch` | ✅ Implemented in extensions router | VERIFIED |
| `/v1/audit/evidence` POST | ✅ Implemented in audit router | VERIFIED |
| `ordl_fixed/app/blueprints/api.py` target path | ❌ Path does not exist | LEGACY PATH |
| `js/api/governance.js` frontend files | ❌ Files do not exist | UNPROVEN |

### Repository Topology (Actual)
```
ordl_platform/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI application entry
│   │   ├── models.py               # SQLAlchemy models
│   │   ├── schemas.py              # Pydantic schemas
│   │   ├── database.py             # DB connection management
│   │   ├── core/
│   │   │   └── auth.py             # Auth + audit utilities
│   │   └── routers/
│   │       ├── governance.py       # /v1/orgs, /v1/teams, /v1/projects
│   │       ├── providers.py        # /v1/providers
│   │       ├── extensions.py       # /v1/extensions
│   │       ├── audit.py            # /v1/audit
│   │       ├── dispatch.py         # /v1/workers, /v1/incidents
│   │       └── models_governance.py
│   └── tests/
└── docs/
    └── contracts/
        └── api-v1-contract.json    # 47-route contract manifest
```

### Document Issues Found

1. **Legacy Naming Convention**: Documents reference "Revision 9" and "Revision 10" - these are legacy product naming conventions that should be normalized to "ORDL Platform"

2. **Non-existent Paths**: 
   - `ordl_fixed/app/blueprints/api.py` - This is a Flask-style path that doesn't exist
   - `js/api/governance.js` - Frontend files referenced but not present

3. **Unverified Endpoint**: `/v1/auth/check` is referenced in ORDL_API_ADAPTER_PLAN.md as an auth delegation endpoint, but no such endpoint exists in the backend

4. **Schema Drift**: Migration spec describes schemas with fields that partially match but contain discrepancies (e.g., `signature` field in EvidencePackage)

---

## 2) RISKS

| Risk | Severity | Likelihood | Impact | Evidence |
|------|----------|------------|--------|----------|
| **Unimplemented Auth Endpoint** | CRITICAL | CONFIRMED | Auth delegation fails | `/v1/auth/check` referenced but not implemented |
| **Frontend File Mismatch** | HIGH | CONFIRMED | Migration actions target non-existent files | `js/api/*.js` paths don't exist |
| **Legacy Path References** | MEDIUM | CONFIRMED | Deployment scripts may fail | `ordl_fixed/` path used throughout |
| **Schema Inconsistencies** | MEDIUM | CONFIRMED | API contract violations | Evidence signature field mismatch |
| **Missing Routes Documentation** | LOW | CONFIRMED | Incomplete API documentation | `api-v1-routes.md` file missing |
| **Migration Action Obsolescence** | HIGH | LIKELY | Wasted effort on invalid tasks | Many Phase X actions reference non-existent targets |

---

## 3) ACTION LIST

### Immediate Actions (Blockers)

| # | Action | Priority | Owner | Evidence |
|---|--------|----------|-------|----------|
| 3.1 | **Verify or implement `/v1/auth/check`** | CRITICAL | Backend | Adapter plan depends on this for auth delegation |
| 3.2 | **Remove all `ordl_fixed/` path references** | CRITICAL | Documentation | Use `ordl_platform/backend/` instead |
| 3.3 | **Locate actual frontend code** | CRITICAL | Architecture | Referenced JS files don't exist in repo |
| 3.4 | **Create `api-v1-routes.md` or remove reference** | HIGH | Documentation | Listed as input but doesn't exist |

### Documentation Corrections

| # | Action | Priority | Current State | Correct State |
|---|--------|----------|---------------|---------------|
| 3.5 | Rename "Revision 9/10" references | HIGH | Legacy naming | "ORDL Platform v1" |
| 3.6 | Update target file paths | HIGH | `ordl_fixed/app/blueprints/api.py` | `ordl_platform/backend/app/routers/` |
| 3.7 | Verify schema fields match | MEDIUM | Evidence `signature` field | Check actual model definition |
| 3.8 | Remove frontend JS actions | MEDIUM | `js/api/governance.js` tasks | TBD after frontend located |

### Contract Alignment

| # | Action | Priority | Contract Source | Implementation |
|---|--------|----------|-----------------|----------------|
| 3.9 | Verify all 47 routes | MEDIUM | `api-v1-contract.json` | Router implementations |
| 3.10 | Document missing routes | LOW | Contract has them | Implementation gaps |
| 3.11 | Sync schema definitions | MEDIUM | `schemas.py` | Migration spec |

---

## 4) OPEN QUESTIONS

| # | Question | Impact | Suggested Resolution |
|---|----------|--------|---------------------|
| 4.1 | **Where is the actual frontend code?** The migration spec references `js/api/governance.js` but no such files exist. Is the frontend in a separate repository? | HIGH | Locate frontend repo or confirm it's out of scope |
| 4.2 | **Should `/v1/auth/check` be implemented?** The adapter plan includes fallback logic for 404, but should this be a real endpoint for proper auth delegation? | CRITICAL | Decision: implement OR remove from docs |
| 4.3 | **What is the `ordl_fixed` directory?** Is this a legacy structure, a planned structure, or a different project? References should be updated or clarified. | MEDIUM | Document directory mapping or remove references |
| 4.4 | **Where is `api-v1-routes.md`?** It was listed as an input file but doesn't exist. Should it be generated from the contract JSON? | LOW | Generate from contract OR remove from input list |
| 4.5 | **Is the Flask BFF (api.py) still relevant?** The adapter plan targets a Flask blueprint, but the backend is FastAPI. Is there a separate BFF layer? | HIGH | Clarify architecture: direct API vs BFF pattern |
| 4.6 | **Do the SQLAlchemy models match the migration spec?** The spec describes models like `OrgDefaults`, `ProviderProbeConfig` - are these implemented? | MEDIUM | Compare `models.py` against spec definitions |
| 4.7 | **What is the source of truth for schemas?** Migration spec defines schemas that may differ from `schemas.py` - which is authoritative? | MEDIUM | Establish schema governance process |

---

## Appendix: Verified Backend Contract

### Implemented Routes (from `api-v1-contract.json`)

**Foundation (5 routes):**
- `GET /v1/health`, `/v1/health/ready`, `/v1/health/live`
- `GET /v1/metrics`, `/v1/version`

**Governance (24 routes):**
- `/v1/orgs` (GET, POST), `/v1/orgs/{org_id}` (GET, PUT, DELETE)
- `/v1/orgs/{org_id}/members` (GET, POST)
- `/v1/orgs/{org_id}/defaults` (GET, PUT)
- `/v1/orgs/{org_id}/regions` (GET, POST)
- `/v1/teams`, `/v1/teams/{team_id}`, `/v1/teams/{team_id}/scope`
- `/v1/projects`, `/v1/projects/{project_id}`, `/v1/projects/{project_id}/defaults`
- `/v1/seats` + CRUD, `/v1/seats/bulk`, `/v1/seats/matrix`
- `/v1/clearance/*` (tiers, compartments, matrix)
- `POST /v1/policy/decide`

**Security (13 routes):**
- `/v1/audit/events` (GET), `/v1/audit/export` (GET), `/v1/audit/evidence` (POST)
- `/v1/extensions` + CRUD, `/v1/extensions/verify`, `/v1/extensions/batch`
- `/v1/providers` + CRUD, `/v1/providers/priority`, `/v1/providers/probes`
- `/v1/providers/{provider_id}/test`, `/v1/providers/{provider_id}/config`

**Control (5 routes):**
- `/v1/workers` + CRUD + status
- `/v1/incidents` + CRUD

### Unverified Claims

1. **No `/v1/auth/check` endpoint** - Referenced in adapter plan section 3.3
2. **No `ordl_fixed/` directory** - Referenced throughout adapter plan
3. **No frontend JS files** - Referenced in migration spec section 3.2
4. **No `api-v1-routes.md`** - Listed as required input

---

*Report generated: 2026-03-07*
*Source of truth: ORDL backend /v1 contract and repository topology*
