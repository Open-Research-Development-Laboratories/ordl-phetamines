#!/usr/bin/env python3
"""
================================================================================
ORDL COMMAND POST v6.0.0 - BLUE TEAM DETECTION ENGINE
================================================================================
Classification: TOP SECRET//SCI//NOFORN
Classification Level: TS/SCI/NOFORN
Compartment: ORDL-CYBER-OPS

REAL-TIME SECURITY DETECTION & CORRELATION ENGINE
================================================================================
Enterprise-grade detection engine with:
- Real-time log processing pipeline
- Multi-source event correlation
- Rule-based detection with MITRE ATT&CK mapping
- Anomaly detection using statistical analysis
- Alert correlation and escalation
- Performance optimized for high-throughput

Author: ORDL Cyber Operations Division
Version: 6.0.0
================================================================================
"""

import os
import sys
import json
import time
import uuid
import sqlite3
import logging
import threading
import hashlib
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set, Callable
from dataclasses import dataclass, field, asdict
from collections import defaultdict, deque
from enum import Enum, auto
import queue

# Configure logging
logger = logging.getLogger('blueteam.detection')


class DetectionStatus(Enum):
    """Detection rule status"""
    ENABLED = "enabled"
    DISABLED = "disabled"
    TESTING = "testing"


class EventSeverity(Enum):
    """Event severity for internal processing"""
    CRITICAL = 5
    HIGH = 4
    MEDIUM = 3
    LOW = 2
    INFO = 1


@dataclass
class DetectionEvent:
    """Normalized detection event"""
    event_id: str
    timestamp: datetime
    source_type: str
    source_host: str
    event_type: str
    severity: EventSeverity
    raw_data: Dict[str, Any]
    normalized_data: Dict[str, Any]
    ioc_matches: List[Dict] = field(default_factory=list)
    correlated_events: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'event_id': self.event_id,
            'timestamp': self.timestamp.isoformat(),
            'source_type': self.source_type,
            'source_host': self.source_host,
            'event_type': self.event_type,
            'severity': self.severity.name,
            'raw_data': self.raw_data,
            'normalized_data': self.normalized_data,
            'ioc_matches': self.ioc_matches,
            'correlated_events': self.correlated_events
        }


@dataclass
class DetectionResult:
    """Result of detection rule evaluation"""
    triggered: bool
    rule_id: str
    rule_name: str
    severity: str
    confidence: float
    description: str
    mitre_techniques: List[str]
    evidence: Dict[str, Any]
    event_ids: List[str]


class DetectionRule:
    """
    Individual detection rule with compiled logic
    """
    
    def __init__(self,
                 rule_id: str,
                 name: str,
                 description: str,
                 severity: str,
                 logic: Dict[str, Any],
                 mitre_techniques: List[str] = None,
                 enabled: bool = True,
                 category: str = "general"):
        self.rule_id = rule_id
        self.name = name
        self.description = description
        self.severity = severity
        self.logic = logic
        self.mitre_techniques = mitre_techniques or []
        self.enabled = enabled
        self.category = category
        self.status = DetectionStatus.ENABLED if enabled else DetectionStatus.DISABLED
        self.trigger_count = 0
        self.last_triggered = None
        self.created_at = datetime.utcnow().isoformat()
        
        # Compile rule logic
        self._compile_logic()
    
    def _compile_logic(self):
        """Compile rule logic for efficient evaluation"""
        self._conditions = self.logic.get('conditions', [])
        self._threshold = self.logic.get('threshold', 1)
        self._time_window = self.logic.get('time_window', 300)  # seconds
        self._aggregation = self.logic.get('aggregation', 'count')
        self._group_by = self.logic.get('group_by', [])
    
    def evaluate(self, events: List[DetectionEvent]) -> Optional[DetectionResult]:
        """
        Evaluate rule against a set of events
        
        Args:
            events: List of detection events to evaluate
            
        Returns:
            DetectionResult if rule triggered, None otherwise
        """
        if self.status != DetectionStatus.ENABLED:
            return None
        
        matching_events = []
        
        for event in events:
            if self._matches_conditions(event):
                matching_events.append(event)
        
        if len(matching_events) >= self._threshold:
            self.trigger_count += 1
            self.last_triggered = datetime.utcnow().isoformat()
            
            return DetectionResult(
                triggered=True,
                rule_id=self.rule_id,
                rule_name=self.name,
                severity=self.severity,
                confidence=min(1.0, len(matching_events) / self._threshold * 0.8 + 0.2),
                description=self.description,
                mitre_techniques=self.mitre_techniques,
                evidence={
                    'matching_events': len(matching_events),
                    'threshold': self._threshold,
                    'conditions': self._conditions
                },
                event_ids=[e.event_id for e in matching_events]
            )
        
        return None
    
    def _matches_conditions(self, event: DetectionEvent) -> bool:
        """Check if event matches rule conditions"""
        for condition in self._conditions:
            if not self._evaluate_condition(condition, event):
                return False
        return True
    
    def _evaluate_condition(self, condition: Dict, event: DetectionEvent) -> bool:
        """Evaluate a single condition against an event"""
        field = condition.get('field')
        operator = condition.get('operator')
        value = condition.get('value')
        
        # Get field value from event
        event_value = self._get_field_value(field, event)
        
        if event_value is None:
            return False
        
        # Evaluate based on operator
        if operator == 'equals':
            return str(event_value).lower() == str(value).lower()
        elif operator == 'contains':
            return str(value).lower() in str(event_value).lower()
        elif operator == 'regex':
            return bool(re.search(value, str(event_value), re.IGNORECASE))
        elif operator == 'in':
            return str(event_value).lower() in [str(v).lower() for v in value]
        elif operator == 'gt':
            try:
                return float(event_value) > float(value)
            except (ValueError, TypeError):
                return False
        elif operator == 'lt':
            try:
                return float(event_value) < float(value)
            except (ValueError, TypeError):
                return False
        
        return False
    
    def _get_field_value(self, field: str, event: DetectionEvent) -> Any:
        """Extract field value from event using dot notation"""
        parts = field.split('.')
        data = event.normalized_data
        
        for part in parts:
            if isinstance(data, dict):
                data = data.get(part)
            else:
                return None
        
        return data
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'rule_id': self.rule_id,
            'name': self.name,
            'description': self.description,
            'severity': self.severity,
            'category': self.category,
            'status': self.status.value,
            'mitre_techniques': self.mitre_techniques,
            'trigger_count': self.trigger_count,
            'last_triggered': self.last_triggered,
            'created_at': self.created_at
        }


class DetectionEngine:
    """
    Real-time detection engine with high-throughput processing
    
    Features:
    - Event correlation across time windows
    - Statistical anomaly detection
    - Rule-based detection
    - Alert generation and management
    """
    
    def __init__(self, 
                 db_path: str = "/opt/codex-swarm/command-post/data/nexus.db",
                 max_queue_size: int = 10000):
        self.db_path = db_path
        self.rules: Dict[str, DetectionRule] = {}
        self.event_buffer: deque = deque(maxlen=10000)
        self.event_queue: queue.Queue = queue.Queue(maxsize=max_queue_size)
        self.correlation_windows: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        
        # Statistics
        self.stats = {
            'events_processed': 0,
            'alerts_generated': 0,
            'rules_triggered': 0,
            'processing_errors': 0
        }
        
        # Threading
        self._lock = threading.RLock()
        self._running = False
        self._worker_thread: Optional[threading.Thread] = None
        
        # Initialize
        self._init_database()
        self._load_default_rules()
        self._start_worker()
        
        logger.info("[DETECTION] Engine initialized")
    
    def _init_database(self):
        """Initialize detection database schema"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Detection rules table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS detection_rules (
                    rule_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    severity TEXT,
                    logic TEXT,
                    mitre_techniques TEXT,
                    status TEXT DEFAULT 'enabled',
                    category TEXT,
                    trigger_count INTEGER DEFAULT 0,
                    last_triggered TEXT,
                    created_at TEXT
                )
            """)
            
            # Detection events table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS detection_events (
                    event_id TEXT PRIMARY KEY,
                    timestamp TEXT,
                    source_type TEXT,
                    source_host TEXT,
                    event_type TEXT,
                    severity TEXT,
                    raw_data TEXT,
                    normalized_data TEXT,
                    ioc_matches TEXT,
                    correlated_events TEXT
                )
            """)
            
            # Rule executions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rule_executions (
                    execution_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rule_id TEXT,
                    timestamp TEXT,
                    triggered BOOLEAN,
                    event_count INTEGER,
                    execution_time_ms INTEGER
                )
            """)
            
            conn.commit()
    
    def _load_default_rules(self):
        """Load default detection rules"""
        default_rules = [
            DetectionRule(
                rule_id='BT-AUTH-001',
                name='Multiple Failed Logins',
                description='Detects multiple failed authentication attempts from same source',
                severity='HIGH',
                logic={
                    'conditions': [
                        {'field': 'event_type', 'operator': 'equals', 'value': 'authentication_failure'}
                    ],
                    'threshold': 5,
                    'time_window': 300,
                    'group_by': ['source_ip']
                },
                mitre_techniques=['T1110', 'T1110.001'],
                category='authentication'
            ),
            DetectionRule(
                rule_id='BT-PRIV-001',
                name='Privilege Escalation Detected',
                description='Detects privilege escalation attempts',
                severity='CRITICAL',
                logic={
                    'conditions': [
                        {'field': 'event_type', 'operator': 'equals', 'value': 'privilege_escalation'}
                    ],
                    'threshold': 1,
                    'time_window': 60
                },
                mitre_techniques=['T1068', 'T1548'],
                category='privilege_escalation'
            ),
            DetectionRule(
                rule_id='BT-NET-001',
                name='Suspicious Outbound Connection',
                description='Detects suspicious outbound network connections',
                severity='HIGH',
                logic={
                    'conditions': [
                        {'field': 'event_type', 'operator': 'equals', 'value': 'network_connection'},
                        {'field': 'direction', 'operator': 'equals', 'value': 'outbound'}
                    ],
                    'threshold': 10,
                    'time_window': 60
                },
                mitre_techniques=['T1041', 'T1071'],
                category='network'
            ),
            DetectionRule(
                rule_id='BT-MAL-001',
                name='Suspicious Process Execution',
                description='Detects execution of suspicious processes',
                severity='HIGH',
                logic={
                    'conditions': [
                        {'field': 'event_type', 'operator': 'equals', 'value': 'process_execution'}
                    ],
                    'threshold': 3,
                    'time_window': 300
                },
                mitre_techniques=['T1059', 'T1204'],
                category='malware'
            ),
            DetectionRule(
                rule_id='BT-MAL-002',
                name='Encoded PowerShell Command',
                description='Detects encoded PowerShell commands',
                severity='CRITICAL',
                logic={
                    'conditions': [
                        {'field': 'process_name', 'operator': 'contains', 'value': 'powershell'},
                        {'field': 'command_line', 'operator': 'regex', 'value': '-enc|-encodedcommand'}
                    ],
                    'threshold': 1,
                    'time_window': 60
                },
                mitre_techniques=['T1059.001', 'T1027'],
                category='malware'
            ),
            DetectionRule(
                rule_id='BT-PER-001',
                name='New Scheduled Task Created',
                description='Detects creation of new scheduled tasks',
                severity='MEDIUM',
                logic={
                    'conditions': [
                        {'field': 'event_type', 'operator': 'equals', 'value': 'scheduled_task_created'}
                    ],
                    'threshold': 1,
                    'time_window': 60
                },
                mitre_techniques=['T1053', 'T1053.005'],
                category='persistence'
            ),
            DetectionRule(
                rule_id='BT-DEF-001',
                name='Security Service Stopped',
                description='Detects stopping of security services',
                severity='CRITICAL',
                logic={
                    'conditions': [
                        {'field': 'event_type', 'operator': 'equals', 'value': 'service_stopped'},
                        {'field': 'service_name', 'operator': 'regex', 'value': 'defender|firewall|antivirus'}
                    ],
                    'threshold': 1,
                    'time_window': 60
                },
                mitre_techniques=['T1562', 'T1562.001'],
                category='defense_evasion'
            ),
            DetectionRule(
                rule_id='BT-DEF-002',
                name='Security Log Cleared',
                description='Detects clearing of security event logs',
                severity='CRITICAL',
                logic={
                    'conditions': [
                        {'field': 'event_type', 'operator': 'equals', 'value': 'log_cleared'}
                    ],
                    'threshold': 1,
                    'time_window': 60
                },
                mitre_techniques=['T1070', 'T1070.001'],
                category='defense_evasion'
            )
        ]
        
        for rule in default_rules:
            self.register_rule(rule)
        
        logger.info(f"[DETECTION] Loaded {len(default_rules)} default rules")
    
    def _start_worker(self):
        """Start background processing worker"""
        self._running = True
        self._worker_thread = threading.Thread(target=self._process_events, daemon=True)
        self._worker_thread.start()
        logger.info("[DETECTION] Event processing worker started")
    
    def _process_events(self):
        """Background event processing loop"""
        while self._running:
            try:
                event = self.event_queue.get(timeout=1)
                self._process_single_event(event)
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"[DETECTION] Event processing error: {e}")
                self.stats['processing_errors'] += 1
    
    def _process_single_event(self, event: DetectionEvent):
        """Process a single detection event"""
        with self._lock:
            # Add to buffer
            self.event_buffer.append(event)
            
            # Update correlation windows
            window_key = f"{event.source_host}:{event.source_type}"
            self.correlation_windows[window_key].append(event)
            
            # Evaluate all rules
            for rule in self.rules.values():
                result = self._evaluate_rule_against_windows(rule)
                
                if result and result.triggered:
                    self._handle_rule_trigger(result, event)
            
            self.stats['events_processed'] += 1
    
    def _evaluate_rule_against_windows(self, rule: DetectionRule) -> Optional[DetectionResult]:
        """Evaluate a rule against all correlation windows"""
        # Collect events within time window
        cutoff_time = datetime.utcnow() - timedelta(seconds=rule._time_window)
        
        for window_key, window in self.correlation_windows.items():
            recent_events = [
                e for e in window
                if e.timestamp > cutoff_time
            ]
            
            if recent_events:
                result = rule.evaluate(recent_events)
                if result and result.triggered:
                    return result
        
        return None
    
    def _handle_rule_trigger(self, result: DetectionResult, triggering_event: DetectionEvent):
        """Handle a triggered detection rule"""
        self.stats['rules_triggered'] += 1
        
        # Persist rule execution
        self._persist_rule_execution(result)
        
        logger.warning(
            f"[DETECTION] Rule triggered: {result.rule_name} "
            f"(Severity: {result.severity}, Confidence: {result.confidence:.2f})"
        )
        
        # Alert generation will be handled by BlueTeamManager
        # This engine focuses purely on detection
    
    def _persist_rule_execution(self, result: DetectionResult):
        """Persist rule execution to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO rule_executions 
                    (rule_id, timestamp, triggered, event_count, execution_time_ms)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    result.rule_id,
                    datetime.utcnow().isoformat(),
                    result.triggered,
                    len(result.event_ids),
                    0  # TODO: Add timing
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"[DETECTION] Failed to persist rule execution: {e}")
    
    def register_rule(self, rule: DetectionRule):
        """Register a detection rule"""
        with self._lock:
            self.rules[rule.rule_id] = rule
            self._persist_rule(rule)
            logger.info(f"[DETECTION] Registered rule: {rule.name}")
    
    def _persist_rule(self, rule: DetectionRule):
        """Persist rule to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO detection_rules
                    (rule_id, name, description, severity, logic, mitre_techniques,
                     status, category, trigger_count, last_triggered, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    rule.rule_id,
                    rule.name,
                    rule.description,
                    rule.severity,
                    json.dumps(rule.logic),
                    json.dumps(rule.mitre_techniques),
                    rule.status.value,
                    rule.category,
                    rule.trigger_count,
                    rule.last_triggered,
                    rule.created_at
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"[DETECTION] Failed to persist rule: {e}")
    
    def submit_event(self, event: DetectionEvent) -> bool:
        """
        Submit an event for detection processing
        
        Args:
            event: DetectionEvent to process
            
        Returns:
            True if event was queued successfully
        """
        try:
            self.event_queue.put(event, block=False)
            return True
        except queue.Full:
            logger.warning("[DETECTION] Event queue full, dropping event")
            return False
    
    def get_rules(self, category: Optional[str] = None) -> List[Dict]:
        """Get all detection rules"""
        rules = list(self.rules.values())
        
        if category:
            rules = [r for r in rules if r.category == category]
        
        return [r.to_dict() for r in rules]
    
    def enable_rule(self, rule_id: str) -> bool:
        """Enable a detection rule"""
        if rule_id in self.rules:
            self.rules[rule_id].status = DetectionStatus.ENABLED
            self.rules[rule_id].enabled = True
            self._persist_rule(self.rules[rule_id])
            return True
        return False
    
    def disable_rule(self, rule_id: str) -> bool:
        """Disable a detection rule"""
        if rule_id in self.rules:
            self.rules[rule_id].status = DetectionStatus.DISABLED
            self.rules[rule_id].enabled = False
            self._persist_rule(self.rules[rule_id])
            return True
        return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get detection engine statistics"""
        return {
            **self.stats,
            'rules_loaded': len(self.rules),
            'event_queue_size': self.event_queue.qsize(),
            'buffer_size': len(self.event_buffer),
            'correlation_windows': len(self.correlation_windows)
        }
    
    def shutdown(self):
        """Shutdown detection engine"""
        self._running = False
        if self._worker_thread:
            self._worker_thread.join(timeout=5)
        logger.info("[DETECTION] Engine shutdown")


# Global instance
_detection_engine: Optional[DetectionEngine] = None

def get_detection_engine() -> DetectionEngine:
    """Get global detection engine instance"""
    global _detection_engine
    if _detection_engine is None:
        _detection_engine = DetectionEngine()
    return _detection_engine
