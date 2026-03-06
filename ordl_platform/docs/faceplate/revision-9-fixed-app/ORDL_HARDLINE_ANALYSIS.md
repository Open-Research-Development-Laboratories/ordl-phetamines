# ORDL HARDLINE EXECUTION ORDER - Contract Matrix Alignment Report

**Worker:** worker-arch-desktop  
**Date:** 2026-03-07  
**Status:** Contract coverage 27/37 routes. 10 routes pending implementation.

---

## SUMMARY

### Current State Analysis

| Module | Implemented | Pending | Coverage |
|--------|-------------|---------|----------|
| Governance (orgs) | 2/6 | 4 | 33% |
| Governance (seats) | 2/6 | 4 | 33% |
| Security (audit) | 3/4 | 1 | 75% |
| Security (extensions) | 3/4 | 2 | 75% |
| Security (providers) | 0/4 | 4 | 0% |

### Critical Finding: Mismatched Expectations
The frontend JS implementation assumes a **much richer API** than currently exists. The 10 pending endpoints represent **high-priority functionality** that is actively being called from the UI (with FIXME warnings currently displayed to users).

---

## ROUTE-BY-ROUTE ACCEPTANCE CHECKLIST

### 1. GET /v1/orgs/{org_id}

| Item | Status | Notes |
|------|--------|-------|
| Route exists | ❌ MISSING | Only `GET /orgs` (list) exists |
| Path parameter validation | ❌ | Requires `org_id: str` validation |
| Tenant scope check | ⚠️ | Pattern exists in `list_orgs` - needs reuse |
| Response schema | ❌ | Need `OrgOut` with additional fields |
| Auth requirement | org member | Any member of tenant can view |

**Required Request Body Fields:** NONE (GET request)

**Response Shape:**
```json
{
  "id": "string",
  "tenant_id": "string",
  "name": "string",
  "owner_user_id": "string",
  "board_scope_mode": "string",
  "legal_name": "string (nullable)",
  "industry": "string (nullable)",
  "short_name": "string (nullable)",
  "tier": "string (nullable)",
  "primary_region": "string (nullable)",
  "created_at": "ISO datetime"
}
```

**Error Cases:**
- `404` - Org not found
- `403` - Tenant scope denied (user not in org's tenant)

**Auth Requirements:** 
- Requires valid JWT token
- User must be member of the same tenant
- No special role required (read-only)

---

### 2. PUT /v1/orgs/{org_id}

| Item | Status | Notes |
|------|--------|-------|
| Route exists | ❌ MISSING | |
| Path parameter validation | ❌ | Requires `org_id: str` |
| Request body validation | ❌ | Need `OrgUpdate` schema |
| Tenant scope check | ⚠️ | Reuse pattern from governance.py |
| Board member check | ⚠️ | May need board_member role |
| Audit logging | ⚠️ | Reuse `append_audit_event` pattern |

**Required Request Body Fields:**
```json
{
  "name": "string (optional)",
  "legal_name": "string (optional)",
  "industry": "string (optional)",
  "short_name": "string (optional)",
  "primary_region": "string (optional)",
  "board_scope_mode": "string (optional)"
}
```

**Response Shape:**
```json
{
  "id": "string",
  "tenant_id": "string",
  "name": "string",
  "owner_user_id": "string",
  "board_scope_mode": "string",
  "updated_at": "ISO datetime"
}
```

**Error Cases:**
- `404` - Org not found
- `403` - Insufficient permissions
- `400` - Invalid field values
- `422` - Validation error

**Auth Requirements:**
- Valid JWT token
- `board_member` role OR `owner_user_id` match
- Must be in same tenant

---

### 3. PUT /v1/orgs/{org_id}/defaults

| Item | Status | Notes |
|------|--------|-------|
| Route exists | ❌ MISSING | Frontend shows FIXME warning |
| Path parameter | ❌ | Requires `org_id` |
| Defaults schema | ❌ | Need policy defaults model |
| Audit logging | ⚠️ | Reuse existing pattern |

**Required Request Body Fields:**
```json
{
  "default_clearance_tier": "string (e.g., 'L2')",
  "default_compartments": ["string"],
  "auto_approve_low_risk": "boolean",
  "require_mfa_for_high_risk": "boolean",
  "session_timeout_minutes": "integer",
  "max_token_lifetime_hours": "integer"
}
```

**Response Shape:**
```json
{
  "org_id": "string",
  "defaults": {
    "default_clearance_tier": "string",
    "default_compartments": ["string"],
    "auto_approve_low_risk": "boolean",
    "require_mfa_for_high_risk": "boolean",
    "session_timeout_minutes": "integer",
    "max_token_lifetime_hours": "integer"
  },
  "updated_at": "ISO datetime",
  "updated_by": "string"
}
```

**Error Cases:**
- `404` - Org not found
- `403` - Board member role required
- `400` - Invalid default values

**Auth Requirements:**
- Valid JWT token
- `board_member` role required
- Same tenant

---

### 4. POST /v1/orgs/{org_id}/members

| Item | Status | Notes |
|------|--------|-------|
| Route exists | ❌ MISSING | Board member management |
| Path parameter | ❌ | Requires `org_id` |
| Member schema | ❌ | Need `OrgMemberCreate` |
| Board history tracking | ⚠️ | May need new model/table |

**Required Request Body Fields:**
```json
{
  "user_id": "string (optional - can invite by email)",
  "email": "string (if user_id not provided)",
  "name": "string",
  "role": "enum: ['Chair', 'Secretary', 'Risk Officer', 'Member']",
  "clearance": "enum: ['L1', 'L2', 'L3', 'L4', 'L5']",
  "appointed_date": "ISO date (optional)",
  "expires_date": "ISO date (optional)"
}
```

**Response Shape:**
```json
{
  "id": "string",
  "org_id": "string",
  "user_id": "string (nullable)",
  "name": "string",
  "role": "string",
  "clearance": "string",
  "status": "enum: ['active', 'pending', 'expired']",
  "appointed": "ISO date",
  "expires": "ISO date",
  "created_at": "ISO datetime"
}
```

**Error Cases:**
- `404` - Org not found
- `403` - Board member role required
- `409` - User already a member
- `400` - Invalid role or clearance

**Auth Requirements:**
- Valid JWT token
- `board_member` role required
- Cannot add members with higher clearance than self

---

### 5. POST /v1/orgs/{org_id}/regions

| Item | Status | Notes |
|------|--------|-------|
| Route exists | ❌ MISSING | Region management |
| Path parameter | ❌ | Requires `org_id` |
| Region schema | ❌ | Need `RegionCreate` |
| Compliance validation | ⚠️ | Validate compliance framework |

**Required Request Body Fields:**
```json
{
  "code": "string (e.g., 'us-east-1')",
  "name": "string (e.g., 'US East (N. Virginia)')",
  "compliance": "enum: ['SOC2', 'GDPR', 'HIPAA', 'PCI', 'PDPA']",
  "residency": "string (e.g., 'US', 'EU', 'APAC')",
  "encryption": "string (default: 'AES-256-GCM')",
  "cross_border": "enum: ['Disabled', 'Requires Approval', 'Audit Required']"
}
```

**Response Shape:**
```json
{
  "id": "string",
  "org_id": "string",
  "code": "string",
  "name": "string",
  "compliance": "string",
  "residency": "string",
  "encryption": "string",
  "cross_border": "string",
  "status": "enum: ['active', 'pending', 'disabled']",
  "created_at": "ISO datetime"
}
```

**Error Cases:**
- `404` - Org not found
- `403` - Board member role required
- `409` - Region code already exists
- `400` - Invalid compliance framework

**Auth Requirements:**
- Valid JWT token
- `board_member` role required

---

### 6. POST /v1/audit/evidence

| Item | Status | Notes |
|------|--------|-------|
| Route exists | ❌ MISSING | Evidence package creation |
| Event IDs validation | ❌ | Must verify events exist |
| Chain verification | ⚠️ | May include Merkle proofs |
| Package storage | ⚠️ | Where to store packages? |

**Required Request Body Fields:**
```json
{
  "name": "string (required)",
  "caseId": "string (optional)",
  "description": "string (optional)",
  "event_ids": ["string"],
  "format": "enum: ['json', 'pdf', 'chain']",
  "include_chain_verification": "boolean (default: true)",
  "retention_years": "integer (default: 7)"
}
```

**Response Shape:**
```json
{
  "id": "string",
  "name": "string",
  "case_id": "string",
  "org_id": "string",
  "event_count": "integer",
  "size_bytes": "integer",
  "format": "string",
  "chain_verified": "boolean",
  "merkle_root": "string (if chain verified)",
  "created_at": "ISO datetime",
  "expires_at": "ISO datetime",
  "custodian": "string",
  "download_url": "string (temporary)"
}
```

**Error Cases:**
- `404` - One or more events not found
- `403` - Auditor role required
- `400` - No event_ids provided
- `413` - Too many events requested

**Auth Requirements:**
- Valid JWT token
- `auditor` or `board_member` role required
- Must have access to all events in package

---

### 7. POST /v1/extensions/verify

| Item | Status | Notes |
|------|--------|-------|
| Route exists | ❌ MISSING | Bulk/single extension verification |
| Signature validation | ✅ EXISTS | Reuse HMAC pattern from extensions.py |
| Batch support | ❌ | Support array of extension_ids |

**Required Request Body Fields:**
```json
{
  "extension_ids": ["string"] (optional - if empty, verify all)
}
```

**Response Shape:**
```json
{
  "verified": "integer (count)",
  "failed": "integer (count)",
  "results": [
    {
      "id": "string",
      "name": "string",
      "verified": "boolean",
      "error": "string (if failed)"
    }
  ]
}
```

**Error Cases:**
- `403` - manage_extensions permission required
- `404` - Extension not found (for single ID)

**Auth Requirements:**
- Valid JWT token
- `manage_extensions` action permission (via `evaluate_authorization`)

---

### 8. POST /v1/extensions/batch

| Item | Status | Notes |
|------|--------|-------|
| Route exists | ❌ MISSING | Batch operations on extensions |
| Operation types | ❌ | Define allowed operations |
| Atomic handling | ⚠️ | All succeed or partial? |

**Required Request Body Fields:**
```json
{
  "operation": "enum: ['revoke', 'activate', 'delete', 'verify']",
  "target_ids": ["string"],
  "reason": "string (required for revoke/delete)"
}
```

**Response Shape:**
```json
{
  "operation": "string",
  "total": "integer",
  "succeeded": "integer",
  "failed": "integer",
  "results": [
    {
      "id": "string",
      "success": "boolean",
      "error": "string (if failed)"
    }
  ]
}
```

**Error Cases:**
- `403` - manage_extensions permission required
- `400` - Invalid operation type
- `400` - Missing required reason

**Auth Requirements:**
- Valid JWT token
- `manage_extensions` action permission

---

### 9. POST /v1/providers/{id}/test

| Item | Status | Notes |
|------|--------|-------|
| Route exists | ❌ MISSING | Provider health testing |
| Provider model | ❌ | Need Provider model |
| Health check logic | ⚠️ | Provider-type specific health checks |

**Required Request Body Fields:** NONE (POST with empty body, or optional:
```json
{
  "test_type": "enum: ['connectivity', 'auth', 'inference'] (default: 'connectivity')"
}
```)

**Response Shape:**
```json
{
  "provider_id": "string",
  "healthy": "boolean",
  "latency_ms": "integer",
  "test_type": "string",
  "tests": {
    "connectivity": "boolean",
    "auth": "boolean",
    "inference": "boolean"
  },
  "error": "string (if unhealthy)",
  "tested_at": "ISO datetime"
}
```

**Error Cases:**
- `404` - Provider not found
- `403` - manage_providers permission required

**Auth Requirements:**
- Valid JWT token
- `manage_providers` permission (new permission needed)

---

### 10. PUT /v1/providers/{id}/config

| Item | Status | Notes |
|------|--------|-------|
| Route exists | ❌ MISSING | Provider configuration |
| Provider model | ❌ | Need Provider model with config JSON |
| Secret handling | ⚠️ | Encrypt API keys at rest |

**Required Request Body Fields:**
```json
{
  "name": "string (optional)",
  "region": "string (optional)",
  "api_key": "string (optional - only if changing)",
  "config": {
    "timeout_seconds": "integer",
    "max_retries": "integer",
    "retry_backoff_ms": "integer",
    "custom_headers": "object"
  }
}
```

**Response Shape:**
```json
{
  "id": "string",
  "name": "string",
  "type": "string",
  "region": "string",
  "priority": "integer",
  "status": "string",
  "config": {
    "timeout_seconds": "integer",
    "max_retries": "integer",
    "retry_backoff_ms": "integer"
  },
  "updated_at": "ISO datetime"
}
```

**Error Cases:**
- `404` - Provider not found
- `403` - manage_providers permission required
- `400` - Invalid configuration values
- `401` - API key validation failed (if testing)

**Auth Requirements:**
- Valid JWT token
- `manage_providers` permission

---

## SCHEMA CORRECTIONS NEEDED FOR UI COMPATIBILITY

### 1. OrgOut Schema Expansion
Current `OrgOut` in governance.py only has:
- id, tenant_id, name, owner_user_id, board_scope_mode

**Required additions:**
```python
class OrgOut(BaseModel):
    id: str
    tenant_id: str
    name: str
    owner_user_id: str
    board_scope_mode: str
    # MISSING FIELDS:
    legal_name: str | None = None
    industry: str | None = None
    short_name: str | None = None
    tier: str | None = None
    primary_region: str | None = None
    created_at: datetime | None = None
```

### 2. New Schema Definitions Required

```python
# governance.py additions
class OrgUpdate(BaseModel):
    name: str | None = None
    legal_name: str | None = None
    industry: str | None = None
    short_name: str | None = None
    primary_region: str | None = None
    board_scope_mode: str | None = None

class PolicyDefaults(BaseModel):
    default_clearance_tier: str = "L2"
    default_compartments: list[str] = []
    auto_approve_low_risk: bool = False
    require_mfa_for_high_risk: bool = True
    session_timeout_minutes: int = 60
    max_token_lifetime_hours: int = 24

class OrgMemberCreate(BaseModel):
    user_id: str | None = None
    email: str | None = None
    name: str
    role: str  # Chair, Secretary, Risk Officer, Member
    clearance: str  # L1-L5
    appointed_date: date | None = None
    expires_date: date | None = None

class OrgMemberOut(BaseModel):
    id: str
    org_id: str
    user_id: str | None
    name: str
    role: str
    clearance: str
    status: str
    appointed: date
    expires: date
    created_at: datetime

class RegionCreate(BaseModel):
    code: str
    name: str
    compliance: str  # SOC2, GDPR, HIPAA, PCI, PDPA
    residency: str | None = None
    encryption: str = "AES-256-GCM"
    cross_border: str = "Disabled"

class RegionOut(BaseModel):
    id: str
    org_id: str
    code: str
    name: str
    compliance: str
    residency: str
    encryption: str
    cross_border: str
    status: str
    created_at: datetime
```

```python
# audit.py additions
class EvidenceCreate(BaseModel):
    name: str
    case_id: str | None = None
    description: str | None = None
    event_ids: list[str]
    format: str = "json"  # json, pdf, chain
    include_chain_verification: bool = True
    retention_years: int = 7

class EvidenceOut(BaseModel):
    id: str
    name: str
    case_id: str | None
    org_id: str
    event_count: int
    size_bytes: int
    format: str
    chain_verified: bool
    merkle_root: str | None
    created_at: datetime
    expires_at: datetime
    custodian: str
    download_url: str | None
```

```python
# extensions.py additions
class ExtensionVerifyRequest(BaseModel):
    extension_ids: list[str] | None = None  # None = verify all

class ExtensionVerifyResult(BaseModel):
    id: str
    name: str
    verified: bool
    error: str | None

class ExtensionVerifyResponse(BaseModel):
    verified: int
    failed: int
    results: list[ExtensionVerifyResult]

class ExtensionBatchRequest(BaseModel):
    operation: str  # revoke, activate, delete, verify
    target_ids: list[str]
    reason: str | None = None

class ExtensionBatchResult(BaseModel):
    id: str
    success: bool
    error: str | None

class ExtensionBatchResponse(BaseModel):
    operation: str
    total: int
    succeeded: int
    failed: int
    results: list[ExtensionBatchResult]
```

```python
# providers.py (NEW FILE)
class ProviderCreate(BaseModel):
    name: str
    type: str  # openai, anthropic, azure, aws, google, cohere
    region: str | None = None
    api_key: str | None = None
    priority: int = 1
    config: dict | None = None

class ProviderOut(BaseModel):
    id: str
    name: str
    type: str
    region: str | None
    priority: int
    status: str
    latency_ms: int | None
    rps: int | None
    last_check: datetime | None
    created_at: datetime

class ProviderUpdate(BaseModel):
    name: str | None = None
    region: str | None = None
    api_key: str | None = None
    priority: int | None = None
    config: dict | None = None

class ProviderTestResponse(BaseModel):
    provider_id: str
    healthy: bool
    latency_ms: int
    test_type: str
    tests: dict
    error: str | None
    tested_at: datetime
```

---

## VERIFICATION: IMPLEMENTED ROUTES VS FRONTEND EXPECTATIONS

### ✅ Aligned Routes

| Route | Backend | Frontend | Status |
|-------|---------|----------|--------|
| POST /v1/orgs | ✅ | ✅ | Aligned |
| GET /v1/orgs | ✅ | ✅ | Aligned |
| POST /v1/teams | ✅ | ✅ | Aligned |
| GET /v1/teams | ✅ | ✅ | Aligned |
| POST /v1/projects | ✅ | ✅ | Aligned |
| GET /v1/projects | ✅ | ✅ | Aligned |
| GET /v1/projects/{id} | ✅ | ✅ | Aligned |
| POST /v1/seats | ✅ | ✅ | Aligned |
| GET /v1/seats | ✅ | ✅ | Aligned |
| POST /v1/policy/decide | ✅ | ✅ | Aligned |
| POST /v1/extensions | ✅ | ✅ | Aligned |
| GET /v1/extensions | ✅ | ✅ | Aligned |
| POST /v1/extensions/{id}/status | ✅ | ✅ | Aligned |
| GET /v1/audit/events | ✅ | ✅ | Aligned |
| GET /v1/audit/export | ✅ | ✅ | Aligned |
| GET /v1/audit/verify | ✅ | ✅ | Aligned |

### ❌ Mismatched Routes

| Route | Issue | Frontend Expects | Backend Has |
|-------|-------|------------------|-------------|
| GET /v1/orgs/{id} | Missing | Full org profile | List only |
| PUT /v1/orgs/{id} | Missing | Edit org profile | Nothing |
| PUT /v1/orgs/{id}/defaults | Missing | Policy defaults | Nothing |
| POST /v1/orgs/{id}/members | Missing | Board management | Nothing |
| POST /v1/orgs/{id}/regions | Missing | Region management | Nothing |
| PUT /v1/seats/{id} | Missing | Edit seat | Create/List only |
| POST /v1/seats/{id}/assign | Missing | Assign seat | Nothing |
| POST /v1/seats/bulk | Missing | Bulk operations | Nothing |
| POST /v1/audit/evidence | Missing | Evidence packages | Export only |
| POST /v1/extensions/verify | Missing | Bulk verify | Individual status only |
| POST /v1/extensions/batch | Missing | Batch ops | Nothing |
| POST /v1/providers | Missing | Add provider | Nothing |
| POST /v1/providers/{id}/test | Missing | Health test | Nothing |
| PUT /v1/providers/{id}/config | Missing | Configure | Nothing |

---

## RISKS

| Risk | Severity | Likelihood | Impact | Mitigation |
|------|----------|------------|--------|------------|
| **Frontend unusable for governance** | HIGH | High | Critical | 5 of 10 pending are governance-critical; users see FIXME warnings |
| **No provider management** | HIGH | High | High | Cannot configure AI providers; system may fail |
| **Evidence packages missing** | MEDIUM | Medium | Medium | Legal/compliance gap; work around with export |
| **Schema drift** | MEDIUM | Medium | Medium | Frontend expects fields backend doesn't provide |
| **Auth model mismatch** | MEDIUM | Low | High | Frontend assumes board_member role; verify authz implementation |
| **Batch operation limits** | LOW | Medium | Low | Need rate limiting on bulk endpoints |
| **Provider secrets exposure** | HIGH | Low | Critical | Encrypt API keys at rest in provider config |

### Critical Risk Detail: Governance Gaps
The frontend orgs.js actively calls:
- `api.getOrganization()` - expects `GET /v1/orgs/{id}` ❌
- `api.updateOrganization()` - expects `PUT /v1/orgs/{id}` ❌
- `api.getPolicyDefaults()` - expects `GET /v1/orgs/{id}/defaults` ❌
- `api.updatePolicyDefaults()` - expects `PUT /v1/orgs/{id}/defaults` ❌
- `api.addBoardMember()` - expects `POST /v1/orgs/{id}/members` ❌
- `api.addRegion()` - expects `POST /v1/orgs/{id}/regions` ❌

**Current behavior:** UI shows "FIXME" warning toast and falls back to console.log.

---

## ACTION LIST

### Priority 1: Critical (Week 1)

1. **Create Provider Model & Base Routes**
   - [ ] Create `app/models/provider.py` with Provider model
   - [ ] Create `app/schemas/provider.py` with ProviderCreate, ProviderOut, etc.
   - [ ] Create `app/blueprints/providers.py` with basic CRUD
   - [ ] Add `POST /v1/providers` endpoint
   - [ ] Add encryption for `api_key` field

2. **Implement GET/PUT /v1/orgs/{org_id}**
   - [ ] Add `GET /v1/orgs/{org_id}` to governance.py
   - [ ] Add `PUT /v1/orgs/{org_id}` to governance.py
   - [ ] Expand OrgOut schema with additional fields
   - [ ] Add audit logging for updates

3. **Implement Org Members (Board Management)**
   - [ ] Create OrgMember model
   - [ ] Add `POST /v1/orgs/{org_id}/members` endpoint
   - [ ] Add `GET /v1/orgs/{org_id}/members` endpoint

### Priority 2: High (Week 2)

4. **Implement Seat Management**
   - [ ] Add `PUT /v1/seats/{seat_id}` endpoint
   - [ ] Add `POST /v1/seats/{seat_id}/assign` endpoint
   - [ ] Add `POST /v1/seats/{seat_id}/vacate` endpoint
   - [ ] Add `POST /v1/seats/bulk` endpoint

5. **Implement Audit Evidence**
   - [ ] Create EvidencePackage model
   - [ ] Add `POST /v1/audit/evidence` endpoint
   - [ ] Implement Merkle chain verification logic
   - [ ] Add download URL generation

6. **Implement Provider Testing & Config**
   - [ ] Add `POST /v1/providers/{id}/test` endpoint
   - [ ] Add `PUT /v1/providers/{id}/config` endpoint
   - [ ] Implement provider-type specific health checks

### Priority 3: Medium (Week 3)

7. **Implement Extensions Batch Operations**
   - [ ] Add `POST /v1/extensions/verify` endpoint (bulk)
   - [ ] Add `POST /v1/extensions/batch` endpoint
   - [ ] Implement atomic batch handling

8. **Implement Org Defaults & Regions**
   - [ ] Add `PUT /v1/orgs/{org_id}/defaults` endpoint
   - [ ] Add `POST /v1/orgs/{org_id}/regions` endpoint
   - [ ] Create PolicyDefaults model/schema

9. **Auth & Permissions**
   - [ ] Verify `board_member` role exists in authz
   - [ ] Add `manage_providers` permission
   - [ ] Add `auditor` permission for evidence

### Priority 4: Polish (Week 4)

10. **Testing & Documentation**
    - [ ] Write unit tests for all new endpoints
    - [ ] Update API documentation
    - [ ] Verify frontend integration
    - [ ] Remove FIXME warnings from JS when aligned

---

## OPEN QUESTIONS

1. **Provider Model Storage**
   - Is there an existing Provider model in the database?
   - How should API keys be encrypted? (Fernet? Vault integration?)

2. **Evidence Package Storage**
   - Should evidence packages be stored as files or in database?
   - What's the retention policy? (Frontend suggests 7 years default)

3. **Board Member User Linking**
   - Should board members be linked to Users table or standalone?
   - How to handle invited members who don't have accounts yet?

4. **Region Data Residency**
   - Do regions affect actual data storage location?
   - Is this metadata-only or policy-enforced?

5. **Clearance Matrix NTK**
   - The clearance.js references an NTK (Need To Know) matrix
   - Is this a separate model or part of the compartment system?

6. **Batch Operation Atomicity**
   - Should batch operations be all-or-nothing or partial success?
   - What's the maximum batch size?

7. **Provider Health Check Frequency**
   - How often should providers be health-checked?
   - Should this be background job or on-demand only?

8. **Audit Event Selection for Evidence**
   - Frontend allows selecting events via checkboxes
   - Is there an event selection API or client-side only?

---

## APPENDIX: IMPLEMENTATION CODE TEMPLATES

### Template: GET /v1/orgs/{org_id}

```python
@router.get('/orgs/{org_id}', response_model=OrgOut)
def get_org(
    org_id: str,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> OrgOut:
    org = db.get(Org, org_id)
    if org is None:
        raise HTTPException(status_code=404, detail='org not found')
    if org.tenant_id != principal.tenant_id:
        raise HTTPException(status_code=403, detail='tenant scope denied')
    
    return OrgOut(
        id=org.id,
        tenant_id=org.tenant_id,
        name=org.name,
        owner_user_id=org.owner_user_id,
        board_scope_mode=org.board_scope_mode,
        legal_name=org.legal_name,
        industry=org.industry,
        # ... additional fields
    )
```

### Template: POST /v1/extensions/verify

```python
@router.post('/extensions/verify', response_model=ExtensionVerifyResponse)
def verify_extensions(
    payload: ExtensionVerifyRequest,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> ExtensionVerifyResponse:
    auth = evaluate_authorization(principal, action='manage_extensions')
    if auth.decision != 'allow':
        raise HTTPException(status_code=403, detail='extension verification denied')
    
    if payload.extension_ids:
        extensions = [db.get(Extension, eid) for eid in payload.extension_ids]
    else:
        extensions = db.scalars(
            select(Extension).where(Extension.tenant_id == principal.tenant_id)
        ).all()
    
    results = []
    verified_count = 0
    failed_count = 0
    
    for ext in extensions:
        if ext is None:
            continue
        # Verify signature logic
        is_valid = verify_extension_signature(ext)
        if is_valid:
            verified_count += 1
        else:
            failed_count += 1
        results.append(ExtensionVerifyResult(
            id=ext.id,
            name=ext.name,
            verified=is_valid,
            error=None if is_valid else 'signature verification failed'
        ))
    
    return ExtensionVerifyResponse(
        verified=verified_count,
        failed=failed_count,
        results=results
    )
```

---

**END REPORT**
