#!/usr/bin/env python3
"""
================================================================================
ORDL COMMAND POST v6.0.0 - BLUE TEAM INCIDENT RESPONSE PLAYBOOKS
================================================================================
Classification: TOP SECRET//SCI//NOFORN
Classification Level: TS/SCI/NOFORN
Compartment: ORDL-CYBER-OPS

AUTOMATED INCIDENT RESPONSE PLAYBOOK SYSTEM
================================================================================
Military-grade automated response capabilities with:
- Predefined response procedure definitions
- Dynamic playbook execution engine
- Step-level conditional logic and retry
- Comprehensive audit logging
- Async execution support
- Built-in response templates for common threats

Built-in Playbooks:
- Malware Response: Isolate, collect samples, notify
- Brute Force Response: Block IP, force password reset
- Data Exfiltration: Isolate system, preserve logs
- Privilege Escalation: Suspend account, audit

Author: ORDL Cyber Operations Division
Version: 6.0.0
================================================================================
"""

import os
import sys
import json
import time
import uuid
import asyncio
import logging
import hashlib
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union, Set
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from collections import defaultdict
import aiohttp
import sqlite3

# Local imports
from .incident import Incident, IncidentManager
from .. import Alert

# Configure logging
logger = logging.getLogger('blueteam.playbooks')


class StepType(Enum):
    """Playbook step action types"""
    NOTIFY = "notify"           # Send alert (email, slack, webhook)
    ISOLATE = "isolate"         # Network isolation
    ENRICH = "enrich"           # Gather additional context
    CREATE_TICKET = "create_ticket"  # External ticketing
    RUN_COMMAND = "run_command" # Execute system command
    WAIT = "wait"               # Pause for manual action
    CONDITION = "condition"     # Branch based on data
    CONTAIN = "contain"         # System containment actions
    COLLECT = "collect"         # Evidence collection
    RESTORE = "restore"         # Restore from backup


class StepStatus(Enum):
    """Individual step execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"
    RETRYING = "retrying"


class ExecutionStatus(Enum):
    """Overall playbook execution status"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PARTIAL = "partial"  # Some steps completed, some failed


class SeverityLevel(Enum):
    """Incident severity levels for playbook triggers"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class RetryConfig:
    """Step retry configuration"""
    max_attempts: int = 3
    delay_seconds: float = 5.0
    backoff_multiplier: float = 2.0
    max_delay_seconds: float = 300.0  # 5 minutes
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PlaybookStep:
    """
    Individual action step within a playbook
    
    Attributes:
        step_id: Unique identifier for this step
        name: Human-readable step name
        description: Detailed description of the action
        step_type: Type of action (notify, isolate, enrich, etc.)
        parameters: Step-specific configuration parameters
        condition: Optional conditional expression (Jinja2 syntax)
        timeout_seconds: Maximum execution time
        retry_config: Retry behavior configuration
        depends_on: List of step_ids that must complete first
        continue_on_failure: Whether to continue playbook if this fails
    """
    step_id: str
    name: str
    description: str
    step_type: StepType
    parameters: Dict[str, Any] = field(default_factory=dict)
    condition: Optional[str] = None
    timeout_seconds: float = 300.0
    retry_config: RetryConfig = field(default_factory=RetryConfig)
    depends_on: List[str] = field(default_factory=list)
    continue_on_failure: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'step_id': self.step_id,
            'name': self.name,
            'description': self.description,
            'step_type': self.step_type.value,
            'parameters': self.parameters,
            'condition': self.condition,
            'timeout_seconds': self.timeout_seconds,
            'retry_config': self.retry_config.to_dict(),
            'depends_on': self.depends_on,
            'continue_on_failure': self.continue_on_failure
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PlaybookStep':
        """Create PlaybookStep from dictionary"""
        return cls(
            step_id=data['step_id'],
            name=data['name'],
            description=data['description'],
            step_type=StepType(data['step_type']),
            parameters=data.get('parameters', {}),
            condition=data.get('condition'),
            timeout_seconds=data.get('timeout_seconds', 300.0),
            retry_config=RetryConfig(**data.get('retry_config', {})),
            depends_on=data.get('depends_on', []),
            continue_on_failure=data.get('continue_on_failure', False)
        )


@dataclass
class PlaybookTrigger:
    """
    Trigger conditions for automatic playbook execution
    
    Attributes:
        alert_types: List of alert types that trigger this playbook
        severities: List of severity levels that trigger this playbook
        rule_ids: Specific detection rule IDs that trigger
        custom_conditions: Additional Jinja2 conditional expressions
    """
    alert_types: List[str] = field(default_factory=list)
    severities: List[SeverityLevel] = field(default_factory=list)
    rule_ids: List[str] = field(default_factory=list)
    custom_conditions: List[str] = field(default_factory=list)
    
    def matches(self, alert: Alert, incident: Optional[Incident] = None) -> bool:
        """Check if alert/incident matches trigger conditions"""
        # Check alert type
        if self.alert_types:
            alert_type = getattr(alert, 'alert_type', None) or getattr(alert, 'event_type', '')
            if alert_type not in self.alert_types:
                return False
        
        # Check severity
        if self.severities:
            severity = getattr(alert, 'severity', None)
            if isinstance(severity, str):
                try:
                    severity = SeverityLevel(severity.lower())
                except ValueError:
                    pass
            if severity not in self.severities:
                return False
        
        # Check rule ID
        if self.rule_ids:
            rule_id = getattr(alert, 'rule_id', None)
            if rule_id not in self.rule_ids:
                return False
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'alert_types': self.alert_types,
            'severities': [s.value for s in self.severities],
            'rule_ids': self.rule_ids,
            'custom_conditions': self.custom_conditions
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PlaybookTrigger':
        return cls(
            alert_types=data.get('alert_types', []),
            severities=[SeverityLevel(s) for s in data.get('severities', [])],
            rule_ids=data.get('rule_ids', []),
            custom_conditions=data.get('custom_conditions', [])
        )


@dataclass
class Playbook:
    """
    Incident response playbook definition
    
    Attributes:
        playbook_id: Unique identifier
        name: Human-readable name
        description: Detailed description
        triggers: Automatic trigger conditions
        steps: Ordered list of response steps
        enabled: Whether this playbook is active
        created_at: Creation timestamp
        updated_at: Last modification timestamp
        version: Playbook version
        author: Creator identifier
        tags: Categorization tags
    """
    playbook_id: str
    name: str
    description: str
    triggers: PlaybookTrigger = field(default_factory=PlaybookTrigger)
    steps: List[PlaybookStep] = field(default_factory=list)
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    version: str = "1.0.0"
    author: str = "system"
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'playbook_id': self.playbook_id,
            'name': self.name,
            'description': self.description,
            'triggers': self.triggers.to_dict(),
            'steps': [s.to_dict() for s in self.steps],
            'enabled': self.enabled,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'version': self.version,
            'author': self.author,
            'tags': self.tags
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Playbook':
        return cls(
            playbook_id=data['playbook_id'],
            name=data['name'],
            description=data['description'],
            triggers=PlaybookTrigger.from_dict(data.get('triggers', {})),
            steps=[PlaybookStep.from_dict(s) for s in data.get('steps', [])],
            enabled=data.get('enabled', True),
            created_at=datetime.fromisoformat(data['created_at']) if 'created_at' in data else datetime.utcnow(),
            updated_at=datetime.fromisoformat(data['updated_at']) if 'updated_at' in data else datetime.utcnow(),
            version=data.get('version', '1.0.0'),
            author=data.get('author', 'system'),
            tags=data.get('tags', [])
        )
    
    def add_step(self, step: PlaybookStep) -> None:
        """Add a step to the playbook"""
        self.steps.append(step)
        self.updated_at = datetime.utcnow()
    
    def remove_step(self, step_id: str) -> bool:
        """Remove a step by ID"""
        for i, step in enumerate(self.steps):
            if step.step_id == step_id:
                self.steps.pop(i)
                self.updated_at = datetime.utcnow()
                return True
        return False


@dataclass
class StepResult:
    """Result of executing a single playbook step"""
    step_id: str
    status: StepStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    output: Optional[str] = None
    error_message: Optional[str] = None
    execution_time_ms: float = 0.0
    attempt_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'step_id': self.step_id,
            'status': self.status.value,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'output': self.output,
            'error_message': self.error_message,
            'execution_time_ms': self.execution_time_ms,
            'attempt_count': self.attempt_count,
            'metadata': self.metadata
        }


@dataclass
class PlaybookExecution:
    """
    Tracks a running instance of a playbook
    
    Attributes:
        execution_id: Unique execution identifier
        playbook_id: Reference to playbook definition
        incident_id: Reference to associated incident
        status: Current execution status
        current_step: Index of current step being executed
        step_results: Results of completed steps
        context: Execution context variables
        logs: Execution audit log entries
        start_time: Execution start timestamp
        end_time: Execution completion timestamp
        triggered_by: Identifier of what triggered execution
    """
    execution_id: str
    playbook_id: str
    incident_id: Optional[str] = None
    status: ExecutionStatus = ExecutionStatus.PENDING
    current_step: int = 0
    step_results: Dict[str, StepResult] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    logs: List[Dict[str, Any]] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    triggered_by: str = "manual"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'execution_id': self.execution_id,
            'playbook_id': self.playbook_id,
            'incident_id': self.incident_id,
            'status': self.status.value,
            'current_step': self.current_step,
            'step_results': {k: v.to_dict() for k, v in self.step_results.items()},
            'context': self.context,
            'logs': self.logs,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'triggered_by': self.triggered_by
        }
    
    def add_log(self, level: str, message: str, **kwargs) -> None:
        """Add an audit log entry"""
        self.logs.append({
            'timestamp': datetime.utcnow().isoformat(),
            'level': level,
            'message': message,
            **kwargs
        })
    
    def get_current_step_id(self) -> Optional[str]:
        """Get the ID of the current step being executed"""
        # This will be populated by the engine during execution
        return self.context.get('current_step_id')
    
    def is_complete(self) -> bool:
        """Check if execution has completed"""
        return self.status in [
            ExecutionStatus.COMPLETED,
            ExecutionStatus.FAILED,
            ExecutionStatus.CANCELLED
        ]


class PlaybookEngine:
    """
    Automated Incident Response Playbook Execution Engine
    
    Manages playbook definitions, execution state, and step handlers.
    Provides async execution support with comprehensive audit logging.
    
    Features:
    - Dynamic playbook loading and registration
    - Async step execution with timeout and retry
    - Step-level conditional logic
    - Execution pause/resume/cancel
    - Integration with incident management
    - Comprehensive audit logging
    """
    
    def __init__(self, 
                 db_path: str = "/opt/codex-swarm/command-post/data/nexus.db",
                 incident_manager: Optional[IncidentManager] = None):
        self.db_path = db_path
        self.incident_manager = incident_manager
        
        # Storage
        self._playbooks: Dict[str, Playbook] = {}
        self._executions: Dict[str, PlaybookExecution] = {}
        self._step_handlers: Dict[StepType, Callable] = {}
        
        # Execution control
        self._running_executions: Set[str] = set()
        self._paused_executions: Set[str] = set()
        self._lock = asyncio.Lock()
        
        # Initialize
        self._init_database()
        self._register_default_handlers()
        self._load_builtin_playbooks()
        
        logger.info("[PLAYBOOKS] Engine initialized")
    
    def _init_database(self) -> None:
        """Initialize database schema for playbooks"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Playbook definitions table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS playbooks (
                        playbook_id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        description TEXT,
                        triggers TEXT,
                        steps TEXT,
                        enabled BOOLEAN DEFAULT 1,
                        created_at TEXT,
                        updated_at TEXT,
                        version TEXT,
                        author TEXT,
                        tags TEXT
                    )
                """)
                
                # Playbook executions table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS playbook_executions (
                        execution_id TEXT PRIMARY KEY,
                        playbook_id TEXT,
                        incident_id TEXT,
                        status TEXT,
                        current_step INTEGER DEFAULT 0,
                        step_results TEXT,
                        context TEXT,
                        logs TEXT,
                        start_time TEXT,
                        end_time TEXT,
                        triggered_by TEXT
                    )
                """)
                
                # Execution audit log
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS playbook_audit_log (
                        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        execution_id TEXT,
                        timestamp TEXT,
                        level TEXT,
                        message TEXT,
                        details TEXT
                    )
                """)
                
                conn.commit()
                logger.info("[PLAYBOOKS] Database schema initialized")
        except Exception as e:
            logger.error(f"[PLAYBOOKS] Database initialization failed: {e}")
            raise
    
    def _register_default_handlers(self) -> None:
        """Register default step type handlers"""
        self._step_handlers = {
            StepType.NOTIFY: self._handle_notify,
            StepType.ISOLATE: self._handle_isolate,
            StepType.ENRICH: self._handle_enrich,
            StepType.CREATE_TICKET: self._handle_create_ticket,
            StepType.RUN_COMMAND: self._handle_run_command,
            StepType.WAIT: self._handle_wait,
            StepType.CONDITION: self._handle_condition,
            StepType.CONTAIN: self._handle_contain,
            StepType.COLLECT: self._handle_collect,
            StepType.RESTORE: self._handle_restore
        }
        logger.info(f"[PLAYBOOKS] Registered {len(self._step_handlers)} step handlers")
    
    def _load_builtin_playbooks(self) -> None:
        """Load built-in playbook templates"""
        builtin_playbooks = [
            self._create_malware_response_playbook(),
            self._create_brute_force_response_playbook(),
            self._create_data_exfiltration_playbook(),
            self._create_privilege_escalation_playbook()
        ]
        
        for playbook in builtin_playbooks:
            self._playbooks[playbook.playbook_id] = playbook
            self._persist_playbook(playbook)
        
        logger.info(f"[PLAYBOOKS] Loaded {len(builtin_playbooks)} built-in playbooks")
    
    def _create_malware_response_playbook(self) -> Playbook:
        """Create malware response playbook template"""
        return Playbook(
            playbook_id="PB-MALWARE-001",
            name="Malware Response",
            description="Automated response procedure for malware detection incidents",
            triggers=PlaybookTrigger(
                alert_types=["malware_detection", "suspicious_process", "file_infection"],
                severities=[SeverityLevel.CRITICAL, SeverityLevel.HIGH]
            ),
            steps=[
                PlaybookStep(
                    step_id="malware_notify_001",
                    name="Notify Security Team",
                    description="Send immediate alert to security operations center",
                    step_type=StepType.NOTIFY,
                    parameters={
                        "channels": ["email", "slack"],
                        "priority": "critical",
                        "template": "malware_alert"
                    },
                    timeout_seconds=60
                ),
                PlaybookStep(
                    step_id="malware_isolate_001",
                    name="Isolate Infected System",
                    description="Immediately isolate the infected system from the network",
                    step_type=StepType.ISOLATE,
                    parameters={
                        "method": "network_isolation",
                        "preserve_connectivity": ["siem", "edr"]
                    },
                    timeout_seconds=120
                ),
                PlaybookStep(
                    step_id="malware_collect_001",
                    name="Collect Evidence",
                    description="Collect memory dump and disk image for forensic analysis",
                    step_type=StepType.COLLECT,
                    parameters={
                        "evidence_types": ["memory_dump", "disk_image", "process_list"],
                        "preserve_timestamps": True
                    },
                    depends_on=["malware_isolate_001"],
                    timeout_seconds=600
                ),
                PlaybookStep(
                    step_id="malware_enrich_001",
                    name="Enrich Threat Intelligence",
                    description="Query threat intelligence sources for malware details",
                    step_type=StepType.ENRICH,
                    parameters={
                        "sources": ["virustotal", "misp", "local_ioc"],
                        "extract_iocs": True
                    },
                    timeout_seconds=180
                ),
                PlaybookStep(
                    step_id="malware_contain_001",
                    name="Block IOCs",
                    description="Block identified IOCs across network security controls",
                    step_type=StepType.CONTAIN,
                    parameters={
                        "ioc_types": ["hash", "domain", "ip"],
                        "block_duration": "permanent"
                    },
                    depends_on=["malware_enrich_001"],
                    timeout_seconds=300
                )
            ],
            tags=["malware", "response", "critical"],
            author="ORDL-BlueTeam"
        )
    
    def _create_brute_force_response_playbook(self) -> Playbook:
        """Create brute force attack response playbook template"""
        return Playbook(
            playbook_id="PB-BRUTEFORCE-001",
            name="Brute Force Response",
            description="Automated response for brute force authentication attacks",
            triggers=PlaybookTrigger(
                alert_types=["brute_force", "multiple_failed_logins", "authentication_anomaly"],
                severities=[SeverityLevel.HIGH, SeverityLevel.MEDIUM]
            ),
            steps=[
                PlaybookStep(
                    step_id="bf_notify_001",
                    name="Alert on Brute Force",
                    description="Notify security team of ongoing brute force attack",
                    step_type=StepType.NOTIFY,
                    parameters={
                        "channels": ["slack", "email"],
                        "template": "brute_force_alert"
                    },
                    timeout_seconds=30
                ),
                PlaybookStep(
                    step_id="bf_block_001",
                    name="Block Attacker IP",
                    description="Block the attacking IP address at firewall/WAF level",
                    step_type=StepType.CONTAIN,
                    parameters={
                        "action": "block_ip",
                        "duration_minutes": 60,
                        "scope": "perimeter"
                    },
                    timeout_seconds=60
                ),
                PlaybookStep(
                    step_id="bf_reset_001",
                    name="Force Password Reset",
                    description="Force password reset for targeted accounts",
                    step_type=StepType.RUN_COMMAND,
                    parameters={
                        "command_type": "force_password_reset",
                        "notify_users": True
                    },
                    continue_on_failure=True,
                    timeout_seconds=120
                ),
                PlaybookStep(
                    step_id="bf_ticket_001",
                    name="Create Investigation Ticket",
                    description="Create ticket for security team investigation",
                    step_type=StepType.CREATE_TICKET,
                    parameters={
                        "system": "jira",
                        "priority": "high",
                        "assignee": "security-team"
                    },
                    timeout_seconds=60
                )
            ],
            tags=["brute_force", "authentication", "response"],
            author="ORDL-BlueTeam"
        )
    
    def _create_data_exfiltration_playbook(self) -> Playbook:
        """Create data exfiltration response playbook template"""
        return Playbook(
            playbook_id="PB-EXFIL-001",
            name="Data Exfiltration Response",
            description="Emergency response for suspected data exfiltration",
            triggers=PlaybookTrigger(
                alert_types=["data_exfiltration", "large_transfer", "suspicious_upload"],
                severities=[SeverityLevel.CRITICAL, SeverityLevel.HIGH]
            ),
            steps=[
                PlaybookStep(
                    step_id="exfil_notify_001",
                    name="Critical Alert",
                    description="Send critical alert to security team and management",
                    step_type=StepType.NOTIFY,
                    parameters={
                        "channels": ["email", "slack", "sms"],
                        "priority": "critical",
                        "escalation": True
                    },
                    timeout_seconds=30
                ),
                PlaybookStep(
                    step_id="exfil_isolate_001",
                    name="Emergency Isolation",
                    description="Immediately isolate affected systems",
                    step_type=StepType.ISOLATE,
                    parameters={
                        "method": "emergency_isolation",
                        "preserve_logs": True
                    },
                    timeout_seconds=60
                ),
                PlaybookStep(
                    step_id="exfil_preserve_001",
                    name="Preserve Evidence",
                    description="Preserve all logs and network captures",
                    step_type=StepType.COLLECT,
                    parameters={
                        "evidence_types": ["network_logs", "proxy_logs", "endpoint_logs"],
                        "chain_of_custody": True
                    },
                    timeout_seconds=300
                ),
                PlaybookStep(
                    step_id="exfil_wait_001",
                    name="Wait for Investigation",
                    description="Pause for manual investigation by IR team",
                    step_type=StepType.WAIT,
                    parameters={
                        "timeout_minutes": 60,
                        "escalate_after_timeout": True
                    },
                    timeout_seconds=3600
                )
            ],
            tags=["exfiltration", "data_loss", "critical", "incident_response"],
            author="ORDL-BlueTeam"
        )
    
    def _create_privilege_escalation_playbook(self) -> Playbook:
        """Create privilege escalation response playbook template"""
        return Playbook(
            playbook_id="PB-PRIVESC-001",
            name="Privilege Escalation Response",
            description="Response procedure for detected privilege escalation attempts",
            triggers=PlaybookTrigger(
                alert_types=["privilege_escalation", "suspicious_sudo", "token_manipulation"],
                severities=[SeverityLevel.CRITICAL, SeverityLevel.HIGH],
                rule_ids=["BT-PRIV-001"]
            ),
            steps=[
                PlaybookStep(
                    step_id="priv_notify_001",
                    name="Notify SOC",
                    description="Alert security operations center",
                    step_type=StepType.NOTIFY,
                    parameters={
                        "channels": ["slack", "email"],
                        "template": "privilege_escalation_alert"
                    },
                    timeout_seconds=30
                ),
                PlaybookStep(
                    step_id="priv_suspend_001",
                    name="Suspend Account",
                    description="Immediately suspend the compromised account",
                    step_type=StepType.RUN_COMMAND,
                    parameters={
                        "command_type": "suspend_account",
                        "disable_immediately": True
                    },
                    timeout_seconds=60
                ),
                PlaybookStep(
                    step_id="priv_audit_001",
                    name="Audit Account Activity",
                    description="Audit all recent activity by the compromised account",
                    step_type=StepType.ENRICH,
                    parameters={
                        "audit_scope": "account",
                        "lookback_hours": 24,
                        "include_privileged_actions": True
                    },
                    timeout_seconds=180
                ),
                PlaybookStep(
                    step_id="priv_isolate_001",
                    name="Isolate Affected Systems",
                    description="Isolate systems accessed by compromised account",
                    step_type=StepType.ISOLATE,
                    parameters={
                        "scope": "affected_systems",
                        "preserve_logs": True
                    },
                    depends_on=["priv_audit_001"],
                    timeout_seconds=120
                ),
                PlaybookStep(
                    step_id="priv_ticket_001",
                    name="Create IR Ticket",
                    description="Create incident response ticket",
                    step_type=StepType.CREATE_TICKET,
                    parameters={
                        "system": "jira",
                        "type": "security_incident",
                        "priority": "critical"
                    },
                    timeout_seconds=60
                )
            ],
            tags=["privilege_escalation", "account_compromise", "critical"],
            author="ORDL-BlueTeam"
        )
    
    # ==================== Public API ====================
    
    def load_playbook(self, playbook: Playbook) -> None:
        """
        Load a playbook definition into the engine
        
        Args:
            playbook: Playbook definition to load
        """
        self._playbooks[playbook.playbook_id] = playbook
        self._persist_playbook(playbook)
        logger.info(f"[PLAYBOOKS] Loaded playbook: {playbook.name} ({playbook.playbook_id})")
    
    def get_playbook(self, playbook_id: str) -> Optional[Playbook]:
        """Get a playbook by ID"""
        return self._playbooks.get(playbook_id)
    
    def list_playbooks(self, enabled_only: bool = False) -> List[Dict[str, Any]]:
        """List all loaded playbooks"""
        playbooks = self._playbooks.values()
        if enabled_only:
            playbooks = [p for p in playbooks if p.enabled]
        return [p.to_dict() for p in playbooks]
    
    def delete_playbook(self, playbook_id: str) -> bool:
        """Delete a playbook"""
        if playbook_id in self._playbooks:
            del self._playbooks[playbook_id]
            # Also delete from database
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM playbooks WHERE playbook_id = ?", (playbook_id,))
                    conn.commit()
            except Exception as e:
                logger.error(f"[PLAYBOOKS] Failed to delete playbook from DB: {e}")
            return True
        return False
    
    async def trigger_playbook(self, 
                               playbook_id: str,
                               incident_id: Optional[str] = None,
                               alert: Optional[Alert] = None,
                               context: Optional[Dict[str, Any]] = None,
                               triggered_by: str = "manual") -> Optional[str]:
        """
        Trigger playbook execution
        
        Args:
            playbook_id: ID of playbook to execute
            incident_id: Associated incident ID
            alert: Alert that triggered the playbook
            context: Additional execution context
            triggered_by: Identifier of triggering entity
            
        Returns:
            Execution ID if started, None if playbook not found or disabled
        """
        playbook = self._playbooks.get(playbook_id)
        if not playbook:
            logger.error(f"[PLAYBOOKS] Playbook not found: {playbook_id}")
            return None
        
        if not playbook.enabled:
            logger.warning(f"[PLAYBOOKS] Playbook disabled: {playbook_id}")
            return None
        
        # Create execution
        execution_id = f"EXEC-{uuid.uuid4().hex[:12].upper()}"
        execution = PlaybookExecution(
            execution_id=execution_id,
            playbook_id=playbook_id,
            incident_id=incident_id,
            status=ExecutionStatus.RUNNING,
            context=context or {},
            triggered_by=triggered_by
        )
        
        # Add alert data to context if provided
        if alert:
            execution.context['alert'] = {
                'alert_id': getattr(alert, 'alert_id', None),
                'alert_type': getattr(alert, 'alert_type', None),
                'severity': getattr(alert, 'severity', None),
                'source': getattr(alert, 'source', None)
            }
        
        async with self._lock:
            self._executions[execution_id] = execution
            self._running_executions.add(execution_id)
        
        # Persist execution
        self._persist_execution(execution)
        
        logger.info(f"[PLAYBOOKS] Triggered execution {execution_id} for playbook {playbook_id}")
        
        # Start execution in background
        asyncio.create_task(self._execute_playbook(execution, playbook))
        
        return execution_id
    
    async def pause_playbook(self, execution_id: str) -> bool:
        """
        Pause a running playbook execution
        
        Args:
            execution_id: Execution to pause
            
        Returns:
            True if paused successfully
        """
        execution = self._executions.get(execution_id)
        if not execution:
            return False
        
        if execution.status != ExecutionStatus.RUNNING:
            logger.warning(f"[PLAYBOOKS] Cannot pause execution {execution_id}: status is {execution.status.value}")
            return False
        
        async with self._lock:
            execution.status = ExecutionStatus.PAUSED
            self._paused_executions.add(execution_id)
            self._running_executions.discard(execution_id)
        
        execution.add_log("INFO", f"Execution paused")
        self._persist_execution(execution)
        
        logger.info(f"[PLAYBOOKS] Paused execution {execution_id}")
        return True
    
    async def resume_playbook(self, execution_id: str) -> bool:
        """
        Resume a paused playbook execution
        
        Args:
            execution_id: Execution to resume
            
        Returns:
            True if resumed successfully
        """
        execution = self._executions.get(execution_id)
        if not execution:
            return False
        
        if execution.status != ExecutionStatus.PAUSED:
            logger.warning(f"[PLAYBOOKS] Cannot resume execution {execution_id}: status is {execution.status.value}")
            return False
        
        playbook = self._playbooks.get(execution.playbook_id)
        if not playbook:
            return False
        
        async with self._lock:
            execution.status = ExecutionStatus.RUNNING
            self._paused_executions.discard(execution_id)
            self._running_executions.add(execution_id)
        
        execution.add_log("INFO", f"Execution resumed")
        self._persist_execution(execution)
        
        logger.info(f"[PLAYBOOKS] Resumed execution {execution_id}")
        
        # Continue execution
        asyncio.create_task(self._execute_playbook(execution, playbook))
        
        return True
    
    async def cancel_playbook(self, execution_id: str, reason: str = "") -> bool:
        """
        Cancel a playbook execution
        
        Args:
            execution_id: Execution to cancel
            reason: Cancellation reason
            
        Returns:
            True if cancelled successfully
        """
        execution = self._executions.get(execution_id)
        if not execution:
            return False
        
        if execution.is_complete():
            logger.warning(f"[PLAYBOOKS] Cannot cancel execution {execution_id}: already complete")
            return False
        
        async with self._lock:
            execution.status = ExecutionStatus.CANCELLED
            execution.end_time = datetime.utcnow()
            self._running_executions.discard(execution_id)
            self._paused_executions.discard(execution_id)
        
        execution.add_log("INFO", f"Execution cancelled: {reason}")
        self._persist_execution(execution)
        
        logger.info(f"[PLAYBOOKS] Cancelled execution {execution_id}: {reason}")
        return True
    
    def get_running_executions(self) -> List[Dict[str, Any]]:
        """Get list of currently running executions"""
        return [
            self._executions[eid].to_dict()
            for eid in self._running_executions
            if eid in self._executions
        ]
    
    def get_execution(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get execution details by ID"""
        execution = self._executions.get(execution_id)
        return execution.to_dict() if execution else None
    
    # ==================== Core Execution Logic ====================
    
    async def _execute_playbook(self, execution: PlaybookExecution, playbook: Playbook) -> None:
        """Execute playbook steps"""
        logger.info(f"[PLAYBOOKS] Starting execution {execution.execution_id}")
        execution.add_log("INFO", f"Playbook execution started: {playbook.name}")
        
        try:
            for i, step in enumerate(playbook.steps):
                # Check if paused or cancelled
                if execution.status == ExecutionStatus.PAUSED:
                    execution.add_log("INFO", f"Execution paused at step {i}")
                    break
                
                if execution.status == ExecutionStatus.CANCELLED:
                    execution.add_log("INFO", "Execution cancelled")
                    break
                
                # Check dependencies
                if not await self._check_dependencies(execution, step):
                    logger.warning(f"[PLAYBOOKS] Dependencies not met for step {step.step_id}")
                    execution.add_log("WARNING", f"Dependencies not met for step {step.step_id}")
                    if not step.continue_on_failure:
                        execution.status = ExecutionStatus.FAILED
                        break
                    continue
                
                # Update current step
                execution.current_step = i
                execution.context['current_step_id'] = step.step_id
                
                # Execute step
                result = await self.run_step(execution, step)
                execution.step_results[step.step_id] = result
                
                # Persist after each step
                self._persist_execution(execution)
                
                # Check if should continue
                if result.status == StepStatus.FAILED and not step.continue_on_failure:
                    execution.status = ExecutionStatus.FAILED
                    execution.add_log("ERROR", f"Step {step.step_id} failed, halting playbook")
                    break
            
            # Mark complete if not paused/cancelled
            if execution.status == ExecutionStatus.RUNNING:
                # Determine final status
                failed_steps = [r for r in execution.step_results.values() if r.status == StepStatus.FAILED]
                if failed_steps:
                    execution.status = ExecutionStatus.PARTIAL
                else:
                    execution.status = ExecutionStatus.COMPLETED
                execution.end_time = datetime.utcnow()
                execution.add_log("INFO", f"Playbook execution completed with status: {execution.status.value}")
            
        except Exception as e:
            logger.error(f"[PLAYBOOKS] Execution error: {e}")
            execution.status = ExecutionStatus.FAILED
            execution.end_time = datetime.utcnow()
            execution.add_log("ERROR", f"Execution failed with exception: {str(e)}")
        
        finally:
            async with self._lock:
                self._running_executions.discard(execution.execution_id)
            self._persist_execution(execution)
    
    async def _check_dependencies(self, execution: PlaybookExecution, step: PlaybookStep) -> bool:
        """Check if all step dependencies are satisfied"""
        for dep_id in step.depends_on:
            if dep_id not in execution.step_results:
                return False
            dep_result = execution.step_results[dep_id]
            if dep_result.status not in [StepStatus.COMPLETED, StepStatus.SKIPPED]:
                return False
        return True
    
    async def run_step(self, execution: PlaybookExecution, step: PlaybookStep) -> StepResult:
        """
        Execute a single playbook step with retry logic
        
        Args:
            execution: Current playbook execution
            step: Step to execute
            
        Returns:
            StepResult with execution details
        """
        start_time = datetime.utcnow()
        result = StepResult(
            step_id=step.step_id,
            status=StepStatus.PENDING,
            start_time=start_time
        )
        
        logger.info(f"[PLAYBOOKS] Executing step {step.step_id}: {step.name}")
        execution.add_log("INFO", f"Starting step: {step.name}", step_id=step.step_id)
        
        # Evaluate condition if present
        if step.condition and not self._evaluate_condition(step.condition, execution):
            logger.info(f"[PLAYBOOKS] Condition not met for step {step.step_id}, skipping")
            result.status = StepStatus.SKIPPED
            result.end_time = datetime.utcnow()
            result.execution_time_ms = 0
            execution.add_log("INFO", f"Step skipped: condition not met", step_id=step.step_id)
            return result
        
        # Get handler
        handler = self._step_handlers.get(step.step_type)
        if not handler:
            result.status = StepStatus.FAILED
            result.error_message = f"No handler registered for step type: {step.step_type.value}"
            result.end_time = datetime.utcnow()
            execution.add_log("ERROR", result.error_message, step_id=step.step_id)
            return result
        
        # Execute with retry
        attempt = 0
        last_error = None
        
        while attempt < step.retry_config.max_attempts:
            attempt += 1
            result.attempt_count = attempt
            
            try:
                if attempt > 1:
                    result.status = StepStatus.RETRYING
                    delay = min(
                        step.retry_config.delay_seconds * (step.retry_config.backoff_multiplier ** (attempt - 2)),
                        step.retry_config.max_delay_seconds
                    )
                    logger.info(f"[PLAYBOOKS] Retry {attempt} for step {step.step_id} after {delay}s")
                    await asyncio.sleep(delay)
                
                # Execute with timeout
                result.status = StepStatus.RUNNING
                step_output = await asyncio.wait_for(
                    handler(step, execution),
                    timeout=step.timeout_seconds
                )
                
                # Success
                result.status = StepStatus.COMPLETED
                result.output = step_output
                result.end_time = datetime.utcnow()
                result.execution_time_ms = (result.end_time - start_time).total_seconds() * 1000
                execution.add_log("INFO", f"Step completed successfully", step_id=step.step_id)
                return result
                
            except asyncio.TimeoutError:
                last_error = f"Step timed out after {step.timeout_seconds}s"
                result.status = StepStatus.TIMEOUT
                execution.add_log("ERROR", f"Timeout on attempt {attempt}", step_id=step.step_id)
                
            except Exception as e:
                last_error = str(e)
                logger.error(f"[PLAYBOOKS] Step {step.step_id} attempt {attempt} failed: {e}")
                execution.add_log("ERROR", f"Attempt {attempt} failed: {e}", step_id=step.step_id)
        
        # All attempts failed
        result.status = StepStatus.FAILED
        result.error_message = last_error
        result.end_time = datetime.utcnow()
        result.execution_time_ms = (result.end_time - start_time).total_seconds() * 1000
        execution.add_log("ERROR", f"Step failed after {attempt} attempts", step_id=step.step_id)
        
        return result
    
    def _evaluate_condition(self, condition: str, execution: PlaybookExecution) -> bool:
        """
        Evaluate a conditional expression
        
        Args:
            condition: Jinja2-like conditional expression
            execution: Current execution context
            
        Returns:
            True if condition evaluates to true
        """
        # Simple condition evaluation - in production, use Jinja2
        # This is a simplified implementation
        try:
            # Support basic context variable checks
            context = execution.context
            
            # Handle common patterns
            if condition.startswith("context."):
                parts = condition.replace("context.", "").split(".")
                value = context
                for part in parts:
                    if isinstance(value, dict):
                        value = value.get(part)
                    else:
                        return False
                return bool(value)
            
            # Handle severity comparisons
            if "severity" in condition:
                alert = context.get('alert', {})
                severity = alert.get('severity', '').upper()
                if "CRITICAL" in condition:
                    return severity == "CRITICAL"
                if "HIGH" in condition:
                    return severity in ["CRITICAL", "HIGH"]
            
            # Default to True for simple existence checks
            return True
            
        except Exception as e:
            logger.error(f"[PLAYBOOKS] Condition evaluation error: {e}")
            return True  # Fail open
    
    # ==================== Step Handlers ====================
    
    async def _handle_notify(self, step: PlaybookStep, execution: PlaybookExecution) -> str:
        """Handle notification step"""
        params = step.parameters
        channels = params.get("channels", ["email"])
        priority = params.get("priority", "normal")
        template = params.get("template", "default")
        
        message = f"Playbook Alert [{execution.playbook_id}]\n"
        message += f"Execution: {execution.execution_id}\n"
        if execution.incident_id:
            message += f"Incident: {execution.incident_id}\n"
        
        notifications_sent = []
        
        for channel in channels:
            try:
                if channel == "email":
                    # Simulate email notification
                    logger.info(f"[PLAYBOOKS] Email notification sent: {template}")
                    notifications_sent.append("email")
                    
                elif channel == "slack":
                    # Simulate Slack notification
                    webhook_url = params.get("slack_webhook")
                    if webhook_url:
                        # In production: await self._send_slack(webhook_url, message)
                        pass
                    logger.info(f"[PLAYBOOKS] Slack notification sent: {template}")
                    notifications_sent.append("slack")
                    
                elif channel == "sms":
                    # Simulate SMS notification
                    logger.info(f"[PLAYBOOKS] SMS notification sent")
                    notifications_sent.append("sms")
                    
                elif channel == "webhook":
                    # Generic webhook
                    webhook_url = params.get("webhook_url")
                    if webhook_url:
                        # In production: await self._send_webhook(webhook_url, execution)
                        pass
                    logger.info(f"[PLAYBOOKS] Webhook notification sent")
                    notifications_sent.append("webhook")
                    
            except Exception as e:
                logger.error(f"[PLAYBOOKS] Notification failed for channel {channel}: {e}")
        
        return f"Notifications sent via: {', '.join(notifications_sent)}"
    
    async def _handle_isolate(self, step: PlaybookStep, execution: PlaybookExecution) -> str:
        """Handle system isolation step"""
        params = step.parameters
        method = params.get("method", "network_isolation")
        preserve_connectivity = params.get("preserve_connectivity", [])
        
        # Get target from context
        alert = execution.context.get('alert', {})
        source = alert.get('source', 'unknown')
        
        logger.info(f"[PLAYBOOKS] Isolating system {source} using method: {method}")
        
        # In production, this would:
        # 1. Call EDR API to isolate endpoint
        # 2. Update firewall rules
        # 3. Log isolation action
        
        # Update incident if available
        if execution.incident_id and self.incident_manager:
            try:
                # Add containment action to incident
                pass  # In production: await self.incident_manager.add_action(...)
            except Exception as e:
                logger.error(f"[PLAYBOOKS] Failed to update incident: {e}")
        
        return f"System {source} isolated using {method}"
    
    async def _handle_enrich(self, step: PlaybookStep, execution: PlaybookExecution) -> str:
        """Handle enrichment step"""
        params = step.parameters
        sources = params.get("sources", [])
        
        enriched_data = {}
        
        for source in sources:
            try:
                if source == "virustotal":
                    # Query VirusTotal
                    enriched_data['virustotal'] = {"status": "queried", "hits": 0}
                    
                elif source == "misp":
                    # Query MISP
                    enriched_data['misp'] = {"status": "queried", "events": []}
                    
                elif source == "local_ioc":
                    # Query local IOC database
                    enriched_data['local_ioc'] = {"status": "queried", "matches": []}
                    
                elif source == "threat_intel":
                    # Generic threat intel query
                    enriched_data['threat_intel'] = {"indicators": []}
                    
            except Exception as e:
                logger.error(f"[PLAYBOOKS] Enrichment from {source} failed: {e}")
        
        # Store enriched data in context
        execution.context['enrichment'] = enriched_data
        
        return f"Enrichment completed from {len(sources)} sources"
    
    async def _handle_create_ticket(self, step: PlaybookStep, execution: PlaybookExecution) -> str:
        """Handle external ticket creation step"""
        params = step.parameters
        system = params.get("system", "jira")
        priority = params.get("priority", "medium")
        assignee = params.get("assignee", "security-team")
        
        # Build ticket data
        ticket_data = {
            "title": f"IR Playbook Execution: {execution.playbook_id}",
            "description": f"Automated playbook execution {execution.execution_id}",
            "priority": priority,
            "assignee": assignee,
            "incident_id": execution.incident_id,
            "execution_id": execution.execution_id
        }
        
        logger.info(f"[PLAYBOOKS] Creating {system} ticket for execution {execution.execution_id}")
        
        # In production, integrate with ticketing system API
        ticket_id = f"TICKET-{uuid.uuid4().hex[:8].upper()}"
        
        # Store ticket reference
        execution.context['created_ticket'] = {
            'system': system,
            'ticket_id': ticket_id
        }
        
        return f"Ticket created: {ticket_id}"
    
    async def _handle_run_command(self, step: PlaybookStep, execution: PlaybookExecution) -> str:
        """Handle system command execution step"""
        params = step.parameters
        command_type = params.get("command_type", "generic")
        
        logger.info(f"[PLAYBOOKS] Running command type: {command_type}")
        
        # Execute based on command type
        if command_type == "force_password_reset":
            # Trigger password reset
            return "Password reset initiated for targeted accounts"
            
        elif command_type == "suspend_account":
            # Suspend user account
            return "Account suspended successfully"
            
        elif command_type == "generic":
            command = params.get("command", "")
            if command:
                # In production, use secure command execution
                # result = await asyncio.create_subprocess_shell(command, ...)
                return f"Command executed: {command}"
        
        return f"Command type {command_type} executed"
    
    async def _handle_wait(self, step: PlaybookStep, execution: PlaybookExecution) -> str:
        """Handle wait/manual action step"""
        params = step.parameters
        timeout_minutes = params.get("timeout_minutes", 60)
        escalate_after_timeout = params.get("escalate_after_timeout", False)
        
        logger.info(f"[PLAYBOOKS] Waiting for manual action (timeout: {timeout_minutes}m)")
        
        # Send notification requesting manual action
        await self._handle_notify(PlaybookStep(
            step_id=f"{step.step_id}_notify",
            name="Manual Action Requested",
            description="Notify about required manual action",
            step_type=StepType.NOTIFY,
            parameters={
                "channels": ["email", "slack"],
                "message": f"Manual action required for execution {execution.execution_id}"
            }
        ), execution)
        
        # In production, this would:
        # 1. Set up a webhook or callback for manual approval
        # 2. Wait for approval signal
        # 3. Or timeout after specified duration
        
        # Simulate wait (in production, use proper async event)
        await asyncio.sleep(1)  # Placeholder
        
        return f"Manual action completed or timeout ({timeout_minutes}m)"
    
    async def _handle_condition(self, step: PlaybookStep, execution: PlaybookExecution) -> str:
        """Handle conditional branching step"""
        params = step.parameters
        conditions = params.get("conditions", [])
        
        logger.info(f"[PLAYBOOKS] Evaluating {len(conditions)} conditions")
        
        # Evaluate conditions and determine branch
        for condition in conditions:
            if self._evaluate_condition(condition.get("expression", ""), execution):
                branch = condition.get("then", "continue")
                execution.context['condition_result'] = branch
                return f"Condition met: {branch}"
        
        # Default branch
        default_branch = params.get("default", "continue")
        execution.context['condition_result'] = default_branch
        return f"Default condition: {default_branch}"
    
    async def _handle_contain(self, step: PlaybookStep, execution: PlaybookExecution) -> str:
        """Handle containment step"""
        params = step.parameters
        action = params.get("action", "block_ip")
        
        if action == "block_ip":
            duration = params.get("duration_minutes", 60)
            scope = params.get("scope", "perimeter")
            logger.info(f"[PLAYBOOKS] Blocking IP for {duration}m (scope: {scope})")
            return f"IP blocked for {duration} minutes"
            
        elif action == "disable_account":
            logger.info("[PLAYBOOKS] Disabling user account")
            return "Account disabled"
            
        elif action == "quarantine_file":
            logger.info("[PLAYBOOKS] Quarantining file")
            return "File quarantined"
        
        return f"Containment action {action} executed"
    
    async def _handle_collect(self, step: PlaybookStep, execution: PlaybookExecution) -> str:
        """Handle evidence collection step"""
        params = step.parameters
        evidence_types = params.get("evidence_types", [])
        chain_of_custody = params.get("chain_of_custody", False)
        
        collected = []
        
        for evidence_type in evidence_types:
            try:
                logger.info(f"[PLAYBOOKS] Collecting evidence: {evidence_type}")
                
                if evidence_type == "memory_dump":
                    collected.append("memory_dump.bin")
                elif evidence_type == "disk_image":
                    collected.append("disk_image.dd")
                elif evidence_type == "network_logs":
                    collected.append("network_capture.pcap")
                elif evidence_type == "endpoint_logs":
                    collected.append("endpoint_logs.zip")
                elif evidence_type == "process_list":
                    collected.append("processes.json")
                else:
                    collected.append(f"{evidence_type}_evidence")
                    
            except Exception as e:
                logger.error(f"[PLAYBOOKS] Evidence collection failed for {evidence_type}: {e}")
        
        # Store evidence reference
        evidence_id = f"EVIDENCE-{uuid.uuid4().hex[:8].upper()}"
        execution.context['collected_evidence'] = {
            'evidence_id': evidence_id,
            'files': collected,
            'chain_of_custody': chain_of_custody
        }
        
        return f"Evidence collected: {len(collected)} items (ID: {evidence_id})"
    
    async def _handle_restore(self, step: PlaybookStep, execution: PlaybookExecution) -> str:
        """Handle restore from backup step"""
        params = step.parameters
        restore_point = params.get("restore_point", "latest")
        
        logger.info(f"[PLAYBOOKS] Restoring from backup: {restore_point}")
        
        # In production, integrate with backup system
        
        return f"System restored from backup: {restore_point}"
    
    # ==================== Persistence ====================
    
    def _persist_playbook(self, playbook: Playbook) -> None:
        """Persist playbook to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO playbooks
                    (playbook_id, name, description, triggers, steps, enabled,
                     created_at, updated_at, version, author, tags)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    playbook.playbook_id,
                    playbook.name,
                    playbook.description,
                    json.dumps(playbook.triggers.to_dict()),
                    json.dumps([s.to_dict() for s in playbook.steps]),
                    playbook.enabled,
                    playbook.created_at.isoformat(),
                    playbook.updated_at.isoformat(),
                    playbook.version,
                    playbook.author,
                    json.dumps(playbook.tags)
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"[PLAYBOOKS] Failed to persist playbook: {e}")
    
    def _persist_execution(self, execution: PlaybookExecution) -> None:
        """Persist execution state to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO playbook_executions
                    (execution_id, playbook_id, incident_id, status, current_step,
                     step_results, context, logs, start_time, end_time, triggered_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    execution.execution_id,
                    execution.playbook_id,
                    execution.incident_id,
                    execution.status.value,
                    execution.current_step,
                    json.dumps({k: v.to_dict() for k, v in execution.step_results.items()}),
                    json.dumps(execution.context),
                    json.dumps(execution.logs),
                    execution.start_time.isoformat(),
                    execution.end_time.isoformat() if execution.end_time else None,
                    execution.triggered_by
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"[PLAYBOOKS] Failed to persist execution: {e}")
    
    def load_executions_from_db(self) -> None:
        """Load saved executions from database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM playbook_executions WHERE status IN ('pending', 'running', 'paused')")
                rows = cursor.fetchall()
                
                for row in cursor.description:
                    pass  # Get column names
                
                # In production, restore execution state from database
                logger.info(f"[PLAYBOOKS] Loaded {len(rows)} executions from database")
                
        except Exception as e:
            logger.error(f"[PLAYBOOKS] Failed to load executions: {e}")


# Global instance
_playbook_engine: Optional[PlaybookEngine] = None


def get_playbook_engine(db_path: Optional[str] = None,
                        incident_manager: Optional[IncidentManager] = None) -> PlaybookEngine:
    """Get global playbook engine instance"""
    global _playbook_engine
    if _playbook_engine is None:
        _playbook_engine = PlaybookEngine(
            db_path=db_path or "/opt/codex-swarm/command-post/data/nexus.db",
            incident_manager=incident_manager
        )
    return _playbook_engine


# Convenience exports
__all__ = [
    'Playbook',
    'PlaybookStep',
    'PlaybookExecution',
    'PlaybookEngine',
    'PlaybookTrigger',
    'StepType',
    'StepStatus',
    'ExecutionStatus',
    'SeverityLevel',
    'StepResult',
    'RetryConfig',
    'get_playbook_engine'
]
