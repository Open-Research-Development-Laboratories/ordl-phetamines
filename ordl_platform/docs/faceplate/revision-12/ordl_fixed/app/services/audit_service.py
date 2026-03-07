"""
Audit Logging Service for ORDL BFF API

Handles audit event logging by forwarding to the backend API.
"""
import os
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from threading import Thread

from flask import request, g

from app.services.backend_client import get_backend_client, BackendClientError


logger = logging.getLogger(__name__)


class AuditLogger:
    """
    Audit logger that forwards events to the backend API.
    
    Supports both synchronous and asynchronous logging modes.
    """
    
    def __init__(self, async_mode: bool = True):
        """
        Initialize audit logger.
        
        Args:
            async_mode: If True, log events asynchronously (non-blocking)
        """
        self.async_mode = async_mode
        self.client = get_backend_client()
    
    def log_event(
        self,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        org_id: Optional[str] = None,
        user_id: Optional[str] = None,
        synchronous: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Log an audit event.
        
        Args:
            action: The action being performed (e.g., 'ORG_READ', 'USER_LOGIN')
            resource_type: Type of resource (e.g., 'org', 'provider', 'user')
            resource_id: Optional identifier for the specific resource
            details: Optional additional details about the event
            org_id: Optional organization ID for context
            user_id: Optional override for user ID (defaults to g.user_id)
            synchronous: If True, wait for backend response
            
        Returns:
            Backend response if synchronous, None otherwise
        """
        event = self._build_event(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            org_id=org_id,
            user_id=user_id
        )
        
        if synchronous or not self.async_mode:
            return self._send_event(event)
        else:
            # Send asynchronously
            Thread(target=self._send_event, args=(event,), daemon=True).start()
            return None
    
    def _build_event(
        self,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        org_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Build the audit event payload."""
        # Get user context from Flask g object or use provided values
        actor_id = user_id or getattr(g, 'user_id', None) or 'anonymous'
        auth_context = getattr(g, 'auth_context', None)
        
        event = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'action': action,
            'resource_type': resource_type,
            'resource_id': resource_id,
            'actor': {
                'user_id': actor_id,
                'ip_address': self._get_client_ip(),
                'user_agent': request.headers.get('User-Agent', ''),
                'session_id': getattr(g, 'session_id', None)
            },
            'details': details or {},
            'source': {
                'service': 'bff-api',
                'version': os.environ.get('APP_VERSION', 'unknown'),
                'hostname': os.environ.get('HOSTNAME', 'unknown')
            }
        }
        
        if org_id:
            event['org_id'] = org_id
        
        if auth_context:
            event['actor']['clearance_level'] = auth_context.clearance_level
            event['actor']['roles'] = auth_context.roles
        
        return event
    
    def _get_client_ip(self) -> str:
        """Get client IP address from request."""
        # Check for proxy headers
        if request.headers.get('X-Forwarded-For'):
            return request.headers.get('X-Forwarded-For').split(',')[0].strip()
        if request.headers.get('X-Real-IP'):
            return request.headers.get('X-Real-IP')
        return request.remote_addr or 'unknown'
    
    def _send_event(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Send the audit event to the backend."""
        try:
            status_code, response = self.client.post(
                '/v1/audit/events',
                json_data=event
            )
            
            if status_code >= 400:
                logger.warning(f"Audit log backend returned error: {status_code}")
                return None
            
            return response
            
        except BackendClientError as e:
            # Log to local logger as fallback
            logger.error(f"Failed to send audit event: {e}")
            return None
        except Exception as e:
            logger.exception(f"Unexpected error sending audit event: {e}")
            return None


# Singleton instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get or create the audit logger singleton."""
    global _audit_logger
    if _audit_logger is None:
        async_mode = os.environ.get('AUDIT_ASYNC', 'true').lower() == 'true'
        _audit_logger = AuditLogger(async_mode=async_mode)
    return _audit_logger


def log_audit_event(
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    org_id: Optional[str] = None,
    synchronous: bool = False
) -> Optional[Dict[str, Any]]:
    """
    Convenience function to log an audit event.
    
    Example:
        log_audit_event(
            action='ORG_READ',
            resource_type='org',
            resource_id='org_123',
            org_id='org_123'
        )
    """
    logger = get_audit_logger()
    return logger.log_event(
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        org_id=org_id,
        synchronous=synchronous
    )
