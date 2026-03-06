#!/usr/bin/env python3
"""
================================================================================
ORDL COMMAND POST v6.0.0 - BLUE TEAM SECURITY MODULE
================================================================================
Classification: TOP SECRET//SCI//NOFORN
Classification Level: TS/SCI/NOFORN
Compartment: ORDL-CYBER-OPS

MILITARY-GRADE DEFENSIVE SECURITY OPERATIONS CENTER (SOC) CAPABILITIES
================================================================================
This module provides comprehensive Blue Team defensive capabilities including:
- Real-time log ingestion and analysis
- SIEM functionality with rule-based detection
- Incident response case management
- Digital forensics and evidence handling
- Threat intelligence with IOC management
- MITRE ATT&CK framework integration
- Automated response playbooks

Author: ORDL Cyber Operations Division
Version: 6.0.0
================================================================================
"""

import os
import sys
import json
import uuid
import time
import hashlib
import sqlite3
import threading
import logging
from datetime import datetime, timedelta
from enum import Enum, auto
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Callable, Tuple, Set
from collections import defaultdict
import re
import ipaddress

# Configure logging
log_file = '/var/log/ordl/blueteam.log'
try:
    os.makedirs('/var/log/ordl', exist_ok=True)
except:
    log_file = '/tmp/ordl_blueteam.log'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_file, mode='a')
    ]
)
logger = logging.getLogger('blueteam')

class AlertSeverity(Enum):
    """Alert severity levels with military classification"""
    CRITICAL = "CRITICAL"      # Immediate response required
    HIGH = "HIGH"              # Urgent response within 1 hour
    MEDIUM = "MEDIUM"          # Response within 4 hours
    LOW = "LOW"                # Response within 24 hours
    INFO = "INFO"              # Informational only

class IncidentStatus(Enum):
    """Incident case status workflow"""
    NEW = "NEW"
    ASSIGNED = "ASSIGNED"
    INVESTIGATING = "INVESTIGATING"
    CONTAINED = "CONTAINED"
    ERADICATED = "ERADICATED"
    RECOVERED = "RECOVERED"
    CLOSED = "CLOSED"

class IOCType(Enum):
    """Types of Indicators of Compromise"""
    IP = "ip"
    DOMAIN = "domain"
    URL = "url"
    HASH_MD5 = "hash_md5"
    HASH_SHA1 = "hash_sha1"
    HASH_SHA256 = "hash_sha256"
    FILE_NAME = "file_name"
    REGISTRY_KEY = "registry_key"
    MUTEX = "mutex"
    YARA_RULE = "yara_rule"
    SIGNATURE = "signature"

class LogSource(Enum):
    """Supported log source types"""
    SYSLOG = "syslog"
    WINDOWS = "windows"
    LINUX_AUTH = "linux_auth"
    APACHE = "apache"
    NGINX = "nginx"
    FIREWALL = "firewall"
    IDS = "ids"
    EDR = "edr"
    CLOUD_TRAIL = "cloud_trail"
    CUSTOM = "custom"

@dataclass
class Alert:
    """Security alert with full forensic context"""
    alert_id: str
    timestamp: datetime
    severity: AlertSeverity
    title: str
    description: str
    source: str
    rule_name: str
    rule_id: str
    raw_data: Dict[str, Any]
    ioc_matches: List[Dict[str, Any]] = field(default_factory=list)
    related_events: List[str] = field(default_factory=list)
    status: str = "OPEN"
    assigned_to: Optional[str] = None
    incident_id: Optional[str] = None
    mitre_techniques: List[str] = field(default_factory=list)
    cvss_score: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "timestamp": self.timestamp.isoformat(),
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
            "source": self.source,
            "rule_name": self.rule_name,
            "rule_id": self.rule_id,
            "raw_data": self.raw_data,
            "ioc_matches": self.ioc_matches,
            "related_events": self.related_events,
            "status": self.status,
            "assigned_to": self.assigned_to,
            "incident_id": self.incident_id,
            "mitre_techniques": self.mitre_techniques,
            "cvss_score": self.cvss_score
        }

@dataclass
class Incident:
    """Incident case with full lifecycle management"""
    incident_id: str
    created_at: datetime
    updated_at: datetime
    title: str
    description: str
    severity: AlertSeverity
    status: IncidentStatus
    lead_analyst: Optional[str] = None
    assigned_team: List[str] = field(default_factory=list)
    related_alerts: List[str] = field(default_factory=list)
    affected_assets: List[str] = field(default_factory=list)
    timeline: List[Dict[str, Any]] = field(default_factory=list)
    evidence_refs: List[str] = field(default_factory=list)
    containment_actions: List[Dict[str, Any]] = field(default_factory=list)
    root_cause: Optional[str] = None
    lessons_learned: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "incident_id": self.incident_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "title": self.title,
            "description": self.description,
            "severity": self.severity.value,
            "status": self.status.value,
            "lead_analyst": self.lead_analyst,
            "assigned_team": self.assigned_team,
            "related_alerts": self.related_alerts,
            "affected_assets": self.affected_assets,
            "timeline": self.timeline,
            "evidence_refs": self.evidence_refs,
            "containment_actions": self.containment_actions,
            "root_cause": self.root_cause,
            "lessons_learned": self.lessons_learned
        }

@dataclass
class IOC:
    """Indicator of Compromise with attribution"""
    ioc_id: str
    ioc_type: IOCType
    value: str
    added_at: datetime
    source: str
    confidence: int  # 0-100
    severity: AlertSeverity
    description: str
    threat_actor: Optional[str] = None
    campaign: Optional[str] = None
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    hit_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "ioc_id": self.ioc_id,
            "ioc_type": self.ioc_type.value,
            "value": self.value,
            "added_at": self.added_at.isoformat(),
            "source": self.source,
            "confidence": self.confidence,
            "severity": self.severity.value,
            "description": self.description,
            "threat_actor": self.threat_actor,
            "campaign": self.campaign,
            "first_seen": self.first_seen.isoformat() if self.first_seen else None,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "hit_count": self.hit_count
        }

@dataclass
class LogEntry:
    """Normalized log entry"""
    entry_id: str
    timestamp: datetime
    source_type: LogSource
    source_host: str
    raw_message: str
    normalized: Dict[str, Any]
    parsed_fields: Dict[str, Any]
    tags: List[str] = field(default_factory=list)
    alert_triggered: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "timestamp": self.timestamp.isoformat(),
            "source_type": self.source_type.value,
            "source_host": self.source_host,
            "raw_message": self.raw_message,
            "normalized": self.normalized,
            "parsed_fields": self.parsed_fields,
            "tags": self.tags,
            "alert_triggered": self.alert_triggered
        }

class DetectionRule:
    """Detection rule with Sigma-like functionality"""
    
    def __init__(self, 
                 rule_id: str,
                 name: str,
                 description: str,
                 severity: AlertSeverity,
                 source_types: List[LogSource],
                 conditions: Dict[str, Any],
                 mitre_techniques: List[str] = None,
                 enabled: bool = True):
        self.rule_id = rule_id
        self.name = name
        self.description = description
        self.severity = severity
        self.source_types = source_types
        self.conditions = conditions
        self.mitre_techniques = mitre_techniques or []
        self.enabled = enabled
        self.created_at = datetime.utcnow()
        self.hit_count = 0
        self.last_hit = None
    
    def matches(self, log_entry: LogEntry) -> bool:
        """Check if log entry matches this rule"""
        if not self.enabled:
            return False
        
        if log_entry.source_type not in self.source_types:
            return False
        
        # Check conditions
        for field, pattern in self.conditions.items():
            value = log_entry.parsed_fields.get(field) or log_entry.normalized.get(field)
            if value is None:
                return False
            
            if isinstance(pattern, str):
                # String match or regex
                if pattern.startswith('/') and pattern.endswith('/'):
                    if not re.search(pattern[1:-1], str(value), re.IGNORECASE):
                        return False
                elif pattern.lower() not in str(value).lower():
                    return False
            elif isinstance(pattern, list):
                if str(value).lower() not in [p.lower() for p in pattern]:
                    return False
            elif isinstance(pattern, dict):
                # Range or comparison
                if 'min' in pattern and float(value) < pattern['min']:
                    return False
                if 'max' in pattern and float(value) > pattern['max']:
                    return False
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "description": self.description,
            "severity": self.severity.value,
            "source_types": [s.value for s in self.source_types],
            "conditions": self.conditions,
            "mitre_techniques": self.mitre_techniques,
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat(),
            "hit_count": self.hit_count,
            "last_hit": self.last_hit.isoformat() if self.last_hit else None
        }

class BlueTeamManager:
    """
    Military-Grade Blue Team Operations Manager
    
    Provides comprehensive defensive security capabilities:
    - Real-time SIEM functionality
    - Incident response management
    - Threat intelligence correlation
    - Forensic evidence handling
    - Automated response playbooks
    """
    
    def __init__(self, db_path: str = "/opt/codex-swarm/command-post/blueteam/blueteam.db"):
        self.db_path = db_path
        self._lock = threading.RLock()
        self._running = False
        self._alert_handlers: List[Callable[[Alert], None]] = []
        self._detection_rules: Dict[str, DetectionRule] = {}
        self._iocs: Dict[str, IOC] = {}
        self._incidents: Dict[str, Incident] = {}
        self._active_alerts: Dict[str, Alert] = {}
        self._mitre_mapping: Dict[str, Dict[str, Any]] = {}
        self._stats = {
            "logs_ingested": 0,
            "alerts_generated": 0,
            "incidents_created": 0,
            "iocs_matched": 0,
            "last_reset": datetime.utcnow().isoformat()
        }
        
        # Ensure log directory exists
        os.makedirs(os.path.dirname('/var/log/ordl/blueteam.log') or '.', exist_ok=True)
        
        self._init_database()
        self._load_builtin_rules()
        self._load_mitre_attck()
    
    def _init_database(self):
        """Initialize Blue Team database with full forensic schema"""
        os.makedirs(os.path.dirname(self.db_path) or '.', exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            
            # Log entries table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS log_entries (
                    entry_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    source_host TEXT NOT NULL,
                    raw_message TEXT,
                    normalized TEXT,
                    parsed_fields TEXT,
                    tags TEXT,
                    alert_triggered INTEGER DEFAULT 0
                )
            """)
            
            # Alerts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    alert_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    source TEXT NOT NULL,
                    rule_name TEXT,
                    rule_id TEXT,
                    raw_data TEXT,
                    ioc_matches TEXT,
                    related_events TEXT,
                    status TEXT DEFAULT 'OPEN',
                    assigned_to TEXT,
                    incident_id TEXT,
                    mitre_techniques TEXT,
                    cvss_score REAL
                )
            """)
            
            # Incidents table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS incidents (
                    incident_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    severity TEXT NOT NULL,
                    status TEXT NOT NULL,
                    lead_analyst TEXT,
                    assigned_team TEXT,
                    related_alerts TEXT,
                    affected_assets TEXT,
                    timeline TEXT,
                    evidence_refs TEXT,
                    containment_actions TEXT,
                    root_cause TEXT,
                    lessons_learned TEXT
                )
            """)
            
            # IOCs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS iocs (
                    ioc_id TEXT PRIMARY KEY,
                    ioc_type TEXT NOT NULL,
                    value TEXT NOT NULL UNIQUE,
                    added_at TEXT NOT NULL,
                    source TEXT,
                    confidence INTEGER,
                    severity TEXT,
                    description TEXT,
                    threat_actor TEXT,
                    campaign TEXT,
                    first_seen TEXT,
                    last_seen TEXT,
                    hit_count INTEGER DEFAULT 0
                )
            """)
            
            # Detection rules table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS detection_rules (
                    rule_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    severity TEXT,
                    source_types TEXT,
                    conditions TEXT,
                    mitre_techniques TEXT,
                    enabled INTEGER DEFAULT 1,
                    created_at TEXT,
                    hit_count INTEGER DEFAULT 0,
                    last_hit TEXT
                )
            """)
            
            # Create indexes for performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_time ON log_entries(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_source ON log_entries(source_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_host ON log_entries(source_host)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_incident ON alerts(incident_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_iocs_type ON iocs(ioc_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_iocs_value ON iocs(value)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents(status)")
            
            conn.commit()
        finally:
            conn.close()
        
        logger.info(f"[BLUE TEAM] Database initialized: {self.db_path}")
    
    def _load_builtin_rules(self):
        """Load military-grade detection rules"""
        builtin_rules = [
            # Authentication anomalies
            DetectionRule(
                rule_id="BT-AUTH-001",
                name="Multiple Failed Logins",
                description="Detects brute force authentication attempts",
                severity=AlertSeverity.HIGH,
                source_types=[LogSource.LINUX_AUTH, LogSource.WINDOWS],
                conditions={
                    "event_type": "authentication",
                    "status": "failure"
                },
                mitre_techniques=["T1110", "T1110.001"]
            ),
            DetectionRule(
                rule_id="BT-PRIV-001",
                name="Privilege Escalation Detected",
                description="User gained elevated privileges",
                severity=AlertSeverity.CRITICAL,
                source_types=[LogSource.LINUX_AUTH, LogSource.WINDOWS, LogSource.EDR],
                conditions={
                    "event_type": "privilege_escalation"
                },
                mitre_techniques=["T1068", "T1548", "T1548.001"]
            ),
            # Network anomalies
            DetectionRule(
                rule_id="BT-NET-001",
                name="Suspicious Outbound Connection",
                description="Connection to suspicious external IP",
                severity=AlertSeverity.HIGH,
                source_types=[LogSource.FIREWALL, LogSource.EDR],
                conditions={
                    "direction": "outbound",
                    "action": "allowed"
                },
                mitre_techniques=["T1041", "T1048", "T1071"]
            ),
            DetectionRule(
                rule_id="BT-NET-002",
                name="Port Scan Detected",
                description="Multiple ports accessed rapidly",
                severity=AlertSeverity.MEDIUM,
                source_types=[LogSource.FIREWALL, LogSource.IDS],
                conditions={
                    "event_type": "port_scan"
                },
                mitre_techniques=["T1046"]
            ),
            # Malware indicators
            DetectionRule(
                rule_id="BT-MAL-001",
                name="Suspicious Process Execution",
                description="Process executed from suspicious location",
                severity=AlertSeverity.HIGH,
                source_types=[LogSource.EDR, LogSource.WINDOWS],
                conditions={
                    "event_type": "process_creation",
                    "image_path": "/tmp/|/var/tmp/|C:\\Users\\.*\\AppData\\Local\\Temp"
                },
                mitre_techniques=["T1059", "T1204", "T1204.002"]
            ),
            DetectionRule(
                rule_id="BT-MAL-002",
                name="Encoded PowerShell Command",
                description="PowerShell with encoded command detected",
                severity=AlertSeverity.CRITICAL,
                source_types=[LogSource.WINDOWS, LogSource.EDR],
                conditions={
                    "command_line": "-enc |-encodedcommand"
                },
                mitre_techniques=["T1059.001", "T1027", "T1027.001"]
            ),
            # Lateral movement
            DetectionRule(
                rule_id="BT-LAT-001",
                name="Suspicious RDP Connection",
                description="RDP from unusual source",
                severity=AlertSeverity.HIGH,
                source_types=[LogSource.WINDOWS, LogSource.FIREWALL],
                conditions={
                    "event_type": "rdp_connection"
                },
                mitre_techniques=["T1021.001"]
            ),
            DetectionRule(
                rule_id="BT-LAT-002",
                name="SMB Lateral Movement",
                description="SMB connection pattern indicating lateral movement",
                severity=AlertSeverity.HIGH,
                source_types=[LogSource.WINDOWS, LogSource.FIREWALL],
                conditions={
                    "event_type": "smb_connection",
                    "share": "\\\\.*\\ADMIN\\$|\\\\.*\\C\\$|\\\\.*\\IPC\\$"
                },
                mitre_techniques=["T1021.002", "T1570"]
            ),
            # Data exfiltration
            DetectionRule(
                rule_id="BT-EXF-001",
                name="Large Data Transfer",
                description="Unusually large outbound data transfer",
                severity=AlertSeverity.HIGH,
                source_types=[LogSource.FIREWALL, LogSource.EDR],
                conditions={
                    "event_type": "data_transfer",
                    "bytes_out": {"min": 100000000}  # 100MB
                },
                mitre_techniques=["T1041", "T1048"]
            ),
            DetectionRule(
                rule_id="BT-EXF-002",
                name="Clipboard Access",
                description="Suspicious clipboard data access",
                severity=AlertSeverity.MEDIUM,
                source_types=[LogSource.EDR],
                conditions={
                    "event_type": "clipboard_access"
                },
                mitre_techniques=["T1115"]
            ),
            # Persistence
            DetectionRule(
                rule_id="BT-PER-001",
                name="New Scheduled Task",
                description="Suspicious scheduled task creation",
                severity=AlertSeverity.MEDIUM,
                source_types=[LogSource.WINDOWS, LogSource.EDR],
                conditions={
                    "event_type": "scheduled_task_created"
                },
                mitre_techniques=["T1053", "T1053.005"]
            ),
            DetectionRule(
                rule_id="BT-PER-002",
                name="Registry Run Key Modified",
                description="Persistence via registry run key",
                severity=AlertSeverity.HIGH,
                source_types=[LogSource.WINDOWS, LogSource.EDR],
                conditions={
                    "event_type": "registry_modified",
                    "key": "run|runonce"
                },
                mitre_techniques=["T1547", "T1547.001"]
            ),
            # Defense evasion
            DetectionRule(
                rule_id="BT-DEF-001",
                name="Service Stop",
                description="Security service stopped",
                severity=AlertSeverity.CRITICAL,
                source_types=[LogSource.WINDOWS, LogSource.LINUX_AUTH],
                conditions={
                    "event_type": "service_stopped",
                    "service_name": "sysmon|windefend|wdnisdrv|wdfilter|mpssvc|iptables|fail2ban|selinux"
                },
                mitre_techniques=["T1562", "T1562.001"]
            ),
            DetectionRule(
                rule_id="BT-DEF-002",
                name="Log Cleared",
                description="Security log cleared",
                severity=AlertSeverity.CRITICAL,
                source_types=[LogSource.WINDOWS, LogSource.LINUX_AUTH],
                conditions={
                    "event_type": "log_cleared"
                },
                mitre_techniques=["T1070", "T1070.001"]
            ),
            # Web attacks
            DetectionRule(
                rule_id="BT-WEB-001",
                name="SQL Injection Attempt",
                description="SQL injection pattern in web request",
                severity=AlertSeverity.HIGH,
                source_types=[LogSource.APACHE, LogSource.NGINX],
                conditions={
                    "request_uri": "union.*select|select.*from|insert.*into|delete.*from|drop.*table|exec\\(|eval\\("
                },
                mitre_techniques=["T1190"]
            ),
            DetectionRule(
                rule_id="BT-WEB-002",
                name="Directory Traversal",
                description="Path traversal attempt detected",
                severity=AlertSeverity.MEDIUM,
                source_types=[LogSource.APACHE, LogSource.NGINX],
                conditions={
                    "request_uri": "\\.\\./|\\.%2e%2e/|\\.%252e/|etc/passwd|win\\.ini|boot\\.ini"
                },
                mitre_techniques=["T1083", "T1083.001"]
            ),
            DetectionRule(
                rule_id="BT-WEB-003",
                name="XSS Attempt",
                description="Cross-site scripting pattern detected",
                severity=AlertSeverity.MEDIUM,
                source_types=[LogSource.APACHE, LogSource.NGINX],
                conditions={
                    "request_uri": "<script|javascript:|onerror=|onload=|alert\\(|prompt\\(|confirm\\("
                },
                mitre_techniques=["T1189"]
            ),
        ]
        
        for rule in builtin_rules:
            self._detection_rules[rule.rule_id] = rule
        
        logger.info(f"[BLUE TEAM] Loaded {len(builtin_rules)} built-in detection rules")
    
    def _load_mitre_attck(self):
        """Load MITRE ATT&CK framework mapping"""
        # Core techniques relevant to our detection rules
        self._mitre_mapping = {
            "T1110": {
                "name": "Brute Force",
                "tactic": "Credential Access",
                "url": "https://attack.mitre.org/techniques/T1110/"
            },
            "T1110.001": {
                "name": "Brute Force: Password Guessing",
                "tactic": "Credential Access",
                "url": "https://attack.mitre.org/techniques/T1110/001/"
            },
            "T1068": {
                "name": "Exploitation for Privilege Escalation",
                "tactic": "Privilege Escalation",
                "url": "https://attack.mitre.org/techniques/T1068/"
            },
            "T1548": {
                "name": "Abuse Elevation Control Mechanism",
                "tactic": "Privilege Escalation",
                "url": "https://attack.mitre.org/techniques/T1548/"
            },
            "T1041": {
                "name": "Exfiltration Over C2 Channel",
                "tactic": "Exfiltration",
                "url": "https://attack.mitre.org/techniques/T1041/"
            },
            "T1048": {
                "name": "Exfiltration Over Alternative Protocol",
                "tactic": "Exfiltration",
                "url": "https://attack.mitre.org/techniques/T1048/"
            },
            "T1071": {
                "name": "Application Layer Protocol",
                "tactic": "Command and Control",
                "url": "https://attack.mitre.org/techniques/T1071/"
            },
            "T1046": {
                "name": "Network Service Scanning",
                "tactic": "Discovery",
                "url": "https://attack.mitre.org/techniques/T1046/"
            },
            "T1059": {
                "name": "Command and Scripting Interpreter",
                "tactic": "Execution",
                "url": "https://attack.mitre.org/techniques/T1059/"
            },
            "T1059.001": {
                "name": "PowerShell",
                "tactic": "Execution",
                "url": "https://attack.mitre.org/techniques/T1059/001/"
            },
            "T1204": {
                "name": "User Execution",
                "tactic": "Execution",
                "url": "https://attack.mitre.org/techniques/T1204/"
            },
            "T1204.002": {
                "name": "Malicious File",
                "tactic": "Execution",
                "url": "https://attack.mitre.org/techniques/T1204/002/"
            },
            "T1021.001": {
                "name": "Remote Desktop Protocol",
                "tactic": "Lateral Movement",
                "url": "https://attack.mitre.org/techniques/T1021/001/"
            },
            "T1021.002": {
                "name": "SMB/Windows Admin Shares",
                "tactic": "Lateral Movement",
                "url": "https://attack.mitre.org/techniques/T1021/002/"
            },
            "T1570": {
                "name": "Lateral Tool Transfer",
                "tactic": "Lateral Movement",
                "url": "https://attack.mitre.org/techniques/T1570/"
            },
            "T1027": {
                "name": "Obfuscated Files or Information",
                "tactic": "Defense Evasion",
                "url": "https://attack.mitre.org/techniques/T1027/"
            },
            "T1027.001": {
                "name": "Binary Padding",
                "tactic": "Defense Evasion",
                "url": "https://attack.mitre.org/techniques/T1027/001/"
            },
            "T1115": {
                "name": "Clipboard Data",
                "tactic": "Collection",
                "url": "https://attack.mitre.org/techniques/T1115/"
            },
            "T1053": {
                "name": "Scheduled Task/Job",
                "tactic": "Execution",
                "url": "https://attack.mitre.org/techniques/T1053/"
            },
            "T1053.005": {
                "name": "Scheduled Task",
                "tactic": "Execution",
                "url": "https://attack.mitre.org/techniques/T1053/005/"
            },
            "T1547": {
                "name": "Boot or Logon Autostart Execution",
                "tactic": "Persistence",
                "url": "https://attack.mitre.org/techniques/T1547/"
            },
            "T1547.001": {
                "name": "Registry Run Keys",
                "tactic": "Persistence",
                "url": "https://attack.mitre.org/techniques/T1547/001/"
            },
            "T1562": {
                "name": "Impair Defenses",
                "tactic": "Defense Evasion",
                "url": "https://attack.mitre.org/techniques/T1562/"
            },
            "T1562.001": {
                "name": "Disable or Modify Tools",
                "tactic": "Defense Evasion",
                "url": "https://attack.mitre.org/techniques/T1562/001/"
            },
            "T1070": {
                "name": "Indicator Removal",
                "tactic": "Defense Evasion",
                "url": "https://attack.mitre.org/techniques/T1070/"
            },
            "T1070.001": {
                "name": "Clear Windows Event Logs",
                "tactic": "Defense Evasion",
                "url": "https://attack.mitre.org/techniques/T1070/001/"
            },
            "T1190": {
                "name": "Exploit Public-Facing Application",
                "tactic": "Initial Access",
                "url": "https://attack.mitre.org/techniques/T1190/"
            },
            "T1189": {
                "name": "Drive-by Compromise",
                "tactic": "Initial Access",
                "url": "https://attack.mitre.org/techniques/T1189/"
            },
            "T1083": {
                "name": "File and Directory Discovery",
                "tactic": "Discovery",
                "url": "https://attack.mitre.org/techniques/T1083/"
            },
        }
        
        logger.info(f"[BLUE TEAM] Loaded {len(self._mitre_mapping)} MITRE ATT&CK techniques")
    
    # ==================== IOC MANAGEMENT ====================
    
    def add_ioc(self, 
                ioc_type: IOCType,
                value: str,
                source: str,
                confidence: int,
                severity: AlertSeverity,
                description: str,
                threat_actor: Optional[str] = None,
                campaign: Optional[str] = None) -> IOC:
        """Add new Indicator of Compromise"""
        with self._lock:
            ioc_id = f"IOC-{uuid.uuid4().hex[:8].upper()}"
            ioc = IOC(
                ioc_id=ioc_id,
                ioc_type=ioc_type,
                value=value,
                added_at=datetime.utcnow(),
                source=source,
                confidence=confidence,
                severity=severity,
                description=description,
                threat_actor=threat_actor,
                campaign=campaign,
                first_seen=datetime.utcnow(),
                last_seen=None,
                hit_count=0
            )
            
            self._iocs[ioc_id] = ioc
            
            # Persist to database
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO iocs 
                    (ioc_id, ioc_type, value, added_at, source, confidence, severity,
                     description, threat_actor, campaign, first_seen, hit_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    ioc_id, ioc_type.value, value, ioc.added_at.isoformat(),
                    source, confidence, severity.value, description,
                    threat_actor, campaign, ioc.first_seen.isoformat(), 0
                ))
                conn.commit()
            
            logger.info(f"[BLUE TEAM] IOC added: {ioc_id} ({ioc_type.value}: {value})")
            return ioc
    
    def check_ioc(self, value: str) -> Optional[IOC]:
        """Check if value matches any IOC"""
        with self._lock:
            for ioc in self._iocs.values():
                if ioc.value == value:
                    # Update hit count
                    ioc.hit_count += 1
                    ioc.last_seen = datetime.utcnow()
                    
                    # Update database
                    with sqlite3.connect(self.db_path) as conn:
                        conn.execute(
                            "UPDATE iocs SET hit_count = ?, last_seen = ? WHERE ioc_id = ?",
                            (ioc.hit_count, ioc.last_seen.isoformat(), ioc.ioc_id)
                        )
                        conn.commit()
                    
                    self._stats["iocs_matched"] += 1
                    return ioc
            return None
    
    def get_iocs(self, 
                 ioc_type: Optional[IOCType] = None,
                 threat_actor: Optional[str] = None) -> List[IOC]:
        """Get IOCs with optional filtering"""
        with self._lock:
            results = list(self._iocs.values())
            
            if ioc_type:
                results = [i for i in results if i.ioc_type == ioc_type]
            if threat_actor:
                results = [i for i in results if i.threat_actor == threat_actor]
            
            return results
    
    def delete_ioc(self, ioc_id: str) -> bool:
        """Delete an IOC"""
        with self._lock:
            if ioc_id in self._iocs:
                del self._iocs[ioc_id]
                
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("DELETE FROM iocs WHERE ioc_id = ?", (ioc_id,))
                    conn.commit()
                
                logger.info(f"[BLUE TEAM] IOC deleted: {ioc_id}")
                return True
            return False
    
    # ==================== LOG INGESTION & ANALYSIS ====================
    
    def ingest_log(self,
                   source_type: LogSource,
                   source_host: str,
                   raw_message: str,
                   timestamp: Optional[datetime] = None,
                   parsed_fields: Optional[Dict[str, Any]] = None) -> LogEntry:
        """Ingest and analyze a log entry"""
        entry_id = f"LOG-{uuid.uuid4().hex[:12].upper()}"
        
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        # Normalize the log
        normalized = self._normalize_log(source_type, raw_message, parsed_fields or {})
        
        entry = LogEntry(
            entry_id=entry_id,
            timestamp=timestamp,
            source_type=source_type,
            source_host=source_host,
            raw_message=raw_message,
            normalized=normalized,
            parsed_fields=parsed_fields or {}
        )
        
        # Check against IOCs
        ioc_matches = self._check_iocs_in_log(entry)
        if ioc_matches:
            entry.tags.append("ioc_match")
        
        # Run detection rules
        alerts = self._run_detection(entry)
        
        # Store in database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO log_entries 
                (entry_id, timestamp, source_type, source_host, raw_message,
                 normalized, parsed_fields, tags, alert_triggered)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entry_id, timestamp.isoformat(), source_type.value, source_host,
                raw_message, json.dumps(normalized), json.dumps(parsed_fields or {}),
                json.dumps(entry.tags), 1 if alerts else 0
            ))
            conn.commit()
        
        self._stats["logs_ingested"] += 1
        
        return entry
    
    def _normalize_log(self,
                       source_type: LogSource,
                       raw_message: str,
                       parsed_fields: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize log to common schema"""
        normalized = {
            "@timestamp": datetime.utcnow().isoformat(),
            "source_type": source_type.value,
            "event": {}
        }
        
        # Extract common fields
        if source_type == LogSource.SYSLOG:
            # Parse syslog format
            match = re.match(
                r'<\d+>(\w+\s+\d+\s+\d+:\d+:\d+)\s+(\S+)\s+(.*)',
                raw_message
            )
            if match:
                normalized["@timestamp"] = match.group(1)
                normalized["host"] = {"name": match.group(2)}
                normalized["message"] = match.group(3)
        
        elif source_type == LogSource.APACHE:
            # Parse Apache access log
            match = re.match(
                r'(\S+)\s+-\s+(\S+)\s+\[(.*?)\]\s+"(.*?)"\s+(\d+)\s+(\S+)',
                raw_message
            )
            if match:
                normalized["source"], = {"ip": match.group(1)}
                normalized["user"] = match.group(2)
                normalized["http"] = {
                    "request": {
                        "method": match.group(4).split()[0] if match.group(4) else "",
                        "uri": match.group(4).split()[1] if len(match.group(4).split()) > 1 else ""
                    },
                    "response": {"status_code": int(match.group(5))}
                }
        
        elif source_type == LogSource.WINDOWS:
            # Parse Windows event log (simplified)
            normalized["event"] = parsed_fields
        
        else:
            # Generic normalization
            normalized["event"] = parsed_fields
        
        return normalized
    
    def _check_iocs_in_log(self, entry: LogEntry) -> List[Dict[str, Any]]:
        """Check log entry against IOC database"""
        matches = []
        
        # Extract values to check
        values_to_check = []
        
        # Check common fields
        if "ip" in entry.parsed_fields:
            values_to_check.append(("ip", entry.parsed_fields["ip"]))
        if "domain" in entry.parsed_fields:
            values_to_check.append(("domain", entry.parsed_fields["domain"]))
        if "hash" in entry.parsed_fields:
            values_to_check.append(("hash", entry.parsed_fields["hash"]))
        if "url" in entry.parsed_fields:
            values_to_check.append(("url", entry.parsed_fields["url"]))
        if "command_line" in entry.parsed_fields:
            values_to_check.append(("cmdline", entry.parsed_fields["command_line"]))
        
        # Check raw message for any IOC patterns
        for ioc in self._iocs.values():
            if ioc.value in entry.raw_message or ioc.value in str(entry.parsed_fields):
                matches.append({
                    "ioc_id": ioc.ioc_id,
                    "ioc_type": ioc.ioc_type.value,
                    "value": ioc.value,
                    "severity": ioc.severity.value,
                    "confidence": ioc.confidence
                })
        
        return matches
    
    def _run_detection(self, entry: LogEntry) -> List[Alert]:
        """Run detection rules against log entry"""
        alerts = []
        
        for rule in self._detection_rules.values():
            if rule.matches(entry):
                # Generate alert
                alert = Alert(
                    alert_id=f"ALT-{uuid.uuid4().hex[:8].upper()}",
                    timestamp=datetime.utcnow(),
                    severity=rule.severity,
                    title=f"[{rule.severity.value}] {rule.name}",
                    description=rule.description,
                    source=entry.source_type.value,
                    rule_name=rule.name,
                    rule_id=rule.rule_id,
                    raw_data=entry.to_dict(),
                    ioc_matches=[],
                    related_events=[entry.entry_id],
                    mitre_techniques=rule.mitre_techniques
                )
                
                # Update rule stats
                rule.hit_count += 1
                rule.last_hit = datetime.utcnow()
                
                # Store alert
                self._store_alert(alert)
                self._active_alerts[alert.alert_id] = alert
                
                # Trigger alert handlers
                for handler in self._alert_handlers:
                    try:
                        handler(alert)
                    except Exception as e:
                        logger.error(f"Alert handler error: {e}")
                
                alerts.append(alert)
                entry.alert_triggered = True
                self._stats["alerts_generated"] += 1
        
        return alerts
    
    def _store_alert(self, alert: Alert):
        """Persist alert to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO alerts 
                (alert_id, timestamp, severity, title, description, source,
                 rule_name, rule_id, raw_data, ioc_matches, related_events,
                 status, assigned_to, incident_id, mitre_techniques, cvss_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                alert.alert_id, alert.timestamp.isoformat(), alert.severity.value,
                alert.title, alert.description, alert.source, alert.rule_name,
                alert.rule_id, json.dumps(alert.raw_data), json.dumps(alert.ioc_matches),
                json.dumps(alert.related_events), alert.status, alert.assigned_to,
                alert.incident_id, json.dumps(alert.mitre_techniques), alert.cvss_score
            ))
            conn.commit()
    
    # ==================== INCIDENT MANAGEMENT ====================
    
    def create_incident(self,
                        title: str,
                        description: str,
                        severity: AlertSeverity,
                        related_alerts: Optional[List[str]] = None,
                        lead_analyst: Optional[str] = None) -> Incident:
        """Create new incident case"""
        incident_id = f"INC-{uuid.uuid4().hex[:8].upper()}"
        now = datetime.utcnow()
        
        incident = Incident(
            incident_id=incident_id,
            created_at=now,
            updated_at=now,
            title=title,
            description=description,
            severity=severity,
            status=IncidentStatus.NEW,
            lead_analyst=lead_analyst,
            related_alerts=related_alerts or [],
            timeline=[{
                "timestamp": now.isoformat(),
                "action": "Incident created",
                "actor": lead_analyst or "system"
            }]
        )
        
        with self._lock:
            self._incidents[incident_id] = incident
            
            # Update related alerts
            for alert_id in related_alerts or []:
                if alert_id in self._active_alerts:
                    self._active_alerts[alert_id].incident_id = incident_id
            
            # Persist
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO incidents 
                    (incident_id, created_at, updated_at, title, description, severity,
                     status, lead_analyst, related_alerts, timeline)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    incident_id, now.isoformat(), now.isoformat(), title, description,
                    severity.value, IncidentStatus.NEW.value, lead_analyst,
                    json.dumps(related_alerts or []), json.dumps(incident.timeline)
                ))
                conn.commit()
            
            self._stats["incidents_created"] += 1
        
        logger.info(f"[BLUE TEAM] Incident created: {incident_id}")
        return incident
    
    def update_incident_status(self,
                                incident_id: str,
                                status: IncidentStatus,
                                actor: str = "system") -> bool:
        """Update incident status"""
        with self._lock:
            if incident_id not in self._incidents:
                return False
            
            incident = self._incidents[incident_id]
            old_status = incident.status
            incident.status = status
            incident.updated_at = datetime.utcnow()
            incident.timeline.append({
                "timestamp": datetime.utcnow().isoformat(),
                "action": f"Status changed: {old_status.value} -> {status.value}",
                "actor": actor
            })
            
            # Persist
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE incidents 
                    SET status = ?, updated_at = ?, timeline = ?
                    WHERE incident_id = ?
                """, (
                    status.value, incident.updated_at.isoformat(),
                    json.dumps(incident.timeline), incident_id
                ))
                conn.commit()
            
            logger.info(f"[BLUE TEAM] Incident {incident_id} status: {status.value}")
            return True
    
    def get_incident(self, incident_id: str) -> Optional[Incident]:
        """Get incident by ID"""
        return self._incidents.get(incident_id)
    
    def get_incidents(self,
                      status: Optional[IncidentStatus] = None,
                      severity: Optional[AlertSeverity] = None) -> List[Incident]:
        """Get incidents with optional filtering"""
        results = list(self._incidents.values())
        
        if status:
            results = [i for i in results if i.status == status]
        if severity:
            results = [i for i in results if i.severity == severity]
        
        return sorted(results, key=lambda x: x.created_at, reverse=True)
    
    def add_containment_action(self,
                                incident_id: str,
                                action: str,
                                description: str,
                                actor: str = "system") -> bool:
        """Add containment action to incident"""
        with self._lock:
            if incident_id not in self._incidents:
                return False
            
            incident = self._incidents[incident_id]
            action_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "action": action,
                "description": description,
                "actor": actor,
                "status": "pending"
            }
            incident.containment_actions.append(action_entry)
            incident.timeline.append({
                "timestamp": datetime.utcnow().isoformat(),
                "action": f"Containment: {action}",
                "actor": actor
            })
            incident.updated_at = datetime.utcnow()
            
            # Persist
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE incidents 
                    SET containment_actions = ?, timeline = ?, updated_at = ?
                    WHERE incident_id = ?
                """, (
                    json.dumps(incident.containment_actions),
                    json.dumps(incident.timeline),
                    incident.updated_at.isoformat(),
                    incident_id
                ))
                conn.commit()
            
            return True
    
    # ==================== ALERT MANAGEMENT ====================
    
    def get_alert(self, alert_id: str) -> Optional[Alert]:
        """Get alert by ID"""
        return self._active_alerts.get(alert_id)
    
    def get_alerts(self,
                   severity: Optional[AlertSeverity] = None,
                   status: Optional[str] = None,
                   since: Optional[datetime] = None) -> List[Alert]:
        """Get alerts with optional filtering"""
        results = list(self._active_alerts.values())
        
        if severity:
            results = [a for a in results if a.severity == severity]
        if status:
            results = [a for a in results if a.status == status]
        if since:
            results = [a for a in results if a.timestamp >= since]
        
        return sorted(results, key=lambda x: x.timestamp, reverse=True)
    
    def assign_alert(self, alert_id: str, analyst: str) -> bool:
        """Assign alert to analyst"""
        with self._lock:
            if alert_id not in self._active_alerts:
                return False
            
            alert = self._active_alerts[alert_id]
            alert.assigned_to = analyst
            alert.status = "ASSIGNED"
            
            # Persist
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE alerts SET assigned_to = ?, status = ? WHERE alert_id = ?",
                    (analyst, "ASSIGNED", alert_id)
                )
                conn.commit()
            
            logger.info(f"[BLUE TEAM] Alert {alert_id} assigned to {analyst}")
            return True
    
    def close_alert(self, alert_id: str, resolution: str) -> bool:
        """Close an alert"""
        with self._lock:
            if alert_id not in self._active_alerts:
                return False
            
            alert = self._active_alerts[alert_id]
            alert.status = "CLOSED"
            
            # Persist
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE alerts SET status = ? WHERE alert_id = ?",
                    ("CLOSED", alert_id)
                )
                conn.commit()
            
            logger.info(f"[BLUE TEAM] Alert {alert_id} closed: {resolution}")
            return True
    
    def add_alert_handler(self, handler: Callable[[Alert], None]):
        """Register alert handler callback"""
        self._alert_handlers.append(handler)
    
    # ==================== DETECTION RULES ====================
    
    def add_detection_rule(self, rule: DetectionRule) -> bool:
        """Add custom detection rule"""
        with self._lock:
            self._detection_rules[rule.rule_id] = rule
            
            # Persist
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO detection_rules 
                    (rule_id, name, description, severity, source_types, conditions,
                     mitre_techniques, enabled, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    rule.rule_id, rule.name, rule.description, rule.severity.value,
                    json.dumps([s.value for s in rule.source_types]),
                    json.dumps(rule.conditions),
                    json.dumps(rule.mitre_techniques),
                    1 if rule.enabled else 0,
                    rule.created_at.isoformat()
                ))
                conn.commit()
            
            logger.info(f"[BLUE TEAM] Detection rule added: {rule.rule_id}")
            return True
    
    def get_detection_rules(self) -> List[DetectionRule]:
        """Get all detection rules"""
        return list(self._detection_rules.values())
    
    def toggle_rule(self, rule_id: str, enabled: bool) -> bool:
        """Enable/disable detection rule"""
        with self._lock:
            if rule_id not in self._detection_rules:
                return False
            
            self._detection_rules[rule_id].enabled = enabled
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE detection_rules SET enabled = ? WHERE rule_id = ?",
                    (1 if enabled else 0, rule_id)
                )
                conn.commit()
            
            return True
    
    # ==================== STATISTICS & REPORTING ====================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get Blue Team operational statistics"""
        with self._lock:
            return {
                **self._stats,
                "active_alerts": len([a for a in self._active_alerts.values() if a.status == "OPEN"]),
                "total_incidents": len(self._incidents),
                "open_incidents": len([i for i in self._incidents.values() if i.status != IncidentStatus.CLOSED]),
                "total_iocs": len(self._iocs),
                "detection_rules": len(self._detection_rules),
                "enabled_rules": len([r for r in self._detection_rules.values() if r.enabled])
            }
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get dashboard data for SOC view"""
        with self._lock:
            # Alert severity distribution
            severity_counts = defaultdict(int)
            for alert in self._active_alerts.values():
                severity_counts[alert.severity.value] += 1
            
            # Recent alerts (last 24 hours)
            day_ago = datetime.utcnow() - timedelta(hours=24)
            recent_alerts = [
                a.to_dict() for a in self._active_alerts.values()
                if a.timestamp > day_ago
            ]
            
            # Open incidents
            open_incidents = [
                i.to_dict() for i in self._incidents.values()
                if i.status != IncidentStatus.CLOSED
            ]
            
            # Top IOCs by hit count
            top_iocs = sorted(
                self._iocs.values(),
                key=lambda x: x.hit_count,
                reverse=True
            )[:10]
            
            return {
                "stats": self.get_stats(),
                "severity_distribution": dict(severity_counts),
                "recent_alerts": recent_alerts[:50],  # Limit to 50
                "open_incidents": open_incidents,
                "top_iocs": [i.to_dict() for i in top_iocs],
                "rule_status": [
                    {"id": r.rule_id, "name": r.name, "enabled": r.enabled, "hits": r.hit_count}
                    for r in self._detection_rules.values()
                ]
            }
    
    # ==================== UTILITY ====================
    
    def reset_stats(self):
        """Reset operational statistics"""
        with self._lock:
            self._stats = {
                "logs_ingested": 0,
                "alerts_generated": 0,
                "incidents_created": 0,
                "iocs_matched": 0,
                "last_reset": datetime.utcnow().isoformat()
            }
    
    def export_iocs(self, format: str = "json") -> str:
        """Export IOCs in various formats"""
        iocs = [ioc.to_dict() for ioc in self._iocs.values()]
        
        if format == "json":
            return json.dumps(iocs, indent=2)
        elif format == "csv":
            import csv
            import io
            output = io.StringIO()
            if iocs:
                writer = csv.DictWriter(output, fieldnames=iocs[0].keys())
                writer.writeheader()
                writer.writerows(iocs)
            return output.getvalue()
        elif format == "stix":
            # Simplified STIX 2.0 format
            stix = {
                "type": "bundle",
                "id": f"bundle--{uuid.uuid4()}",
                "spec_version": "2.1",
                "objects": []
            }
            for ioc in iocs:
                stix["objects"].append({
                    "type": "indicator",
                    "id": f"indicator--{ioc['ioc_id']}",
                    "created": ioc["added_at"],
                    "modified": ioc["last_seen"] or ioc["added_at"],
                    "pattern": f"[{ioc['ioc_type']} = '{ioc['value']}']",
                    "labels": ["malicious-activity"]
                })
            return json.dumps(stix, indent=2)
        else:
            return json.dumps(iocs, indent=2)


# Singleton instance
_blueteam_manager = None

def get_blueteam_manager(db_path: str = None) -> BlueTeamManager:
    """Get or create Blue Team manager singleton"""
    global _blueteam_manager
    if _blueteam_manager is None:
        if db_path is None:
            db_path = "/opt/codex-swarm/command-post/blueteam/blueteam.db"
        _blueteam_manager = BlueTeamManager(db_path)
    return _blueteam_manager
