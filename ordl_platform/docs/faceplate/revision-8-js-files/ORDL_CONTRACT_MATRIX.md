# ORDL Frontend-to-Backend Contract Matrix
## Hardline Execution Order Analysis

**Date:** 2026-03-07  
**Source of Truth:** `/v1` backend routers in `/root/openclaw/kimi/downloads/`  
**Frontend Files:** `/root/.openclaw/workspace/static/js/`

---

## 1. CONTRACT MATRIX

### Governance Module

| Frontend Action | File | Backend Endpoint | Method | Payload Schema | Response Fields Used |
|----------------|------|------------------|--------|----------------|---------------------|
| **edit-tiers** | clearance.js | ❌ **NO ENDPOINT** | - | `{tier, name, level, description}` | N/A |
| **add-compartment** | clearance.js | ❌ **NO ENDPOINT** | - | `{name, code, description}` | N/A |
| **view-tier** | clearance.js | ❌ **NO ENDPOINT** | - | `tier_id` | N/A |
| **edit-tier** | clearance.js | ❌ **NO ENDPOINT** | - | `{tier_id, name, level}` | N/A |
| **edit-comp** | clearance.js | ❌ **NO ENDPOINT** | - | `{comp_id, name, code}` | N/A |
| **view-comp** | clearance.js | ❌ **NO ENDPOINT** | - | `comp_id` | N/A |
| **export-matrix** | clearance.js | ❌ **NO ENDPOINT** | - | `{format?}` | N/A |
| **edit-matrix** | clearance.js | ❌ **NO ENDPOINT** | - | `{matrix_data}` | N/A |
| **edit-profile** | orgs.js | ❌ **NO ENDPOINT** | - | `{org_id, name, description}` | N/A |
| **add-board-member** | orgs.js | ❌ **NO ENDPOINT** | - | `{org_id, user_id, role}` | N/A |
| **edit-defaults** | orgs.js | ❌ **NO ENDPOINT** | - | `{org_id, default_settings}` | N/A |
| **add-region** | orgs.js | ❌ **NO ENDPOINT** | - | `{org_id, region_code, name}` | N/A |
| **run-simulation** | policy.js | ✅ `POST /v1/policy/decide` | POST | `PolicyDecideRequest` | `decision, reason_codes, request_hash, policy_token` |
| **create-project** | projects.js | ✅ `POST /v1/projects` | POST | `ProjectCreate` | `id, team_id, code, name, ingress_mode, visibility_mode` |
| **edit-defaults** (project) | projects.js | ❌ **NO ENDPOINT** | - | `{project_id, defaults}` | N/A |
| **create-seat** | seats.js | ✅ `POST /v1/seats` | POST | `SeatCreate` | `id, project_id, user_id, role, rank, position, group_name, clearance_tier, compartments, status` |
| **bulk-assign** | seats.js | ❌ **NO ENDPOINT** | - | `{seats: [{user_id, role, ...}]}` | N/A |
| **edit-matrix** (seat) | seats.js | ❌ **NO ENDPOINT** | - | `{matrix_config}` | N/A |
| **edit-seat** | seats.js | ❌ **NO ENDPOINT** | - | `{seat_id, role, rank, ...}` | N/A |
| **assign-seat** | seats.js | ❌ **NO ENDPOINT** | - | `{seat_id, user_id}` | N/A |
| **create-team** | teams.js | ✅ `POST /v1/teams` | POST | `TeamCreate` | `id, org_id, name` |
| **edit-scope** | teams.js | ❌ **NO ENDPOINT** | - | `{team_id, scope_matrix}` | N/A |

### Security Module

| Frontend Action | File | Backend Endpoint | Method | Payload Schema | Response Fields Used |
|----------------|------|------------------|--------|----------------|---------------------|
| **create-evidence** | audit.js | ❌ **NO ENDPOINT** | - | `{event_ids, format, chain_verify}` | N/A |
| **new-export** | audit.js | ✅ `GET /v1/audit/export` | GET | Query: `project_id, format, limit, filters` | File stream (JSON/CSV) |
| **pagination** | audit.js | ✅ `GET /v1/audit/events` | GET | Query: `project_id, limit, offset, filters` | Events array |
| **register-extension** | extensions.js | ✅ `POST /v1/extensions` | POST | `ExtensionCreate` | `id, tenant_id, name, version, scopes, status` |
| **verify-all** | extensions.js | ❌ **NO ENDPOINT** | - | `{extension_ids[]}` | N/A |
| **batch operations** | extensions.js | ❌ **NO ENDPOINT** | - | `{operation, target_ids[]}` | N/A |
| **add-provider** | providers.js | ❌ **NO ENDPOINT** | - | `{name, type, config, priority}` | N/A |
| **save-priority** | providers.js | ❌ **NO ENDPOINT** | - | `{providers: [{id, priority}]}` | N/A |
| **edit-probes** | providers.js | ❌ **NO ENDPOINT** | - | `{probe_config}` | N/A |

---

## 2. BACKEND GAPS

### Critical Missing Endpoints (Governance)

| Frontend Action | Required Endpoint | Method | Priority |
|----------------|-------------------|--------|----------|
| edit-tiers | `GET/PUT /v1/clearance/tiers` | GET/PUT | HIGH |
| add-compartment | `POST /v1/clearance/compartments` | POST | HIGH |
| view-tier | `GET /v1/clearance/tiers/{tier_id}` | GET | MEDIUM |
| edit-tier | `PUT /v1/clearance/tiers/{tier_id}` | PUT | MEDIUM |
| edit-comp | `PUT /v1/clearance/compartments/{comp_id}` | PUT | MEDIUM |
| view-comp | `GET /v1/clearance/compartments/{comp_id}` | GET | LOW |
| export-matrix | `GET /v1/clearance/matrix/export` | GET | MEDIUM |
| edit-matrix | `PUT /v1/clearance/matrix` | PUT | HIGH |
| edit-profile | `GET/PUT /v1/orgs/{org_id}` | GET/PUT | HIGH |
| add-board-member | `POST /v1/orgs/{org_id}/members` | POST | HIGH |
| edit-defaults (org) | `PUT /v1/orgs/{org_id}/defaults` | PUT | MEDIUM |
| add-region | `POST /v1/orgs/{org_id}/regions` | POST | MEDIUM |
| edit-defaults (project) | `PUT /v1/projects/{project_id}/defaults` | PUT | MEDIUM |
| bulk-assign | `POST /v1/seats/bulk` | POST | HIGH |
| edit-matrix (seat) | `PUT /v1/seats/matrix` | PUT | MEDIUM |
| edit-seat | `PUT /v1/seats/{seat_id}` | PUT | HIGH |
| assign-seat | `POST /v1/seats/{seat_id}/assign` | POST | HIGH |
| vacate-seat | `POST /v1/seats/{seat_id}/vacate` | POST | HIGH |
| edit-scope | `PUT /v1/teams/{team_id}/scope` | PUT | MEDIUM |

### Critical Missing Endpoints (Security)

| Frontend Action | Required Endpoint | Method | Priority |
|----------------|-------------------|--------|----------|
| create-evidence | `POST /v1/audit/evidence` | POST | HIGH |
| verify-all | `POST /v1/extensions/verify` | POST | MEDIUM |
| batch operations | `POST /v1/extensions/batch` | POST | MEDIUM |
| add-provider | `POST /v1/providers` | POST | HIGH |
| save-priority | `PUT /v1/providers/priority` | PUT | MEDIUM |
| edit-probes | `PUT /v1/providers/probes` | PUT | MEDIUM |
| test-provider | `POST /v1/providers/{id}/test` | POST | LOW |
| configure-provider | `PUT /v1/providers/{id}/config` | PUT | LOW |

---

## 3. RECOMMENDATIONS

### Immediate Implementation (HIGH Priority)

```python
# 1. Clearance Tier Management
@router.get('/v1/clearance/tiers')
@router.put('/v1/clearance/tiers')
@router.post('/v1/clearance/compartments')

# 2. Organization Profile & Members
@router.get('/v1/orgs/{org_id}')
@router.put('/v1/orgs/{org_id}')
@router.post('/v1/orgs/{org_id}/members')
@router.put('/v1/orgs/{org_id}/defaults')

# 3. Seat Management (CRUD)
@router.put('/v1/seats/{seat_id}')
@router.post('/v1/seats/{seat_id}/assign')
@router.post('/v1/seats/{seat_id}/vacate')
@router.post('/v1/seats/bulk')

# 4. Evidence Package Creation
@router.post('/v1/audit/evidence')

# 5. Provider Management
@router.post('/v1/providers')
```

### Schema Definitions Needed

```python
# Clearance Schemas
class ClearanceTier(BaseModel):
    id: str
    name: str
    level: int
    description: str
    compartments: list[str]

class Compartment(BaseModel):
    id: str
    code: str
    name: str
    description: str

# Org Member Schema
class OrgMemberCreate(BaseModel):
    user_id: str
    role: str  # board_member, observer, etc.
    permissions: list[str]

# Seat Update Schema
class SeatUpdate(BaseModel):
    role: str | None = None
    rank: str | None = None
    position: str | None = None
    group_name: str | None = None
    clearance_tier: str | None = None
    compartments: list[str] | None = None
    status: str | None = None

# Evidence Schema
class EvidenceCreate(BaseModel):
    event_ids: list[str]
    format: str  # 'json', 'pdf', 'chain'
    include_chain_verification: bool = True
    description: str | None = None
```

---

## 4. SUMMARY

### Coverage Statistics
- **Total Frontend TODOs:** 31 actions
- **Mapped to Backend:** 5 actions (16%)
- **Backend Gaps:** 26 actions (84%)
- **CRITICAL Gaps:** 11 actions

### Existing Backend Coverage
The backend provides solid foundations for:
- ✅ Policy decisions (`/v1/policy/decide`)
- ✅ Basic CRUD for Orgs, Teams, Projects, Seats (CREATE/LIST only)
- ✅ Audit event streaming and export
- ✅ Extension registration and status
- ✅ Worker management (extensive)

### Frontend-Backend Alignment
The frontend anticipates a **much richer governance model** than currently exists:
- Matrix-based clearance management (NTK - Need To Know)
- Compartment hierarchies
- Board member management
- Region support
- Provider failover chains
- Evidence packaging with chain verification

---

## 5. RISKS

| Risk | Impact | Mitigation |
|------|--------|------------|
| **84% of frontend actions have no backend** | HIGH | Prioritize HIGH priority gaps first |
| **Seat management incomplete** | CRITICAL | Implement PUT/assign/vacate immediately |
| **No org profile management** | HIGH | Add org GET/PUT endpoints |
| **Evidence packages not supported** | MEDIUM | Implies legal/compliance gap |
| **Extension batch ops missing** | LOW | Can work around with individual calls |
| **Provider management missing** | MEDIUM | Security feature gap |

---

## 6. ACTION LIST

### Phase 1: Critical Governance (Week 1)
1. Implement `PUT /v1/seats/{seat_id}` for seat editing
2. Implement `POST /v1/seats/{seat_id}/assign` for seat assignment
3. Implement `POST /v1/seats/{seat_id}/vacate` for seat vacating
4. Implement `POST /v1/seats/bulk` for bulk operations
5. Implement `GET/PUT /v1/orgs/{org_id}` for profile management

### Phase 2: Clearance System (Week 2)
6. Implement `GET/PUT /v1/clearance/tiers`
7. Implement `POST/GET /v1/clearance/compartments`
8. Implement `PUT /v1/clearance/matrix`
9. Implement `GET /v1/clearance/matrix/export`

### Phase 3: Security Features (Week 3)
10. Implement `POST /v1/audit/evidence`
11. Implement `POST /v1/providers`
12. Implement `PUT /v1/providers/priority`
13. Implement `POST /v1/extensions/verify` (bulk)

### Phase 4: Extended Features (Week 4)
14. Implement board member management
15. Implement region management
16. Implement provider probe configuration

---

## 7. OPEN QUESTIONS

1. **Clearance Matrix Format**: What is the exact schema for the NTK (Need To Know) matrix? Is it tier×compartment permissions?

2. **Board Member Permissions**: What roles/permissions should board members have? Is this already in the authz system?

3. **Evidence Chain Verification**: Should evidence packages include Merkle proofs? What's the chain verification requirement?

4. **Provider Failover**: Is there a provider model in the database? The frontend expects priority chains but no backend model exists.

5. **Region Support**: Are regions purely metadata or do they affect data residency/policy enforcement?

6. **Seat Matrix vs Clearance Matrix**: Are these the same concept or different? Frontend has both.

7. **Bulk Operation Limits**: What are the rate limits for bulk seat assignments?

8. **Extension Verification**: What does "verify" mean for extensions? Signature re-check? Runtime attestation?

---

**END CONTRACT MATRIX**
