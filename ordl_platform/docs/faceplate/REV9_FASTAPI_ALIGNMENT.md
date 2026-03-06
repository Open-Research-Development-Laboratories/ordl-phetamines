# REV9 FASTAPI ALIGNMENT DOCUMENT

## Hardline Execution Order - Contract Diff Analysis

**Date:** 2026-03-07  
**Source of Truth:** `/root/openclaw/kimi/downloads/` FastAPI Routers  
**Target Contract:** Rev9 API v1 Specification  
**Status:** 🔴 CRITICAL GAPS IDENTIFIED

---

## EXECUTIVE SUMMARY

### Coverage Statistics

| Metric                      | Value    |
| --------------------------- | -------- |
| Total Rev9 Routes Required  | 48       |
| Currently Implemented       | 21       |
| Missing Routes              | 27 (56%) |
| CRITICAL Priority Missing   | 14       |
| HIGH Priority Missing       | 8        |
| MEDIUM/LOW Priority Missing | 5        |

### Module Breakdown

| Module     | Required | Implemented | Missing | Coverage |
| ---------- | -------- | ----------- | ------- | -------- |
| Foundation | 5        | 1           | 4       | 20%      |
| Governance | 26       | 11          | 15      | 42%      |
| Security   | 13       | 6           | 7       | 46%      |
| Control    | 4        | 3           | 1       | 75%      |

---

## 1. ROUTE-BY-ROUTE CONTRACT ANALYSIS

### 1.1 FOUNDATION MODULE

| Method | Path            | Status        | Auth     | Request Schema | Response Schema                            | Notes               |
| ------ | --------------- | ------------- | -------- | -------------- | ------------------------------------------ | ------------------- |
| GET    | `/health`       | ✅ IMPLEMENTED | None     | -              | `{"status": "ok", "service", "timestamp"}` | Basic health check  |
| GET    | `/health/ready` | ❌ MISSING     | Required | -              | `{"ready": bool, "checks": {}}`            | K8s readiness probe |
| GET    | `/health/live`  | ❌ MISSING     | Required | -              | `{"alive": bool}`                          | K8s liveness probe  |
| GET    | `/metrics`      | ❌ MISSING     | Required | -              | Prometheus format                          | Observability       |
| GET    | `/version`      | ❌ MISSING     | Required | -              | `{"version", "commit", "build_time"}`      | Version info        |

**Implementation Gap:** Only basic `/health` exists. Production requires full observability stack.

---

### 1.2 GOVERNANCE MODULE - ORGANIZATIONS

| Method   | Path                             | Status        | Auth           | Request Schema      | Response Schema      | Notes                |
| -------- | -------------------------------- | ------------- | -------------- | ------------------- | -------------------- | -------------------- |
| POST     | `/v1/orgs`                       | ✅ IMPLEMENTED | `board_member` | `OrgCreate`         | `OrgOut`             | Create org           |
| GET      | `/v1/orgs`                       | ✅ IMPLEMENTED | Authenticated  | Query: `tenant_id`  | `list[OrgOut]`       | List orgs            |
| **GET**  | **`/v1/orgs/{org_id}`**          | ❌ **MISSING** | Authenticated  | Path: `org_id`      | `OrgOut` + details   | Single org retrieval |
| **PUT**  | **`/v1/orgs/{org_id}`**          | ❌ **MISSING** | `board_member` | `OrgUpdate`         | `OrgOut`             | Update org profile   |
| DELETE   | `/v1/orgs/{org_id}`              | ❌ MISSING     | `board_member` | Path: `org_id`      | `{"deleted": true}`  | Delete org           |
| **GET**  | **`/v1/orgs/{org_id}/members`**  | ❌ **MISSING** | Authenticated  | Path: `org_id`      | `list[OrgMemberOut]` | List board members   |
| **POST** | **`/v1/orgs/{org_id}/members`**  | ❌ **MISSING** | `board_member` | `OrgMemberCreate`   | `OrgMemberOut`       | Add board member     |
| **GET**  | **`/v1/orgs/{org_id}/defaults`** | ❌ **MISSING** | Authenticated  | Path: `org_id`      | `OrgDefaultsOut`     | Get policy defaults  |
| **PUT**  | **`/v1/orgs/{org_id}/defaults`** | ❌ **MISSING** | `board_member` | `OrgDefaultsUpdate` | `OrgDefaultsOut`     | Update defaults      |
| **GET**  | **`/v1/orgs/{org_id}/regions`**  | ❌ **MISSING** | Authenticated  | Path: `org_id`      | `list[RegionOut]`    | List regions         |
| **POST** | **`/v1/orgs/{org_id}/regions`**  | ❌ **MISSING** | `board_member` | `RegionCreate`      | `RegionOut`          | Add region           |

**CRITICAL GAPS:**

- No single org retrieval endpoint (blocks profile editing)
- No org update capability
- No board member management
- No policy defaults configuration
- No region support

---

### 1.3 GOVERNANCE MODULE - TEAMS

| Method  | Path                            | Status        | Auth          | Request Schema    | Response Schema     | Notes            |
| ------- | ------------------------------- | ------------- | ------------- | ----------------- | ------------------- | ---------------- |
| POST    | `/v1/teams`                     | ✅ IMPLEMENTED | Authenticated | `TeamCreate`      | `TeamOut`           | Create team      |
| GET     | `/v1/teams`                     | ✅ IMPLEMENTED | Authenticated | Query: `org_id`   | `list[TeamOut]`     | List teams       |
| GET     | `/v1/teams/{team_id}`           | ❌ MISSING     | Authenticated | Path: `team_id`   | `TeamOut`           | Get team         |
| PUT     | `/v1/teams/{team_id}`           | ❌ MISSING     | `team_admin`  | `TeamUpdate`      | `TeamOut`           | Update team      |
| DELETE  | `/v1/teams/{team_id}`           | ❌ MISSING     | `team_admin`  | Path: `team_id`   | `{"deleted": true}` | Delete team      |
| **GET** | **`/v1/teams/{team_id}/scope`** | ❌ **MISSING** | Authenticated | Path: `team_id`   | `TeamScopeOut`      | Get scope matrix |
| **PUT** | **`/v1/teams/{team_id}/scope`** | ❌ **MISSING** | `team_admin`  | `TeamScopeUpdate` | `TeamScopeOut`      | Update scope     |

---

### 1.4 GOVERNANCE MODULE - PROJECTS

| Method  | Path                                     | Status        | Auth            | Request Schema          | Response Schema      | Notes           |
| ------- | ---------------------------------------- | ------------- | --------------- | ----------------------- | -------------------- | --------------- |
| POST    | `/v1/projects`                           | ✅ IMPLEMENTED | Authenticated   | `ProjectCreate`         | `ProjectOut`         | Create project  |
| GET     | `/v1/projects`                           | ✅ IMPLEMENTED | Authenticated   | Query: `team_id`        | `list[ProjectOut]`   | List projects   |
| GET     | `/v1/projects/{project_id}`              | ✅ IMPLEMENTED | Authenticated   | Path: `project_id`      | `ProjectOut`         | Get project     |
| PUT     | `/v1/projects/{project_id}`              | ❌ MISSING     | `project_admin` | `ProjectUpdate`         | `ProjectOut`         | Update project  |
| DELETE  | `/v1/projects/{project_id}`              | ❌ MISSING     | `project_admin` | Path: `project_id`      | `{"deleted": true}`  | Delete project  |
| **GET** | **`/v1/projects/{project_id}/defaults`** | ❌ **MISSING** | Authenticated   | Path: `project_id`      | `ProjectDefaultsOut` | Get defaults    |
| **PUT** | **`/v1/projects/{project_id}/defaults`** | ❌ **MISSING** | `project_admin` | `ProjectDefaultsUpdate` | `ProjectDefaultsOut` | Update defaults |

---

### 1.5 GOVERNANCE MODULE - SEATS

| Method   | Path                             | Status        | Auth           | Request Schema      | Response Schema     | Notes           |
| -------- | -------------------------------- | ------------- | -------------- | ------------------- | ------------------- | --------------- |
| POST     | `/v1/seats`                      | ✅ IMPLEMENTED | `manage_seats` | `SeatCreate`        | `SeatOut`           | Create seat     |
| GET      | `/v1/seats`                      | ✅ IMPLEMENTED | Authenticated  | Query: `project_id` | `list[SeatOut]`     | List seats      |
| **GET**  | **`/v1/seats/{seat_id}`**        | ❌ **MISSING** | Authenticated  | Path: `seat_id`     | `SeatOut`           | Get seat        |
| **PUT**  | **`/v1/seats/{seat_id}`**        | ❌ **MISSING** | `manage_seats` | `SeatUpdate`        | `SeatOut`           | Update seat     |
| DELETE   | `/v1/seats/{seat_id}`            | ❌ MISSING     | `manage_seats` | Path: `seat_id`     | `{"deleted": true}` | Delete seat     |
| **POST** | **`/v1/seats/{seat_id}/assign`** | ❌ **MISSING** | `manage_seats` | `SeatAssignRequest` | `SeatOut`           | Assign user     |
| **POST** | **`/v1/seats/{seat_id}/vacate`** | ❌ **MISSING** | `manage_seats` | `SeatVacateRequest` | `SeatOut`           | Vacate seat     |
| **POST** | **`/v1/seats/bulk`**             | ❌ **MISSING** | `manage_seats` | `SeatBulkRequest`   | `SeatBulkOut`       | Bulk operations |
| **GET**  | **`/v1/seats/matrix`**           | ❌ **MISSING** | Authenticated  | Query: `project_id` | `SeatMatrixOut`     | Get seat matrix |
| **PUT**  | **`/v1/seats/matrix`**           | ❌ **MISSING** | `manage_seats` | `SeatMatrixUpdate`  | `SeatMatrixOut`     | Update matrix   |

**CRITICAL GAPS:**

- No seat retrieval by ID
- No seat update capability
- No assign/vacate operations (core seat lifecycle)
- No bulk operations for mass assignment

---

### 1.6 GOVERNANCE MODULE - CLEARANCE

| Method   | Path                                       | Status        | Auth             | Request Schema             | Response Schema            | Notes              |
| -------- | ------------------------------------------ | ------------- | ---------------- | -------------------------- | -------------------------- | ------------------ |
| **GET**  | **`/v1/clearance/tiers`**                  | ❌ **MISSING** | Authenticated    | -                          | `list[ClearanceTierOut]`   | List tiers         |
| **PUT**  | **`/v1/clearance/tiers`**                  | ❌ **MISSING** | `security_admin` | `ClearanceTierUpdate`      | `list[ClearanceTierOut]`   | Update tiers       |
| **GET**  | **`/v1/clearance/tiers/{tier_id}`**        | ❌ **MISSING** | Authenticated    | Path: `tier_id`            | `ClearanceTierOut`         | Get tier           |
| **GET**  | **`/v1/clearance/compartments`**           | ❌ **MISSING** | Authenticated    | -                          | `list[CompartmentOut]`     | List compartments  |
| **POST** | **`/v1/clearance/compartments`**           | ❌ **MISSING** | `security_admin` | `CompartmentCreate`        | `CompartmentOut`           | Create compartment |
| **GET**  | **`/v1/clearance/compartments/{comp_id}`** | ❌ **MISSING** | Authenticated    | Path: `comp_id`            | `CompartmentOut`           | Get compartment    |
| **PUT**  | **`/v1/clearance/compartments/{comp_id}`** | ❌ **MISSING** | `security_admin` | `CompartmentUpdate`        | `CompartmentOut`           | Update compartment |
| **GET**  | **`/v1/clearance/matrix`**                 | ❌ **MISSING** | Authenticated    | Query params               | `ClearanceMatrixOut`       | Get NTK matrix     |
| **PUT**  | **`/v1/clearance/matrix`**                 | ❌ **MISSING** | `security_admin` | `ClearanceMatrixUpdate`    | `ClearanceMatrixOut`       | Update matrix      |
| **GET**  | **`/v1/clearance/matrix/export`**          | ❌ **MISSING** | Authenticated    | Query: `format`            | File (JSON/CSV/PDF)        | Export matrix      |
| POST     | `/v1/clearance/evaluate`                   | ✅ IMPLEMENTED | Authenticated    | `ClearanceEvaluateRequest` | `AuthorizationDecisionOut` | Evaluate clearance |

**CRITICAL GAPS:**

- Entire clearance management subsystem missing
- No tier/compartment CRUD
- No NTK (Need To Know) matrix support

---

### 1.7 GOVERNANCE MODULE - POLICY

| Method | Path                  | Status        | Auth          | Request Schema          | Response Schema        | Notes           |
| ------ | --------------------- | ------------- | ------------- | ----------------------- | ---------------------- | --------------- |
| POST   | `/v1/policy/decide`   | ✅ IMPLEMENTED | Authenticated | `PolicyDecideRequest`   | `PolicyDecideResponse` | Policy decision |
| POST   | `/v1/policy/validate` | ✅ IMPLEMENTED | Authenticated | `PolicyValidateRequest` | `{"valid": bool}`      | Validate token  |

---

### 1.8 SECURITY MODULE - AUDIT

| Method   | Path                     | Status        | Auth          | Request Schema      | Response Schema                   | Notes            |
| -------- | ------------------------ | ------------- | ------------- | ------------------- | --------------------------------- | ---------------- |
| GET      | `/v1/audit`              | ✅ IMPLEMENTED | Authenticated | Query: `project_id` | `list[PolicyDecisionOut]`         | Policy decisions |
| GET      | `/v1/audit/events`       | ✅ IMPLEMENTED | Authenticated | Query params        | `list[AuditEventOut]`             | Audit events     |
| GET      | `/v1/audit/verify`       | ✅ IMPLEMENTED | Authenticated | Query: `project_id` | `{"valid": bool, "broken_at": ?}` | Verify chain     |
| GET      | `/v1/audit/export`       | ✅ IMPLEMENTED | Authenticated | Query: `format`     | File stream                       | Export audit     |
| **POST** | **`/v1/audit/evidence`** | ❌ **MISSING** | Authenticated | `EvidenceCreate`    | `EvidencePackageOut`              | Create evidence  |

---

### 1.9 SECURITY MODULE - EXTENSIONS

| Method   | Path                             | Status        | Auth                | Request Schema           | Response Schema      | Notes              |
| -------- | -------------------------------- | ------------- | ------------------- | ------------------------ | -------------------- | ------------------ |
| POST     | `/v1/extensions`                 | ✅ IMPLEMENTED | `manage_extensions` | `ExtensionCreate`        | `ExtensionOut`       | Register extension |
| GET      | `/v1/extensions`                 | ✅ IMPLEMENTED | Authenticated       | -                        | `list[ExtensionOut]` | List extensions    |
| GET      | `/v1/extensions/{ext_id}`        | ❌ MISSING     | Authenticated       | Path: `ext_id`           | `ExtensionOut`       | Get extension      |
| PUT      | `/v1/extensions/{ext_id}`        | ❌ MISSING     | `manage_extensions` | `ExtensionUpdate`        | `ExtensionOut`       | Update extension   |
| DELETE   | `/v1/extensions/{ext_id}`        | ❌ MISSING     | `manage_extensions` | Path: `ext_id`           | `{"deleted": true}`  | Delete extension   |
| POST     | `/v1/extensions/{ext_id}/status` | ✅ IMPLEMENTED | `manage_extensions` | Body: `status`           | `ExtensionOut`       | Set status         |
| **POST** | **`/v1/extensions/verify`**      | ❌ **MISSING** | `manage_extensions` | `ExtensionVerifyRequest` | `VerifyResultOut`    | Batch verify       |
| **POST** | **`/v1/extensions/batch`**       | ❌ **MISSING** | `manage_extensions` | `ExtensionBatchRequest`  | `BatchResultOut`     | Bulk operations    |

---

### 1.10 SECURITY MODULE - PROVIDERS

| Method     | Path                                     | Status        | Auth             | Request Schema           | Response Schema     | Notes                 |
| ---------- | ---------------------------------------- | ------------- | ---------------- | ------------------------ | ------------------- | --------------------- |
| **GET**    | **`/v1/providers`**                      | ❌ **MISSING** | Authenticated    | Query params             | `list[ProviderOut]` | List providers        |
| **POST**   | **`/v1/providers`**                      | ❌ **MISSING** | `security_admin` | `ProviderCreate`         | `ProviderOut`       | Create provider       |
| **GET**    | **`/v1/providers/{provider_id}`**        | ❌ **MISSING** | Authenticated    | Path: `provider_id`      | `ProviderOut`       | Get provider          |
| **PUT**    | **`/v1/providers/{provider_id}`**        | ❌ **MISSING** | `security_admin` | `ProviderUpdate`         | `ProviderOut`       | Update provider       |
| **DELETE** | **`/v1/providers/{provider_id}`**        | ❌ **MISSING** | `security_admin` | Path: `provider_id`      | `{"deleted": true}` | Delete provider       |
| **PUT**    | **`/v1/providers/priority`**             | ❌ **MISSING** | `security_admin` | `ProviderPriorityUpdate` | `list[ProviderOut]` | Update priority chain |
| **GET**    | **`/v1/providers/probes`**               | ❌ **MISSING** | Authenticated    | -                        | `ProbeConfigOut`    | Get probe config      |
| **PUT**    | **`/v1/providers/probes`**               | ❌ **MISSING** | `security_admin` | `ProbeConfigUpdate`      | `ProbeConfigOut`    | Update probes         |
| **POST**   | **`/v1/providers/{provider_id}/test`**   | ❌ **MISSING** | `security_admin` | Path: `provider_id`      | `ProviderTestOut`   | Health check          |
| **PUT**    | **`/v1/providers/{provider_id}/config`** | ❌ **MISSING** | `security_admin` | `ProviderConfigUpdate`   | `ProviderOut`       | Configure provider    |

**CRITICAL GAP:** Entire provider subsystem missing. Frontend has full provider management UI with no backend.

**ALIAS REQUIREMENT:** Provider endpoints MUST support both `{provider_id}` and `{provider}` path parameters for compatibility.

---

### 1.11 CONTROL MODULE - WORKERS

| Method | Path                                                    | Status        | Auth            | Request Schema                 | Response Schema                  | Notes             |
| ------ | ------------------------------------------------------- | ------------- | --------------- | ------------------------------ | -------------------------------- | ----------------- |
| POST   | `/v1/workers/register`                                  | ✅ IMPLEMENTED | Authenticated   | `WorkerRegister`               | `WorkerOut`                      | Register worker   |
| GET    | `/v1/workers`                                           | ✅ IMPLEMENTED | Authenticated   | Query: `project_id`            | `list[WorkerOut]`                | List workers      |
| GET    | `/v1/workers/{worker_id}`                               | ❌ MISSING     | Authenticated   | Path: `worker_id`              | `WorkerOut`                      | Get worker        |
| PUT    | `/v1/workers/{worker_id}`                               | ❌ MISSING     | `worker_action` | `WorkerUpdate`                 | `WorkerOut`                      | Update worker     |
| DELETE | `/v1/workers/{worker_id}`                               | ❌ MISSING     | `worker_action` | Path: `worker_id`              | `{"deleted": true}`              | Delete worker     |
| POST   | `/v1/workers/{worker_id}/action`                        | ✅ IMPLEMENTED | `worker_action` | `WorkerActionRequest`          | `{"worker_action_id"}`           | Queue action      |
| POST   | `/v1/workers/{worker_id}/heartbeat`                     | ✅ IMPLEMENTED | `worker_action` | `WorkerHeartbeatRequest`       | `WorkerHeartbeatOut`             | Heartbeat         |
| POST   | `/v1/workers/{worker_id}/probe`                         | ✅ IMPLEMENTED | `worker_action` | `WorkerProbeRequest`           | `WorkerProbeOut`                 | Probe worker      |
| GET    | `/v1/workers/connectivity`                              | ✅ IMPLEMENTED | Authenticated   | Query: `project_id`            | `list[WorkerConnectivityOut]`    | List connectivity |
| POST   | `/v1/workers/monitor/config`                            | ✅ IMPLEMENTED | `worker_action` | `WorkerMonitorConfigUpsert`    | `WorkerMonitorConfigOut`         | Monitor config    |
| GET    | `/v1/workers/monitor/config`                            | ✅ IMPLEMENTED | Authenticated   | Query: `project_id`            | `WorkerMonitorConfigOut`         | Get config        |
| POST   | `/v1/workers/monitor/run-once`                          | ✅ IMPLEMENTED | `worker_action` | `WorkerMonitorRunRequest`      | `MonitorRunResult`               | Run monitor       |
| POST   | `/v1/workers/update-bundles`                            | ✅ IMPLEMENTED | `worker_action` | `WorkerUpdateBundleCreate`     | `WorkerUpdateBundleOut`          | Create bundle     |
| GET    | `/v1/workers/update-bundles`                            | ✅ IMPLEMENTED | Authenticated   | Query: `project_id`            | `list[WorkerUpdateBundleOut]`    | List bundles      |
| GET    | `/v1/workers/update-bundles/{bundle_id}`                | ✅ IMPLEMENTED | Authenticated   | Path: `bundle_id`              | `WorkerUpdateBundleOut`          | Get bundle        |
| POST   | `/v1/workers/update-campaigns`                          | ✅ IMPLEMENTED | `worker_action` | `WorkerUpdateCampaignCreate`   | `WorkerUpdateCampaignOut`        | Create campaign   |
| GET    | `/v1/workers/update-campaigns`                          | ✅ IMPLEMENTED | Authenticated   | Query: `project_id`            | `list[WorkerUpdateCampaignOut]`  | List campaigns    |
| POST   | `/v1/workers/update-campaigns/{campaign_id}/start`      | ✅ IMPLEMENTED | `worker_action` | `WorkerUpdateCampaignStart`    | `CampaignStartOut`               | Start campaign    |
| GET    | `/v1/workers/update-campaigns/{campaign_id}/executions` | ✅ IMPLEMENTED | Authenticated   | Path: `campaign_id`            | `list[WorkerUpdateExecutionOut]` | List executions   |
| POST   | `/v1/workers/update-campaigns/{campaign_id}/rollback`   | ✅ IMPLEMENTED | `worker_action` | `WorkerUpdateCampaignRollback` | `WorkerUpdateCampaignOut`        | Rollback          |
| POST   | `/v1/workers/discovery/scans`                           | ✅ IMPLEMENTED | `worker_action` | `WorkerDiscoveryScanCreate`    | `WorkerDiscoveryScanOut`         | Create scan       |
| GET    | `/v1/workers/discovery/scans`                           | ✅ IMPLEMENTED | Authenticated   | Query: `project_id`            | `list[WorkerDiscoveryScanOut]`   | List scans        |
| GET    | `/v1/workers/discovery/scans/{scan_id}`                 | ✅ IMPLEMENTED | Authenticated   | Path: `scan_id`                | `WorkerDiscoveryScanOut`         | Get scan          |
| GET    | `/v1/workers/{worker_id}/actions/pending`               | ✅ IMPLEMENTED | `worker_action` | Path: `worker_id`              | `list[WorkerActionOut]`          | Pending actions   |
| POST   | `/v1/workers/actions/{action_id}/ack`                   | ✅ IMPLEMENTED | `worker_action` | `WorkerActionAckRequest`       | `WorkerActionOut`                | Ack action        |

**Workers module is EXTENSIVELY implemented** (25+ endpoints) - this is the most complete module.

---

## 2. SCHEMA DEFINITIONS FOR MISSING ENDPOINTS

### 2.1 Organization Schemas

```python
# Request Schemas
class OrgUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    board_scope_mode: str | None = None  # 'scoped', 'open', 'locked'

class OrgDefaultsUpdate(BaseModel):
    default_clearance_tier: str | None = None
    default_compartments: list[str] | None = None
    require_approval_for_high_risk: bool = True
    auto_escalation_enabled: bool = False
    session_timeout_minutes: int = 30

class OrgMemberCreate(BaseModel):
    user_id: str
    role: str  # 'board_member', 'board_observer', 'security_admin'
    permissions: list[str] | None = None
    term_expires_at: datetime | None = None

class RegionCreate(BaseModel):
    region_code: str  # 'us-east-1', 'eu-west-1', etc.
    name: str
    datacenter_codes: list[str] | None = None
    compliance_frameworks: list[str] | None = None  # 'soc2', 'iso27001', etc.

# Response Schemas
class OrgMemberOut(BaseModel):
    id: str
    org_id: str
    user_id: str
    role: str
    permissions: list[str]
    term_expires_at: str | None
    created_at: str

class OrgDefaultsOut(BaseModel):
    org_id: str
    default_clearance_tier: str | None
    default_compartments: list[str]
    require_approval_for_high_risk: bool
    auto_escalation_enabled: bool
    session_timeout_minutes: int
    updated_at: str

class RegionOut(BaseModel):
    id: str
    org_id: str
    region_code: str
    name: str
    datacenter_codes: list[str]
    compliance_frameworks: list[str]
    status: str  # 'active', 'maintenance', 'deprecated'
    created_at: str
```

### 2.2 Team Schemas

```python
class TeamUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None  # 'active', 'archived'

class TeamScopeOut(BaseModel):
    team_id: str
    allowed_regions: list[str]
    default_region: str | None
    max_projects: int
    max_seats_per_project: int
    clearance_ceiling: str | None
    compartment_whitelist: list[str]
    compartment_blacklist: list[str]

class TeamScopeUpdate(BaseModel):
    allowed_regions: list[str] | None = None
    default_region: str | None = None
    max_projects: int | None = None
    max_seats_per_project: int | None = None
    clearance_ceiling: str | None = None
    compartment_whitelist: list[str] | None = None
    compartment_blacklist: list[str] | None = None
```

### 2.3 Project Schemas

```python
class ProjectUpdate(BaseModel):
    name: str | None = None
    code: str | None = None
    ingress_mode: str | None = None  # 'open', 'invite', 'closed'
    visibility_mode: str | None = None  # 'public', 'private', 'secret'
    status: str | None = None  # 'active', 'archived', 'frozen'

class ProjectDefaultsOut(BaseModel):
    project_id: str
    default_seat_role: str
    default_seat_rank: str
    auto_assign_clearance: bool
    inherited_clearance_tier: str | None
    inherited_compartments: list[str]
    require_seat_approval: bool

class ProjectDefaultsUpdate(BaseModel):
    default_seat_role: str | None = None
    default_seat_rank: str | None = None
    auto_assign_clearance: bool | None = None
    inherited_clearance_tier: str | None = None
    inherited_compartments: list[str] | None = None
    require_seat_approval: bool | None = None
```

### 2.4 Seat Schemas

```python
class SeatUpdate(BaseModel):
    role: str | None = None
    rank: str | None = None  # 'owner', 'admin', 'member', 'guest'
    position: str | None = None
    group_name: str | None = None
    clearance_tier: str | None = None
    compartments: list[str] | None = None
    status: str | None = None  # 'active', 'suspended', 'revoked'

class SeatAssignRequest(BaseModel):
    user_id: str
    assigned_by: str | None = None  # Optional override
    reason: str | None = None

class SeatVacateRequest(BaseModel):
    vacated_by: str | None = None  # Optional override
    reason: str | None = None
    permanent: bool = False  # True = delete seat, False = just unassign

class SeatBulkRequest(BaseModel):
    operation: str  # 'assign', 'vacate', 'update', 'create'
    seats: list[SeatBulkItem]
    continue_on_error: bool = True

class SeatBulkItem(BaseModel):
    seat_id: str | None = None  # For existing seats
    project_id: str | None = None  # For new seats
    user_id: str | None = None
    role: str | None = None
    rank: str | None = None
    position: str | None = None
    group_name: str | None = None
    clearance_tier: str | None = None
    compartments: list[str] | None = None

class SeatBulkOut(BaseModel):
    total: int
    succeeded: int
    failed: int
    results: list[SeatBulkResult]

class SeatBulkResult(BaseModel):
    seat_id: str | None
    status: str  # 'success', 'error'
    error: str | None
    previous_state: dict | None

class SeatMatrixOut(BaseModel):
    project_id: str
    matrix: dict  # role × clearance mapping
    last_updated: str
    updated_by: str

class SeatMatrixUpdate(BaseModel):
    matrix: dict
```

### 2.5 Clearance Schemas

```python
class ClearanceTierOut(BaseModel):
    id: str
    name: str  # 'public', 'internal', 'confidential', 'restricted'
    level: int  # 1, 2, 3, 4
    description: str
    color: str  # UI color code
    compartments: list[str]  # Required compartments for this tier

class ClearanceTierUpdate(BaseModel):
    tiers: list[ClearanceTierItem]

class ClearanceTierItem(BaseModel):
    id: str
    name: str
    level: int
    description: str
    color: str
    compartments: list[str]

class CompartmentOut(BaseModel):
    id: str
    code: str  # Short code like 'FIN', 'HR', 'ENG'
    name: str
    description: str
    parent_id: str | None  # For hierarchical compartments
    created_at: str

class CompartmentCreate(BaseModel):
    code: str
    name: str
    description: str
    parent_id: str | None = None

class CompartmentUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    parent_id: str | None = None

class ClearanceMatrixOut(BaseModel):
    tiers: list[str]  # Tier IDs as rows
    compartments: list[str]  # Compartment IDs as columns
    permissions: dict  # tier_id × comp_id → permission level
    last_updated: str
    updated_by: str

class ClearanceMatrixUpdate(BaseModel):
    permissions: dict  # tier_id × comp_id → permission level
```

### 2.6 Audit Evidence Schema

```python
class EvidenceCreate(BaseModel):
    event_ids: list[str]
    format: str = 'json'  # 'json', 'pdf', 'chain'
    include_chain_verification: bool = True
    include_raw_events: bool = True
    description: str | None = None
    expires_at: datetime | None = None

class EvidencePackageOut(BaseModel):
    id: str
    project_id: str
    format: str
    description: str | None
    event_count: int
    events_included: list[str]
    chain_verification: dict  # {valid: bool, checked_at: str, broken_at: str|None}
    package_hash: str  # Merkle root of evidence
    signature: str | None  # Signed by evidence officer
    expires_at: str | None
    download_url: str
    created_at: str
    created_by: str
```

### 2.7 Extension Batch Schemas

```python
class ExtensionVerifyRequest(BaseModel):
    extension_ids: list[str]  # Empty = verify all
    verify_signatures: bool = True
    verify_permissions: bool = True

class VerifyResultOut(BaseModel):
    total: int
    valid: int
    invalid: int
    results: list[ExtensionVerifyItem]

class ExtensionVerifyItem(BaseModel):
    extension_id: str
    name: str
    valid: bool
    signature_valid: bool
    permissions_valid: bool
    errors: list[str]

class ExtensionBatchRequest(BaseModel):
    operation: str  # 'activate', 'deactivate', 'delete', 'verify'
    target_ids: list[str]
    continue_on_error: bool = True

class BatchResultOut(BaseModel):
    total: int
    succeeded: int
    failed: int
    results: list[BatchItemResult]

class BatchItemResult(BaseModel):
    extension_id: str
    status: str  # 'success', 'error'
    previous_status: str | None
    error: str | None
```

### 2.8 Provider Schemas

```python
class ProviderCreate(BaseModel):
    name: str
    provider_type: str  # 'ai', 'storage', 'compute', 'gateway'
    config: dict  # Type-specific configuration
    priority: int = 0  # Lower = higher priority in failover chain
    region: str | None = None
    health_check_enabled: bool = True
    health_check_interval_seconds: int = 60
    timeout_seconds: int = 30
    retry_policy: dict | None = None

class ProviderUpdate(BaseModel):
    name: str | None = None
    config: dict | None = None
    priority: int | None = None
    health_check_enabled: bool | None = None
    health_check_interval_seconds: int | None = None
    timeout_seconds: int | None = None
    retry_policy: dict | None = None
    status: str | None = None  # 'active', 'inactive', 'degraded'

class ProviderOut(BaseModel):
    id: str
    name: str
    provider_type: str
    config: dict  # Masked sensitive values
    priority: int
    region: str | None
    status: str  # 'active', 'inactive', 'degraded', 'failed'
    health_status: dict  # Last health check result
    last_health_check_at: str | None
    health_check_enabled: bool
    created_at: str
    updated_at: str

class ProviderPriorityUpdate(BaseModel):
    providers: list[ProviderPriorityItem]

class ProviderPriorityItem(BaseModel):
    provider_id: str
    priority: int

class ProbeConfigOut(BaseModel):
    global_interval_seconds: int
    global_timeout_seconds: int
    failure_threshold: int
    recovery_threshold: int
    providers: list[ProviderProbeConfig]

class ProviderProbeConfig(BaseModel):
    provider_id: str
    endpoint: str
    method: str  # 'GET', 'POST', etc.
    headers: dict | None
    expected_status: int
    expected_body_contains: str | None

class ProbeConfigUpdate(BaseModel):
    global_interval_seconds: int | None = None
    global_timeout_seconds: int | None = None
    failure_threshold: int | None = None
    recovery_threshold: int | None = None
    providers: list[ProviderProbeConfig] | None = None

class ProviderTestOut(BaseModel):
    provider_id: str
    tested_at: str
    success: bool
    latency_ms: int
    status_code: int | None
    error: str | None
    details: dict | None

class ProviderConfigUpdate(BaseModel):
    config: dict
    merge: bool = False  # True = merge, False = replace
```

---

## 3. SQLALCHEMY MODEL CHANGES NEEDED

### 3.1 New Models Required

```python
# app/models.py additions

class OrgMember(Base):
    """Board member assignments."""
    __tablename__ = 'org_members'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id = Column(String(36), ForeignKey('orgs.id'), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey('users.id'), nullable=False, index=True)
    role = Column(String(50), nullable=False)  # board_member, board_observer
    permissions_json = Column(Text, default='[]')
    term_expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('org_id', 'user_id', name='uq_org_member'),
    )

class OrgDefaults(Base):
    """Organization-level policy defaults."""
    __tablename__ = 'org_defaults'

    org_id = Column(String(36), ForeignKey('orgs.id'), primary_key=True)
    default_clearance_tier = Column(String(50), nullable=True)
    default_compartments_json = Column(Text, default='[]')
    require_approval_for_high_risk = Column(Integer, default=1)  # Boolean
    auto_escalation_enabled = Column(Integer, default=0)
    session_timeout_minutes = Column(Integer, default=30)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Region(Base):
    """Geographic regions for data residency."""
    __tablename__ = 'regions'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id = Column(String(36), ForeignKey('orgs.id'), nullable=False, index=True)
    region_code = Column(String(50), nullable=False)
    name = Column(String(200), nullable=False)
    datacenter_codes_json = Column(Text, default='[]')
    compliance_frameworks_json = Column(Text, default='[]')
    status = Column(String(50), default='active')
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('org_id', 'region_code', name='uq_org_region'),
    )

class TeamScope(Base):
    """Team-level scope restrictions."""
    __tablename__ = 'team_scopes'

    team_id = Column(String(36), ForeignKey('teams.id'), primary_key=True)
    allowed_regions_json = Column(Text, default='[]')
    default_region = Column(String(50), nullable=True)
    max_projects = Column(Integer, default=10)
    max_seats_per_project = Column(Integer, default=50)
    clearance_ceiling = Column(String(50), nullable=True)
    compartment_whitelist_json = Column(Text, nullable=True)
    compartment_blacklist_json = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ProjectDefaults(Base):
    """Project-level policy defaults."""
    __tablename__ = 'project_defaults'

    project_id = Column(String(36), ForeignKey('projects.id'), primary_key=True)
    default_seat_role = Column(String(50), default='member')
    default_seat_rank = Column(String(50), default='member')
    auto_assign_clearance = Column(Integer, default=0)
    inherited_clearance_tier = Column(String(50), nullable=True)
    inherited_compartments_json = Column(Text, nullable=True)
    require_seat_approval = Column(Integer, default=1)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ClearanceTier(Base):
    """Clearance tier definitions per tenant."""
    __tablename__ = 'clearance_tiers'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey('tenants.id'), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    level = Column(Integer, nullable=False)  # 1, 2, 3, 4
    description = Column(Text, nullable=True)
    color = Column(String(7), default='#000000')  # Hex color
    compartments_json = Column(Text, default='[]')  # Required compartments
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('tenant_id', 'name', name='uq_tenant_tier_name'),
        UniqueConstraint('tenant_id', 'level', name='uq_tenant_tier_level'),
    )

class Compartment(Base):
    """Security compartments per tenant."""
    __tablename__ = 'compartments'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey('tenants.id'), nullable=False, index=True)
    code = Column(String(50), nullable=False)  # Short code like 'FIN'
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    parent_id = Column(String(36), ForeignKey('compartments.id'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('tenant_id', 'code', name='uq_tenant_compartment_code'),
    )

class ClearanceMatrix(Base):
    """NTK (Need To Know) matrix permissions."""
    __tablename__ = 'clearance_matrix'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey('tenants.id'), nullable=False, index=True)
    tier_id = Column(String(36), ForeignKey('clearance_tiers.id'), nullable=False)
    compartment_id = Column(String(36), ForeignKey('compartments.id'), nullable=False)
    permission_level = Column(String(50), default='read')  # 'none', 'read', 'write', 'admin'
    updated_by = Column(String(36), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('tenant_id', 'tier_id', 'compartment_id', name='uq_matrix_entry'),
    )

class EvidencePackage(Base):
    """Audit evidence packages."""
    __tablename__ = 'evidence_packages'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey('projects.id'), nullable=False, index=True)
    created_by = Column(String(36), ForeignKey('users.id'), nullable=False)
    format = Column(String(20), nullable=False)  # json, pdf, chain
    description = Column(Text, nullable=True)
    event_ids_json = Column(Text, nullable=False)  # List of event IDs
    chain_verification_json = Column(Text, nullable=True)
    package_hash = Column(String(128), nullable=True)  # Merkle root
    signature = Column(Text, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    storage_path = Column(String(500), nullable=True)  # Path to stored package
    created_at = Column(DateTime, default=datetime.utcnow)

class Provider(Base):
    """External service providers."""
    __tablename__ = 'providers'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey('tenants.id'), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    provider_type = Column(String(50), nullable=False)  # ai, storage, compute, gateway
    config_json = Column(Text, default='{}')  # Encrypted configuration
    priority = Column(Integer, default=0)
    region = Column(String(50), nullable=True)
    status = Column(String(50), default='active')  # active, inactive, degraded, failed
    health_status_json = Column(Text, nullable=True)
    last_health_check_at = Column(DateTime, nullable=True)
    health_check_enabled = Column(Integer, default=1)
    health_check_interval_seconds = Column(Integer, default=60)
    timeout_seconds = Column(Integer, default=30)
    retry_policy_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('tenant_id', 'name', name='uq_tenant_provider_name'),
    )

class ProviderProbeConfig(Base):
    """Health probe configuration for providers."""
    __tablename__ = 'provider_probe_configs'

    provider_id = Column(String(36), ForeignKey('providers.id'), primary_key=True)
    endpoint = Column(String(500), nullable=False)
    method = Column(String(10), default='GET')
    headers_json = Column(Text, nullable=True)
    expected_status = Column(Integer, default=200)
    expected_body_contains = Column(String(500), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class SeatMatrix(Base):
    """Seat assignment matrix configuration."""
    __tablename__ = 'seat_matrices'

    project_id = Column(String(36), ForeignKey('projects.id'), primary_key=True)
    matrix_json = Column(Text, default='{}')
    updated_by = Column(String(36), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### 3.2 Model Modifications

```python
# Existing Org model additions
class Org(Base):
    # ... existing fields ...
    description = Column(Text, nullable=True)  # NEW
    # board_scope_mode already exists

# Existing SeatAssignment modifications
class SeatAssignment(Base):
    # ... existing fields ...
    vacated_at = Column(DateTime, nullable=True)  # NEW - track when vacated
    vacated_by = Column(String(36), nullable=True)  # NEW - who vacated
    vacate_reason = Column(Text, nullable=True)  # NEW - why vacated
    assigned_at = Column(DateTime, nullable=True)  # NEW - when assigned
    assigned_by = Column(String(36), nullable=True)  # NEW - who assigned
```

---

## 4. PRIORITY ORDER FOR IMPLEMENTATION

### PHASE 1: CRITICAL - Foundation & Core Governance (Week 1)

**Blocking frontend functionality, required for basic operations**

1. `GET /v1/orgs/{org_id}` - Single org retrieval
2. `PUT /v1/orgs/{org_id}` - Org updates
3. `GET /v1/seats/{seat_id}` - Single seat retrieval
4. `PUT /v1/seats/{seat_id}` - Seat updates
5. `POST /v1/seats/{seat_id}/assign` - Seat assignment
6. `POST /v1/seats/{seat_id}/vacate` - Seat vacating
7. `POST /v1/seats/bulk` - Bulk seat operations
8. `GET /v1/teams/{team_id}` - Single team retrieval
9. `GET /v1/projects/{project_id}/defaults` - Project defaults
10. `PUT /v1/projects/{project_id}/defaults` - Update defaults

**Models needed:** Seat lifecycle tracking (vacated_at, assigned_at, etc.)

### PHASE 2: CRITICAL - Organization Management (Week 2)

**Required for org administration**

11. `POST /v1/orgs/{org_id}/members` - Board member management
12. `GET /v1/orgs/{org_id}/members` - List board members
13. `PUT /v1/orgs/{org_id}/defaults` - Org policy defaults
14. `GET /v1/orgs/{org_id}/defaults` - Get org defaults
15. `POST /v1/orgs/{org_id}/regions` - Region management
16. `GET /v1/orgs/{org_id}/regions` - List regions
17. `PUT /v1/teams/{team_id}` - Team updates
18. `PUT /v1/teams/{team_id}/scope` - Team scope management

**Models needed:** OrgMember, OrgDefaults, Region, TeamScope

### PHASE 3: HIGH - Security Infrastructure (Week 3)

**Required for security operations**

19. `GET /v1/clearance/tiers` - List clearance tiers
20. `PUT /v1/clearance/tiers` - Update clearance tiers
21. `GET /v1/clearance/compartments` - List compartments
22. `POST /v1/clearance/compartments` - Create compartments
23. `GET /v1/clearance/matrix` - Get NTK matrix
24. `PUT /v1/clearance/matrix` - Update NTK matrix
25. `POST /v1/audit/evidence` - Evidence packages

**Models needed:** ClearanceTier, Compartment, ClearanceMatrix, EvidencePackage

### PHASE 4: HIGH - Providers (Week 4)

**Required for provider management UI**

26. `POST /v1/providers` - Create provider
27. `GET /v1/providers` - List providers
28. `GET /v1/providers/{provider_id}` - Get provider
29. `PUT /v1/providers/{provider_id}` - Update provider
30. `PUT /v1/providers/priority` - Update priority chain

**Models needed:** Provider, ProviderProbeConfig

### PHASE 5: MEDIUM - Extended Features (Week 5-6)

**Nice to have, can be worked around**

31. `POST /v1/providers/{provider_id}/test` - Provider health check
32. `PUT /v1/providers/{provider_id}/config` - Provider configuration
33. `GET /v1/providers/probes` - Get probe config
34. `PUT /v1/providers/probes` - Update probe config
35. `POST /v1/extensions/verify` - Batch extension verification
36. `POST /v1/extensions/batch` - Extension bulk operations
37. `GET /v1/clearance/tiers/{tier_id}` - Single tier
38. `PUT /v1/clearance/compartments/{comp_id}` - Update compartment
39. `GET /v1/clearance/compartments/{comp_id}` - Single compartment
40. `GET /v1/clearance/matrix/export` - Export matrix

### PHASE 6: LOW - Foundation Observability (Week 6)

**Production operations**

41. `GET /health/ready` - K8s readiness
42. `GET /health/live` - K8s liveness
43. `GET /metrics` - Prometheus metrics
44. `GET /version` - Version endpoint

---

## 5. SUMMARY

### Current State

- **21 of 48** Rev9 routes implemented (44%)
- Workers module: **Comprehensive** (25+ endpoints, feature-complete)
- Audit module: **Good** (5 endpoints, core functionality)
- Extensions module: **Basic** (3 endpoints, missing batch ops)
- Policy module: **Minimal** (2 endpoints, core decisioning)
- Governance module: **Severely lacking** (11 of 26 routes - 42%)
- Security/Providers: **Missing entirely** (0 of 10 routes)
- Foundation: **Minimal** (1 of 5 routes)

### Critical Gaps Summary

| Category         | Missing Count | Impact                        |
| ---------------- | ------------- | ----------------------------- |
| Seat Lifecycle   | 5 endpoints   | CRITICAL - Core functionality |
| Org Management   | 6 endpoints   | HIGH - Administration         |
| Clearance System | 10 endpoints  | HIGH - Security               |
| Providers        | 10 endpoints  | MEDIUM - Operations           |
| Foundation       | 4 endpoints   | MEDIUM - Production           |

### Estimated Effort

- **Phase 1:** 3-4 days
- **Phase 2:** 3-4 days
- **Phase 3:** 4-5 days
- **Phase 4:** 3-4 days
- **Phase 5:** 4-5 days
- **Phase 6:** 1-2 days

**Total: ~18-24 days of focused development**

---

## 6. RISKS

| Risk                               | Severity | Likelihood | Impact                            | Mitigation                       |
| ---------------------------------- | -------- | ---------- | --------------------------------- | -------------------------------- |
| **56% of frontend has no backend** | CRITICAL | Certain    | Cannot use 31 UI actions          | Prioritize Phase 1-2 immediately |
| **Seat management incomplete**     | CRITICAL | Certain    | Cannot assign/vacate seats        | Implement assign/vacate first    |
| **No provider backend**            | HIGH     | Certain    | Provider management UI is dead    | Create stub providers.py         |
| **Schema drift**                   | MEDIUM   | Likely     | Frontend expects different fields | Align schemas with frontend      |
| **Clearance system missing**       | HIGH     | Certain    | Security features unavailable     | Phase 3 must be prioritized      |
| **Evidence packages missing**      | MEDIUM   | Possible   | Compliance/legal gap              | Phase 3 implementation           |
| **Missing K8s probes**             | MEDIUM   | Likely     | Deployment issues                 | Phase 6 before production        |

---

## 7. ACTION LIST

### Immediate Actions (This Week)

- [ ] Create `providers.py` router stub (empty endpoints returning 501)
- [ ] Implement `GET /v1/orgs/{org_id}`
- [ ] Implement `PUT /v1/orgs/{org_id}`
- [ ] Implement `PUT /v1/seats/{seat_id}`
- [ ] Implement `POST /v1/seats/{seat_id}/assign`
- [ ] Implement `POST /v1/seats/{seat_id}/vacate`

### Week 2 Actions

- [ ] Add OrgMember, OrgDefaults, Region models
- [ ] Implement board member management
- [ ] Implement org defaults
- [ ] Implement region management
- [ ] Implement team scope

### Week 3 Actions

- [ ] Add ClearanceTier, Compartment, ClearanceMatrix models
- [ ] Implement clearance tier management
- [ ] Implement compartment management
- [ ] Implement NTK matrix
- [ ] Implement evidence packages

### Week 4 Actions

- [ ] Add Provider, ProviderProbeConfig models
- [ ] Implement provider CRUD
- [ ] Implement priority chains
- [ ] Add provider alias compatibility (`{id}` and `{provider}`)

---

## 8. OPEN QUESTIONS

1. **Provider Model**: Does a Provider model exist anywhere? The frontend expects full provider management but no backend model exists.

2. **Board Member Permissions**: What specific permissions should board members have? Is this already defined in the authz system?

3. **Evidence Chain Verification**: Should evidence packages include Merkle proofs? What's the exact chain verification requirement?

4. **Clearance Tier Levels**: Are clearance levels fixed (1-4) or configurable per tenant? What's the default tier setup?

5. **Compartment Hierarchy**: Are compartments hierarchical (parent/child relationships)? How deep can nesting go?

6. **NTK Matrix Permissions**: What are the valid permission levels in the clearance matrix? `['none', 'read', 'write', 'admin']`?

7. **Region Data Residency**: Do regions affect actual data storage location or are they just metadata labels?

8. **Extension Verification**: What does "verify" mean for extensions? Signature re-check? Runtime attestation? Permission validation?

9. **Bulk Operation Limits**: What are the rate limits for bulk seat assignments? Max batch size?

10. **Provider Alias Compatibility**: Should routes accept BOTH `{provider_id}` AND `{provider}` path parameters for backward compatibility?

---

## 9. DELIVERABLES CHECKLIST

- [x] Route-by-route contract analysis
- [x] Schema definitions for missing endpoints
- [x] SQLAlchemy model changes documented
- [x] Priority order for implementation
- [x] Summary statistics
- [x] Risk analysis
- [x] Action list
- [x] Open questions

---

**Document Version:** Rev9-FastAPI-Alignment-v1.0  
**Generated:** 2026-03-07  
**Status:** COMPLETE
