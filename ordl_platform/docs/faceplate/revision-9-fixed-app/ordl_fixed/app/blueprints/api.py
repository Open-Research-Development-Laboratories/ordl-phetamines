"""API blueprint - REST API endpoints with /v1 prefix."""
from flask import Blueprint, jsonify, request, g
from datetime import datetime
from functools import wraps

bp = Blueprint('api', __name__)

# =============================================================================
# Authorization Utilities
# =============================================================================

def evaluate_authorization(resource_type, action, resource_id=None, org_id=None):
    """
    Evaluate authorization for a given resource and action.
    
    Args:
        resource_type: Type of resource (org, provider, extension, audit)
        action: Action being performed (read, write, delete, admin)
        resource_id: Optional specific resource ID
        org_id: Optional organization ID for context
    
    Returns:
        dict: Authorization result with 'allowed' boolean and 'reason' string
    """
    # In production, this would integrate with the policy engine
    # For now, implement basic authorization checks
    auth_header = request.headers.get('Authorization', '')
    
    # Mock user context - in production would be from JWT/session
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
    
    # Check org membership for org-scoped resources
    if org_id and org_id not in user_context['org_memberships']:
        return {'allowed': False, 'reason': 'not_org_member'}
    
    # Clearance level checks
    clearance_requirements = {
        'org': {'read': 1, 'write': 3, 'delete': 4, 'admin': 5},
        'provider': {'read': 2, 'write': 3, 'delete': 4, 'admin': 5},
        'extension': {'read': 1, 'write': 2, 'delete': 3, 'admin': 4},
        'audit': {'read': 3, 'write': 4, 'delete': 5, 'admin': 5}
    }
    
    required_level = clearance_requirements.get(resource_type, {}).get(action, 5)
    if user_context['clearance_level'] < required_level:
        return {'allowed': False, 'reason': 'insufficient_clearance'}
    
    return {'allowed': True, 'reason': 'authorized'}


def require_auth(resource_type, action):
    """Decorator to require authorization for a route."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            org_id = kwargs.get('org_id')
            resource_id = kwargs.get('id') or kwargs.get('provider') or kwargs.get('org_id')
            
            auth_result = evaluate_authorization(resource_type, action, resource_id, org_id)
            
            if not auth_result['allowed']:
                return jsonify({
                    'error': 'Forbidden',
                    'reason': auth_result['reason'],
                    'resource_type': resource_type,
                    'action': action
                }), 403
            
            # Store auth result for potential audit logging
            g.auth_result = auth_result
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def log_audit_event(action, resource_type, resource_id, details=None):
    """Log an audit event for the current operation."""
    event = {
        'timestamp': datetime.utcnow().isoformat(),
        'action': action,
        'resource_type': resource_type,
        'resource_id': resource_id,
        'actor': g.get('user_id', 'system'),
        'ip_address': request.remote_addr,
        'user_agent': request.headers.get('User-Agent', ''),
        'details': details or {}
    }
    # In production, persist to audit log store
    # audit_store.append(event)
    return event


# =============================================================================
# In-Memory Data Stores (Replace with database in production)
# =============================================================================

orgs_db = {
    'org_2vH8kL9mN3pQ': {
        'id': 'org_2vH8kL9mN3pQ',
        'name': 'Acme Corporation',
        'short_name': 'AC',
        'tier': 'Enterprise',
        'primary_region': 'us-east-1',
        'legal_name': 'Acme Corporation, Inc.',
        'tax_id': '12-3456789',
        'industry': 'Technology',
        'employee_count': 2847,
        'data_residency': 'US, EU, APAC',
        'created_at': '2023-01-15T00:00:00Z',
        'updated_at': '2023-01-15T00:00:00Z',
        'settings': {
            'default_clearance': 'L2',
            'require_mfa': True,
            'session_timeout': 3600,
            'audit_retention_days': 2555
        },
        'members': [
            {'user_id': 'user_001', 'role': 'admin', 'joined_at': '2023-01-15T00:00:00Z'},
            {'user_id': 'user_002', 'role': 'member', 'joined_at': '2023-02-01T00:00:00Z'}
        ],
        'regions': [
            {'code': 'us-east-1', 'name': 'US East (N. Virginia)', 'status': 'active'},
            {'code': 'eu-west-1', 'name': 'EU (Ireland)', 'status': 'active'}
        ]
    }
}

providers_db = {
    'prov_001': {
        'id': 'prov_001',
        'name': 'OpenAI GPT-4',
        'type': 'openai',
        'priority': 1,
        'status': 'healthy',
        'auth': 'valid',
        'latency': 18,
        'rps': 500,
        'region': 'us-east-1',
        'last_check': '2s ago',
        'config': {
            'api_key_ref': 'vault://openai/api_key',
            'base_url': 'https://api.openai.com/v1',
            'timeout': 30,
            'retry_policy': 'exponential_backoff'
        }
    },
    'prov_002': {
        'id': 'prov_002',
        'name': 'Anthropic Claude',
        'type': 'anthropic',
        'priority': 2,
        'status': 'healthy',
        'auth': 'valid',
        'latency': 24,
        'rps': 300,
        'region': 'us-west-2',
        'last_check': '5s ago',
        'config': {
            'api_key_ref': 'vault://anthropic/api_key',
            'base_url': 'https://api.anthropic.com',
            'timeout': 45,
            'retry_policy': 'linear_backoff'
        }
    }
}

extensions_db = {
    'ext_001': {
        'id': 'ext_001',
        'name': 'OpenAPI Spec Validator',
        'type': 'plugin',
        'version': '2.1.0',
        'author': 'ORDL Team',
        'signature': 'verified',
        'status': 'active',
        'updated': '2024-03-01'
    },
    'ext_002': {
        'id': 'ext_002',
        'name': 'Python Code Analyzer',
        'type': 'skill',
        'version': '1.5.3',
        'author': 'Safety Lab',
        'signature': 'verified',
        'status': 'active',
        'updated': '2024-02-28'
    }
}

evidence_db = {}


# =============================================================================
# Fleet API
# =============================================================================

@bp.route('/v1/fleet/nodes')
def fleet_nodes():
    """Get all nodes in the fleet."""
    return jsonify({
        'nodes': [
            {'id': 'node-1', 'name': 'Gateway Node 1', 'status': 'online', 'region': 'us-east'},
            {'id': 'node-2', 'name': 'Worker Node 2', 'status': 'online', 'region': 'us-west'},
        ],
        'total': 2,
        'timestamp': datetime.utcnow().isoformat()
    })

@bp.route('/v1/fleet/gateways')
def fleet_gateways():
    """Get all gateways."""
    return jsonify({
        'gateways': [
            {'id': 'gw-1', 'name': 'Main Gateway', 'endpoint': 'gw1.ordl.io', 'status': 'active'},
        ],
        'total': 1
    })

@bp.route('/v1/fleet/discovery')
def fleet_discovery():
    """Get discovery status."""
    return jsonify({
        'status': 'idle',
        'last_scan': datetime.utcnow().isoformat(),
        'discovered_count': 5
    })

@bp.route('/v1/fleet/upgrades')
def fleet_upgrades():
    """Get available upgrades."""
    return jsonify({
        'available': [
            {'version': '1.2.0', 'component': 'agent', 'urgency': 'recommended'},
        ],
        'pending': [],
        'in_progress': []
    })

# =============================================================================
# Models API
# =============================================================================

@bp.route('/v1/models/models')
def models_list():
    """Get all models."""
    return jsonify({
        'models': [
            {'id': 'model-1', 'name': 'GPT-4 Clone', 'version': '1.0', 'status': 'ready'},
            {'id': 'model-2', 'name': 'Embedding Model', 'version': '2.1', 'status': 'training'},
        ],
        'total': 2
    })

@bp.route('/v1/models/training')
def models_training():
    """Get training jobs."""
    return jsonify({
        'jobs': [
            {'id': 'train-1', 'model': 'model-2', 'progress': 67, 'status': 'running'},
        ],
        'queue': []
    })

@bp.route('/v1/models/inference')
def models_inference():
    """Get inference endpoints."""
    return jsonify({
        'endpoints': [
            {'id': 'inf-1', 'model': 'model-1', 'url': '/v1/infer/model-1', 'status': 'active'},
        ]
    })

@bp.route('/v1/models/lineage')
def models_lineage():
    """Get model lineage."""
    return jsonify({
        'lineage': [
            {'model_id': 'model-2', 'parent_id': 'model-1', 'relationship': 'fine-tuned'},
        ]
    })

# =============================================================================
# Deployments API
# =============================================================================

@bp.route('/v1/deployments/deployments')
def deployments_list():
    """Get all deployments."""
    return jsonify({
        'deployments': [
            {'id': 'dep-1', 'name': 'Production API', 'status': 'running', 'replicas': 3},
            {'id': 'dep-2', 'name': 'Staging API', 'status': 'stopped', 'replicas': 0},
        ],
        'total': 2
    })

@bp.route('/v1/deployments/pipelines')
def deployments_pipelines():
    """Get deployment pipelines."""
    return jsonify({
        'pipelines': [
            {'id': 'pipe-1', 'name': 'CI/CD Main', 'status': 'active', 'last_run': datetime.utcnow().isoformat()},
        ]
    })

@bp.route('/v1/deployments/stages')
def deployments_stages():
    """Get pipeline stages."""
    return jsonify({
        'stages': [
            {'id': 'stage-1', 'name': 'Build', 'status': 'passed'},
            {'id': 'stage-2', 'name': 'Test', 'status': 'passed'},
            {'id': 'stage-3', 'name': 'Deploy', 'status': 'running'},
        ]
    })

# =============================================================================
# Audit API
# =============================================================================

@bp.route('/v1/audit/events')
def audit_events():
    """Get audit events."""
    return jsonify({
        'events': [
            {'id': 'evt-1', 'type': 'login', 'user': 'admin', 'timestamp': datetime.utcnow().isoformat()},
            {'id': 'evt-2', 'type': 'deploy', 'user': 'ci-bot', 'timestamp': datetime.utcnow().isoformat()},
        ],
        'total': 2
    })

@bp.route('/v1/audit/export')
def audit_export():
    """Export audit log."""
    return jsonify({'status': 'ready', 'download_url': '/api/v1/audit/export/download'})

@bp.route('/v1/audit/evidence', methods=['POST'])
@require_auth('audit', 'write')
def create_audit_evidence():
    """
    Create an evidence package from audit events.
    
    Request Body:
        - event_ids: List of event IDs to include
        - format: Export format ('json', 'pdf', 'chain')
        - include_chain_verification: Include verification hashes
        - description: Optional description
        - case_id: Optional case identifier
    
    Returns:
        - evidence_id: Unique identifier for the evidence package
        - download_url: URL to download the evidence
        - expires_at: Expiration timestamp
        - chain_hash: Merkle root hash for verification
    """
    data = request.get_json() or {}
    
    # Validate required fields
    event_ids = data.get('event_ids', [])
    if not event_ids:
        return jsonify({'error': 'event_ids is required'}), 400
    
    if not isinstance(event_ids, list):
        return jsonify({'error': 'event_ids must be a list'}), 400
    
    if len(event_ids) > 10000:
        return jsonify({'error': 'Maximum 10,000 events per evidence package'}), 400
    
    format_type = data.get('format', 'json')
    if format_type not in ['json', 'pdf', 'chain']:
        return jsonify({'error': 'format must be json, pdf, or chain'}), 400
    
    # Generate evidence package
    evidence_id = f"evp_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{len(evidence_db) + 1}"
    
    # Calculate chain hash (Merkle root simulation)
    import hashlib
    chain_data = f"{evidence_id}:{':'.join(sorted(event_ids))}"
    chain_hash = hashlib.sha256(chain_data.encode()).hexdigest()
    
    # Create evidence package
    evidence_package = {
        'id': evidence_id,
        'event_ids': event_ids,
        'event_count': len(event_ids),
        'format': format_type,
        'include_chain_verification': data.get('include_chain_verification', True),
        'description': data.get('description', ''),
        'case_id': data.get('case_id', ''),
        'created_at': datetime.utcnow().isoformat(),
        'expires_at': (datetime.utcnow().replace(year=datetime.utcnow().year + 3)).isoformat(),
        'created_by': g.get('user_id', 'system'),
        'chain_hash': chain_hash,
        'download_url': f'/api/v1/audit/evidence/{evidence_id}/download',
        'status': 'ready',
        'size_bytes': len(event_ids) * 512  # Estimate
    }
    
    evidence_db[evidence_id] = evidence_package
    
    # Log audit event
    log_audit_event(
        action='EVIDENCE_CREATED',
        resource_type='audit',
        resource_id=evidence_id,
        details={
            'event_count': len(event_ids),
            'format': format_type,
            'case_id': data.get('case_id')
        }
    )
    
    return jsonify({
        'evidence_id': evidence_id,
        'download_url': evidence_package['download_url'],
        'expires_at': evidence_package['expires_at'],
        'chain_hash': chain_hash,
        'event_count': len(event_ids),
        'status': 'ready'
    }), 201


# =============================================================================
# Messages API
# =============================================================================

@bp.route('/v1/messages/messages')
def messages_list():
    """Get messages."""
    return jsonify({
        'messages': [
            {'id': 'msg-1', 'from': 'system', 'subject': 'Deployment Complete', 'unread': True},
        ],
        'unread_count': 1
    })

@bp.route('/v1/messages/approvals')
def messages_approvals():
    """Get pending approvals."""
    return jsonify({
        'approvals': [
            {'id': 'app-1', 'type': 'deployment', 'requester': 'dev-team', 'status': 'pending'},
        ],
        'pending_count': 1
    })

# =============================================================================
# Governance API - Organization Routes
# =============================================================================

@bp.route('/v1/governance/orgs')
def governance_orgs():
    """Get organizations."""
    return jsonify({
        'orgs': list(orgs_db.values())
    })


# ENDPOINT 1: GET /v1/orgs/{org_id}
@bp.route('/v1/orgs/<org_id>', methods=['GET'])
@require_auth('org', 'read')
def get_org(org_id):
    """
    Get organization by ID.
    
    Path Parameters:
        - org_id: Organization identifier
    
    Returns:
        - Organization details including profile, settings, and metadata
    """
    if org_id not in orgs_db:
        return jsonify({'error': 'Organization not found', 'org_id': org_id}), 404
    
    org = orgs_db[org_id]
    
    # Log audit access
    log_audit_event(
        action='ORG_READ',
        resource_type='org',
        resource_id=org_id
    )
    
    return jsonify(org)


# ENDPOINT 2: PUT /v1/orgs/{org_id}
@bp.route('/v1/orgs/<org_id>', methods=['PUT'])
@require_auth('org', 'write')
def update_org(org_id):
    """
    Update organization profile.
    
    Path Parameters:
        - org_id: Organization identifier
    
    Request Body:
        - name: Organization display name
        - short_name: Short identifier
        - legal_name: Legal entity name
        - tax_id: Tax identification number
        - industry: Industry category
        - primary_region: Default region
        - data_residency: Comma-separated region list
    
    Returns:
        - Updated organization object
    """
    if org_id not in orgs_db:
        return jsonify({'error': 'Organization not found', 'org_id': org_id}), 404
    
    data = request.get_json() or {}
    org = orgs_db[org_id]
    
    # Update allowed fields
    allowed_fields = ['name', 'short_name', 'legal_name', 'tax_id', 'industry', 
                      'primary_region', 'data_residency', 'employee_count']
    
    for field in allowed_fields:
        if field in data:
            org[field] = data[field]
    
    org['updated_at'] = datetime.utcnow().isoformat()
    
    # Log audit event
    log_audit_event(
        action='ORG_UPDATED',
        resource_type='org',
        resource_id=org_id,
        details={'updated_fields': list(data.keys())}
    )
    
    return jsonify(org)


# ENDPOINT 3: PUT /v1/orgs/{org_id}/defaults
@bp.route('/v1/orgs/<org_id>/defaults', methods=['PUT'])
@require_auth('org', 'admin')
def update_org_defaults(org_id):
    """
    Update organization default settings.
    
    Path Parameters:
        - org_id: Organization identifier
    
    Request Body:
        - default_clearance: Default clearance tier for new members
        - require_mfa: Boolean requiring MFA
        - session_timeout: Session timeout in seconds
        - audit_retention_days: Number of days to retain audit logs
    
    Returns:
        - Updated settings object
    """
    if org_id not in orgs_db:
        return jsonify({'error': 'Organization not found', 'org_id': org_id}), 404
    
    data = request.get_json() or {}
    org = orgs_db[org_id]
    
    # Update settings
    settings = org.get('settings', {})
    
    allowed_settings = ['default_clearance', 'require_mfa', 'session_timeout', 'audit_retention_days']
    for key in allowed_settings:
        if key in data:
            settings[key] = data[key]
    
    org['settings'] = settings
    org['updated_at'] = datetime.utcnow().isoformat()
    
    # Log audit event
    log_audit_event(
        action='ORG_DEFAULTS_UPDATED',
        resource_type='org',
        resource_id=org_id,
        details={'settings_updated': list(data.keys())}
    )
    
    return jsonify({
        'org_id': org_id,
        'settings': settings,
        'updated_at': org['updated_at']
    })


# ENDPOINT 4: POST /v1/orgs/{org_id}/members
@bp.route('/v1/orgs/<org_id>/members', methods=['POST'])
@require_auth('org', 'admin')
def add_org_member(org_id):
    """
    Add a member to the organization.
    
    Path Parameters:
        - org_id: Organization identifier
    
    Request Body:
        - user_id: User to add
        - role: Member role (admin, member, observer)
        - clearance_tier: Initial clearance level
        - compartments: List of compartment access
    
    Returns:
        - Member details with joined timestamp
    """
    if org_id not in orgs_db:
        return jsonify({'error': 'Organization not found', 'org_id': org_id}), 404
    
    data = request.get_json() or {}
    
    # Validate required fields
    user_id = data.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400
    
    role = data.get('role', 'member')
    if role not in ['admin', 'member', 'observer']:
        return jsonify({'error': 'role must be admin, member, or observer'}), 400
    
    org = orgs_db[org_id]
    members = org.get('members', [])
    
    # Check if user already member
    for member in members:
        if member['user_id'] == user_id:
            return jsonify({'error': 'User is already a member', 'user_id': user_id}), 409
    
    new_member = {
        'user_id': user_id,
        'role': role,
        'clearance_tier': data.get('clearance_tier', org.get('settings', {}).get('default_clearance', 'L2')),
        'compartments': data.get('compartments', []),
        'joined_at': datetime.utcnow().isoformat()
    }
    
    members.append(new_member)
    org['members'] = members
    org['updated_at'] = datetime.utcnow().isoformat()
    
    # Log audit event
    log_audit_event(
        action='ORG_MEMBER_ADDED',
        resource_type='org',
        resource_id=org_id,
        details={'user_id': user_id, 'role': role}
    )
    
    return jsonify({
        'org_id': org_id,
        'member': new_member,
        'total_members': len(members)
    }), 201


# ENDPOINT 5: POST /v1/orgs/{org_id}/regions
@bp.route('/v1/orgs/<org_id>/regions', methods=['POST'])
@require_auth('org', 'write')
def add_org_region(org_id):
    """
    Add a region to the organization.
    
    Path Parameters:
        - org_id: Organization identifier
    
    Request Body:
        - code: Region code (e.g., 'us-east-1')
        - name: Human-readable region name
        - status: Region status (active, pending, disabled)
        - compliance: Compliance frameworks (SOC2, GDPR, etc.)
        - encryption: Encryption standard
    
    Returns:
        - Region details with created timestamp
    """
    if org_id not in orgs_db:
        return jsonify({'error': 'Organization not found', 'org_id': org_id}), 404
    
    data = request.get_json() or {}
    
    # Validate required fields
    code = data.get('code')
    name = data.get('name')
    if not code or not name:
        return jsonify({'error': 'code and name are required'}), 400
    
    org = orgs_db[org_id]
    regions = org.get('regions', [])
    
    # Check if region already exists
    for region in regions:
        if region['code'] == code:
            return jsonify({'error': 'Region already exists', 'code': code}), 409
    
    new_region = {
        'code': code,
        'name': name,
        'status': data.get('status', 'active'),
        'compliance': data.get('compliance', []),
        'encryption': data.get('encryption', 'AES-256-GCM'),
        'cross_border': data.get('cross_border', 'Audit Required'),
        'created_at': datetime.utcnow().isoformat()
    }
    
    regions.append(new_region)
    org['regions'] = regions
    org['updated_at'] = datetime.utcnow().isoformat()
    
    # Log audit event
    log_audit_event(
        action='ORG_REGION_ADDED',
        resource_type='org',
        resource_id=org_id,
        details={'region_code': code, 'region_name': name}
    )
    
    return jsonify({
        'org_id': org_id,
        'region': new_region,
        'total_regions': len(regions)
    }), 201


@bp.route('/v1/governance/teams')
def governance_teams():
    """Get teams."""
    return jsonify({
        'teams': [
            {'id': 'team-1', 'name': 'Platform', 'org_id': 'org-1', 'members': 5},
            {'id': 'team-2', 'name': 'ML', 'org_id': 'org-1', 'members': 3},
        ]
    })

@bp.route('/v1/governance/projects')
def governance_projects():
    """Get projects."""
    return jsonify({
        'projects': [
            {'id': 'proj-1', 'name': 'AI Platform', 'team_id': 'team-1', 'status': 'active'},
        ]
    })

@bp.route('/v1/governance/seats')
def governance_seats():
    """Get seat allocation."""
    return jsonify({
        'total_seats': 100,
        'used_seats': 45,
        'available_seats': 55,
        'by_org': {'org-1': 45}
    })

@bp.route('/v1/governance/clearance')
def governance_clearance():
    """Get clearance levels."""
    return jsonify({
        'levels': [
            {'level': 1, 'name': 'Public', 'users': 100},
            {'level': 2, 'name': 'Internal', 'users': 50},
            {'level': 3, 'name': 'Confidential', 'users': 20},
        ]
    })

@bp.route('/v1/governance/policy')
def governance_policy():
    """Get policies."""
    return jsonify({
        'policies': [
            {'id': 'pol-1', 'name': 'Data Retention', 'enforced': True},
            {'id': 'pol-2', 'name': 'Access Control', 'enforced': True},
        ]
    })

# =============================================================================
# Security API - Provider Routes
# =============================================================================

@bp.route('/v1/security/providers')
def security_providers_list():
    """Get auth providers."""
    return jsonify({
        'providers': list(providers_db.values())
    })


# ENDPOINT 9: POST /v1/providers/{id}/test (alias for compatibility)
# Also supports {provider} parameter name for backward compatibility
@bp.route('/v1/providers/<id>/test', methods=['POST'])
@bp.route('/v1/providers/<provider>/test', methods=['POST'])
@require_auth('provider', 'read')
def test_provider(id=None, provider=None):
    """
    Test provider connectivity and authentication.
    
    Path Parameters:
        - id: Provider identifier (preferred)
        - provider: Provider identifier (alias for compatibility)
    
    Request Body:
        - test_type: Type of test ('connectivity', 'auth', 'inference')
        - timeout: Test timeout in seconds
    
    Returns:
        - Test results with latency, status, and details
    """
    provider_id = id or provider
    
    if provider_id not in providers_db:
        return jsonify({'error': 'Provider not found', 'provider_id': provider_id}), 404
    
    data = request.get_json() or {}
    test_type = data.get('test_type', 'connectivity')
    timeout = data.get('timeout', 30)
    
    if test_type not in ['connectivity', 'auth', 'inference']:
        return jsonify({'error': 'test_type must be connectivity, auth, or inference'}), 400
    
    provider = providers_db[provider_id]
    
    # Simulate test (in production, perform actual test)
    import random
    latency_ms = random.randint(10, 100)
    
    test_result = {
        'provider_id': provider_id,
        'test_type': test_type,
        'status': 'passed',
        'latency_ms': latency_ms,
        'timestamp': datetime.utcnow().isoformat(),
        'details': {}
    }
    
    if test_type == 'connectivity':
        test_result['details'] = {
            'dns_resolved': True,
            'tcp_connected': True,
            'tls_established': True,
            'endpoint': provider['config'].get('base_url')
        }
    elif test_type == 'auth':
        test_result['details'] = {
            'api_key_valid': provider['auth'] == 'valid',
            'permissions': ['inference', 'finetune', 'embeddings'],
            'rate_limit_remaining': 499
        }
    elif test_type == 'inference':
        test_result['details'] = {
            'model_accessible': True,
            'test_inference_ms': latency_ms + 50,
            'token_rate': 1250
        }
    
    # Log audit event
    log_audit_event(
        action='PROVIDER_TESTED',
        resource_type='provider',
        resource_id=provider_id,
        details={'test_type': test_type, 'result': test_result['status']}
    )
    
    return jsonify(test_result)


# ENDPOINT 10: PUT /v1/providers/{id}/config (alias for compatibility)
# Also supports {provider} parameter name for backward compatibility
@bp.route('/v1/providers/<id>/config', methods=['PUT'])
@bp.route('/v1/providers/<provider>/config', methods=['PUT'])
@require_auth('provider', 'write')
def update_provider_config(id=None, provider=None):
    """
    Update provider configuration.
    
    Path Parameters:
        - id: Provider identifier (preferred)
        - provider: Provider identifier (alias for compatibility)
    
    Request Body:
        - api_key_ref: Vault reference to API key
        - base_url: Provider API base URL
        - timeout: Request timeout in seconds
        - retry_policy: Retry strategy name
        - priority: Failover priority (1 = highest)
        - rps: Rate limit requests per second
    
    Returns:
        - Updated provider configuration
    """
    provider_id = id or provider
    
    if provider_id not in providers_db:
        return jsonify({'error': 'Provider not found', 'provider_id': provider_id}), 404
    
    data = request.get_json() or {}
    provider = providers_db[provider_id]
    
    # Update config
    config = provider.get('config', {})
    
    config_fields = ['api_key_ref', 'base_url', 'timeout', 'retry_policy']
    for field in config_fields:
        if field in data:
            config[field] = data[field]
    
    provider['config'] = config
    
    # Update top-level fields
    if 'priority' in data:
        provider['priority'] = data['priority']
    if 'rps' in data:
        provider['rps'] = data['rps']
    
    provider['updated_at'] = datetime.utcnow().isoformat()
    
    # Log audit event
    log_audit_event(
        action='PROVIDER_CONFIG_UPDATED',
        resource_type='provider',
        resource_id=provider_id,
        details={'config_updated': list(data.keys())}
    )
    
    return jsonify({
        'provider_id': provider_id,
        'config': config,
        'priority': provider['priority'],
        'rps': provider['rps'],
        'updated_at': provider['updated_at']
    })


# =============================================================================
# Security API - Extension Routes
# =============================================================================

@bp.route('/v1/security/extensions')
def security_extensions_list():
    """Get security extensions."""
    return jsonify({
        'extensions': list(extensions_db.values())
    })


# ENDPOINT 7: POST /v1/extensions/verify
@bp.route('/v1/extensions/verify', methods=['POST'])
@require_auth('extension', 'write')
def verify_extensions():
    """
    Verify extension signatures and integrity.
    
    Request Body:
        - extension_ids: List of extension IDs to verify (optional, verifies all if empty)
        - verify_chain: Verify full certificate chain
        - check_revocation: Check certificate revocation status
    
    Returns:
        - Verification results for each extension
    """
    data = request.get_json() or {}
    extension_ids = data.get('extension_ids', [])
    verify_chain = data.get('verify_chain', True)
    check_revocation = data.get('check_revocation', False)
    
    # If no IDs specified, verify all
    if not extension_ids:
        extension_ids = list(extensions_db.keys())
    
    results = []
    for ext_id in extension_ids:
        if ext_id not in extensions_db:
            results.append({
                'extension_id': ext_id,
                'status': 'not_found',
                'verified': False
            })
            continue
        
        ext = extensions_db[ext_id]
        
        # Simulate verification
        verified = ext.get('signature') == 'verified'
        
        result = {
            'extension_id': ext_id,
            'name': ext['name'],
            'version': ext['version'],
            'verified': verified,
            'status': 'valid' if verified else 'invalid',
            'signature_valid': verified,
            'certificate_chain_valid': verify_chain,
            'not_revoked': not check_revocation or True,
            'verified_at': datetime.utcnow().isoformat()
        }
        
        if verified:
            result['checksum'] = f"sha256:{ext_id}abcd1234"
        else:
            result['errors'] = ['Signature verification failed']
        
        results.append(result)
    
    all_verified = all(r['verified'] for r in results)
    
    # Log audit event
    log_audit_event(
        action='EXTENSIONS_VERIFIED',
        resource_type='extension',
        resource_id='batch',
        details={
            'extension_count': len(extension_ids),
            'all_verified': all_verified
        }
    )
    
    return jsonify({
        'results': results,
        'total': len(results),
        'verified_count': sum(1 for r in results if r['verified']),
        'failed_count': sum(1 for r in results if not r['verified']),
        'all_verified': all_verified
    })


# ENDPOINT 8: POST /v1/extensions/batch
@bp.route('/v1/extensions/batch', methods=['POST'])
@require_auth('extension', 'write')
def batch_extension_operation():
    """
    Perform batch operations on extensions.
    
    Request Body:
        - operation: Operation type ('enable', 'disable', 'delete', 'update')
        - extension_ids: List of extension IDs to operate on
        - options: Operation-specific options
    
    Returns:
        - Batch operation results
    """
    data = request.get_json() or {}
    
    # Validate operation
    operation = data.get('operation')
    if not operation:
        return jsonify({'error': 'operation is required'}), 400
    
    if operation not in ['enable', 'disable', 'delete', 'update']:
        return jsonify({'error': 'operation must be enable, disable, delete, or update'}), 400
    
    extension_ids = data.get('extension_ids', [])
    if not extension_ids:
        return jsonify({'error': 'extension_ids is required'}), 400
    
    if len(extension_ids) > 100:
        return jsonify({'error': 'Maximum 100 extensions per batch operation'}), 400
    
    options = data.get('options', {})
    results = []
    
    for ext_id in extension_ids:
        if ext_id not in extensions_db:
            results.append({
                'extension_id': ext_id,
                'success': False,
                'error': 'Extension not found'
            })
            continue
        
        ext = extensions_db[ext_id]
        
        if operation == 'enable':
            ext['status'] = 'active'
            success = True
        elif operation == 'disable':
            ext['status'] = 'disabled'
            success = True
        elif operation == 'delete':
            # Mark for deletion (actual deletion would be async)
            ext['status'] = 'deleting'
            success = True
        elif operation == 'update':
            if 'version' in options:
                ext['version'] = options['version']
            if 'config' in options:
                ext['config'] = options['config']
            ext['updated'] = datetime.utcnow().strftime('%Y-%m-%d')
            success = True
        else:
            success = False
        
        results.append({
            'extension_id': ext_id,
            'success': success,
            'new_status': ext.get('status')
        })
    
    success_count = sum(1 for r in results if r['success'])
    
    # Log audit event
    log_audit_event(
        action=f'EXTENSION_BATCH_{operation.upper()}',
        resource_type='extension',
        resource_id='batch',
        details={
            'operation': operation,
            'extension_count': len(extension_ids),
            'success_count': success_count
        }
    )
    
    return jsonify({
        'operation': operation,
        'results': results,
        'total': len(results),
        'success_count': success_count,
        'failed_count': len(results) - success_count
    })


# =============================================================================
# Nodes API
# =============================================================================

@bp.route('/v1/nodes/discovery')
def nodes_discovery():
    """Get node discovery status."""
    return jsonify({
        'status': 'scanning',
        'discovered': 3,
        'pending': 2,
        'networks': ['198.51.100.0/24', '192.168.1.0/24']
    })

@bp.route('/v1/nodes/autoupdate')
def nodes_autoupdate():
    """Get auto-update status."""
    return jsonify({
        'enabled': True,
        'schedule': '0 2 * * *',
        'channel': 'stable',
        'last_check': datetime.utcnow().isoformat()
    })

# =============================================================================
# Health API
# =============================================================================

@bp.route('/v1/health/health')
def health_status():
    """Get system health."""
    return jsonify({
        'status': 'healthy',
        'components': {
            'database': 'up',
            'cache': 'up',
            'queue': 'up'
        },
        'timestamp': datetime.utcnow().isoformat()
    })

@bp.route('/v1/health/slos')
def health_slos():
    """Get SLO status."""
    return jsonify({
        'slos': [
            {'name': 'Availability', 'target': 99.9, 'current': 99.95, 'status': 'met'},
            {'name': 'Latency', 'target': 100, 'current': 85, 'status': 'met'},
        ]
    })

@bp.route('/v1/health/reconnect')
def health_reconnect():
    """Get reconnection status."""
    return jsonify({
        'reconnecting': False,
        'last_disconnect': None,
        'reconnect_count': 0
    })

# =============================================================================
# Incidents API
# =============================================================================

@bp.route('/v1/incidents/incidents')
def incidents_list():
    """Get incidents."""
    return jsonify({
        'incidents': [
            {
                'id': 'inc-1',
                'title': 'Database Latency Spike',
                'severity': 'high',
                'status': 'resolved',
                'created_at': datetime.utcnow().isoformat()
            },
        ],
        'open_count': 0,
        'total': 1
    })

@bp.route('/v1/incidents/postmortems')
def incidents_postmortems():
    """Get postmortems."""
    return jsonify({
        'postmortems': [
            {
                'id': 'pm-1',
                'incident_id': 'inc-1',
                'title': 'Postmortem: Database Latency',
                'status': 'published',
                'published_at': datetime.utcnow().isoformat()
            },
        ]
    })
