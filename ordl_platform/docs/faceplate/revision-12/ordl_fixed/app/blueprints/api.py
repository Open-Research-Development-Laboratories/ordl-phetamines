"""
API blueprint - BFF Proxy Layer for ORDL Backend /v1 API

This blueprint proxies all requests to the ORDL backend API with:
- JWT authentication and validation
- Circuit breaker pattern for resilience
- Automatic retry logic
- Audit logging via POST /v1/audit/events

All routes proxy to corresponding /v1 endpoints on the backend.
"""
from flask import Blueprint, jsonify, request, g
from datetime import datetime

from app.services import (
    get_backend_client,
    require_auth,
    optional_auth,
    get_auth_headers,
    log_audit_event,
    BackendClientError,
    BackendConnectionError,
    BackendTimeoutError,
    BackendCircuitOpenError
)

bp = Blueprint('api', __name__)


def _proxy_to_backend(method: str, path: str, audit_action: str = None) -> tuple:
    """
    Generic proxy handler for backend requests.
    
    Args:
        method: HTTP method
        path: Backend API path
        audit_action: Optional audit action to log
        
    Returns:
        Flask response tuple (jsonify, status_code)
    """
    client = get_backend_client()
    headers = get_auth_headers()
    
    # Build full path with /v1 prefix
    if not path.startswith('/v1/'):
        path = f'/v1/{path}'
    
    try:
        # Get request body for POST/PUT/PATCH
        json_data = request.get_json(silent=True) if method in ['POST', 'PUT', 'PATCH'] else None
        params = request.args.to_dict() if request.args else None
        
        # Make backend request
        status_code, response = client._make_request(
            method=method,
            path=path,
            headers=headers,
            json_data=json_data,
            params=params
        )
        
        # Log audit event if specified
        if audit_action:
            resource_type = path.split('/')[2] if len(path.split('/')) > 2 else 'unknown'
            resource_id = path.split('/')[-1] if path.split('/')[-1] not in ['orgs', 'providers', 'extensions'] else None
            
            log_audit_event(
                action=audit_action,
                resource_type=resource_type,
                resource_id=resource_id,
                details={
                    'method': method,
                    'path': path,
                    'status_code': status_code
                },
                org_id=request.view_args.get('org_id') if request.view_args else None
            )
        
        return jsonify(response), status_code
        
    except BackendCircuitOpenError:
        return jsonify({
            'error': 'Service Unavailable',
            'message': 'Backend service is temporarily unavailable. Please try again later.',
            'code': 'CIRCUIT_OPEN'
        }), 503
        
    except BackendTimeoutError:
        return jsonify({
            'error': 'Gateway Timeout',
            'message': 'Backend service did not respond in time.',
            'code': 'BACKEND_TIMEOUT'
        }), 504
        
    except BackendConnectionError as e:
        return jsonify({
            'error': 'Service Unavailable',
            'message': 'Unable to connect to backend service.',
            'code': 'BACKEND_CONNECTION_ERROR'
        }), 503
        
    except BackendClientError as e:
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Error communicating with backend service.',
            'code': 'BACKEND_ERROR',
            'details': str(e) if request.environ.get('FLASK_ENV') == 'development' else None
        }), 500


# =============================================================================
# Fleet API (4 routes)
# =============================================================================

@bp.route('/v1/fleet/nodes', methods=['GET'])
@require_auth
def fleet_nodes():
    """Get all nodes in the fleet."""
    return _proxy_to_backend('GET', '/fleet/nodes', 'FLEET_NODES_READ')


@bp.route('/v1/fleet/gateways', methods=['GET'])
@require_auth
def fleet_gateways():
    """Get all gateways."""
    return _proxy_to_backend('GET', '/fleet/gateways', 'FLEET_GATEWAYS_READ')


@bp.route('/v1/fleet/discovery', methods=['GET'])
@require_auth
def fleet_discovery():
    """Get discovery status."""
    return _proxy_to_backend('GET', '/fleet/discovery', 'FLEET_DISCOVERY_READ')


@bp.route('/v1/fleet/upgrades', methods=['GET'])
@require_auth
def fleet_upgrades():
    """Get available upgrades."""
    return _proxy_to_backend('GET', '/fleet/upgrades', 'FLEET_UPGRADES_READ')


# =============================================================================
# Models API (4 routes)
# =============================================================================

@bp.route('/v1/models/models', methods=['GET'])
@require_auth
def models_list():
    """Get all models."""
    return _proxy_to_backend('GET', '/models/models', 'MODELS_LIST_READ')


@bp.route('/v1/models/training', methods=['GET'])
@require_auth
def models_training():
    """Get training jobs."""
    return _proxy_to_backend('GET', '/models/training', 'MODELS_TRAINING_READ')


@bp.route('/v1/models/inference', methods=['GET'])
@require_auth
def models_inference():
    """Get inference endpoints."""
    return _proxy_to_backend('GET', '/models/inference', 'MODELS_INFERENCE_READ')


@bp.route('/v1/models/lineage', methods=['GET'])
@require_auth
def models_lineage():
    """Get model lineage."""
    return _proxy_to_backend('GET', '/models/lineage', 'MODELS_LINEAGE_READ')


# =============================================================================
# Deployments API (2 routes)
# =============================================================================

@bp.route('/v1/deployments/deployments', methods=['GET'])
@require_auth
def deployments_list():
    """Get all deployments."""
    return _proxy_to_backend('GET', '/deployments/deployments', 'DEPLOYMENTS_LIST_READ')


@bp.route('/v1/deployments/pipelines', methods=['GET'])
@require_auth
def deployments_pipelines():
    """Get deployment pipelines."""
    return _proxy_to_backend('GET', '/deployments/pipelines', 'DEPLOYMENTS_PIPELINES_READ')


# =============================================================================
# Audit API (3 routes)
# =============================================================================

@bp.route('/v1/audit/events', methods=['GET'])
@require_auth
def audit_events():
    """Get audit events."""
    return _proxy_to_backend('GET', '/audit/events', 'AUDIT_EVENTS_READ')


@bp.route('/v1/audit/events', methods=['POST'])
@require_auth
def create_audit_event():
    """
    Create an audit event.
    
    Request Body:
        - action: The action being performed
        - resource_type: Type of resource
        - resource_id: Optional resource identifier
        - details: Optional additional details
    """
    return _proxy_to_backend('POST', '/audit/events', 'AUDIT_EVENT_CREATED')


@bp.route('/v1/audit/export', methods=['GET'])
@require_auth
def audit_export():
    """Export audit log."""
    return _proxy_to_backend('GET', '/audit/export', 'AUDIT_EXPORT_READ')


# =============================================================================
# Messages API (2 routes)
# =============================================================================

@bp.route('/v1/messages/messages', methods=['GET'])
@require_auth
def messages_list():
    """Get messages."""
    return _proxy_to_backend('GET', '/messages/messages', 'MESSAGES_LIST_READ')


@bp.route('/v1/messages/approvals', methods=['GET'])
@require_auth
def messages_approvals():
    """Get pending approvals."""
    return _proxy_to_backend('GET', '/messages/approvals', 'MESSAGES_APPROVALS_READ')


# =============================================================================
# Governance API - Organization Routes (9 routes)
# =============================================================================

@bp.route('/v1/governance/orgs', methods=['GET'])
@require_auth
def governance_orgs():
    """Get organizations."""
    return _proxy_to_backend('GET', '/governance/orgs', 'GOVERNANCE_ORGS_READ')


@bp.route('/v1/orgs/<org_id>', methods=['GET'])
@require_auth
def get_org(org_id):
    """
    Get organization by ID.
    
    Path Parameters:
        - org_id: Organization identifier
    """
    return _proxy_to_backend('GET', f'/orgs/{org_id}', 'ORG_READ')


@bp.route('/v1/orgs', methods=['POST'])
@require_auth
def create_org():
    """
    Create a new organization.
    
    Request Body:
        - name: Organization display name
        - short_name: Short identifier
        - legal_name: Legal entity name
        - tax_id: Tax identification number
        - industry: Industry category
        - primary_region: Default region
    """
    return _proxy_to_backend('POST', '/orgs', 'ORG_CREATED')


@bp.route('/v1/orgs/<org_id>', methods=['PUT'])
@require_auth
def update_org(org_id):
    """
    Update organization profile.
    
    Path Parameters:
        - org_id: Organization identifier
    """
    return _proxy_to_backend('PUT', f'/orgs/{org_id}', 'ORG_UPDATED')


@bp.route('/v1/orgs/<org_id>/defaults', methods=['PUT'])
@require_auth
def update_org_defaults(org_id):
    """
    Update organization default settings.
    
    Path Parameters:
        - org_id: Organization identifier
    """
    return _proxy_to_backend('PUT', f'/orgs/{org_id}/defaults', 'ORG_DEFAULTS_UPDATED')


@bp.route('/v1/orgs/<org_id>/members', methods=['GET'])
@require_auth
def list_org_members(org_id):
    """List organization members."""
    return _proxy_to_backend('GET', f'/orgs/{org_id}/members', 'ORG_MEMBERS_LIST_READ')


@bp.route('/v1/orgs/<org_id>/members', methods=['POST'])
@require_auth
def add_org_member(org_id):
    """Add a member to the organization."""
    return _proxy_to_backend('POST', f'/orgs/{org_id}/members', 'ORG_MEMBER_ADDED')


@bp.route('/v1/orgs/<org_id>/regions', methods=['GET'])
@require_auth
def list_org_regions(org_id):
    """List organization regions."""
    return _proxy_to_backend('GET', f'/orgs/{org_id}/regions', 'ORG_REGIONS_LIST_READ')


@bp.route('/v1/orgs/<org_id>/regions', methods=['POST'])
@require_auth
def add_org_region(org_id):
    """Add a region to the organization."""
    return _proxy_to_backend('POST', f'/orgs/{org_id}/regions', 'ORG_REGION_ADDED')


# =============================================================================
# Governance API - Additional Routes (4 routes)
# =============================================================================

@bp.route('/v1/governance/teams', methods=['GET'])
@require_auth
def governance_teams():
    """Get teams."""
    return _proxy_to_backend('GET', '/governance/teams', 'GOVERNANCE_TEAMS_READ')


@bp.route('/v1/governance/projects', methods=['GET'])
@require_auth
def governance_projects():
    """Get projects."""
    return _proxy_to_backend('GET', '/governance/projects', 'GOVERNANCE_PROJECTS_READ')


@bp.route('/v1/governance/clearance', methods=['GET'])
@require_auth
def governance_clearance():
    """Get clearance levels."""
    return _proxy_to_backend('GET', '/governance/clearance', 'GOVERNANCE_CLEARANCE_READ')


@bp.route('/v1/governance/policy', methods=['GET'])
@require_auth
def governance_policy():
    """Get policies."""
    return _proxy_to_backend('GET', '/governance/policy', 'GOVERNANCE_POLICY_READ')


# =============================================================================
# Security API - Provider Routes (6 routes)
# =============================================================================

@bp.route('/v1/security/providers', methods=['GET'])
@require_auth
def security_providers_list():
    """Get auth providers."""
    return _proxy_to_backend('GET', '/security/providers', 'SECURITY_PROVIDERS_READ')


@bp.route('/v1/providers', methods=['GET'])
@require_auth
def list_providers():
    """List all providers."""
    return _proxy_to_backend('GET', '/providers', 'PROVIDERS_LIST_READ')


@bp.route('/v1/providers', methods=['POST'])
@require_auth
def create_provider():
    """Create a new provider."""
    return _proxy_to_backend('POST', '/providers', 'PROVIDER_CREATED')


@bp.route('/v1/providers/<provider_id>', methods=['GET'])
@require_auth
def get_provider(provider_id):
    """Get provider by ID."""
    return _proxy_to_backend('GET', f'/providers/{provider_id}', 'PROVIDER_READ')


@bp.route('/v1/providers/<provider_id>', methods=['PUT'])
@require_auth
def update_provider(provider_id):
    """Update provider."""
    return _proxy_to_backend('PUT', f'/providers/{provider_id}', 'PROVIDER_UPDATED')


@bp.route('/v1/providers/<provider_id>/test', methods=['POST'])
@require_auth
def test_provider(provider_id):
    """Test provider connectivity and authentication."""
    return _proxy_to_backend('POST', f'/providers/{provider_id}/test', 'PROVIDER_TESTED')


# =============================================================================
# Security API - Extension Routes (3 routes)
# =============================================================================

@bp.route('/v1/extensions', methods=['GET'])
@require_auth
def list_extensions():
    """List all extensions."""
    return _proxy_to_backend('GET', '/extensions', 'EXTENSIONS_LIST_READ')


@bp.route('/v1/extensions/<extension_id>', methods=['GET'])
@require_auth
def get_extension(extension_id):
    """Get extension by ID."""
    return _proxy_to_backend('GET', f'/extensions/{extension_id}', 'EXTENSION_READ')


@bp.route('/v1/extensions/verify', methods=['POST'])
@require_auth
def verify_extensions():
    """Verify extension signatures and integrity."""
    return _proxy_to_backend('POST', '/extensions/verify', 'EXTENSIONS_VERIFIED')


# =============================================================================
# Nodes API (2 routes)
# =============================================================================

@bp.route('/v1/nodes/discovery', methods=['GET'])
@require_auth
def nodes_discovery():
    """Get node discovery status."""
    return _proxy_to_backend('GET', '/nodes/discovery', 'NODES_DISCOVERY_READ')


@bp.route('/v1/nodes/autoupdate', methods=['GET'])
@require_auth
def nodes_autoupdate():
    """Get auto-update status."""
    return _proxy_to_backend('GET', '/nodes/autoupdate', 'NODES_AUTOUPDATE_READ')


# =============================================================================
# Health API (2 routes)
# =============================================================================

@bp.route('/v1/health/health', methods=['GET'])
@optional_auth
def health_status():
    """Get system health."""
    return _proxy_to_backend('GET', '/health/health')


@bp.route('/v1/health/slos', methods=['GET'])
@require_auth
def health_slos():
    """Get SLO status."""
    return _proxy_to_backend('GET', '/health/slos', 'HEALTH_SLOS_READ')


# =============================================================================
# Incidents API (2 routes)
# =============================================================================

@bp.route('/v1/incidents/incidents', methods=['GET'])
@require_auth
def incidents_list():
    """Get incidents."""
    return _proxy_to_backend('GET', '/incidents/incidents', 'INCIDENTS_LIST_READ')


@bp.route('/v1/incidents/incidents', methods=['POST'])
@require_auth
def create_incident():
    """Create a new incident."""
    return _proxy_to_backend('POST', '/incidents/incidents', 'INCIDENT_CREATED')


# =============================================================================
# Evidence API (2 routes)
# =============================================================================

@bp.route('/v1/audit/evidence', methods=['POST'])
@require_auth
def create_audit_evidence():
    """
    Create an evidence package from audit events.
    
    Request Body:
        - event_ids: List of event IDs to include
        - format: Export format ('json', 'pdf', 'chain')
        - include_chain_verification: Include verification hashes
        - description: Optional description
        - case_id: Optional case identifier
    """
    return _proxy_to_backend('POST', '/audit/evidence', 'EVIDENCE_CREATED')


@bp.route('/v1/audit/evidence/<evidence_id>', methods=['GET'])
@require_auth
def get_evidence(evidence_id):
    """Get evidence package by ID."""
    return _proxy_to_backend('GET', f'/audit/evidence/{evidence_id}', 'EVIDENCE_READ')


# =============================================================================
# Authentication Routes (2 routes)
# =============================================================================

@bp.route('/v1/auth/login', methods=['POST'])
@optional_auth
def auth_login():
    """Authenticate and get access token."""
    return _proxy_to_backend('POST', '/auth/login', 'USER_LOGIN')


@bp.route('/v1/auth/me', methods=['GET'])
@require_auth
def auth_me():
    """Get current user information."""
    return _proxy_to_backend('GET', '/auth/me', 'USER_PROFILE_READ')
