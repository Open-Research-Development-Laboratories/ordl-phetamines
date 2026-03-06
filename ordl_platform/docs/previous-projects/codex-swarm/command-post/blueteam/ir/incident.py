#!/usr/bin/env python3
"""
================================================================================
ORDL COMMAND POST v6.0.0 - BLUE TEAM INCIDENT RESPONSE MANAGEMENT
================================================================================
Classification: TOP SECRET//SCI//NOFORN
Classification Level: TS/SCI/NOFORN
Compartment: ORDL-CYBER-OPS

MILITARY-GRADE INCIDENT RESPONSE MANAGEMENT SYSTEM
================================================================================
Comprehensive incident management for AI operations center:
- Full incident lifecycle management (NIST SP 800-61 compliant)
- Timeline tracking with forensic integrity
- MITRE ATT&CK technique correlation
- IOC and affected asset tracking
- Automated alert correlation
- Search and filter capabilities
- Async database operations

Author: ORDL Cyber Operations Division
Version: 6.0.0
================================================================================
"""

import os
import sys
import json
import uuid
import sqlite3
import logging
import asyncio
import hashlib
from datetime import datetime, timedelta
from enum import Enum, auto
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Callable, Set, Tuple, Union
from collections import defaultdict

# Configure logging
logger = logging.getLogger('blueteam.ir.incident')


class IncidentStatus(Enum):
    """
    NIST SP 800-61 compliant incident lifecycle status.
    
    Status progression:
        NEW → TRIAGE → INVESTIGATING → CONTAINED → ERADICATED → RECOVERED → CLOSED
    """
    NEW = "NEW"                          # Initial detection, unverified
    TRIAGE = "TRIAGE"                    # Initial assessment ongoing
    INVESTIGATING = "INVESTIGATING"      # Active investigation
    CONTAINED = "CONTAINED"              # Threat contained
    ERADICATED = "ERADICATED"            # Threat removed
    RECOVERED = "RECOVERED"              # Systems restored
    CLOSED = "CLOSED"                    # Case closed with documentation


class SeverityLevel(Enum):
    """
    Incident severity levels with military response time requirements.
    
    Response Times:
        CRITICAL: Immediate (15 minutes)
        HIGH: Urgent (1 hour)
        MEDIUM: Standard (4 hours)
        LOW: Routine (24 hours)
    """
    LOW = 1          # Routine response within 24 hours
    MEDIUM = 2       # Standard response within 4 hours
    HIGH = 3         # Urgent response within 1 hour
    CRITICAL = 4     # Immediate response required


class TimelineEventType(Enum):
    """Types of events recorded in incident timeline."""
    STATUS_CHANGE = "status_change"
    ALERT_CORRELATED = "alert_correlated"
    ANALYST_ASSIGNED = "analyst_assigned"
    ANALYST_ACTION = "analyst_action"
    CONTAINMENT_ACTION = "containment_action"
    EVIDENCE_COLLECTED = "evidence_collected"
    IOC_ADDED = "ioc_added"
    ASSET_IDENTIFIED = "asset_identified"
    NOTE_ADDED = "note_added"
    EXTERNAL_NOTIFICATION = "external_notification"
    LESSON_LEARNED = "lesson_learned"


@dataclass
class TimelineEvent:
    """
    Single event in incident timeline with forensic integrity.
    
    Attributes:
        event_id: Unique identifier for this timeline event
        event_type: Type of event occurred
        timestamp: When the event occurred
        actor: Who performed the action (analyst, system, etc.)
        description: Human-readable description
        data: Additional structured data
        hash: Integrity hash for tamper detection
    """
    event_id: str
    event_type: TimelineEventType
    timestamp: datetime
    actor: str
    description: str
    data: Dict[str, Any] = field(default_factory=dict)
    hash: Optional[str] = None
    
    def __post_init__(self):
        """Calculate integrity hash after initialization."""
        if self.hash is None:
            self.hash = self._calculate_hash()
    
    def _calculate_hash(self) -> str:
        """Calculate SHA-256 hash for tamper detection."""
        content = f"{self.event_id}:{self.event_type.value}:{self.timestamp.isoformat()}:{self.actor}:{self.description}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def verify_integrity(self) -> bool:
        """Verify the integrity hash matches current state."""
        return self.hash == self._calculate_hash()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert timeline event to dictionary."""
        return {
            'event_id': self.event_id,
            'event_type': self.event_type.value,
            'timestamp': self.timestamp.isoformat(),
            'actor': self.actor,
            'description': self.description,
            'data': self.data,
            'hash': self.hash,
            'integrity_verified': self.verify_integrity()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TimelineEvent':
        """Create timeline event from dictionary."""
        return cls(
            event_id=data['event_id'],
            event_type=TimelineEventType(data['event_type']),
            timestamp=datetime.fromisoformat(data['timestamp']),
            actor=data['actor'],
            description=data['description'],
            data=data.get('data', {}),
            hash=data.get('hash')
        )


@dataclass
class IndicatorOfCompromise:
    """
    IOC associated with an incident.
    
    Attributes:
        ioc_id: Unique identifier
        ioc_type: Type (IP, domain, hash, etc.)
        value: The actual IOC value
        added_at: When added to incident
        added_by: Analyst who added it
        confidence: Confidence score (0-100)
        context: Additional context about the IOC
    """
    ioc_id: str
    ioc_type: str
    value: str
    added_at: datetime
    added_by: str
    confidence: int = 50
    context: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'ioc_id': self.ioc_id,
            'ioc_type': self.ioc_type,
            'value': self.value,
            'added_at': self.added_at.isoformat(),
            'added_by': self.added_by,
            'confidence': self.confidence,
            'context': self.context
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'IndicatorOfCompromise':
        return cls(
            ioc_id=data['ioc_id'],
            ioc_type=data['ioc_type'],
            value=data['value'],
            added_at=datetime.fromisoformat(data['added_at']),
            added_by=data['added_by'],
            confidence=data.get('confidence', 50),
            context=data.get('context', '')
        )


@dataclass
class AffectedAsset:
    """
    Asset affected by the incident.
    
    Attributes:
        asset_id: Unique identifier
        asset_type: Type (server, workstation, network_device, etc.)
        hostname: Hostname or identifier
        ip_address: IP address
        operating_system: OS information
        criticality: Asset criticality level
        impact_description: How the asset was impacted
        discovered_at: When asset impact was discovered
    """
    asset_id: str
    asset_type: str
    hostname: str
    ip_address: Optional[str] = None
    operating_system: Optional[str] = None
    criticality: str = "medium"
    impact_description: str = ""
    discovered_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'asset_id': self.asset_id,
            'asset_type': self.asset_type,
            'hostname': self.hostname,
            'ip_address': self.ip_address,
            'operating_system': self.operating_system,
            'criticality': self.criticality,
            'impact_description': self.impact_description,
            'discovered_at': self.discovered_at.isoformat() if self.discovered_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AffectedAsset':
        return cls(
            asset_id=data['asset_id'],
            asset_type=data['asset_type'],
            hostname=data['hostname'],
            ip_address=data.get('ip_address'),
            operating_system=data.get('operating_system'),
            criticality=data.get('criticality', 'medium'),
            impact_description=data.get('impact_description', ''),
            discovered_at=datetime.fromisoformat(data['discovered_at']) if data.get('discovered_at') else None
        )


@dataclass
class Alert:
    """
    Simplified alert reference for incident correlation.
    
    Note: This is a local dataclass for IR module use.
    For full alert data, reference the detection engine Alert class.
    """
    alert_id: str
    timestamp: datetime
    severity: str
    title: str
    description: str
    source: str
    rule_id: str
    mitre_techniques: List[str] = field(default_factory=list)
    raw_data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'alert_id': self.alert_id,
            'timestamp': self.timestamp.isoformat(),
            'severity': self.severity,
            'title': self.title,
            'description': self.description,
            'source': self.source,
            'rule_id': self.rule_id,
            'mitre_techniques': self.mitre_techniques,
            'raw_data': self.raw_data
        }


@dataclass
class Incident:
    """
    Full incident representation with complete forensic tracking.
    
    Classification: TOP SECRET//SCI//NOFORN
    
    Attributes:
        incident_id: Unique incident identifier (UUID)
        title: Short incident title
        description: Detailed incident description
        severity: Incident severity level
        status: Current incident status
        alerts: List of correlated alert references
        timeline: Chronological event history
        assigned_analyst: Primary analyst assigned
        assigned_team: Additional team members
        created_at: Incident creation timestamp
        updated_at: Last modification timestamp
        mitre_techniques: Associated MITRE ATT&CK techniques
        iocs: Indicators of compromise
        affected_assets: Impacted systems/assets
        root_cause: Root cause analysis (populated on close)
        resolution: Resolution summary (populated on close)
        lessons_learned: Post-incident lessons
        classification: Information classification
        tags: User-defined tags
    """
    incident_id: str
    title: str
    description: str
    severity: SeverityLevel
    status: IncidentStatus
    alerts: List[Alert] = field(default_factory=list)
    timeline: List[TimelineEvent] = field(default_factory=list)
    assigned_analyst: Optional[str] = None
    assigned_team: List[str] = field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    mitre_techniques: List[str] = field(default_factory=list)
    iocs: List[IndicatorOfCompromise] = field(default_factory=list)
    affected_assets: List[AffectedAsset] = field(default_factory=list)
    root_cause: Optional[str] = None
    resolution: Optional[str] = None
    lessons_learned: Optional[str] = None
    classification: str = "TOP SECRET//SCI//NOFORN"
    tags: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Initialize timestamps if not provided."""
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()
    
    def add_timeline_event(self,
                          event_type: TimelineEventType,
                          actor: str,
                          description: str,
                          data: Optional[Dict[str, Any]] = None) -> TimelineEvent:
        """
        Add a new event to the incident timeline.
        
        Args:
            event_type: Type of event
            actor: Who performed the action
            description: Description of the event
            data: Additional structured data
            
        Returns:
            The created TimelineEvent
        """
        event = TimelineEvent(
            event_id=f"EVT-{uuid.uuid4().hex[:8].upper()}",
            event_type=event_type,
            timestamp=datetime.utcnow(),
            actor=actor,
            description=description,
            data=data or {}
        )
        self.timeline.append(event)
        self.updated_at = datetime.utcnow()
        return event
    
    def add_alert(self, alert: Alert, actor: str = "system") -> None:
        """Add an alert to the incident and record timeline event."""
        self.alerts.append(alert)
        
        # Add timeline event
        self.add_timeline_event(
            event_type=TimelineEventType.ALERT_CORRELATED,
            actor=actor,
            description=f"Alert {alert.alert_id} correlated to incident",
            data={'alert_id': alert.alert_id, 'alert_title': alert.title}
        )
        
        # Merge MITRE techniques
        for technique in alert.mitre_techniques:
            if technique not in self.mitre_techniques:
                self.mitre_techniques.append(technique)
        
        self.updated_at = datetime.utcnow()
    
    def add_ioc(self, ioc: IndicatorOfCompromise) -> None:
        """Add an IOC to the incident."""
        self.iocs.append(ioc)
        self.add_timeline_event(
            event_type=TimelineEventType.IOC_ADDED,
            actor=ioc.added_by,
            description=f"IOC added: {ioc.ioc_type} - {ioc.value}",
            data=ioc.to_dict()
        )
        self.updated_at = datetime.utcnow()
    
    def add_affected_asset(self, asset: AffectedAsset, actor: str = "system") -> None:
        """Add an affected asset to the incident."""
        if asset.discovered_at is None:
            asset.discovered_at = datetime.utcnow()
        self.affected_assets.append(asset)
        self.add_timeline_event(
            event_type=TimelineEventType.ASSET_IDENTIFIED,
            actor=actor,
            description=f"Affected asset identified: {asset.hostname}",
            data=asset.to_dict()
        )
        self.updated_at = datetime.utcnow()
    
    def change_status(self, new_status: IncidentStatus, actor: str, reason: str = "") -> None:
        """Change incident status with timeline tracking."""
        old_status = self.status
        self.status = new_status
        
        self.add_timeline_event(
            event_type=TimelineEventType.STATUS_CHANGE,
            actor=actor,
            description=f"Status changed from {old_status.value} to {new_status.value}",
            data={
                'old_status': old_status.value,
                'new_status': new_status.value,
                'reason': reason
            }
        )
        self.updated_at = datetime.utcnow()
        
        logger.info(f"[INCIDENT] {self.incident_id} status: {old_status.value} -> {new_status.value} by {actor}")
    
    def assign(self, analyst: str, actor: str = "system") -> None:
        """Assign incident to analyst."""
        previous = self.assigned_analyst
        self.assigned_analyst = analyst
        
        if analyst not in self.assigned_team:
            self.assigned_team.append(analyst)
        
        self.add_timeline_event(
            event_type=TimelineEventType.ANALYST_ASSIGNED,
            actor=actor,
            description=f"Incident assigned to {analyst}" + (f" (was {previous})" if previous else ""),
            data={'analyst': analyst, 'previous': previous}
        )
        self.updated_at = datetime.utcnow()
    
    def get_alert_ids(self) -> List[str]:
        """Get list of correlated alert IDs."""
        return [alert.alert_id for alert in self.alerts]
    
    def get_unique_mitre_techniques(self) -> List[str]:
        """Get unique MITRE ATT&CK techniques."""
        return list(set(self.mitre_techniques))
    
    def get_severity_name(self) -> str:
        """Get severity as string name."""
        return self.severity.name
    
    def get_status_name(self) -> str:
        """Get status as string name."""
        return self.status.value
    
    def get_duration(self) -> timedelta:
        """Get incident duration since creation."""
        return datetime.utcnow() - self.created_at
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert incident to dictionary for JSON serialization."""
        return {
            'incident_id': self.incident_id,
            'title': self.title,
            'description': self.description,
            'severity': self.severity.name,
            'severity_value': self.severity.value,
            'status': self.status.value,
            'alerts': [alert.to_dict() for alert in self.alerts],
            'timeline': [event.to_dict() for event in self.timeline],
            'assigned_analyst': self.assigned_analyst,
            'assigned_team': self.assigned_team,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'mitre_techniques': self.mitre_techniques,
            'iocs': [ioc.to_dict() for ioc in self.iocs],
            'affected_assets': [asset.to_dict() for asset in self.affected_assets],
            'root_cause': self.root_cause,
            'resolution': self.resolution,
            'lessons_learned': self.lessons_learned,
            'classification': self.classification,
            'tags': self.tags,
            'duration_seconds': self.get_duration().total_seconds()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Incident':
        """Create incident from dictionary."""
        incident = cls(
            incident_id=data['incident_id'],
            title=data['title'],
            description=data['description'],
            severity=SeverityLevel[data['severity']],
            status=IncidentStatus(data['status']),
            alerts=[Alert(**alert) for alert in data.get('alerts', [])],
            timeline=[TimelineEvent.from_dict(evt) for evt in data.get('timeline', [])],
            assigned_analyst=data.get('assigned_analyst'),
            assigned_team=data.get('assigned_team', []),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else None,
            updated_at=datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else None,
            mitre_techniques=data.get('mitre_techniques', []),
            iocs=[IndicatorOfCompromise.from_dict(ioc) for ioc in data.get('iocs', [])],
            affected_assets=[AffectedAsset.from_dict(asset) for asset in data.get('affected_assets', [])],
            root_cause=data.get('root_cause'),
            resolution=data.get('resolution'),
            lessons_learned=data.get('lessons_learned'),
            classification=data.get('classification', 'TOP SECRET//SCI//NOFORN'),
            tags=data.get('tags', [])
        )
        return incident
    
    def to_json(self) -> str:
        """Serialize incident to JSON string."""
        return json.dumps(self.to_dict(), indent=2, default=str)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Incident':
        """Create incident from JSON string."""
        return cls.from_dict(json.loads(json_str))


class IncidentManager:
    """
    Military-grade incident management interface.
    
    Provides comprehensive incident lifecycle management with:
    - Async database operations
    - Timeline integrity verification
    - MITRE ATT&CK correlation
    - Advanced search and filtering
    - Alert correlation capabilities
    
    Classification: TOP SECRET//SCI//NOFORN
    """
    
    def __init__(self, db_path: str = "/opt/codex-swarm/command-post/blueteam/blueteam.db"):
        """
        Initialize incident manager.
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self._incidents: Dict[str, Incident] = {}
        self._alert_index: Dict[str, str] = {}  # alert_id -> incident_id
        self._lock = asyncio.Lock()
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(db_path) or '.', exist_ok=True)
        
        # Initialize database
        self._init_database()
        
        logger.info(f"[INCIDENT_MANAGER] Initialized with database: {db_path}")
    
    def _init_database(self) -> None:
        """Initialize incident database schema."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Incidents table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ir_incidents (
                    incident_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    severity TEXT NOT NULL,
                    status TEXT NOT NULL,
                    assigned_analyst TEXT,
                    assigned_team TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    mitre_techniques TEXT,
                    root_cause TEXT,
                    resolution TEXT,
                    lessons_learned TEXT,
                    classification TEXT DEFAULT 'TOP SECRET//SCI//NOFORN',
                    tags TEXT,
                    data TEXT
                )
            """)
            
            # Timeline events table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ir_timeline_events (
                    event_id TEXT PRIMARY KEY,
                    incident_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    description TEXT,
                    data TEXT,
                    hash TEXT,
                    FOREIGN KEY (incident_id) REFERENCES ir_incidents(incident_id)
                )
            """)
            
            # Alert correlations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ir_alert_correlations (
                    correlation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    incident_id TEXT NOT NULL,
                    alert_id TEXT NOT NULL,
                    correlated_at TEXT NOT NULL,
                    UNIQUE(incident_id, alert_id),
                    FOREIGN KEY (incident_id) REFERENCES ir_incidents(incident_id)
                )
            """)
            
            # IOCs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ir_iocs (
                    ioc_id TEXT PRIMARY KEY,
                    incident_id TEXT NOT NULL,
                    ioc_type TEXT NOT NULL,
                    value TEXT NOT NULL,
                    added_at TEXT NOT NULL,
                    added_by TEXT,
                    confidence INTEGER,
                    context TEXT,
                    FOREIGN KEY (incident_id) REFERENCES ir_incidents(incident_id)
                )
            """)
            
            # Affected assets table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ir_affected_assets (
                    asset_id TEXT PRIMARY KEY,
                    incident_id TEXT NOT NULL,
                    asset_type TEXT NOT NULL,
                    hostname TEXT NOT NULL,
                    ip_address TEXT,
                    operating_system TEXT,
                    criticality TEXT,
                    impact_description TEXT,
                    discovered_at TEXT,
                    FOREIGN KEY (incident_id) REFERENCES ir_incidents(incident_id)
                )
            """)
            
            # Create indexes for performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ir_status ON ir_incidents(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ir_severity ON ir_incidents(severity)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ir_analyst ON ir_incidents(assigned_analyst)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ir_created ON ir_incidents(created_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ir_updated ON ir_incidents(updated_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ir_alert_corr ON ir_alert_correlations(alert_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ir_timeline_incident ON ir_timeline_events(incident_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ir_ioc_value ON ir_iocs(value)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ir_asset_hostname ON ir_affected_assets(hostname)")
            
            conn.commit()
        
        logger.info("[INCIDENT_MANAGER] Database schema initialized")
    
    # ==================== INCIDENT CRUD OPERATIONS ====================
    
    async def create_incident(self,
                             title: str,
                             description: str,
                             severity: SeverityLevel,
                             source_alert: Optional[Alert] = None,
                             mitre_techniques: Optional[List[str]] = None,
                             actor: str = "system") -> Incident:
        """
        Create a new incident from alert or manual entry.
        
        Args:
            title: Incident title
            description: Incident description
            severity: Incident severity level
            source_alert: Optional alert that triggered the incident
            mitre_techniques: Associated MITRE ATT&CK techniques
            actor: Who created the incident
            
        Returns:
            The created Incident object
        """
        incident_id = f"INC-{uuid.uuid4().hex[:12].upper()}"
        
        incident = Incident(
            incident_id=incident_id,
            title=title,
            description=description,
            severity=severity,
            status=IncidentStatus.NEW,
            mitre_techniques=mitre_techniques or [],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Add source alert if provided
        if source_alert:
            incident.add_alert(source_alert, actor)
            for technique in source_alert.mitre_techniques:
                if technique not in incident.mitre_techniques:
                    incident.mitre_techniques.append(technique)
        
        # Add creation timeline event
        incident.add_timeline_event(
            event_type=TimelineEventType.STATUS_CHANGE,
            actor=actor,
            description=f"Incident created from {source_alert.alert_id if source_alert else 'manual entry'}",
            data={'source': 'alert' if source_alert else 'manual'}
        )
        
        async with self._lock:
            self._incidents[incident_id] = incident
            
            if source_alert:
                self._alert_index[source_alert.alert_id] = incident_id
            
            # Persist to database
            await self._persist_incident(incident)
        
        logger.info(f"[INCIDENT_MANAGER] Created incident {incident_id}: {title}")
        return incident
    
    async def create_incident_from_detection_alert(self,
                                                    detection_alert: Any,
                                                    actor: str = "system") -> Incident:
        """
        Create incident from detection engine Alert object.
        
        Args:
            detection_alert: Alert object from detection engine
            actor: Who created the incident
            
        Returns:
            The created Incident object
        """
        # Convert detection alert to IR alert
        ir_alert = Alert(
            alert_id=detection_alert.alert_id,
            timestamp=detection_alert.timestamp,
            severity=detection_alert.severity.value if hasattr(detection_alert.severity, 'value') else str(detection_alert.severity),
            title=detection_alert.title,
            description=detection_alert.description,
            source=detection_alert.source,
            rule_id=detection_alert.rule_id,
            mitre_techniques=detection_alert.mitre_techniques,
            raw_data=detection_alert.raw_data
        )
        
        # Map detection severity to incident severity
        severity_map = {
            'CRITICAL': SeverityLevel.CRITICAL,
            'HIGH': SeverityLevel.HIGH,
            'MEDIUM': SeverityLevel.MEDIUM,
            'LOW': SeverityLevel.LOW,
            'INFO': SeverityLevel.LOW
        }
        severity = severity_map.get(ir_alert.severity, SeverityLevel.MEDIUM)
        
        return await self.create_incident(
            title=f"Incident: {ir_alert.title}",
            description=ir_alert.description,
            severity=severity,
            source_alert=ir_alert,
            mitre_techniques=ir_alert.mitre_techniques,
            actor=actor
        )
    
    async def get_incident(self, incident_id: str) -> Optional[Incident]:
        """
        Retrieve incident by ID.
        
        Args:
            incident_id: Incident identifier
            
        Returns:
            Incident object or None if not found
        """
        async with self._lock:
            # Check memory cache first
            if incident_id in self._incidents:
                return self._incidents[incident_id]
            
            # Load from database
            incident = await self._load_incident(incident_id)
            if incident:
                self._incidents[incident_id] = incident
            return incident
    
    async def update_incident(self,
                             incident_id: str,
                             title: Optional[str] = None,
                             description: Optional[str] = None,
                             actor: str = "system") -> Optional[Incident]:
        """
        Update incident fields.
        
        Args:
            incident_id: Incident identifier
            title: New title (optional)
            description: New description (optional)
            actor: Who made the update
            
        Returns:
            Updated Incident or None if not found
        """
        async with self._lock:
            incident = self._incidents.get(incident_id)
            if not incident:
                incident = await self._load_incident(incident_id)
                if not incident:
                    return None
            
            updates = []
            if title and title != incident.title:
                incident.title = title
                updates.append('title')
            
            if description and description != incident.description:
                incident.description = description
                updates.append('description')
            
            if updates:
                incident.updated_at = datetime.utcnow()
                incident.add_timeline_event(
                    event_type=TimelineEventType.ANALYST_ACTION,
                    actor=actor,
                    description=f"Updated fields: {', '.join(updates)}"
                )
                await self._persist_incident(incident)
                self._incidents[incident_id] = incident
                logger.info(f"[INCIDENT_MANAGER] Updated incident {incident_id}: {updates}")
        
        return incident
    
    async def add_alert_to_incident(self,
                                    incident_id: str,
                                    alert: Alert,
                                    actor: str = "system") -> bool:
        """
        Correlate an alert to an existing incident.
        
        Args:
            incident_id: Target incident
            alert: Alert to correlate
            actor: Who performed the correlation
            
        Returns:
            True if successful, False if incident not found
        """
        async with self._lock:
            incident = self._incidents.get(incident_id)
            if not incident:
                incident = await self._load_incident(incident_id)
                if not incident:
                    return False
            
            incident.add_alert(alert, actor)
            self._alert_index[alert.alert_id] = incident_id
            
            await self._persist_incident(incident)
            await self._persist_alert_correlation(incident_id, alert)
            
            self._incidents[incident_id] = incident
            
            logger.info(f"[INCIDENT_MANAGER] Added alert {alert.alert_id} to incident {incident_id}")
            return True
    
    async def assign_incident(self,
                             incident_id: str,
                             analyst: str,
                             actor: str = "system") -> bool:
        """
        Assign incident to analyst.
        
        Args:
            incident_id: Incident identifier
            analyst: Analyst identifier
            actor: Who performed the assignment
            
        Returns:
            True if successful, False if incident not found
        """
        async with self._lock:
            incident = self._incidents.get(incident_id)
            if not incident:
                incident = await self._load_incident(incident_id)
                if not incident:
                    return False
            
            incident.assign(analyst, actor)
            
            # Update status if NEW
            if incident.status == IncidentStatus.NEW:
                incident.change_status(IncidentStatus.TRIAGE, actor, "Analyst assigned")
            
            await self._persist_incident(incident)
            self._incidents[incident_id] = incident
            
            logger.info(f"[INCIDENT_MANAGER] Assigned incident {incident_id} to {analyst}")
            return True
    
    async def change_status(self,
                           incident_id: str,
                           new_status: IncidentStatus,
                           actor: str,
                           reason: str = "") -> bool:
        """
        Update incident lifecycle status.
        
        Args:
            incident_id: Incident identifier
            new_status: New status value
            actor: Who changed the status
            reason: Reason for status change
            
        Returns:
            True if successful, False if incident not found
        """
        async with self._lock:
            incident = self._incidents.get(incident_id)
            if not incident:
                incident = await self._load_incident(incident_id)
                if not incident:
                    return False
            
            incident.change_status(new_status, actor, reason)
            await self._persist_incident(incident)
            self._incidents[incident_id] = incident
            
            return True
    
    async def close_incident(self,
                            incident_id: str,
                            resolution: str,
                            root_cause: Optional[str] = None,
                            lessons_learned: Optional[str] = None,
                            actor: str = "system") -> bool:
        """
        Close incident with resolution documentation.
        
        Args:
            incident_id: Incident identifier
            resolution: Resolution summary
            root_cause: Root cause analysis
            lessons_learned: Lessons learned documentation
            actor: Who closed the incident
            
        Returns:
            True if successful, False if incident not found
        """
        async with self._lock:
            incident = self._incidents.get(incident_id)
            if not incident:
                incident = await self._load_incident(incident_id)
                if not incident:
                    return False
            
            incident.resolution = resolution
            incident.root_cause = root_cause
            incident.lessons_learned = lessons_learned
            
            incident.change_status(IncidentStatus.CLOSED, actor, "Incident resolved")
            
            incident.add_timeline_event(
                event_type=TimelineEventType.LESSON_LEARNED,
                actor=actor,
                description="Incident closed with resolution documentation",
                data={
                    'resolution': resolution,
                    'root_cause': root_cause,
                    'lessons_learned': lessons_learned
                }
            )
            
            await self._persist_incident(incident)
            self._incidents[incident_id] = incident
            
            logger.info(f"[INCIDENT_MANAGER] Closed incident {incident_id}")
            return True
    
    # ==================== LIST & SEARCH OPERATIONS ====================
    
    async def list_incidents(self,
                            status: Optional[Union[IncidentStatus, List[IncidentStatus]]] = None,
                            severity: Optional[Union[SeverityLevel, List[SeverityLevel]]] = None,
                            assignee: Optional[str] = None,
                            since: Optional[datetime] = None,
                            until: Optional[datetime] = None,
                            technique: Optional[str] = None,
                            limit: int = 100,
                            offset: int = 0) -> List[Incident]:
        """
        List incidents with filtering capabilities.
        
        Args:
            status: Filter by status (single or list)
            severity: Filter by severity (single or list)
            assignee: Filter by assigned analyst
            since: Filter incidents created after this time
            until: Filter incidents created before this time
            technique: Filter by MITRE ATT&CK technique
            limit: Maximum number of results
            offset: Pagination offset
            
        Returns:
            List of matching incidents
        """
        async with self._lock:
            # Build query
            query = "SELECT incident_id FROM ir_incidents WHERE 1=1"
            params = []
            
            if status:
                if isinstance(status, list):
                    placeholders = ','.join('?' * len(status))
                    query += f" AND status IN ({placeholders})"
                    params.extend([s.value for s in status])
                else:
                    query += " AND status = ?"
                    params.append(status.value)
            
            if severity:
                if isinstance(severity, list):
                    placeholders = ','.join('?' * len(severity))
                    query += f" AND severity IN ({placeholders})"
                    params.extend([s.name for s in severity])
                else:
                    query += " AND severity = ?"
                    params.append(severity.name)
            
            if assignee:
                query += " AND assigned_analyst = ?"
                params.append(assignee)
            
            if since:
                query += " AND created_at >= ?"
                params.append(since.isoformat())
            
            if until:
                query += " AND created_at <= ?"
                params.append(until.isoformat())
            
            if technique:
                query += " AND mitre_techniques LIKE ?"
                params.append(f'%"{technique}"%')
            
            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            # Execute query
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                incident_ids = [row[0] for row in cursor.fetchall()]
            
            # Load incidents
            incidents = []
            for inc_id in incident_ids:
                incident = self._incidents.get(inc_id)
                if not incident:
                    incident = await self._load_incident(inc_id)
                    if incident:
                        self._incidents[inc_id] = incident
                if incident:
                    incidents.append(incident)
            
            return incidents
    
    async def get_incidents_by_status(self, status: IncidentStatus) -> List[Incident]:
        """Get all incidents with specific status."""
        return await self.list_incidents(status=status)
    
    async def get_incidents_by_severity(self, severity: SeverityLevel) -> List[Incident]:
        """Get all incidents with specific severity."""
        return await self.list_incidents(severity=severity)
    
    async def get_incidents_by_assignee(self, analyst: str) -> List[Incident]:
        """Get all incidents assigned to specific analyst."""
        return await self.list_incidents(assignee=analyst)
    
    async def get_incidents_by_technique(self, technique: str) -> List[Incident]:
        """Get all incidents with specific MITRE ATT&CK technique."""
        return await self.list_incidents(technique=technique)
    
    async def get_incidents_by_timerange(self,
                                        since: datetime,
                                        until: Optional[datetime] = None) -> List[Incident]:
        """Get incidents created within time range."""
        return await self.list_incidents(since=since, until=until)
    
    async def find_incident_by_alert(self, alert_id: str) -> Optional[Incident]:
        """
        Find incident by associated alert ID.
        
        Args:
            alert_id: Alert identifier
            
        Returns:
            Associated Incident or None
        """
        async with self._lock:
            # Check index
            incident_id = self._alert_index.get(alert_id)
            if incident_id:
                return self._incidents.get(incident_id) or await self._load_incident(incident_id)
            
            # Query database
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT incident_id FROM ir_alert_correlations WHERE alert_id = ?",
                    (alert_id,)
                )
                row = cursor.fetchone()
                if row:
                    return await self.get_incident(row[0])
            
            return None
    
    async def get_open_incidents(self) -> List[Incident]:
        """Get all non-closed incidents."""
        return await self.list_incidents(
            status=[s for s in IncidentStatus if s != IncidentStatus.CLOSED]
        )
    
    async def get_critical_incidents(self) -> List[Incident]:
        """Get all critical severity incidents."""
        return await self.list_incidents(severity=SeverityLevel.CRITICAL)
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get incident statistics."""
        async with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Total incidents
                cursor.execute("SELECT COUNT(*) FROM ir_incidents")
                total = cursor.fetchone()[0]
                
                # By status
                cursor.execute(
                    "SELECT status, COUNT(*) FROM ir_incidents GROUP BY status"
                )
                by_status = {row[0]: row[1] for row in cursor.fetchall()}
                
                # By severity
                cursor.execute(
                    "SELECT severity, COUNT(*) FROM ir_incidents GROUP BY severity"
                )
                by_severity = {row[0]: row[1] for row in cursor.fetchall()}
                
                # Recent (last 24 hours)
                since = (datetime.utcnow() - timedelta(hours=24)).isoformat()
                cursor.execute(
                    "SELECT COUNT(*) FROM ir_incidents WHERE created_at >= ?",
                    (since,)
                )
                recent = cursor.fetchone()[0]
                
                return {
                    'total_incidents': total,
                    'by_status': by_status,
                    'by_severity': by_severity,
                    'recent_24h': recent
                }
    
    # ==================== UTILITY OPERATIONS ====================
    
    async def add_ioc_to_incident(self,
                                  incident_id: str,
                                  ioc_type: str,
                                  value: str,
                                  added_by: str,
                                  confidence: int = 50,
                                  context: str = "") -> bool:
        """
        Add IOC to incident.
        
        Args:
            incident_id: Target incident
            ioc_type: Type of IOC (IP, domain, hash, etc.)
            value: IOC value
            added_by: Analyst adding the IOC
            confidence: Confidence score (0-100)
            context: Additional context
            
        Returns:
            True if successful, False if incident not found
        """
        async with self._lock:
            incident = self._incidents.get(incident_id)
            if not incident:
                incident = await self._load_incident(incident_id)
                if not incident:
                    return False
            
            ioc = IndicatorOfCompromise(
                ioc_id=f"IOC-{uuid.uuid4().hex[:8].upper()}",
                ioc_type=ioc_type,
                value=value,
                added_at=datetime.utcnow(),
                added_by=added_by,
                confidence=confidence,
                context=context
            )
            
            incident.add_ioc(ioc)
            await self._persist_incident(incident)
            await self._persist_ioc(incident_id, ioc)
            
            self._incidents[incident_id] = incident
            return True
    
    async def add_affected_asset(self,
                                 incident_id: str,
                                 asset_type: str,
                                 hostname: str,
                                 ip_address: Optional[str] = None,
                                 operating_system: Optional[str] = None,
                                 criticality: str = "medium",
                                 impact_description: str = "",
                                 actor: str = "system") -> bool:
        """
        Add affected asset to incident.
        
        Args:
            incident_id: Target incident
            asset_type: Type of asset
            hostname: Hostname/identifier
            ip_address: IP address
            operating_system: OS information
            criticality: Asset criticality
            impact_description: Impact description
            actor: Who identified the asset
            
        Returns:
            True if successful, False if incident not found
        """
        async with self._lock:
            incident = self._incidents.get(incident_id)
            if not incident:
                incident = await self._load_incident(incident_id)
                if not incident:
                    return False
            
            asset = AffectedAsset(
                asset_id=f"AST-{uuid.uuid4().hex[:8].upper()}",
                asset_type=asset_type,
                hostname=hostname,
                ip_address=ip_address,
                operating_system=operating_system,
                criticality=criticality,
                impact_description=impact_description
            )
            
            incident.add_affected_asset(asset, actor)
            await self._persist_incident(incident)
            await self._persist_asset(incident_id, asset)
            
            self._incidents[incident_id] = incident
            return True
    
    async def add_note(self,
                      incident_id: str,
                      note: str,
                      actor: str) -> bool:
        """Add analyst note to incident timeline."""
        async with self._lock:
            incident = self._incidents.get(incident_id)
            if not incident:
                incident = await self._load_incident(incident_id)
                if not incident:
                    return False
            
            incident.add_timeline_event(
                event_type=TimelineEventType.NOTE_ADDED,
                actor=actor,
                description=note
            )
            
            await self._persist_incident(incident)
            self._incidents[incident_id] = incident
            return True
    
    # ==================== DATABASE PERSISTENCE ====================
    
    async def _persist_incident(self, incident: Incident) -> None:
        """Persist incident to database."""
        def _persist():
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO ir_incidents
                    (incident_id, title, description, severity, status, assigned_analyst,
                     assigned_team, created_at, updated_at, mitre_techniques, root_cause,
                     resolution, lessons_learned, classification, tags, data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    incident.incident_id,
                    incident.title,
                    incident.description,
                    incident.severity.name,
                    incident.status.value,
                    incident.assigned_analyst,
                    json.dumps(incident.assigned_team),
                    incident.created_at.isoformat(),
                    incident.updated_at.isoformat(),
                    json.dumps(incident.mitre_techniques),
                    incident.root_cause,
                    incident.resolution,
                    incident.lessons_learned,
                    incident.classification,
                    json.dumps(incident.tags),
                    json.dumps(incident.to_dict())
                ))
                conn.commit()
        
        # Run in thread pool for async
        await asyncio.get_event_loop().run_in_executor(None, _persist)
    
    async def _persist_alert_correlation(self, incident_id: str, alert: Alert) -> None:
        """Persist alert correlation to database."""
        def _persist():
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR IGNORE INTO ir_alert_correlations
                    (incident_id, alert_id, correlated_at)
                    VALUES (?, ?, ?)
                """, (
                    incident_id,
                    alert.alert_id,
                    datetime.utcnow().isoformat()
                ))
                conn.commit()
        
        await asyncio.get_event_loop().run_in_executor(None, _persist)
    
    async def _persist_ioc(self, incident_id: str, ioc: IndicatorOfCompromise) -> None:
        """Persist IOC to database."""
        def _persist():
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO ir_iocs
                    (ioc_id, incident_id, ioc_type, value, added_at, added_by, confidence, context)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    ioc.ioc_id,
                    incident_id,
                    ioc.ioc_type,
                    ioc.value,
                    ioc.added_at.isoformat(),
                    ioc.added_by,
                    ioc.confidence,
                    ioc.context
                ))
                conn.commit()
        
        await asyncio.get_event_loop().run_in_executor(None, _persist)
    
    async def _persist_asset(self, incident_id: str, asset: AffectedAsset) -> None:
        """Persist affected asset to database."""
        def _persist():
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO ir_affected_assets
                    (asset_id, incident_id, asset_type, hostname, ip_address,
                     operating_system, criticality, impact_description, discovered_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    asset.asset_id,
                    incident_id,
                    asset.asset_type,
                    asset.hostname,
                    asset.ip_address,
                    asset.operating_system,
                    asset.criticality,
                    asset.impact_description,
                    asset.discovered_at.isoformat() if asset.discovered_at else None
                ))
                conn.commit()
        
        await asyncio.get_event_loop().run_in_executor(None, _persist)
    
    async def _load_incident(self, incident_id: str) -> Optional[Incident]:
        """Load incident from database."""
        def _load():
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT data FROM ir_incidents WHERE incident_id = ?",
                    (incident_id,)
                )
                row = cursor.fetchone()
                if row and row[0]:
                    return Incident.from_dict(json.loads(row[0]))
                return None
        
        return await asyncio.get_event_loop().run_in_executor(None, _load)
    
    # ==================== IMPORT/EXPORT ====================
    
    async def export_incident(self, incident_id: str, format: str = "json") -> Optional[str]:
        """
        Export incident in specified format.
        
        Args:
            incident_id: Incident to export
            format: Export format (json, stix)
            
        Returns:
            Exported data as string or None if not found
        """
        incident = await self.get_incident(incident_id)
        if not incident:
            return None
        
        if format.lower() == "json":
            return incident.to_json()
        elif format.lower() == "stix":
            # Simplified STIX 2.1 representation
            return json.dumps({
                "type": "incident",
                "spec_version": "2.1",
                "id": f"incident--{incident.incident_id.lower()}",
                "created": incident.created_at.isoformat(),
                "modified": incident.updated_at.isoformat(),
                "name": incident.title,
                "description": incident.description,
                "labels": [incident.severity.name, incident.status.value],
                "external_references": [
                    {"mitre_technique": tech} for tech in incident.mitre_techniques
                ]
            }, indent=2)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    async def import_incident(self, data: str, format: str = "json") -> Incident:
        """
        Import incident from serialized data.
        
        Args:
            data: Serialized incident data
            format: Import format (json)
            
        Returns:
            Imported Incident object
        """
        if format.lower() == "json":
            incident = Incident.from_json(data)
            # Generate new ID to avoid conflicts
            incident.incident_id = f"INC-{uuid.uuid4().hex[:12].upper()}"
            incident.created_at = datetime.utcnow()
            incident.updated_at = datetime.utcnow()
            
            async with self._lock:
                self._incidents[incident.incident_id] = incident
                await self._persist_incident(incident)
            
            return incident
        else:
            raise ValueError(f"Unsupported format: {format}")


# Global instance for singleton pattern
_incident_manager: Optional[IncidentManager] = None


def get_incident_manager(db_path: str = "/opt/codex-swarm/command-post/blueteam/blueteam.db") -> IncidentManager:
    """
    Get global incident manager instance (singleton).
    
    Args:
        db_path: Path to SQLite database
        
    Returns:
        IncidentManager instance
    """
    global _incident_manager
    if _incident_manager is None:
        _incident_manager = IncidentManager(db_path)
    return _incident_manager


def reset_incident_manager() -> None:
    """Reset global incident manager instance."""
    global _incident_manager
    _incident_manager = None


# Export public API
__all__ = [
    # Enums
    'IncidentStatus',
    'SeverityLevel',
    'TimelineEventType',
    
    # Data classes
    'TimelineEvent',
    'IndicatorOfCompromise',
    'AffectedAsset',
    'Alert',
    'Incident',
    
    # Manager
    'IncidentManager',
    'get_incident_manager',
    'reset_incident_manager'
]
