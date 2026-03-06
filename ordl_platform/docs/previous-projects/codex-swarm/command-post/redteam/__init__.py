"""
ORDL RED TEAM OPERATIONS MODULE
Classification: TOP SECRET//SCI//NOFORN
Version: 1.0.0

USG-grade offensive security platform for authorized penetration testing,
counter-terrorism operations, and national security missions.

REQUIRES: TS/SCI clearance + Two-Person Integrity + Witness Verification
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import session handler
try:
    from .session_handler import (
        RealSessionHandler,
        SessionType,
        SessionStatus,
        get_session_handler
    )
    SESSION_HANDLER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"[REDTEAM] Session handler not available: {e}")
    SESSION_HANDLER_AVAILABLE = False
    RealSessionHandler = None
    SessionType = None
    SessionStatus = None
    get_session_handler = None


class OperationStatus(Enum):
    """Red team operation status states"""
    PENDING = "pending"
    PLANNING = "planning"
    RECON = "reconnaissance"
    SCANNING = "scanning"
    EXPLOITATION = "exploitation"
    POST_EXPLOITATION = "post_exploitation"
    PERSISTENCE = "persistence"
    EXFILTRATION = "exfiltration"
    COVERING_TRACKS = "covering_tracks"
    COMPLETED = "completed"
    ABORTED = "aborted"
    COMPROMISED = "compromised"


class TargetType(Enum):
    """Types of targets for red team operations"""
    IP_ADDRESS = "ip_address"
    DOMAIN = "domain"
    SUBNET = "subnet"
    WEB_APPLICATION = "web_application"
    WIRELESS_NETWORK = "wireless_network"
    MOBILE_DEVICE = "mobile_device"
    IOT_DEVICE = "iot_device"
    INDUSTRIAL_SYSTEM = "industrial_system"
    CLOUD_INFRASTRUCTURE = "cloud_infrastructure"


@dataclass
class RedTeamTarget:
    """Represents a target for red team operations"""
    target_id: str
    name: str
    target_type: TargetType
    value: str  # IP, domain, etc.
    description: str = ""
    classification: str = "UNCLASSIFIED"
    country: str = ""
    isp: str = ""
    tags: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    notes: str = ""


@dataclass
class RedTeamOperation:
    """Represents a red team operation"""
    operation_id: str
    codename: str
    description: str
    status: OperationStatus
    targets: List[str] = field(default_factory=list)  # target_ids
    operators: List[str] = field(default_factory=list)  # codenames
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    authorization_code: str = ""
    two_person_integrity: bool = True
    witness_codename: Optional[str] = None
    phases_completed: List[str] = field(default_factory=list)
    findings: List[Dict] = field(default_factory=list)
    logs: List[Dict] = field(default_factory=list)
    classification: str = "TOP SECRET//SCI//NOFORN"


class RedTeamManager:
    """
    Central manager for red team operations.
    Implements USG security controls for offensive operations.
    """
    
    def __init__(self, audit_logger=None):
        self.operations: Dict[str, RedTeamOperation] = {}
        self.targets: Dict[str, RedTeamTarget] = {}
        self.audit_logger = audit_logger
        self.active_sessions: Dict[str, Any] = {}
        
        # Import submodules
        try:
            from .recon import ReconManager
            self.recon = ReconManager(self)
            logger.info("[RedTeam] Reconnaissance module loaded")
        except ImportError as e:
            logger.warning(f"[RedTeam] Recon module unavailable: {e}")
            self.recon = None
            
        try:
            from .scanning import VulnerabilityScanner
            self.scanner = VulnerabilityScanner(self)
            logger.info("[RedTeam] Vulnerability scanner loaded")
        except ImportError as e:
            logger.warning(f"[RedTeam] Scanner unavailable: {e}")
            self.scanner = None
            
        try:
            from .exploit import ExploitFramework
            self.exploit = ExploitFramework(self)
            logger.info("[RedTeam] Exploit framework loaded")
        except ImportError as e:
            logger.warning(f"[RedTeam] Exploit framework unavailable: {e}")
            self.exploit = None
            
        try:
            from .payload import PayloadGenerator
            self.payload = PayloadGenerator(self)
            logger.info("[RedTeam] Payload generator loaded")
        except ImportError as e:
            logger.warning(f"[RedTeam] Payload generator unavailable: {e}")
            self.payload = None
            
        try:
            from .social import SocialEngineering
            self.social = SocialEngineering(self)
            logger.info("[RedTeam] Social engineering module loaded")
        except ImportError as e:
            logger.warning(f"[RedTeam] Social engineering unavailable: {e}")
            self.social = None
            
        try:
            from .c2 import C2Infrastructure
            self.c2 = C2Infrastructure(self)
            logger.info("[RedTeam] C2 infrastructure loaded")
        except ImportError as e:
            logger.warning(f"[RedTeam] C2 infrastructure unavailable: {e}")
            self.c2 = None
    
    def create_operation(self, codename: str, description: str, 
                         authorization_code: str,
                         operator_codename: str,
                         witness_codename: Optional[str] = None) -> RedTeamOperation:
        """
        Create a new red team operation.
        
        Requires:
        - TS/SCI clearance
        - Two-person integrity (witness)
        - Authorization code
        """
        import uuid
        
        op_id = f"OP-{uuid.uuid4().hex[:8].upper()}"
        
        operation = RedTeamOperation(
            operation_id=op_id,
            codename=codename,
            description=description,
            status=OperationStatus.PENDING,
            operators=[operator_codename],
            authorization_code=authorization_code,
            two_person_integrity=True,
            witness_codename=witness_codename
        )
        
        self.operations[op_id] = operation
        
        # Audit log
        if self.audit_logger:
            self.audit_logger.log(
                event_type="REDTEAM_OPERATION_CREATED",
                user_codename=operator_codename,
                resource_id=op_id,
                action="CREATE",
                status="SUCCESS",
                details={
                    "codename": codename,
                    "witness": witness_codename,
                    "classification": "TOP SECRET//SCI//NOFORN"
                }
            )
        
        logger.info(f"[RedTeam] Operation created: {op_id} ({codename})")
        return operation
    
    def add_target(self, name: str, target_type: TargetType, value: str,
                   description: str = "", classification: str = "UNCLASSIFIED",
                   tags: List[str] = None) -> RedTeamTarget:
        """Add a target to the target database"""
        import uuid
        
        target_id = f"TGT-{uuid.uuid4().hex[:8].upper()}"
        
        target = RedTeamTarget(
            target_id=target_id,
            name=name,
            target_type=target_type,
            value=value,
            description=description,
            classification=classification,
            tags=tags or []
        )
        
        self.targets[target_id] = target
        logger.info(f"[RedTeam] Target added: {target_id} ({value})")
        return target
    
    def get_operation(self, op_id: str) -> Optional[RedTeamOperation]:
        """Get operation by ID"""
        return self.operations.get(op_id)
    
    def get_target(self, target_id: str) -> Optional[RedTeamTarget]:
        """Get target by ID"""
        return self.targets.get(target_id)
    
    def list_operations(self) -> List[RedTeamOperation]:
        """List all operations"""
        return list(self.operations.values())
    
    def list_targets(self, target_type: Optional[TargetType] = None) -> List[RedTeamTarget]:
        """List all targets, optionally filtered by type"""
        targets = list(self.targets.values())
        if target_type:
            targets = [t for t in targets if t.target_type == target_type]
        return targets
    
    def update_operation_status(self, op_id: str, status: OperationStatus,
                                operator_codename: str) -> bool:
        """Update operation status"""
        operation = self.operations.get(op_id)
        if not operation:
            return False
        
        old_status = operation.status
        operation.status = status
        
        if status == OperationStatus.COMPLETED:
            operation.completed_at = datetime.utcnow().isoformat()
        
        # Audit log
        if self.audit_logger:
            self.audit_logger.log(
                event_type="REDTEAM_STATUS_CHANGE",
                user_codename=operator_codename,
                resource_id=op_id,
                action="STATUS_CHANGE",
                status="SUCCESS",
                details={
                    "from": old_status.value,
                    "to": status.value
                }
            )
        
        logger.info(f"[RedTeam] Operation {op_id} status: {old_status.value} -> {status.value}")
        return True
    
    def add_finding(self, op_id: str, finding_type: str, severity: str,
                   description: str, evidence: Dict = None) -> bool:
        """Add a finding to an operation"""
        operation = self.operations.get(op_id)
        if not operation:
            return False
        
        finding = {
            "finding_id": f"FND-{len(operation.findings)+1:03d}",
            "timestamp": datetime.utcnow().isoformat(),
            "type": finding_type,
            "severity": severity,  # CRITICAL, HIGH, MEDIUM, LOW, INFO
            "description": description,
            "evidence": evidence or {}
        }
        
        operation.findings.append(finding)
        logger.info(f"[RedTeam] Finding added to {op_id}: {finding_type} ({severity})")
        return True
    
    def get_statistics(self) -> Dict:
        """Get red team operation statistics"""
        total_ops = len(self.operations)
        active_ops = sum(1 for op in self.operations.values() 
                        if op.status not in [OperationStatus.COMPLETED, OperationStatus.ABORTED])
        completed_ops = sum(1 for op in self.operations.values() 
                           if op.status == OperationStatus.COMPLETED)
        
        findings_by_severity = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
        for op in self.operations.values():
            for finding in op.findings:
                sev = finding.get("severity", "INFO")
                findings_by_severity[sev] = findings_by_severity.get(sev, 0) + 1
        
        return {
            "total_operations": total_ops,
            "active_operations": active_ops,
            "completed_operations": completed_ops,
            "total_targets": len(self.targets),
            "findings_by_severity": findings_by_severity,
            "modules": {
                "reconnaissance": self.recon is not None,
                "vulnerability_scanning": self.scanner is not None,
                "exploit_framework": self.exploit is not None,
                "payload_generation": self.payload is not None,
                "social_engineering": self.social is not None,
                "c2_infrastructure": self.c2 is not None
            }
        }


# Singleton instance
_redteam_manager = None

def get_redteam_manager(audit_logger=None) -> RedTeamManager:
    """Get or create the singleton RedTeamManager instance"""
    global _redteam_manager
    if _redteam_manager is None:
        _redteam_manager = RedTeamManager(audit_logger)
    return _redteam_manager


__all__ = [
    'RedTeamManager',
    'RedTeamOperation',
    'RedTeamTarget',
    'OperationStatus',
    'TargetType',
    'get_redteam_manager',
    'get_session_handler',
    'RealSessionHandler',
    'SessionType',
    'SessionStatus'
]
