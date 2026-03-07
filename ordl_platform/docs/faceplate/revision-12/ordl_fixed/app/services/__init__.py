"""
Services package for ORDL BFF API.

Provides backend client, authentication, and audit logging services.
"""

from app.services.backend_client import (
    BackendClient,
    get_backend_client,
    BackendClientError,
    BackendConnectionError,
    BackendTimeoutError,
    BackendCircuitOpenError
)

from app.services.auth_middleware import (
    JWTValidator,
    AuthContext,
    AuthError,
    require_auth,
    optional_auth,
    authenticate_request,
    get_auth_token,
    get_auth_headers,
    check_org_access,
    check_clearance
)

from app.services.audit_service import (
    AuditLogger,
    get_audit_logger,
    log_audit_event
)

__all__ = [
    # Backend Client
    'BackendClient',
    'get_backend_client',
    'BackendClientError',
    'BackendConnectionError',
    'BackendTimeoutError',
    'BackendCircuitOpenError',
    
    # Auth Middleware
    'JWTValidator',
    'AuthContext',
    'AuthError',
    'require_auth',
    'optional_auth',
    'authenticate_request',
    'get_auth_token',
    'get_auth_headers',
    'check_org_access',
    'check_clearance',
    
    # Audit Service
    'AuditLogger',
    'get_audit_logger',
    'log_audit_event',
]
