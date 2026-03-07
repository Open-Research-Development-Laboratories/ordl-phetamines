# ORDL Revision 9 - Production Migration Specification
## Mock Implementation to Real ORDL /v1 Backend

**Document Version:** 1.0.0  
**Date:** 2026-03-07  
**Source:** Revision 9 UI Integration / ORDL Backend v1  
**Classification:** Production Migration Spec

---

## 1) SUMMARY

### 1.1 Overview
This document provides the production migration specification for transitioning the Revision 9 UI from its current Flask-based mock implementation to a production-ready integration against the ORDL backend v1 API.

### 1.2 Current State (Mock Implementation)
The Rev9 UI currently integrates with a Flask backend that uses **in-memory Python dictionaries** as data stores:

| Store | File | Type | Data Structure |
|-------|------|------|----------------|
| `orgs_db` | `api.py` | dict | Organization profiles, members, regions, settings |
| `providers_db` | `api.py` | dict | Provider configs, health status, priority chains |
| `extensions_db` | `api.py` | dict | Extension registry, signatures, status |
| `evidence_db` | `api.py` | dict | Evidence packages, chain hashes |

### 1.3 Target State (Production Backend)
All data operations must migrate to the ORDL /v1 REST API with:
- **Persistent database storage** (PostgreSQL via SQLAlchemy models)
- **JWT-based authentication** with clearance levels
- **Real authorization policy engine** integration
- **Audit logging** to persistent store

### 1.4 In-Memory to API Mapping

#### 1.4.1 Organizations (`orgs_db`)

| Mock Operation | Mock Code | Production Endpoint | Method | Auth Required |
|----------------|-----------|---------------------|--------|---------------|
| Get org by ID | `orgs_db[org_id]` | `/v1/orgs/{org_id}` | GET | `org:read` |
| Update org | `orgs_db[org_id].update(data)` | `/v1/orgs/{org_id}` | PUT | `org:write` |
| Update defaults | `orgs_db[org_id]['settings'].update(data)` | `/v1/orgs/{org_id}/defaults` | PUT | `org:admin` |
| Add member | `orgs_db[org_id]['members'].append(...)` | `/v1/orgs/{org_id}/members` | POST | `org:admin` |
| Add region | `orgs_db[org_id]['regions'].append(...)` | `/v1/orgs/{org_id}/regions` | POST | `org:write` |

**Request/Response Payload Mapping:**
```python
# Mock (Flask)
org = orgs_db[org_id]
# Returns: {id, name, short_name, legal_name, tax_id, industry, ...}

# Production API Contract
GET /v1/orgs/{org_id}
# Returns: OrgOut schema
{
  "id": "org_2vH8kL9mN3pQ",
  "name": "Acme Corporation",
  "short_name": "AC",
  "legal_name": "Acme Corporation, Inc.",
  "tax_id": "12-3456789",
  "industry": "Technology",
  "primary_region": "us-east-1",
  "data_residency": "US, EU, APAC",
  "employee_count": 2847,
  "created_at": "2023-01-15T00:00:00Z",
  "updated_at": "2023-01-15T00:00:00Z"
}

PUT /v1/orgs/{org_id}
# Request: OrgUpdate schema
{
  "name": "Updated Corp",
  "legal_name": "Updated Corporation, Inc.",
  "industry": "Technology",
  "primary_region": "us-west-2"
}
```

#### 1.4.2 Providers (`providers_db`)

| Mock Operation | Mock Code | Production Endpoint | Method | Auth Required |
|----------------|-----------|---------------------|--------|---------------|
| List providers | `list(providers_db.values())` | `/v1/providers` | GET | `provider:read` |
| Get provider | `providers_db[provider_id]` | `/v1/providers/{provider_id}` | GET | `provider:read` |
| Create provider | `providers_db[new_id] = {...}` | `/v1/providers` | POST | `provider:admin` |
| Update provider | `providers_db[id].update(...)` | `/v1/providers/{provider_id}` | PUT | `provider:write` |
| Delete provider | `del providers_db[id]` | `/v1/providers/{provider_id}` | DELETE | `provider:admin` |
| Update priority | Loop update priority field | `/v1/providers/priority` | PUT | `provider:admin` |
| Test provider | Simulated health check | `/v1/providers/{provider_id}/test` | POST | `provider:read` |
| Update config | `providers_db[id]['config'].update(...)` | `/v1/providers/{provider_id}/config` | PUT | `provider:write` |
| Get probes | Static config return | `/v1/providers/probes` | GET | `provider:read` |
| Update probes | Config update | `/v1/providers/probes` | PUT | `provider:admin` |

**Provider Schema Changes:**
```python
# Mock (in-memory dict)
{
  "id": "prov_001",
  "name": "OpenAI GPT-4",
  "type": "openai",
  "priority": 1,
  "status": "healthy",
  "auth": "valid",
  "latency": 18,
  "rps": 500,
  "config": {"api_key_ref": "vault://...", "base_url": "..."}
}

# Production (ORM model via API)
ProviderOut {
  id: str
  name: str
  provider_type: str  # Note: field name change from 'type'
  config: dict  # Encrypted at rest
  priority: int
  region: str | None
  status: str  # 'active', 'inactive', 'degraded', 'failed'
  health_status: dict  # Last health check result
  last_health_check_at: str | None
  health_check_enabled: bool
  created_at: str
  updated_at: str
}
```

#### 1.4.3 Extensions (`extensions_db`)

| Mock Operation | Mock Code | Production Endpoint | Method | Auth Required |
|----------------|-----------|---------------------|--------|---------------|
| List extensions | `list(extensions_db.values())` | `/v1/extensions` | GET | `extension:read` |
| Get extension | `extensions_db[ext_id]` | `/v1/extensions/{ext_id}` | GET | `extension:read` |
| Register extension | `extensions_db[new_id] = {...}` | `/v1/extensions` | POST | `extension:admin` |
| Update extension | `extensions_db[id].update(...)` | `/v1/extensions/{ext_id}` | PUT | `extension:write` |
| Delete extension | `del extensions_db[id]` | `/v1/extensions/{ext_id}` | DELETE | `extension:admin` |
| Verify signatures | Simulated verification | `/v1/extensions/verify` | POST | `extension:write` |
| Batch operations | Loop operations | `/v1/extensions/batch` | POST | `extension:write` |

**Extension Verification Mapping:**
```python
# Mock verification
verified = ext.get('signature') == 'verified'

# Production verification
POST /v1/extensions/verify
Request: {
  "extension_ids": ["ext_001", "ext_002"],
  "verify_signatures": true,
  "verify_permissions": true
}
Response: {
  "total": 2,
  "valid": 2,
  "invalid": 0,
  "results": [
    {
      "extension_id": "ext_001",
      "name": "OpenAPI Spec Validator",
      "valid": true,
      "signature_valid": true,
      "permissions_valid": true,
      "errors": []
    }
  ]
}
```

#### 1.4.4 Evidence (`evidence_db`)

| Mock Operation | Mock Code | Production Endpoint | Method | Auth Required |
|----------------|-----------|---------------------|--------|---------------|
| Create evidence | `evidence_db[evidence_id] = {...}` | `/v1/audit/evidence` | POST | `audit:write` |
| Get evidence | `evidence_db[evidence_id]` | `/v1/audit/evidence/{evidence_id}` | GET | `audit:read` |
| Download evidence | Simulated URL | `/v1/audit/evidence/{evidence_id}/download` | GET | `audit:read` |

**Evidence Creation Mapping:**
```python
# Mock evidence creation
evidence_id = f"evp_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{len(evidence_db) + 1}"
chain_hash = hashlib.sha256(...).hexdigest()
evidence_db[evidence_id] = {...}

# Production evidence creation
POST /v1/audit/evidence
Request: {
  "event_ids": ["evt-1", "evt-2"],
  "format": "json",  # or 'pdf', 'chain'
  "include_chain_verification": true,
  "include_raw_events": true,
  "description": "Incident investigation evidence",
  "expires_at": "2027-03-07T00:00:00Z"
}
Response: {
  "id": "evp_abc123",
  "project_id": "proj_001",
  "format": "json",
  "description": "Incident investigation evidence",
  "event_count": 2,
  "events_included": ["evt-1", "evt-2"],
  "chain_verification": {
    "valid": true,
    "checked_at": "2026-03-07T05:53:00Z",
    "broken_at": null
  },
  "package_hash": "sha256:abc123...",
  "signature": "signed_by_evidence_officer",
  "expires_at": "2027-03-07T00:00:00Z",
  "download_url": "/v1/audit/evidence/evp_abc123/download",
  "created_at": "2026-03-07T05:53:00Z",
  "created_by": "user_001"
}
```

### 1.5 Authorization Boundary Changes

#### 1.5.1 Current Mock Authorization
```python
# Current Flask implementation
def evaluate_authorization(resource_type, action, resource_id=None, org_id=None):
    # Mock user context from g (Flask global)
    user_context = {
        'user_id': g.get('user_id', 'anonymous'),
        'clearance_level': g.get('clearance_level', 1),
        'compartments': g.get('compartments', []),
        'is_admin': g.get('is_admin', False),
        'org_memberships': g.get('org_memberships', [])
    }
    
    # Admin bypass
    if user_context['is_admin']:
        return {'allowed': True, 'reason': 'admin_override'}
    
    # Clearance level checks (hardcoded matrix)
    clearance_requirements = {
        'org': {'read': 1, 'write': 3, 'delete': 4, 'admin': 5},
        'provider': {'read': 2, 'write': 3, 'delete': 4, 'admin': 5},
        'extension': {'read': 1, 'write': 2, 'delete': 3, 'admin': 4},
        'audit': {'read': 3, 'write': 4, 'delete': 5, 'admin': 5}
    }
```

#### 1.5.2 Production Authorization
```python
# Production: JWT validation + Policy Engine
def require_auth(resource_type: str, action: str):
    """Production decorator using JWT and policy engine."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 1. Extract JWT from Authorization header
            auth_header = request.headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                return jsonify({'error': 'Missing or invalid authorization'}), 401
            
            token = auth_header[7:]
            
            # 2. Validate JWT (signature, expiry, issuer)
            try:
                payload = jwt.decode(token, PUBLIC_KEY, algorithms=['RS256'])
            except jwt.ExpiredSignatureError:
                return jsonify({'error': 'Token expired'}), 401
            except jwt.InvalidTokenError:
                return jsonify({'error': 'Invalid token'}), 401
            
            # 3. Extract claims
            user_id = payload.get('sub')
            clearance_level = payload.get('clearance_level', 1)
            compartments = payload.get('compartments', [])
            org_memberships = payload.get('org_memberships', [])
            
            # 4. Call policy engine for decision
            org_id = kwargs.get('org_id')
            resource_id = kwargs.get('id') or kwargs.get('provider_id') or kwargs.get('ext_id')
            
            policy_request = {
                'subject': {
                    'id': user_id,
                    'clearance_level': clearance_level,
                    'compartments': compartments,
                    'org_memberships': org_memberships
                },
                'resource': {
                    'type': resource_type,
                    'id': resource_id,
                    'org_id': org_id
                },
                'action': action
            }
            
            # 5. Query policy engine
            policy_response = requests.post(
                'http://policy-engine:8080/v1/decide',
                json=policy_request,
                timeout=5
            )
            
            if policy_response.status_code != 200:
                return jsonify({'error': 'Policy engine unavailable'}), 503
            
            decision = policy_response.json()
            
            if not decision.get('allowed', False):
                return jsonify({
                    'error': 'Forbidden',
                    'reason': decision.get('reason', 'policy_denied'),
                    'resource_type': resource_type,
                    'action': action
                }), 403
            
            # 6. Store auth context for audit logging
            g.user_id = user_id
            g.clearance_level = clearance_level
            g.compartments = compartments
            g.auth_decision = decision
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator
```

### 1.6 Required Database Models

The following SQLAlchemy models must be implemented in production:

```python
# Organization Models
class Org(Base):
    __tablename__ = 'orgs'
    id = Column(String(36), primary_key=True)
    name = Column(String(200), nullable=False)
    short_name = Column(String(50))
    legal_name = Column(String(300))
    tax_id = Column(String(50))
    industry = Column(String(100))
    primary_region = Column(String(50))
    data_residency = Column(String(200))
    employee_count = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class OrgMember(Base):
    __tablename__ = 'org_members'
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id = Column(String(36), ForeignKey('orgs.id'), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey('users.id'), nullable=False, index=True)
    role = Column(String(50), nullable=False)  # board_member, board_observer, security_admin
    permissions_json = Column(Text, default='[]')
    term_expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class OrgDefaults(Base):
    __tablename__ = 'org_defaults'
    org_id = Column(String(36), ForeignKey('orgs.id'), primary_key=True)
    default_clearance_tier = Column(String(50))
    default_compartments_json = Column(Text, default='[]')
    require_approval_for_high_risk = Column(Boolean, default=True)
    auto_escalation_enabled = Column(Boolean, default=False)
    session_timeout_minutes = Column(Integer, default=30)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Region(Base):
    __tablename__ = 'regions'
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id = Column(String(36), ForeignKey('orgs.id'), nullable=False, index=True)
    region_code = Column(String(50), nullable=False)
    name = Column(String(200), nullable=False)
    datacenter_codes_json = Column(Text, default='[]')
    compliance_frameworks_json = Column(Text, default='[]')
    status = Column(String(50), default='active')
    created_at = Column(DateTime, default=datetime.utcnow)

# Provider Models
class Provider(Base):
    __tablename__ = 'providers'
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey('tenants.id'), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    provider_type = Column(String(50), nullable=False)  # 'ai', 'storage', 'compute', 'gateway'
    config_json = Column(Text, default='{}')  # Encrypted configuration
    priority = Column(Integer, default=0)
    region = Column(String(50))
    status = Column(String(50), default='active')
    health_status_json = Column(Text)
    last_health_check_at = Column(DateTime)
    health_check_enabled = Column(Boolean, default=True)
    health_check_interval_seconds = Column(Integer, default=60)
    timeout_seconds = Column(Integer, default=30)
    retry_policy_json = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ProviderProbeConfig(Base):
    __tablename__ = 'provider_probe_configs'
    provider_id = Column(String(36), ForeignKey('providers.id'), primary_key=True)
    endpoint = Column(String(500), nullable=False)
    method = Column(String(10), default='GET')
    headers_json = Column(Text)
    expected_status = Column(Integer, default=200)
    expected_body_contains = Column(String(500))
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Extension Models
class Extension(Base):
    __tablename__ = 'extensions'
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey('tenants.id'), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    extension_type = Column(String(50), nullable=False)  # 'plugin', 'skill'
    version = Column(String(50), nullable=False)
    author = Column(String(200))
    signature = Column(String(500))
    signature_valid = Column(Boolean)
    status = Column(String(50), default='active')
    scopes_json = Column(Text, default='[]')
    config_json = Column(Text, default='{}')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Evidence Model
class EvidencePackage(Base):
    __tablename__ = 'evidence_packages'
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey('projects.id'), nullable=False, index=True)
    created_by = Column(String(36), ForeignKey('users.id'), nullable=False)
    format = Column(String(20), nullable=False)  # 'json', 'pdf', 'chain'
    description = Column(Text)
    event_ids_json = Column(Text, nullable=False)
    chain_verification_json = Column(Text)
    package_hash = Column(String(128))  # Merkle root
    signature = Column(Text)
    expires_at = Column(DateTime)
    storage_path = Column(String(500))  # S3 or file path
    created_at = Column(DateTime, default=datetime.utcnow)
```

---

## 2) RISKS

### 2.1 Critical Risks

| Risk | Severity | Likelihood | Impact | Mitigation |
|------|----------|------------|--------|------------|
| **Data Loss on Migration** | CRITICAL | Low | Complete loss of mock data | Export in-memory data before shutdown; implement migration scripts |
| **Authorization Bypass** | CRITICAL | Medium | Unauthorized access to resources | Full JWT validation audit; policy engine integration testing |
| **API Contract Mismatch** | CRITICAL | High | Frontend breakage, 500 errors | Schema validation layer; integration test suite |
| **Provider Secrets Exposure** | CRITICAL | Medium | API keys leaked in logs/configs | Vault integration; encrypted config storage; audit logging |

### 2.2 High Risks

| Risk | Severity | Likelihood | Impact | Mitigation |
|------|----------|------------|--------|------------|
| **Performance Degradation** | HIGH | Medium | Slow UI response, timeouts | Database indexing; connection pooling; caching layer |
| **Evidence Tampering** | HIGH | Low | Legal/compliance failure | Immutable storage (S3 with versioning); cryptographic signatures |
| **JWT Secret Compromise** | HIGH | Low | Session hijacking, impersonation | HSM for key storage; regular key rotation; short expiry |
| **Batch Operation Failures** | HIGH | Medium | Partial data updates, inconsistencies | Transaction wrapping; rollback capability; idempotency keys |
| **Audit Log Gaps** | HIGH | Medium | Compliance violations | Middleware-based audit logging; log shipping to SIEM |

### 2.3 Medium Risks

| Risk | Severity | Likelihood | Impact | Mitigation |
|------|----------|------------|--------|------------|
| **Rate Limiting Bypass** | MEDIUM | Medium | DoS vulnerability | Flask-Limiter or API gateway rate limiting |
| **Provider Health Check Failures** | MEDIUM | High | False negatives in failover | Retry logic; circuit breaker pattern |
| **Extension Signature Validation** | MEDIUM | Medium | Malicious extension execution | Offline CA validation; certificate pinning |
| **Regional Data Residency** | MEDIUM | Medium | GDPR/compliance violations | Region-aware routing; data classification |
| **Cache Invalidation** | MEDIUM | Medium | Stale data display | TTL-based caching; explicit invalidation on writes |

### 2.4 Risk Matrix Visualization

```
Impact
   |
 H |  [Auth Bypass]  [API Mismatch]
   |  [Secrets Exp]
   |
 M |  [Perf Deg]    [Batch Fail]
   |  [Evidence Tam]  [Audit Gaps]
   |
 L |  [Rate Limit]
   |_____________________________
     L      M      H
           Likelihood
```

---

## 3) ACTION LIST

### 3.1 Backend Migration Actions

#### Phase 1: Database Schema (Week 1)

| # | Action | Priority | Owner | Deliverable |
|---|--------|----------|-------|-------------|
| 1.1 | Create SQLAlchemy models for Org, OrgMember, OrgDefaults, Region | CRITICAL | Backend | models/governance.py |
| 1.2 | Create SQLAlchemy models for Provider, ProviderProbeConfig | CRITICAL | Backend | models/security.py |
| 1.3 | Create SQLAlchemy models for Extension | CRITICAL | Backend | models/security.py |
| 1.4 | Create SQLAlchemy models for EvidencePackage | CRITICAL | Backend | models/audit.py |
| 1.5 | Generate Alembic migrations | CRITICAL | Backend | migrations/versions/ |
| 1.6 | Implement database connection pooling | HIGH | Backend | config/database.py |

#### Phase 2: API Implementation (Week 2-3)

| # | Action | Priority | Owner | Deliverable |
|---|--------|----------|-------|-------------|
| 2.1 | Implement `/v1/orgs/{org_id}` GET/PUT | CRITICAL | Backend | routers/orgs.py |
| 2.2 | Implement `/v1/orgs/{org_id}/members` POST | CRITICAL | Backend | routers/orgs.py |
| 2.3 | Implement `/v1/orgs/{org_id}/defaults` PUT | CRITICAL | Backend | routers/orgs.py |
| 2.4 | Implement `/v1/orgs/{org_id}/regions` POST | CRITICAL | Backend | routers/orgs.py |
| 2.5 | Implement `/v1/providers` full CRUD | CRITICAL | Backend | routers/providers.py |
| 2.6 | Implement `/v1/providers/{provider_id}/test` POST | HIGH | Backend | routers/providers.py |
| 2.7 | Implement `/v1/providers/{provider_id}/config` PUT | HIGH | Backend | routers/providers.py |
| 2.8 | Implement `/v1/providers/priority` PUT | HIGH | Backend | routers/providers.py |
| 2.9 | Implement `/v1/extensions/verify` POST | MEDIUM | Backend | routers/extensions.py |
| 2.10 | Implement `/v1/extensions/batch` POST | MEDIUM | Backend | routers/extensions.py |
| 2.11 | Implement `/v1/audit/evidence` POST | HIGH | Backend | routers/audit.py |

#### Phase 3: Authentication & Authorization (Week 3)

| # | Action | Priority | Owner | Deliverable |
|---|--------|----------|-------|-------------|
| 3.1 | Implement JWT validation middleware | CRITICAL | Backend | middleware/auth.py |
| 3.2 | Integrate with policy engine | CRITICAL | Backend | services/policy.py |
| 3.3 | Add clearance level checks | CRITICAL | Backend | decorators/auth.py |
| 3.4 | Implement compartment-based access control | HIGH | Backend | decorators/auth.py |
| 3.5 | Add audit logging middleware | HIGH | Backend | middleware/audit.py |
| 3.6 | Implement JWT refresh token flow | MEDIUM | Backend | routers/auth.py |

#### Phase 4: Security Hardening (Week 4)

| # | Action | Priority | Owner | Deliverable |
|---|--------|----------|-------|-------------|
| 4.1 | Integrate HashiCorp Vault for secrets | CRITICAL | Backend | services/vault.py |
| 4.2 | Encrypt provider config at rest | CRITICAL | Backend | models/security.py |
| 4.3 | Implement API rate limiting | HIGH | Backend | middleware/rate_limit.py |
| 4.4 | Add request/response logging | HIGH | Backend | middleware/logging.py |
| 4.5 | Implement input validation (Pydantic) | HIGH | Backend | schemas/*.py |
| 4.6 | Add CORS configuration | MEDIUM | Backend | config/cors.py |
| 4.7 | Implement request ID tracing | MEDIUM | Backend | middleware/tracing.py |

#### Phase 5: Evidence & Compliance (Week 4)

| # | Action | Priority | Owner | Deliverable |
|---|--------|----------|-------|-------------|
| 5.1 | Implement S3 storage backend for evidence | HIGH | Backend | services/storage.py |
| 5.2 | Add Merkle tree chain verification | HIGH | Backend | services/chain.py |
| 5.3 | Implement evidence package signing | HIGH | Backend | services/crypto.py |
| 5.4 | Add evidence expiration/retention | MEDIUM | Backend | jobs/evidence_cleanup.py |
| 5.5 | Implement tamper-evident logging | MEDIUM | Backend | services/audit_logger.py |

### 3.2 Frontend Integration Actions

#### Phase 1: API Client Updates (Week 1)

| # | Action | Priority | Owner | Deliverable |
|---|--------|----------|-------|-------------|
| F1.1 | Update `governanceApi.getOrganization()` to call `/v1/orgs/{org_id}` | CRITICAL | Frontend | js/api/governance.js |
| F1.2 | Update `governanceApi.updateOrganization()` to call `/v1/orgs/{org_id}` | CRITICAL | Frontend | js/api/governance.js |
| F1.3 | Update `governanceApi.addBoardMember()` to call `/v1/orgs/{org_id}/members` | CRITICAL | Frontend | js/api/governance.js |
| F1.4 | Update `governanceApi.updatePolicyDefaults()` to call `/v1/orgs/{org_id}/defaults` | CRITICAL | Frontend | js/api/governance.js |
| F1.5 | Update `governanceApi.addRegion()` to call `/v1/orgs/{org_id}/regions` | CRITICAL | Frontend | js/api/governance.js |

#### Phase 2: Provider API Integration (Week 2)

| # | Action | Priority | Owner | Deliverable |
|---|--------|----------|-------|-------------|
| F2.1 | Update `securityApi.createProvider()` to call `/v1/providers` | CRITICAL | Frontend | js/api/security.js |
| F2.2 | Update `securityApi.getProvider()` to call `/v1/providers/{id}` | CRITICAL | Frontend | js/api/security.js |
| F2.3 | Update `securityApi.updateProvider()` to call `/v1/providers/{id}` | CRITICAL | Frontend | js/api/security.js |
| F2.4 | Update `securityApi.updateFailoverPriority()` to call `/v1/providers/priority` | HIGH | Frontend | js/api/security.js |
| F2.5 | Update `securityApi.testProvider()` to call `/v1/providers/{id}/test` | HIGH | Frontend | js/api/security.js |
| F2.6 | Update `securityApi.updateProviderConfig()` to call `/v1/providers/{id}/config` | HIGH | Frontend | js/api/security.js |

#### Phase 3: Extension & Evidence Integration (Week 2-3)

| # | Action | Priority | Owner | Deliverable |
|---|--------|----------|-------|-------------|
| F3.1 | Update `securityApi.verifyExtensions()` to call `/v1/extensions/verify` | MEDIUM | Frontend | js/api/security.js |
| F3.2 | Update `securityApi.batchExtensions()` to call `/v1/extensions/batch` | MEDIUM | Frontend | js/api/security.js |
| F3.3 | Update `securityApi.createEvidence()` to call `/v1/audit/evidence` | HIGH | Frontend | js/api/security.js |
| F3.4 | Handle evidence download URLs | HIGH | Frontend | js/api/security.js |

#### Phase 4: Authentication Integration (Week 3)

| # | Action | Priority | Owner | Deliverable |
|---|--------|----------|-------|-------------|
| F4.1 | Implement JWT token storage (httpOnly cookie) | CRITICAL | Frontend | js/auth/token.js |
| F4.2 | Add Authorization header to all API calls | CRITICAL | Frontend | js/api/client.js |
| F4.3 | Implement token refresh logic | HIGH | Frontend | js/auth/refresh.js |
| F4.4 | Handle 401/403 responses with redirect to login | HIGH | Frontend | js/auth/guard.js |
| F4.5 | Add clearance level indicators to UI | MEDIUM | Frontend | js/ui/clearance.js |

#### Phase 5: Error Handling & UX (Week 3-4)

| # | Action | Priority | Owner | Deliverable |
|---|--------|----------|-------|-------------|
| F5.1 | Update error handling for new API error formats | HIGH | Frontend | js/api/errors.js |
| F5.2 | Add loading states for async operations | MEDIUM | Frontend | js/ui/spinner.js |
| F5.3 | Implement optimistic updates for better UX | LOW | Frontend | js/ui/optimistic.js |
| F5.4 | Add retry logic for transient failures | MEDIUM | Frontend | js/api/retry.js |
| F5.5 | Implement request deduplication | LOW | Frontend | js/api/dedup.js |

### 3.3 Testing Actions

| # | Action | Priority | Owner | Deliverable |
|---|--------|----------|-------|-------------|
| T1 | Write unit tests for all new API endpoints | CRITICAL | QA | tests/routers/ |
| T2 | Write integration tests for auth flow | CRITICAL | QA | tests/integration/auth/ |
| T3 | Write contract tests (Pact) for frontend-backend | HIGH | QA | tests/contract/ |
| T4 | Perform penetration testing on auth endpoints | CRITICAL | Security | pentest-report.md |
| T5 | Load test batch operations | HIGH | QA | tests/load/batch_ops.py |
| T6 | Verify audit log completeness | HIGH | QA | tests/audit/completeness.py |

### 3.4 Deployment Actions

| # | Action | Priority | Owner | Deliverable |
|---|--------|----------|-------|-------------|
| D1 | Set up production database | CRITICAL | DevOps | terraform/rds.tf |
| D2 | Configure Vault for secrets | CRITICAL | DevOps | terraform/vault.tf |
| D3 | Set up S3 bucket for evidence | HIGH | DevOps | terraform/s3.tf |
| D4 | Configure API gateway | HIGH | DevOps | terraform/apigw.tf |
| D5 | Set up monitoring/alerting | HIGH | DevOps | terraform/monitoring.tf |
| D6 | Create runbook for incident response | MEDIUM | DevOps | docs/runbook.md |
| D7 | Perform blue-green deployment | HIGH | DevOps | deployment script |

---

## 4) OPEN QUESTIONS

### 4.1 Architecture Questions

| # | Question | Impact | Suggested Resolution |
|---|----------|--------|---------------------|
| 4.1.1 | **What is the canonical source for JWT public keys?** Is it the policy engine, a dedicated auth service, or should the API validate against a JWKS endpoint? | Authentication flow | Define JWKS endpoint URL; implement key rotation schedule |
| 4.1.2 | **How should the policy engine be called?** Is it an HTTP call to a separate service, a gRPC call, or a sidecar container? | Authorization latency | Document policy engine service discovery; set timeout budgets |
| 4.1.3 | **What is the database architecture?** Single PostgreSQL instance, read replicas, or distributed (CockroachDB)? | Performance, HA | Define RTO/RPO; select appropriate architecture |
| 4.1.4 | **Should evidence packages be stored encrypted?** If so, what is the key management strategy? | Compliance, security | Define encryption at rest requirements; integrate with KMS |
| 4.1.5 | **What is the expected QPS for batch operations?** This affects rate limiting and database connection pooling. | Capacity planning | Gather traffic estimates; configure limits accordingly |

### 4.2 Data Model Questions

| # | Question | Impact | Suggested Resolution |
|---|----------|--------|---------------------|
| 4.2.1 | **Are compartment hierarchies supported?** The mock code suggests flat compartments, but the schema has `parent_id`. | Clearance model | Confirm hierarchy depth limit; update UI if needed |
| 4.2.2 | **What is the maximum batch size for extensions and seats?** Mock code uses 100, but is this the production limit? | API limits | Define and document MAX_BATCH_SIZE constants |
| 4.2.3 | **How are provider secrets rotated?** Is there an automated process or manual procedure? | Security operations | Document rotation SOP; implement if automated |
| 4.2.4 | **What is the retention policy for evidence packages?** 3 years? 7 years? Configurable per org? | Storage costs | Define retention tiers; implement lifecycle policies |
| 4.2.5 | **Are audit logs immutable once written?** Can administrators delete or modify audit entries? | Compliance | Implement WORM storage; document immutability guarantees |

### 4.3 Integration Questions

| # | Question | Impact | Suggested Resolution |
|---|----------|--------|---------------------|
| 4.3.1 | **What certificate authority signs extension signatures?** Is it an internal CA, or do extensions use code signing certs from public CAs? | Extension trust model | Document CA chain; implement cert pinning if internal |
| 4.3.2 | **How are provider health checks performed?** Is there a background job, or are checks done on-demand? | Provider reliability | Implement health check daemon; define check frequency |
| 4.3.3 | **What happens when evidence chain verification fails?** Is the evidence package rejected, flagged, or still delivered with warnings? | Evidence integrity | Define failure modes; update API response schema |
| 4.3.4 | **Is there a webhook system for async operations?** For long-running batch operations, how is completion communicated? | UX for batch ops | Define webhook payload format; implement if needed |
| 4.3.5 | **What is the provider alias requirement?** The mock code supports both `{id}` and `{provider}` path parameters. Is backward compatibility required? | API design | Confirm alias requirement; document deprecation timeline |

### 4.4 Security Questions

| # | Question | Impact | Suggested Resolution |
|---|----------|--------|---------------------|
| 4.4.1 | **What clearance levels exist in production?** Mock uses L1-L5, but are these fixed or configurable per tenant? | Authorization model | Define clearance schema; implement if configurable |
| 4.4.2 | **What specific permissions does each role have?** Board member, security admin, etc. - what can they actually do? | RBAC implementation | Document permission matrix; implement in policy engine |
| 4.4.3 | **Are there any cross-origin requirements for the API?** What domains should be allowed in CORS? | Browser security | Define allowed origins; implement CORS config |
| 4.4.4 | **What is the session timeout strategy?** JWT expiry, refresh tokens, or sliding sessions? | User experience | Define session policy; implement accordingly |
| 4.4.5 | **Is MFA required for admin operations?** The mock code has `require_mfa` in settings - is this enforced? | Access security | Implement MFA challenge for sensitive operations |

### 4.5 Operational Questions

| # | Question | Impact | Suggested Resolution |
|---|----------|--------|---------------------|
| 4.5.1 | **What is the rollback strategy if migration fails?** Can we revert to the mock implementation quickly? | Deployment risk | Implement feature flags; prepare rollback procedures |
| 4.5.2 | **How do we migrate existing mock data to production?** Is there an export/import process? | Data continuity | Write migration scripts; test with staging data |
| 4.5.3 | **What monitoring metrics are required?** Error rates, latency, auth failures? | Observability | Define SLIs/SLOs; implement metric collection |
| 4.5.4 | **What is the disaster recovery plan?** Database backups, evidence storage recovery? | Business continuity | Document DR procedures; test recovery quarterly |
| 4.5.5 | **How are API changes versioned?** Will there be a /v2, or is the contract stable? | API evolution | Document versioning policy; implement deprecation headers |

### 4.6 Frontend-Specific Questions

| # | Question | Impact | Suggested Resolution |
|---|----------|--------|---------------------|
| 4.6.1 | **What is the expected JWT payload format?** What claims are available for the frontend to use? | Client-side auth | Document JWT schema; update auth library |
| 4.6.2 | **How should the frontend handle token expiration during long-running operations?** Auto-refresh or prompt re-login? | UX | Implement silent refresh; handle 401 gracefully |
| 4.6.3 | **Are there any specific error codes the frontend should handle specially?** Rate limit (429), auth (401/403), etc.? | Error handling | Document error codes; implement specific handlers |
| 4.6.4 | **What is the pagination strategy for large lists?** Cursor-based or offset-based? | Performance | Implement consistent pagination; update list components |
| 4.6.5 | **Should the frontend cache any data?** If so, what is the cache invalidation strategy? | Performance vs consistency | Define caching policy; implement with TTL |

---

## Appendix A: Full API Contract Reference

### A.1 Organization Endpoints

```yaml
GET /v1/orgs/{org_id}:
  summary: Get organization by ID
  auth: org:read
  responses:
    200:
      content:
        application/json:
          schema: OrgOut
    404:
      description: Organization not found

PUT /v1/orgs/{org_id}:
  summary: Update organization
  auth: org:write
  requestBody:
    content:
      application/json:
        schema: OrgUpdate
  responses:
    200:
      content:
        application/json:
          schema: OrgOut
    403:
      description: Insufficient clearance

PUT /v1/orgs/{org_id}/defaults:
  summary: Update organization defaults
  auth: org:admin
  requestBody:
    content:
      application/json:
        schema: OrgDefaultsUpdate
  responses:
    200:
      content:
        application/json:
          schema: OrgDefaultsOut

POST /v1/orgs/{org_id}/members:
  summary: Add organization member
  auth: org:admin
  requestBody:
    content:
      application/json:
        schema: OrgMemberCreate
  responses:
    201:
      content:
        application/json:
          schema: OrgMemberOut
    409:
      description: User already a member

POST /v1/orgs/{org_id}/regions:
  summary: Add region to organization
  auth: org:write
  requestBody:
    content:
      application/json:
        schema: RegionCreate
  responses:
    201:
      content:
        application/json:
          schema: RegionOut
    409:
      description: Region already exists
```

### A.2 Provider Endpoints

```yaml
GET /v1/providers:
  summary: List providers
  auth: provider:read
  responses:
    200:
      content:
        application/json:
          schema: list[ProviderOut]

POST /v1/providers:
  summary: Create provider
  auth: provider:admin
  requestBody:
    content:
      application/json:
        schema: ProviderCreate
  responses:
    201:
      content:
        application/json:
          schema: ProviderOut

GET /v1/providers/{provider_id}:
  summary: Get provider by ID
  auth: provider:read
  responses:
    200:
      content:
        application/json:
          schema: ProviderOut

PUT /v1/providers/{provider_id}:
  summary: Update provider
  auth: provider:write
  requestBody:
    content:
      application/json:
        schema: ProviderUpdate
  responses:
    200:
      content:
        application/json:
          schema: ProviderOut

DELETE /v1/providers/{provider_id}:
  summary: Delete provider
  auth: provider:admin
  responses:
    200:
      content:
        application/json:
          schema: '{"deleted": true}'

PUT /v1/providers/priority:
  summary: Update provider priority chain
  auth: provider:admin
  requestBody:
    content:
      application/json:
        schema: ProviderPriorityUpdate
  responses:
    200:
      content:
        application/json:
          schema: list[ProviderOut]

POST /v1/providers/{provider_id}/test:
  summary: Test provider connectivity
  auth: provider:read
  requestBody:
    content:
      application/json:
        schema: '{"test_type": "connectivity|auth|inference"}'
  responses:
    200:
      content:
        application/json:
          schema: ProviderTestOut

PUT /v1/providers/{provider_id}/config:
  summary: Update provider configuration
  auth: provider:write
  requestBody:
    content:
      application/json:
        schema: ProviderConfigUpdate
  responses:
    200:
      content:
        application/json:
          schema: ProviderOut
```

### A.3 Extension Endpoints

```yaml
POST /v1/extensions/verify:
  summary: Verify extension signatures
  auth: extension:write
  requestBody:
    content:
      application/json:
        schema: ExtensionVerifyRequest
  responses:
    200:
      content:
        application/json:
          schema: VerifyResultOut

POST /v1/extensions/batch:
  summary: Batch operations on extensions
  auth: extension:write
  requestBody:
    content:
      application/json:
        schema: ExtensionBatchRequest
  responses:
    200:
      content:
        application/json:
          schema: BatchResultOut
```

### A.4 Evidence Endpoints

```yaml
POST /v1/audit/evidence:
  summary: Create evidence package
  auth: audit:write
  requestBody:
    content:
      application/json:
        schema: EvidenceCreate
  responses:
    201:
      content:
        application/json:
          schema: EvidencePackageOut
```

---

## Appendix B: Schema Definitions

### B.1 Organization Schemas

```python
class OrgOut(BaseModel):
    id: str
    name: str
    short_name: str | None
    legal_name: str | None
    tax_id: str | None
    industry: str | None
    primary_region: str | None
    data_residency: str | None
    employee_count: int | None
    created_at: str
    updated_at: str

class OrgUpdate(BaseModel):
    name: str | None = None
    short_name: str | None = None
    legal_name: str | None = None
    tax_id: str | None = None
    industry: str | None = None
    primary_region: str | None = None
    data_residency: str | None = None
    employee_count: int | None = None

class OrgDefaultsOut(BaseModel):
    org_id: str
    default_clearance_tier: str | None
    default_compartments: list[str]
    require_approval_for_high_risk: bool
    auto_escalation_enabled: bool
    session_timeout_minutes: int
    updated_at: str

class OrgDefaultsUpdate(BaseModel):
    default_clearance_tier: str | None = None
    default_compartments: list[str] | None = None
    require_approval_for_high_risk: bool | None = None
    auto_escalation_enabled: bool | None = None
    session_timeout_minutes: int | None = None

class OrgMemberOut(BaseModel):
    id: str
    org_id: str
    user_id: str
    role: str
    permissions: list[str]
    term_expires_at: str | None
    created_at: str

class OrgMemberCreate(BaseModel):
    user_id: str
    role: str  # 'board_member', 'board_observer', 'security_admin'
    permissions: list[str] | None = None
    term_expires_at: datetime | None = None

class RegionOut(BaseModel):
    id: str
    org_id: str
    region_code: str
    name: str
    datacenter_codes: list[str]
    compliance_frameworks: list[str]
    status: str
    created_at: str

class RegionCreate(BaseModel):
    region_code: str
    name: str
    datacenter_codes: list[str] | None = None
    compliance_frameworks: list[str] | None = None
```

### B.2 Provider Schemas

```python
class ProviderOut(BaseModel):
    id: str
    name: str
    provider_type: str
    config: dict  # Masked in responses
    priority: int
    region: str | None
    status: str
    health_status: dict | None
    last_health_check_at: str | None
    health_check_enabled: bool
    created_at: str
    updated_at: str

class ProviderCreate(BaseModel):
    name: str
    provider_type: str
    config: dict
    priority: int = 0
    region: str | None = None
    health_check_enabled: bool = True

class ProviderUpdate(BaseModel):
    name: str | None = None
    config: dict | None = None
    priority: int | None = None
    region: str | None = None
    status: str | None = None

class ProviderPriorityUpdate(BaseModel):
    providers: list[ProviderPriorityItem]

class ProviderPriorityItem(BaseModel):
    provider_id: str
    priority: int

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
    merge: bool = False
```

### B.3 Extension Schemas

```python
class ExtensionVerifyRequest(BaseModel):
    extension_ids: list[str]
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
    status: str
    previous_status: str | None
    error: str | None
```

### B.4 Evidence Schemas

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
    chain_verification: dict
    package_hash: str
    signature: str | None
    expires_at: str | None
    download_url: str
    created_at: str
    created_by: str
```

---

**End of Document**

*This specification maps the Revision 9 mock implementation to the ORDL /v1 production backend. All in-memory stores, mock authentication, and Flask-specific code must be migrated according to this document.*
