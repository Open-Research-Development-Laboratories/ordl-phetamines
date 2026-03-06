#!/usr/bin/env python3
"""
ORDL Security Package
USG-Grade Security Infrastructure
Classification: TOP SECRET//NOFORN//SCI

This package provides comprehensive security controls for the ORDL
Terminal Command System, meeting and exceeding US Government standards.

Modules:
- clearance: USG clearance level management and access control
- audit: NIST 800-53 compliant audit logging with tamper-evident chain
- mfa: Multi-factor authentication (TOTP, hardware tokens)
- session: Session management with timeouts and security controls
- decorators: Flask route security decorators
"""

__version__ = "6.0.0"
__classification__ = "TOP SECRET//NOFORN//SCI"

# Export main classes for easy import
try:
    from .clearance import (
        ClearanceLevel,
        ClearanceAttributes,
        AccessControlList,
        get_acl,
        ORDL_RESOURCES
    )
    
    from .audit.logger import (
        AuditLogger,
        AuditRecord,
        AuditEventType,
        AuditSeverity,
        get_audit_logger
    )
    
    from .mfa.totp import (
        MFAManager,
        TOTPGenerator,
        MFAType,
        get_mfa_manager
    )
    
    from .session.manager import (
        SessionManager,
        Session,
        SessionStatus,
        SessionContext,
        get_session_manager
    )
    
    from .decorators import (
        require_auth,
        require_clearance,
        require_mfa,
        require_session,
        audit_log,
        require_secret,
        require_top_secret,
        require_sci,
        require_noforn
    )
    
    __all__ = [
        # Clearance
        'ClearanceLevel',
        'ClearanceAttributes',
        'AccessControlList',
        'get_acl',
        'ORDL_RESOURCES',
        
        # Audit
        'AuditLogger',
        'AuditRecord',
        'AuditEventType',
        'AuditSeverity',
        'get_audit_logger',
        
        # MFA
        'MFAManager',
        'TOTPGenerator',
        'MFAType',
        'get_mfa_manager',
        
        # Session
        'SessionManager',
        'Session',
        'SessionStatus',
        'SessionContext',
        'get_session_manager',
        
        # Decorators
        'require_auth',
        'require_clearance',
        'require_mfa',
        'require_session',
        'audit_log',
        'require_secret',
        'require_top_secret',
        'require_sci',
        'require_noforn'
    ]
    
except ImportError as e:
    # During initial setup, modules might not be fully available
    print(f"[INFO] Security package partial load: {e}")
    __all__ = []


def get_security_status() -> dict:
    """Get overall security system status"""
    status = {
        'package_version': __version__,
        'classification': __classification__,
        'components': {}
    }
    
    try:
        from .clearance import get_acl
        acl = get_acl()
        status['components']['clearance'] = {
            'status': 'operational',
            'resources_defined': len(acl.resources)
        }
    except Exception as e:
        status['components']['clearance'] = {'status': 'error', 'error': str(e)}
    
    try:
        from .audit.logger import get_audit_logger
        logger = get_audit_logger()
        status['components']['audit'] = {
            'status': 'operational',
            'database': logger.db_path
        }
    except Exception as e:
        status['components']['audit'] = {'status': 'error', 'error': str(e)}
    
    try:
        from .mfa.totp import get_mfa_manager
        mfa = get_mfa_manager()
        status['components']['mfa'] = {
            'status': 'operational'
        }
    except Exception as e:
        status['components']['mfa'] = {'status': 'error', 'error': str(e)}
    
    try:
        from .session.manager import get_session_manager
        mgr = get_session_manager()
        status['components']['session'] = {
            'status': 'operational',
            'active_sessions': len([s for s in mgr._sessions.values() if s.status.value == 'active'])
        }
    except Exception as e:
        status['components']['session'] = {'status': 'error', 'error': str(e)}
    
    return status


if __name__ == '__main__':
    # Run security system check
    print("ORDL Security System v6.0.0")
    print("=" * 50)
    
    status = get_security_status()
    print(f"Classification: {status['classification']}")
    print(f"Version: {status['package_version']}")
    print()
    
    for component, info in status['components'].items():
        print(f"{component.upper()}: {info['status']}")
        if 'error' in info:
            print(f"  Error: {info['error']}")
