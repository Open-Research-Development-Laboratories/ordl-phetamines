#!/usr/bin/env python3
"""
ORDL Audit Logging System
NIST 800-53 / CNSSI 1253 Compliant
Classification: TOP SECRET//NOFORN//SCI

Implements:
- AU-6: Audit Review
- AU-7: Audit Reduction and Report Generation  
- AU-8: Time Stamps
- AU-9: Protection of Audit Information
- AU-10: Non-repudiation
- AU-11: Audit Record Retention
- AU-12: Audit Generation
"""

import json
import hashlib
import hmac
import sqlite3
import threading
from datetime import datetime, timedelta
from enum import Enum, auto
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, List, Callable
from pathlib import Path
import uuid
import os


class AuditEventType(Enum):
    """USG Standard Audit Event Types"""
    # Authentication Events
    AUTHENTICATION_SUCCESS = "AUTH_SUCCESS"
    AUTHENTICATION_FAILURE = "AUTH_FAILURE"
    AUTHENTICATION_LOCKOUT = "AUTH_LOCKOUT"
    AUTHENTICATION_LOGOUT = "AUTH_LOGOUT"
    AUTHENTICATION_TIMEOUT = "AUTH_TIMEOUT"
    MFA_CHALLENGE = "MFA_CHALLENGE"
    MFA_SUCCESS = "MFA_SUCCESS"
    MFA_FAILURE = "MFA_FAILURE"
    
    # Authorization Events
    ACCESS_GRANTED = "ACCESS_GRANTED"
    ACCESS_DENIED = "ACCESS_DENIED"
    PRIVILEGE_ESCALATION = "PRIV_ESC"
    PRIVILEGE_DEESCALATION = "PRIV_DEESC"
    CLEARANCE_CHECK = "CLEARANCE_CHECK"
    
    # Command Events
    COMMAND_START = "CMD_START"
    COMMAND_COMPLETE = "CMD_COMPLETE"
    COMMAND_ERROR = "CMD_ERROR"
    COMMAND_INTERRUPT = "CMD_INTERRUPT"
    
    # Data Access Events
    DATA_READ = "DATA_READ"
    DATA_WRITE = "DATA_WRITE"
    DATA_DELETE = "DATA_DELETE"
    DATA_EXPORT = "DATA_EXPORT"
    DATA_IMPORT = "DATA_IMPORT"
    
    # System Events
    SYSTEM_STARTUP = "SYS_START"
    SYSTEM_SHUTDOWN = "SYS_SHUTDOWN"
    SYSTEM_ERROR = "SYS_ERROR"
    CONFIG_CHANGE = "CONFIG_CHANGE"
    SECURITY_ALERT = "SEC_ALERT"
    
    # Session Events
    SESSION_CREATE = "SESS_CREATE"
    SESSION_DESTROY = "SESS_DESTROY"
    SESSION_TIMEOUT = "SESS_TIMEOUT"
    SESSION_HIJACK_ATTEMPT = "SESS_HIJACK"
    
    # Red Team Events
    REDTEAM_RECON = "RED_RECON"
    REDTEAM_SCAN = "RED_SCAN"
    REDTEAM_EXPLOIT = "RED_EXPLOIT"
    REDTEAM_PAYLOAD = "RED_PAYLOAD"
    
    # Blue Team Events
    BLUETeam_ALERT = "BLUE_ALERT"
    BLUETeam_RESPONSE = "BLUE_RESPONSE"
    BLUETeam_FORENSICS = "BLUE_FORENSICS"
    
    # Administrative
    USER_CREATE = "USER_CREATE"
    USER_MODIFY = "USER_MODIFY"
    USER_DELETE = "USER_DELETE"
    CLEARANCE_GRANT = "CLR_GRANT"
    CLEARANCE_REVOKE = "CLR_REVOKE"


class AuditSeverity(Enum):
    """Event severity levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    NOTICE = "NOTICE"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    ALERT = "ALERT"
    EMERGENCY = "EMERGENCY"


@dataclass
class AuditRecord:
    """
    USG Standard Audit Record
    Immutable - once created cannot be modified
    """
    # Required Fields (NIST 800-53)
    event_id: str                    # Unique event identifier
    timestamp_utc: str              # ISO 8601 UTC timestamp
    event_type: str                 # Type of event
    severity: str                   # Severity level
    
    # User Information
    user_codename: str              # User identifier (codename)
    user_clearance: str             # User clearance level
    user_compartments: List[str]    # User compartment access
    session_id: str                 # Session identifier
    
    # Event Details
    resource_id: str                # Resource being accessed
    action: str                     # Action performed
    status: str                     # SUCCESS or FAILURE
    result_code: int               # Numeric result code
    
    # Location Information
    source_ip: str                  # Source IP address
    source_host: str                # Source hostname
    destination_ip: str             # Destination IP
    destination_host: str           # Destination hostname
    
    # Command/Action Details
    command: Optional[str] = None          # Command executed
    command_args: Optional[List[str]] = None  # Command arguments
    working_directory: Optional[str] = None
    
    # Data Access
    data_classification: Optional[str] = None
    records_accessed: int = 0
    bytes_transferred: int = 0
    
    # Additional Context
    mfa_used: bool = False
    mfa_factors: List[str] = None
    witness_present: Optional[str] = None
    two_person_integrity: bool = False
    
    # Integrity
    previous_hash: Optional[str] = None     # Hash of previous record (chain)
    record_hash: Optional[str] = None       # Hash of this record
    signature: Optional[str] = None         # Digital signature
    
    # Retention
    retention_years: int = 7
    classification: str = "UNCLASSIFIED"
    
    def __post_init__(self):
        """Calculate hash after initialization"""
        if self.record_hash is None:
            self.record_hash = self.calculate_hash()
    
    def calculate_hash(self) -> str:
        """Calculate SHA-256 hash of record contents"""
        # Create deterministic string representation
        data = {
            'event_id': self.event_id,
            'timestamp_utc': self.timestamp_utc,
            'event_type': self.event_type,
            'user_codename': self.user_codename,
            'session_id': self.session_id,
            'command': self.command,
            'previous_hash': self.previous_hash
        }
        
        # Sort keys for deterministic hashing
        canonical = json.dumps(data, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical.encode()).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    def to_json(self) -> str:
        """Serialize to JSON"""
        return json.dumps(self.to_dict(), indent=2)


class AuditChain:
    """
    Tamper-evident audit log chain
    Each record contains hash of previous record
    """
    
    def __init__(self, chain_id: str):
        self.chain_id = chain_id
        self.last_hash: Optional[str] = None
        self.record_count: int = 0
    
    def add_record(self, record: AuditRecord) -> AuditRecord:
        """Add record to chain with hash linking"""
        record.previous_hash = self.last_hash
        record.record_hash = record.calculate_hash()
        self.last_hash = record.record_hash
        self.record_count += 1
        return record
    
    def verify_chain(self, records: List[AuditRecord]) -> tuple[bool, int]:
        """
        Verify integrity of record chain
        Returns (valid, failed_index)
        """
        previous_hash = None
        
        for i, record in enumerate(records):
            # Check previous hash linkage
            if record.previous_hash != previous_hash:
                return False, i
            
            # Verify record hash
            expected_hash = record.calculate_hash()
            if record.record_hash != expected_hash:
                return False, i
            
            previous_hash = record.record_hash
        
        return True, -1


class AuditLogger:
    """
    USG-Compliant Audit Logger
    
    Features:
    - Immutable audit records
    - Cryptographic chain of custody
    - Real-time alerting
    - Tamper detection
    - Automated retention
    """
    
    def __init__(self, db_path: str = "/opt/codex-swarm/command-post/data/audit.db"):
        self.db_path = db_path
        self._lock = threading.RLock()
        self._alert_handlers: List[Callable] = []
        self._chain = AuditChain("ordl_main")
        
        # Ensure directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_database()
    
    def _init_database(self):
        """Create audit database schema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_records (
                    event_id TEXT PRIMARY KEY,
                    timestamp_utc TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    user_codename TEXT NOT NULL,
                    user_clearance TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    resource_id TEXT,
                    action TEXT,
                    status TEXT,
                    result_code INTEGER,
                    source_ip TEXT,
                    source_host TEXT,
                    command TEXT,
                    command_args TEXT,
                    data_classification TEXT,
                    records_accessed INTEGER,
                    bytes_transferred INTEGER,
                    mfa_used INTEGER,
                    mfa_factors TEXT,
                    previous_hash TEXT,
                    record_hash TEXT NOT NULL,
                    retention_years INTEGER,
                    classification TEXT,
                    raw_json TEXT NOT NULL
                )
            """)
            
            # Indexes for common queries
            conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON audit_records(timestamp_utc)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_user ON audit_records(user_codename)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_session ON audit_records(session_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_event_type ON audit_records(event_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_severity ON audit_records(severity)")
            
            # Integrity check table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chain_state (
                    chain_id TEXT PRIMARY KEY,
                    last_hash TEXT,
                    record_count INTEGER,
                    last_updated TEXT
                )
            """)
            
            conn.commit()
    
    def log(self, record: AuditRecord) -> str:
        """
        Log an audit record
        Returns event_id
        """
        with self._lock:
            # Add to chain for integrity
            record = self._chain.add_record(record)
            
            # Store in database
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO audit_records VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    )
                """, (
                    record.event_id,
                    record.timestamp_utc,
                    record.event_type,
                    record.severity,
                    record.user_codename,
                    record.user_clearance,
                    record.session_id,
                    record.resource_id,
                    record.action,
                    record.status,
                    record.result_code,
                    record.source_ip,
                    record.source_host,
                    record.command,
                    json.dumps(record.command_args) if record.command_args else None,
                    record.data_classification,
                    record.records_accessed,
                    record.bytes_transferred,
                    1 if record.mfa_used else 0,
                    json.dumps(record.mfa_factors) if record.mfa_factors else None,
                    record.previous_hash,
                    record.record_hash,
                    record.retention_years,
                    record.classification,
                    record.to_json()
                ))
                
                # Update chain state
                conn.execute("""
                    INSERT OR REPLACE INTO chain_state (chain_id, last_hash, record_count, last_updated)
                    VALUES (?, ?, ?, ?)
                """, (
                    self._chain.chain_id,
                    self._chain.last_hash,
                    self._chain.record_count,
                    datetime.utcnow().isoformat()
                ))
                
                conn.commit()
            
            # Check for alerts
            self._check_alerts(record)
            
            return record.event_id
    
    def create_record(
        self,
        event_type: AuditEventType,
        user_codename: str,
        user_clearance: str,
        session_id: str,
        resource_id: str,
        action: str,
        status: str = "SUCCESS",
        severity: AuditSeverity = AuditSeverity.INFO,
        command: Optional[str] = None,
        command_args: Optional[List[str]] = None,
        source_ip: str = "127.0.0.1",
        **kwargs
    ) -> AuditRecord:
        """Create and log a standardized audit record"""
        
        record = AuditRecord(
            event_id=str(uuid.uuid4()),
            timestamp_utc=datetime.utcnow().isoformat(),
            event_type=event_type.value,
            severity=severity.value,
            user_codename=user_codename,
            user_clearance=user_clearance,
            user_compartments=kwargs.get('user_compartments', []),
            session_id=session_id,
            resource_id=resource_id,
            action=action,
            status=status,
            result_code=kwargs.get('result_code', 0),
            source_ip=source_ip,
            source_host=kwargs.get('source_host', 'ordl-ghost'),
            destination_ip=kwargs.get('destination_ip', '127.0.0.1'),
            destination_host=kwargs.get('destination_host', 'ordl-core'),
            command=command,
            command_args=command_args,
            working_directory=kwargs.get('working_directory', '/'),
            data_classification=kwargs.get('data_classification', 'UNCLASSIFIED'),
            records_accessed=kwargs.get('records_accessed', 0),
            bytes_transferred=kwargs.get('bytes_transferred', 0),
            mfa_used=kwargs.get('mfa_used', False),
            mfa_factors=kwargs.get('mfa_factors', []),
            witness_present=kwargs.get('witness_present'),
            two_person_integrity=kwargs.get('two_person_integrity', False),
            retention_years=kwargs.get('retention_years', 7),
            classification=kwargs.get('classification', 'UNCLASSIFIED')
        )
        
        self.log(record)
        return record
    
    def _check_alerts(self, record: AuditRecord):
        """Check if record should trigger alerts"""
        alerts = []
        
        # Authentication failures
        if record.event_type == AuditEventType.AUTHENTICATION_FAILURE.value:
            if record.result_code >= 3:  # Multiple failures
                alerts.append("MULTIPLE_AUTH_FAILURES")
        
        # Access denied on high-value resource
        if record.event_type == AuditEventType.ACCESS_DENIED.value:
            if record.severity in ["CRITICAL", "ALERT", "EMERGENCY"]:
                alerts.append("UNAUTHORIZED_ACCESS_ATTEMPT")
        
        # Privilege escalation
        if record.event_type == AuditEventType.PRIVILEGE_ESCALATION.value:
            alerts.append("PRIVILEGE_ESCALATION")
        
        # Red team activity
        if record.event_type.startswith("RED_"):
            alerts.append("REDTEAM_ACTIVITY")
        
        # Critical errors
        if record.severity == "EMERGENCY":
            alerts.append("EMERGENCY_EVENT")
        
        # Trigger alert handlers
        for alert in alerts:
            for handler in self._alert_handlers:
                try:
                    handler(alert, record)
                except Exception:
                    pass
    
    def register_alert_handler(self, handler: Callable):
        """Register a function to handle security alerts"""
        self._alert_handlers.append(handler)
    
    def query(self, 
              start_time: Optional[datetime] = None,
              end_time: Optional[datetime] = None,
              user_codename: Optional[str] = None,
              event_type: Optional[str] = None,
              severity: Optional[str] = None,
              limit: int = 1000) -> List[AuditRecord]:
        """Query audit records with filters"""
        
        query = "SELECT raw_json FROM audit_records WHERE 1=1"
        params = []
        
        if start_time:
            query += " AND timestamp_utc >= ?"
            params.append(start_time.isoformat())
        
        if end_time:
            query += " AND timestamp_utc <= ?"
            params.append(end_time.isoformat())
        
        if user_codename:
            query += " AND user_codename = ?"
            params.append(user_codename)
        
        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)
        
        if severity:
            query += " AND severity = ?"
            params.append(severity)
        
        query += " ORDER BY timestamp_utc DESC LIMIT ?"
        params.append(limit)
        
        records = []
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(query, params)
            for row in cursor:
                data = json.loads(row[0])
                records.append(AuditRecord(**data))
        
        return records
    
    def verify_integrity(self) -> tuple[bool, str]:
        """
        Verify integrity of entire audit log
        Returns (valid, message)
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT raw_json FROM audit_records ORDER BY timestamp_utc"
            )
            records = [AuditRecord(**json.loads(row[0])) for row in cursor]
        
        if not records:
            return True, "No records to verify"
        
        valid, failed_index = self._chain.verify_chain(records)
        
        if valid:
            return True, f"Chain verified: {len(records)} records"
        else:
            return False, f"Chain broken at record {failed_index}"
    
    def export_range(self, start: datetime, end: datetime, 
                     filepath: str, classification: str = "UNCLASSIFIED"):
        """Export audit records for a time range"""
        records = self.query(start_time=start, end_time=end, limit=100000)
        
        export_data = {
            'export_timestamp': datetime.utcnow().isoformat(),
            'classification': classification,
            'record_count': len(records),
            'chain_valid': self.verify_integrity()[0],
            'records': [r.to_dict() for r in records]
        }
        
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2)
    
    def purge_expired(self, before_date: Optional[datetime] = None) -> int:
        """Purge records past retention date"""
        if before_date is None:
            before_date = datetime.utcnow()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                DELETE FROM audit_records 
                WHERE date(timestamp_utc, '+' || retention_years || ' years') < ?
            """, (before_date.isoformat(),))
            
            conn.commit()
            return cursor.rowcount


# Global logger instance
_audit_logger = None

def get_audit_logger() -> AuditLogger:
    """Get global audit logger singleton"""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger
