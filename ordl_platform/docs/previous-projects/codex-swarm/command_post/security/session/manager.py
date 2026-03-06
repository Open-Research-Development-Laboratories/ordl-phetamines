#!/usr/bin/env python3
"""
ORDL Session Management System
USG-Compliant Session Control with Timeouts
Classification: TOP SECRET//NOFORN//SCI
"""

import uuid
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import threading
import time


class SessionStatus(Enum):
    """Session lifecycle states"""
    ACTIVE = "active"
    IDLE = "idle"
    LOCKED = "locked"
    EXPIRED = "expired"
    TERMINATED = "terminated"
    SUSPICIOUS = "suspicious"


@dataclass
class SessionContext:
    """Security context for a session"""
    clearance_verified: bool = False
    mfa_verified: bool = False
    witness_verified: Optional[str] = None  # Witness codename
    two_person_integrity: bool = False
    location_verified: bool = False
    device_trusted: bool = False
    last_activity: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def is_fresh(self, max_age_seconds: int = 300) -> bool:
        """Check if context is fresh (within timeout)"""
        last = datetime.fromisoformat(self.last_activity)
        return datetime.utcnow() - last < timedelta(seconds=max_age_seconds)


@dataclass
class Session:
    """User session state"""
    # Identity
    session_id: str
    user_codename: str
    user_clearance: str
    user_compartments: List[str]
    
    # Timing
    created_at: datetime
    last_activity: datetime
    expires_at: datetime
    idle_timeout: int  # seconds
    absolute_timeout: int  # seconds
    
    # Status
    status: SessionStatus
    context: SessionContext
    
    # Security
    ip_address: str
    user_agent: str
    device_fingerprint: str
    csrf_token: str
    
    # Tracking
    command_count: int = 0
    data_accessed: int = 0  # bytes
    privilege_escalations: List[Dict] = field(default_factory=list)
    
    def is_expired(self) -> bool:
        """Check if session has expired"""
        now = datetime.utcnow()
        if now > self.expires_at:
            return True
        if now - self.last_activity > timedelta(seconds=self.idle_timeout):
            return True
        if now - self.created_at > timedelta(seconds=self.absolute_timeout):
            return True
        return False
    
    def touch(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.utcnow()
        self.context.last_activity = self.last_activity.isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            'session_id': self.session_id,
            'user_codename': self.user_codename,
            'user_clearance': self.user_clearance,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'last_activity': self.last_activity.isoformat(),
            'expires_at': self.expires_at.isoformat(),
            'ip_address': self.ip_address,
            'command_count': self.command_count
        }


class SessionManager:
    """
    USG-Compliant Session Management
    
    Features:
    - Idle and absolute timeouts
    - Clearance-based session policies
    - Concurrent session limits
    - Automatic cleanup
    - Suspicious activity detection
    """
    
    # Timeout configurations by clearance level
    DEFAULT_TIMEOUTS = {
        'UNCLASSIFIED': {
            'idle': 3600,      # 1 hour
            'absolute': 28800  # 8 hours
        },
        'CONFIDENTIAL': {
            'idle': 1800,      # 30 minutes
            'absolute': 14400  # 4 hours
        },
        'SECRET': {
            'idle': 900,       # 15 minutes
            'absolute': 7200   # 2 hours
        },
        'TOP SECRET': {
            'idle': 600,       # 10 minutes
            'absolute': 3600   # 1 hour
        },
        'TS/SCI': {
            'idle': 300,       # 5 minutes
            'absolute': 1800   # 30 minutes
        },
        'TS/SCI/NOFORN': {
            'idle': 120,       # 2 minutes
            'absolute': 900    # 15 minutes
        }
    }
    
    # Maximum concurrent sessions by clearance
    MAX_CONCURRENT = {
        'UNCLASSIFIED': 5,
        'CONFIDENTIAL': 3,
        'SECRET': 2,
        'TOP SECRET': 2,
        'TS/SCI': 1,
        'TS/SCI/NOFORN': 1
    }
    
    def __init__(self):
        self._sessions: Dict[str, Session] = {}
        self._user_sessions: Dict[str, List[str]] = {}  # user -> session IDs
        self._lock = threading.RLock()
        self._callbacks: Dict[str, List[Callable]] = {
            'created': [],
            'expired': [],
            'terminated': [],
            'suspicious': []
        }
        
        # Start cleanup thread
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()
    
    def create_session(
        self,
        user_codename: str,
        user_clearance: str,
        user_compartments: List[str],
        ip_address: str,
        user_agent: str,
        device_fingerprint: Optional[str] = None
    ) -> Session:
        """
        Create new user session
        
        Returns:
            New Session object
            
        Raises:
            SessionLimitExceeded: If user has too many concurrent sessions
        """
        with self._lock:
            # Check concurrent session limit
            current_sessions = self._user_sessions.get(user_codename, [])
            max_sessions = self.MAX_CONCURRENT.get(user_clearance, 2)
            
            if len(current_sessions) >= max_sessions:
                # Terminate oldest session
                oldest_id = current_sessions[0]
                self.terminate_session(oldest_id, "CONCURRENT_LIMIT")
            
            # Generate session ID
            session_id = self._generate_session_id()
            
            # Get timeouts
            timeouts = self.DEFAULT_TIMEOUTS.get(user_clearance, self.DEFAULT_TIMEOUTS['SECRET'])
            
            now = datetime.utcnow()
            
            # Create session
            session = Session(
                session_id=session_id,
                user_codename=user_codename,
                user_clearance=user_clearance,
                user_compartments=user_compartments,
                created_at=now,
                last_activity=now,
                expires_at=now + timedelta(seconds=timeouts['absolute']),
                idle_timeout=timeouts['idle'],
                absolute_timeout=timeouts['absolute'],
                status=SessionStatus.ACTIVE,
                context=SessionContext(),
                ip_address=ip_address,
                user_agent=user_agent,
                device_fingerprint=device_fingerprint or self._fingerprint(ip_address, user_agent),
                csrf_token=secrets.token_hex(32)
            )
            
            # Store session
            self._sessions[session_id] = session
            
            if user_codename not in self._user_sessions:
                self._user_sessions[user_codename] = []
            self._user_sessions[user_codename].append(session_id)
            
            # Trigger callbacks
            self._trigger('created', session)
            
            return session
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID, checking expiration"""
        with self._lock:
            session = self._sessions.get(session_id)
            
            if not session:
                return None
            
            if session.is_expired():
                self._expire_session(session_id)
                return None
            
            return session
    
    def validate_session(
        self,
        session_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> tuple[bool, str]:
        """
        Validate session with security checks
        
        Returns:
            (is_valid, reason)
        """
        session = self.get_session(session_id)
        
        if not session:
            return False, "SESSION_NOT_FOUND"
        
        if session.status == SessionStatus.TERMINATED:
            return False, "SESSION_TERMINATED"
        
        if session.status == SessionStatus.LOCKED:
            return False, "SESSION_LOCKED"
        
        # IP check (optional but recommended for high clearance)
        if ip_address and session.user_clearance in ['TS/SCI', 'TS/SCI/NOFORN']:
            if ip_address != session.ip_address:
                self._flag_suspicious(session_id, "IP_MISMATCH")
                return False, "IP_MISMATCH"
        
        # Device fingerprint check
        if user_agent and session.user_clearance in ['TOP SECRET', 'TS/SCI', 'TS/SCI/NOFORN']:
            current_fp = self._fingerprint(ip_address or session.ip_address, user_agent)
            if current_fp != session.device_fingerprint:
                self._flag_suspicious(session_id, "DEVICE_MISMATCH")
                return False, "DEVICE_MISMATCH"
        
        return True, "VALID"
    
    def touch_session(self, session_id: str) -> bool:
        """Update session activity timestamp"""
        with self._lock:
            session = self._sessions.get(session_id)
            if session and session.status == SessionStatus.ACTIVE:
                session.touch()
                return True
            return False
    
    def lock_session(self, session_id: str, reason: str = "USER_LOCKED") -> bool:
        """Lock session (requires re-authentication to unlock)"""
        with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.status = SessionStatus.LOCKED
                return True
            return False
    
    def unlock_session(self, session_id: str, mfa_verified: bool = False) -> bool:
        """Unlock a locked session"""
        with self._lock:
            session = self._sessions.get(session_id)
            if session and session.status == SessionStatus.LOCKED:
                if mfa_verified or session.user_clearance in ['UNCLASSIFIED', 'CONFIDENTIAL']:
                    session.status = SessionStatus.ACTIVE
                    session.touch()
                    return True
            return False
    
    def terminate_session(self, session_id: str, reason: str = "USER_LOGOUT") -> bool:
        """Terminate a session immediately"""
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return False
            
            session.status = SessionStatus.TERMINATED
            
            # Remove from user sessions
            user = session.user_codename
            if user in self._user_sessions:
                if session_id in self._user_sessions[user]:
                    self._user_sessions[user].remove(session_id)
            
            # Keep in sessions dict for audit, mark for cleanup
            self._trigger('terminated', session, reason)
            
            return True
    
    def terminate_all_user_sessions(self, user_codename: str, except_session: Optional[str] = None) -> int:
        """Terminate all sessions for a user (e.g., password change, breach)"""
        count = 0
        with self._lock:
            session_ids = self._user_sessions.get(user_codename, []).copy()
            for sid in session_ids:
                if sid != except_session:
                    self.terminate_session(sid, "ADMIN_TERMINATED")
                    count += 1
        return count
    
    def _expire_session(self, session_id: str):
        """Mark session as expired"""
        session = self._sessions.get(session_id)
        if session:
            session.status = SessionStatus.EXPIRED
            self._trigger('expired', session)
    
    def _flag_suspicious(self, session_id: str, reason: str):
        """Flag session for suspicious activity"""
        session = self._sessions.get(session_id)
        if session:
            session.status = SessionStatus.SUSPICIOUS
            self._trigger('suspicious', session, reason)
    
    def _cleanup_loop(self):
        """Background thread to clean up expired sessions"""
        while True:
            time.sleep(60)  # Check every minute
            self._cleanup_expired()
    
    def _cleanup_expired(self):
        """Remove expired/terminated sessions from memory"""
        with self._lock:
            to_remove = []
            for sid, session in self._sessions.items():
                if session.status in [SessionStatus.EXPIRED, SessionStatus.TERMINATED]:
                    # Keep for 24 hours for audit, then remove
                    if datetime.utcnow() - session.last_activity > timedelta(hours=24):
                        to_remove.append(sid)
            
            for sid in to_remove:
                del self._sessions[sid]
    
    def _generate_session_id(self) -> str:
        """Generate cryptographically secure session ID"""
        return secrets.token_urlsafe(32)
    
    def _fingerprint(self, ip: str, user_agent: str) -> str:
        """Generate device fingerprint"""
        data = f"{ip}:{user_agent}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    def register_callback(self, event: str, callback: Callable):
        """Register callback for session events"""
        if event in self._callbacks:
            self._callbacks[event].append(callback)
    
    def _trigger(self, event: str, *args):
        """Trigger event callbacks"""
        for callback in self._callbacks.get(event, []):
            try:
                callback(*args)
            except Exception:
                pass
    
    def get_user_sessions(self, user_codename: str) -> List[Dict]:
        """Get all active sessions for user"""
        result = []
        with self._lock:
            for sid in self._user_sessions.get(user_codename, []):
                session = self._sessions.get(sid)
                if session and session.status == SessionStatus.ACTIVE:
                    result.append(session.to_dict())
        return result
    
    def get_stats(self) -> Dict[str, Any]:
        """Get session statistics"""
        with self._lock:
            total = len(self._sessions)
            active = sum(1 for s in self._sessions.values() if s.status == SessionStatus.ACTIVE)
            locked = sum(1 for s in self._sessions.values() if s.status == SessionStatus.LOCKED)
            suspicious = sum(1 for s in self._sessions.values() if s.status == SessionStatus.SUSPICIOUS)
            
            return {
                'total_sessions': total,
                'active_sessions': active,
                'locked_sessions': locked,
                'suspicious_sessions': suspicious,
                'unique_users': len(self._user_sessions)
            }


# Global session manager
_session_manager = None

def get_session_manager() -> SessionManager:
    """Get global session manager singleton"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager


class SessionLimitExceeded(Exception):
    """Raised when user exceeds concurrent session limit"""
    pass
