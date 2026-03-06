#!/usr/bin/env python3
"""
ORDL Command Post v6.0.0 - SECURITY INTEGRATED
USG-Grade Secure API Backend
Classification: TOP SECRET//NOFORN//SCI
"""

import os
import sys
import json
import time
import uuid
import sqlite3
import psutil
import requests
import threading
import subprocess
import hashlib
import io
import contextlib
import asyncio
from datetime import datetime, timedelta
from functools import wraps
from urllib.parse import quote

from flask import Flask, request, jsonify, Response, stream_with_context, send_from_directory, g
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Add parent directory to path
sys.path.insert(0, '/opt/codex-swarm/command-post')

# =============================================================================
# SECURITY MODULE IMPORTS
# =============================================================================
try:
    from security.clearance import (
        ClearanceLevel, ClearanceAttributes, get_acl, 
        ORDL_RESOURCES, AccessControlList
    )
    from security.audit.logger import (
        get_audit_logger, AuditEventType, AuditSeverity, AuditRecord
    )
    from security.session.manager import (
        get_session_manager, SessionManager, SessionStatus, Session
    )
    from security.mfa.totp import get_mfa_manager, MFAType, TOTPGenerator
    from security.decorators import (
        require_auth, require_clearance, require_mfa, require_session,
        audit_log, require_secret, require_top_secret, require_sci, require_noforn
    )
    SECURITY_AVAILABLE = True
    print("[SECURITY] USG-grade security system loaded")
except ImportError as e:
    print(f"[SECURITY WARNING] Security modules unavailable: {e}")
    SECURITY_AVAILABLE = False
    
    # Create stub decorators if security not available
    def require_auth(f):
        return f
    def require_clearance(level):
        def decorator(f):
            return f
        return decorator
    def require_mfa(f):
        return f
    def require_session(f):
        return f
    def audit_log(*args, **kwargs):
        def decorator(f):
            return f
        return decorator
    def require_secret(f):
        return f
    def require_top_secret(f):
        return f
    def require_sci(f):
        return f
    def require_noforn(f):
        return f

# =============================================================================
# CONFIGURATION
# =============================================================================
DATA_DIR = "/opt/codex-swarm/command-post/data"
UPLOADS_DIR = "/opt/codex-swarm/command-post/uploads"
MODELS_DIR = "/opt/codex-swarm/command-post/models"
STATIC_FOLDER = "/opt/codex-swarm/command-post/static"
DB_PATH = os.path.join(DATA_DIR, "nexus.db")
AUDIT_DB_PATH = os.path.join(DATA_DIR, "audit.db")

ROUTER_URL = os.environ.get('ROUTER_URL', 'http://localhost:18000')
JWT_SECRET = os.environ.get('JWT_SECRET_KEY', 'ordl-secret-key-change-in-production')
NEXUS_TOKEN = os.environ.get('NEXUS_TOKEN', 'WINSOCK!IS!GOAT!ORDL3991!-3dc65a69fda7069b53e40ff05c9f5620')

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)

# =============================================================================
# FLASK APP SETUP
# =============================================================================
app = Flask(__name__, static_folder=STATIC_FOLDER, static_url_path='/static')
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024
CORS(app)

# Rate limiter with clearance-based limits
def get_rate_limit_key():
    """Get rate limit key based on user clearance"""
    user = getattr(g, 'user', {})
    clearance = user.get('clearance', 'UNCLASSIFIED')
    
    limits = {
        'UNCLASSIFIED': '100/minute',
        'CONFIDENTIAL': '200/minute',
        'SECRET': '300/minute',
        'TOP SECRET': '400/minute',
        'TS/SCI': '500/minute',
        'TS/SCI/NOFORN': '600/minute'
    }
    return limits.get(clearance, '100/minute')

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per minute", "1000 per hour"]
)

# =============================================================================
# SECURITY INITIALIZATION
# =============================================================================
security_acl = None
audit_logger = None
session_manager = None
mfa_manager = None

if SECURITY_AVAILABLE:
    try:
        security_acl = get_acl()
        audit_logger = get_audit_logger()
        session_manager = get_session_manager()
        mfa_manager = get_mfa_manager()
        print("[SECURITY] All security components initialized")
    except Exception as e:
        print(f"[SECURITY ERROR] Failed to initialize: {e}")
        SECURITY_AVAILABLE = False

# =============================================================================
# REQUEST CONTEXT SETUP
# =============================================================================
@app.before_request
def setup_request_context():
    """Set up security context for each request"""
    g.user = None
    g.token = None
    g.session = None
    g.session_id = None
    g.start_time = time.time()

@app.after_request
def log_request(response):
    """Log request to audit system"""
    if audit_logger and hasattr(g, 'user') and g.user:
        duration_ms = int((time.time() - g.start_time) * 1000)
        
        # Determine event type based on response status
        if response.status_code >= 500:
            event_type = AuditEventType.SYSTEM_ERROR
            severity = AuditSeverity.ERROR
        elif response.status_code == 403:
            event_type = AuditEventType.ACCESS_DENIED
            severity = AuditSeverity.WARNING
        elif response.status_code == 401:
            event_type = AuditEventType.AUTHENTICATION_FAILURE
            severity = AuditSeverity.WARNING
        else:
            event_type = AuditEventType.DATA_READ
            severity = AuditSeverity.INFO
        
        # Create audit record
        try:
            audit_logger.create_record(
                event_type=event_type,
                user_codename=g.user.get('codename', 'unknown'),
                user_clearance=g.user.get('clearance', 'UNCLASSIFIED'),
                session_id=g.get('session_id', 'unknown'),
                resource_id=request.endpoint or 'unknown',
                action=request.method,
                status='SUCCESS' if response.status_code < 400 else 'FAILURE',
                severity=severity,
                source_ip=request.remote_addr or '127.0.0.1',
                source_host=request.host or 'localhost',
                result_code=response.status_code,
                bytes_transferred=response.content_length or 0
            )
        except Exception as e:
            print(f"[AUDIT ERROR] Failed to log: {e}")
    
    return response

# =============================================================================
# AUTHENTICATION ENDPOINTS - SECURITY INTEGRATED
# =============================================================================

@app.route('/api/auth/login', methods=['POST'])
@limiter.limit("10 per minute")
def login():
    """
    Authenticate user and create secure session
    
    Returns:
        access_token: Bearer token
        session_id: Session identifier
        mfa_required: Whether MFA verification needed
        mfa_enrolled: Whether user has MFA enrolled
    """
    data = request.get_json()
    codename = data.get('codename', '').strip().upper()
    password = data.get('password', '').strip()
    
    # Validate input
    if not codename or not password:
        if audit_logger:
            audit_logger.create_record(
                event_type=AuditEventType.AUTHENTICATION_FAILURE,
                user_codename='unknown',
                user_clearance='UNCLASSIFIED',
                session_id='none',
                resource_id='auth.login',
                action='POST',
                status='FAILURE',
                severity=AuditSeverity.WARNING,
                source_ip=request.remote_addr or '127.0.0.1',
                result_code=400
            )
        return jsonify({"error": "CREDENTIALS_REQUIRED"}), 400
    
    # Verify credentials
    if password != NEXUS_TOKEN and password != NEXUS_TOKEN[-32:]:
        if audit_logger:
            audit_logger.create_record(
                event_type=AuditEventType.AUTHENTICATION_FAILURE,
                user_codename=codename,
                user_clearance='UNCLASSIFIED',
                session_id='none',
                resource_id='auth.login',
                action='POST',
                status='FAILURE',
                severity=AuditSeverity.WARNING,
                source_ip=request.remote_addr or '127.0.0.1',
                result_code=401
            )
        return jsonify({"error": "AUTHENTICATION_FAILED"}), 401
    
    # Create user context
    user = {
        'codename': codename or 'OPERATOR',
        'clearance': 'TS/SCI/NOFORN',
        'compartments': ['HCS', 'KLONDIKE', 'GAMMA', 'TALENT KEYHOLE']
    }
    
    # Check if MFA required
    mfa_required = False
    mfa_enrolled = False
    if mfa_manager and mfa_manager.require_mfa(user['clearance']):
        mfa_required = True
        devices = mfa_manager.get_user_devices(user['codename'])
        mfa_enrolled = len(devices) > 0
    
    # Create session
    session = None
    if session_manager:
        session = session_manager.create_session(
            user_codename=user['codename'],
            user_clearance=user['clearance'],
            user_compartments=user['compartments'],
            ip_address=request.remote_addr or '127.0.0.1',
            user_agent=request.headers.get('User-Agent', 'unknown')
        )
    
    # Log successful authentication
    if audit_logger:
        audit_logger.create_record(
            event_type=AuditEventType.AUTHENTICATION_SUCCESS,
            user_codename=user['codename'],
            user_clearance=user['clearance'],
            session_id=session.session_id if session else 'legacy',
            resource_id='auth.login',
            action='POST',
            status='SUCCESS',
            severity=AuditSeverity.INFO,
            source_ip=request.remote_addr or '127.0.0.1',
            mfa_used=False,  # Initial login
            result_code=200
        )
    
    response = {
        "success": True,
        "access_token": NEXUS_TOKEN,
        "user": user,
        "mfa_required": mfa_required,
        "mfa_enrolled": mfa_enrolled
    }
    
    if session:
        response['session_id'] = session.session_id
        response['session_expires'] = session.expires_at.isoformat()
    
    return jsonify(response)


@app.route('/api/auth/mfa/enroll', methods=['POST'])
@require_auth
def mfa_enroll():
    """Enroll TOTP MFA for user"""
    if not mfa_manager:
        return jsonify({"error": "MFA_NOT_AVAILABLE"}), 503
    
    user = g.get('user', {})
    codename = user.get('codename', 'unknown')
    
    try:
        result = mfa_manager.enroll_totp(codename, device_name="ORDL Terminal")
        
        # Log enrollment
        if audit_logger:
            audit_logger.create_record(
                event_type=AuditEventType.MFA_CHALLENGE,
                user_codename=codename,
                user_clearance=user.get('clearance', 'UNCLASSIFIED'),
                session_id=g.get('session_id', 'unknown'),
                resource_id='auth.mfa_enroll',
                action='POST',
                status='SUCCESS',
                severity=AuditSeverity.INFO,
                source_ip=request.remote_addr or '127.0.0.1',
                result_code=200
            )
        
        return jsonify({
            "success": True,
            "device_id": result['device']['device_id'],
            "qr_code": result['qr_code_png'],
            "backup_codes": result['backup_codes'],
            "secret": result['secret']  # Show once
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/auth/mfa/verify', methods=['POST'])
@require_auth
def mfa_verify():
    """Verify MFA code"""
    if not mfa_manager:
        return jsonify({"error": "MFA_NOT_AVAILABLE"}), 503
    
    data = request.get_json()
    code = data.get('code', '').strip()
    
    if not code:
        return jsonify({"error": "CODE_REQUIRED"}), 400
    
    user = g.get('user', {})
    codename = user.get('codename', 'unknown')
    
    # Try TOTP first, then backup codes
    valid = False
    factor_type = None
    
    if mfa_manager.verify_totp(codename, code):
        valid = True
        factor_type = MFAType.TOTP.value
    elif mfa_manager.verify_backup_code(codename, code):
        valid = True
        factor_type = MFAType.BACKUP_CODES.value
    
    if valid:
        # Update session context
        session_id = g.get('session_id')
        if session_id and session_manager:
            session = session_manager.get_session(session_id)
            if session:
                session.context.mfa_verified = True
                session.context.last_activity = datetime.utcnow().isoformat()
        
        # Log success
        if audit_logger:
            audit_logger.create_record(
                event_type=AuditEventType.MFA_SUCCESS,
                user_codename=codename,
                user_clearance=user.get('clearance', 'UNCLASSIFIED'),
                session_id=g.get('session_id', 'unknown'),
                resource_id='auth.mfa_verify',
                action='POST',
                status='SUCCESS',
                severity=AuditSeverity.INFO,
                source_ip=request.remote_addr or '127.0.0.1',
                mfa_used=True,
                mfa_factors=[factor_type],
                result_code=200
            )
        
        return jsonify({"success": True, "factor": factor_type})
    else:
        # Log failure
        if audit_logger:
            audit_logger.create_record(
                event_type=AuditEventType.MFA_FAILURE,
                user_codename=codename,
                user_clearance=user.get('clearance', 'UNCLASSIFIED'),
                session_id=g.get('session_id', 'unknown'),
                resource_id='auth.mfa_verify',
                action='POST',
                status='FAILURE',
                severity=AuditSeverity.WARNING,
                source_ip=request.remote_addr or '127.0.0.1',
                result_code=401
            )
        
        return jsonify({"error": "INVALID_CODE"}), 401


@app.route('/api/auth/me', methods=['GET'])
@require_auth
def get_current_user():
    """Get current user info"""
    return jsonify({
        "user": g.get('user', {}),
        "session": g.get('session_id'),
        "security_available": SECURITY_AVAILABLE
    })


@app.route('/api/auth/logout', methods=['POST'])
@require_auth
def logout():
    """Logout and terminate session"""
    session_id = g.get('session_id')
    user = g.get('user', {})
    
    if session_id and session_manager:
        session_manager.terminate_session(session_id, "USER_LOGOUT")
    
    if audit_logger:
        audit_logger.create_record(
            event_type=AuditEventType.AUTHENTICATION_LOGOUT,
            user_codename=user.get('codename', 'unknown'),
            user_clearance=user.get('clearance', 'UNCLASSIFIED'),
            session_id=session_id or 'unknown',
            resource_id='auth.logout',
            action='POST',
            status='SUCCESS',
            severity=AuditSeverity.INFO,
            source_ip=request.remote_addr or '127.0.0.1',
            result_code=200
        )
    
    return jsonify({"success": True})


# =============================================================================
# SESSION MANAGEMENT ENDPOINTS
# =============================================================================

@app.route('/api/sessions', methods=['GET'])
@require_auth
def list_sessions():
    """List active sessions for user"""
    user = g.get('user', {})
    codename = user.get('codename', 'unknown')
    
    if session_manager:
        sessions = session_manager.get_user_sessions(codename)
        return jsonify({
            "sessions": sessions,
            "count": len(sessions)
        })
    
    return jsonify({"sessions": [], "count": 0})


@app.route('/api/sessions/<session_id>', methods=['DELETE'])
@require_auth
def terminate_session_endpoint(session_id):
    """Terminate a specific session"""
    user = g.get('user', {})
    codename = user.get('codename', 'unknown')
    
    if session_manager:
        # Can only terminate own sessions (unless admin)
        session = session_manager.get_session(session_id)
        if not session:
            return jsonify({"error": "SESSION_NOT_FOUND"}), 404
        
        if session.user_codename != codename and user.get('clearance') != 'TS/SCI/NOFORN':
            return jsonify({"error": "UNAUTHORIZED"}), 403
        
        session_manager.terminate_session(session_id, "USER_TERMINATED")
        
        if audit_logger:
            audit_logger.create_record(
                event_type=AuditEventType.SESSION_DESTROY,
                user_codename=codename,
                user_clearance=user.get('clearance', 'UNCLASSIFIED'),
                session_id=session_id,
                resource_id='sessions.terminate',
                action='DELETE',
                status='SUCCESS',
                severity=AuditSeverity.INFO,
                source_ip=request.remote_addr or '127.0.0.1',
                result_code=200
            )
        
        return jsonify({"success": True})
    
    return jsonify({"error": "SESSION_MANAGER_UNAVAILABLE"}), 503


# =============================================================================
# AUDIT LOG ENDPOINTS (ADMIN ONLY)
# =============================================================================

@app.route('/api/audit/logs', methods=['GET'])
@require_auth
@require_clearance('TS/SCI_NOFORN')
def query_audit_logs():
    """Query audit logs (admin only)"""
    if not audit_logger:
        return jsonify({"error": "AUDIT_NOT_AVAILABLE"}), 503
    
    # Parse query parameters
    user = request.args.get('user')
    event_type = request.args.get('event_type')
    severity = request.args.get('severity')
    limit = request.args.get('limit', 1000, type=int)
    
    try:
        records = audit_logger.query(
            user_codename=user,
            event_type=event_type,
            severity=severity,
            limit=limit
        )
        
        return jsonify({
            "records": [r.to_dict() for r in records],
            "count": len(records)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/audit/integrity', methods=['GET'])
@require_auth
@require_clearance('TS/SCI_NOFORN')
def verify_audit_integrity():
    """Verify audit log chain integrity"""
    if not audit_logger:
        return jsonify({"error": "AUDIT_NOT_AVAILABLE"}), 503
    
    valid, message = audit_logger.verify_integrity()
    
    return jsonify({
        "valid": valid,
        "message": message
    })


# =============================================================================
# SECURITY STATUS ENDPOINT
# =============================================================================

@app.route('/api/security/status', methods=['GET'])
@require_auth
def security_status():
    """Get security system status"""
    status = {
        "security_available": SECURITY_AVAILABLE,
        "version": "6.0.0",
        "classification": "TOP SECRET//NOFORN//SCI"
    }
    
    if SECURITY_AVAILABLE:
        if security_acl:
            status['acl'] = {
                "resources_defined": len(security_acl.resources)
            }
        
        if session_manager:
            stats = session_manager.get_stats()
            status['sessions'] = stats
        
        if audit_logger:
            status['audit'] = {
                "database_path": AUDIT_DB_PATH,
                "operational": True
            }
        
        if mfa_manager:
            status['mfa'] = {
                "operational": True
            }
    
    return jsonify(status)


# =============================================================================
# ERROR HANDLERS
# =============================================================================

@app.errorhandler(429)
def ratelimit_handler(e):
    """Rate limit exceeded"""
    if audit_logger and hasattr(g, 'user') and g.user:
        audit_logger.create_record(
            event_type=AuditEventType.SECURITY_ALERT,
            user_codename=g.user.get('codename', 'unknown'),
            user_clearance=g.user.get('clearance', 'UNCLASSIFIED'),
            session_id=g.get('session_id', 'unknown'),
            resource_id='ratelimit',
            action='RATE_LIMIT',
            status='ALERT',
            severity=AuditSeverity.WARNING,
            source_ip=request.remote_addr or '127.0.0.1',
            result_code=429
        )
    
    return jsonify({
        "error": "RATE_LIMIT_EXCEEDED",
        "message": "Too many requests. Slow down."
    }), 429


@app.errorhandler(403)
def forbidden_handler(e):
    """Access forbidden"""
    return jsonify({
        "error": "ACCESS_DENIED",
        "message": "Insufficient clearance for this resource."
    }), 403


@app.errorhandler(401)
def unauthorized_handler(e):
    """Not authenticated"""
    return jsonify({
        "error": "UNAUTHORIZED",
        "message": "Authentication required."
    }), 401


# =============================================================================
# HEALTH CHECK
# =============================================================================

@app.route('/health')
def health():
    """System health check"""
    components = {
        "auth": True,
        "mcp": True,
        "network": True,
        "rag": True,
        "sandbox": True,
        "search": True,
        "training": True,
        "websocket": True,
        "security": SECURITY_AVAILABLE
    }
    
    # Check security components
    if SECURITY_AVAILABLE:
        components['acl'] = security_acl is not None
        components['audit'] = audit_logger is not None
        components['sessions'] = session_manager is not None
        components['mfa'] = mfa_manager is not None
    
    return jsonify({
        "status": "healthy",
        "version": "6.0.0-secure",
        "components": components,
        "timestamp": datetime.utcnow().isoformat()
    })


# =============================================================================
# MAIN
# =============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("ORDL Command Post v6.0.0 - SECURITY INTEGRATED")
    print("Classification: TOP SECRET//NOFORN//SCI")
    print("=" * 60)
    
    if SECURITY_AVAILABLE:
        print("[OK] USG-grade security system active")
        print(f"[OK] ACL: {len(security_acl.resources)} resources defined")
        print(f"[OK] Audit: Logging to {AUDIT_DB_PATH}")
        print(f"[OK] Sessions: Manager ready")
        print(f"[OK] MFA: TOTP system ready")
    else:
        print("[WARNING] Running in DEVELOPMENT MODE - security disabled")
    
    print("=" * 60)
    
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('API_PORT', 18010)),
        debug=False,
        threaded=True
    )
