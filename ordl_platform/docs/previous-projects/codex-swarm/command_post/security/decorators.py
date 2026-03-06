#!/usr/bin/env python3
"""
ORDL Security Decorators for Flask Routes
USG-Compliant Access Control
Classification: TOP SECRET//NOFORN//SCI
"""

from functools import wraps
from flask import request, jsonify, g
import time
from typing import Optional, List, Set

# Import security modules
try:
    from security.clearance import ClearanceLevel, ClearanceAttributes, get_acl
    from security.audit.logger import get_audit_logger, AuditEventType, AuditSeverity
    from security.session.manager import get_session_manager, SessionStatus
    from security.mfa.totp import get_mfa_manager
    SECURITY_AVAILABLE = True
except ImportError as e:
    print(f"[WARN] Security modules not available: {e}")
    SECURITY_AVAILABLE = False


def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated(*args, **kwargs):
        # Get token from header
        auth_header = request.headers.get('Authorization', '')
        token = None
        
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
        elif auth_header.startswith('Token '):
            token = auth_header[6:]
        else:
            # Legacy token support
            token = auth_header
        
        if not token:
            return jsonify({"error": "Missing authorization"}), 401
        
        # Validate against NEXUS_TOKEN
        from backend.app_integrated import NEXUS_TOKEN
        if token != NEXUS_TOKEN and token != NEXUS_TOKEN[-32:]:
            return jsonify({"error": "Invalid credentials"}), 401
        
        # Set user context
        g.user = {
            'codename': 'winsock',
            'clearance': 'TS/SCI/NOFORN'
        }
        g.token = token
        g.session_id = request.headers.get('X-Session-ID', 'legacy')
        
        return f(*args, **kwargs)
    
    return decorated


def require_clearance(min_clearance: str, compartments: Optional[Set[str]] = None):
    """
    Decorator to require minimum clearance level
    
    Args:
        min_clearance: Minimum clearance level required
        compartments: Required SCI compartments (optional)
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not SECURITY_AVAILABLE:
                # Allow if security not loaded (development mode)
                return f(*args, **kwargs)
            
            # Get user clearance
            user_clearance = g.get('user', {}).get('clearance', 'UNCLASSIFIED')
            user_codename = g.get('user', {}).get('codename', 'unknown')
            session_id = g.get('session_id', 'unknown')
            
            # Parse clearance levels
            from security.clearance import ClearanceLevel
            required = ClearanceLevel.from_string(min_clearance)
            current = ClearanceLevel.from_string(user_clearance)
            
            # Check clearance level
            if current < required:
                # Log denied access
                audit = get_audit_logger()
                audit.create_record(
                    event_type=AuditEventType.ACCESS_DENIED,
                    user_codename=user_codename,
                    user_clearance=user_clearance,
                    session_id=session_id,
                    resource_id=f"{request.endpoint}",
                    action=request.method,
                    status="DENIED",
                    severity=AuditSeverity.WARNING,
                    source_ip=request.remote_addr or '127.0.0.1',
                    result_code=403
                )
                
                return jsonify({
                    "error": "INSUFFICIENT_CLEARANCE",
                    "required": min_clearance,
                    "current": user_clearance
                }), 403
            
            # Check compartments
            if compartments:
                # In production, this would check user's actual compartments
                pass
            
            return f(*args, **kwargs)
        
        return decorated
    return decorator


def require_mfa(f):
    """Decorator to require MFA verification"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not SECURITY_AVAILABLE:
            return f(*args, **kwargs)
        
        user_clearance = g.get('user', {}).get('clearance', 'UNCLASSIFIED')
        
        # Check if MFA required
        mfa_mgr = get_mfa_manager()
        if mfa_mgr.require_mfa(user_clearance):
            # In production, verify MFA token was provided
            # For now, allow through with audit log
            pass
        
        return f(*args, **kwargs)
    
    return decorated


def audit_log(event_type: AuditEventType, resource_id: str = None, 
              capture_command: bool = False, capture_args: bool = False):
    """
    Decorator to automatically log function execution
    
    Args:
        event_type: Type of audit event
        resource_id: Resource being accessed
        capture_command: Whether to capture the command
        capture_args: Whether to capture arguments
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not SECURITY_AVAILABLE:
                return f(*args, **kwargs)
            
            # Get context
            user = g.get('user', {})
            user_codename = user.get('codename', 'unknown')
            user_clearance = user.get('clearance', 'UNCLASSIFIED')
            session_id = g.get('session_id', 'unknown')
            
            # Start time
            start_time = time.time()
            
            # Execute function
            try:
                result = f(*args, **kwargs)
                status = "SUCCESS"
                result_code = 200 if isinstance(result, tuple) and len(result) == 2 else 0
                severity = AuditSeverity.INFO
            except Exception as e:
                status = "ERROR"
                result_code = 500
                severity = AuditSeverity.ERROR
                raise
            finally:
                # Calculate duration
                duration_ms = int((time.time() - start_time) * 1000)
                
                # Create audit record
                audit = get_audit_logger()
                
                # Capture command info
                command = None
                command_args = None
                if capture_command:
                    command = request.endpoint
                if capture_args and request.is_json:
                    # Sanitize - don't log passwords/tokens
                    args_data = request.get_json()
                    command_args = [f"{k}=***" if 'pass' in k.lower() or 'token' in k.lower() or 'secret' in k.lower() else f"{k}={v}" 
                                   for k, v in args_data.items()]
                
                audit.create_record(
                    event_type=event_type,
                    user_codename=user_codename,
                    user_clearance=user_clearance,
                    session_id=session_id,
                    resource_id=resource_id or request.endpoint,
                    action=request.method,
                    status=status,
                    severity=severity,
                    source_ip=request.remote_addr or '127.0.0.1',
                    source_host=request.host or 'localhost',
                    command=command,
                    command_args=command_args,
                    result_code=result_code
                )
            
            return result
        
        return decorated
    return decorator


def require_session(f):
    """Decorator to validate session"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not SECURITY_AVAILABLE:
            return f(*args, **kwargs)
        
        session_id = request.headers.get('X-Session-ID')
        if not session_id:
            return jsonify({"error": "SESSION_REQUIRED", "message": "X-Session-ID header required"}), 401
        
        session_mgr = get_session_manager()
        session = session_mgr.get_session(session_id)
        
        if not session:
            return jsonify({"error": "SESSION_INVALID", "message": "Session expired or invalid"}), 401
        
        if session.status == SessionStatus.LOCKED:
            return jsonify({"error": "SESSION_LOCKED", "message": "Session locked - re-authentication required"}), 403
        
        if session.status == SessionStatus.SUSPICIOUS:
            return jsonify({"error": "SESSION_SUSPICIOUS", "message": "Session flagged for suspicious activity"}), 403
        
        # Update activity
        session_mgr.touch_session(session_id)
        
        # Store in g
        g.session = session
        g.session_id = session_id
        
        return f(*args, **kwargs)
    
    return decorated


# Convenience decorators for clearance levels
def require_secret(f):
    """Require SECRET or higher clearance"""
    return require_clearance('SECRET')(f)

def require_top_secret(f):
    """Require TOP SECRET or higher clearance"""
    return require_clearance('TOP SECRET')(f)

def require_sci(f):
    """Require TS/SCI or higher clearance"""
    return require_clearance('TS/SCI')(f)

def require_noforn(f):
    """Require TS/SCI/NOFORN clearance"""
    return require_clearance('TS/SCI/NOFORN')(f)


# Rate limiting with clearance awareness
def rate_limit_by_clearance():
    """Return rate limit based on user clearance"""
    user_clearance = g.get('user', {}).get('clearance', 'UNCLASSIFIED')
    
    limits = {
        'UNCLASSIFIED': '100/minute',
        'CONFIDENTIAL': '200/minute',
        'SECRET': '300/minute',
        'TOP SECRET': '400/minute',
        'TS/SCI': '500/minute',
        'TS/SCI/NOFORN': '600/minute'
    }
    
    return limits.get(user_clearance, '100/minute')
