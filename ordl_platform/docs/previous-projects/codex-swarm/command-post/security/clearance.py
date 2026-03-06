#!/usr/bin/env python3
"""
ORDL Security Clearance System
USG Standard Implementation - DoD 5200.2-R
Classification: TOP SECRET//NOFORN//SCI
"""

from enum import IntEnum, auto
from dataclasses import dataclass, field
from typing import List, Set, Optional, Dict, Any
from datetime import datetime, timedelta
import hashlib
import json


class ClearanceLevel(IntEnum):
    """USG Standard Clearance Levels - Ordered by increasing sensitivity"""
    UNCLASSIFIED = 0
    CONFIDENTIAL = 1
    SECRET = 2
    TOP_SECRET = 3
    TS_SCI = 4
    TS_SCI_NOFORN = 5
    
    @classmethod
    def from_string(cls, level: str) -> 'ClearanceLevel':
        """Parse clearance from string representation"""
        mapping = {
            'UNCLASSIFIED': cls.UNCLASSIFIED,
            'CONFIDENTIAL': cls.CONFIDENTIAL,
            'SECRET': cls.SECRET,
            'TOP SECRET': cls.TOP_SECRET,
            'TS/SCI': cls.TS_SCI,
            'TS/SCI/NOFORN': cls.TS_SCI_NOFORN,
        }
        return mapping.get(level.upper(), cls.UNCLASSIFIED)
    
    def to_string(self) -> str:
        """Convert to display string"""
        mapping = {
            self.UNCLASSIFIED: 'UNCLASSIFIED',
            self.CONFIDENTIAL: 'CONFIDENTIAL',
            self.SECRET: 'SECRET',
            self.TOP_SECRET: 'TOP SECRET',
            self.TS_SCI: 'TS/SCI',
            self.TS_SCI_NOFORN: 'TS/SCI/NOFORN',
        }
        return mapping[self]
    
    def to_short_string(self) -> str:
        """Short abbreviation"""
        mapping = {
            self.UNCLASSIFIED: 'U',
            self.CONFIDENTIAL: 'C',
            self.SECRET: 'S',
            self.TOP_SECRET: 'TS',
            self.TS_SCI: 'SCI',
            self.TS_SCI_NOFORN: 'NF',
        }
        return mapping[self]


@dataclass
class Compartment:
    """SCI Compartment/SAP access control"""
    code: str
    name: str
    description: str
    parent: Optional[str] = None
    sub_compartments: Set[str] = field(default_factory=set)


@dataclass
class ClearanceAttributes:
    """Complete clearance profile for a user"""
    level: ClearanceLevel
    compartments: Set[str] = field(default_factory=set)
    special_access_programs: Set[str] = field(default_factory=set)
    countries_releasable: Set[str] = field(default_factory=lambda: {'USA'})
    polygraph_date: Optional[datetime] = None
    polygraph_type: Optional[str] = None  # 'CI' or 'Full Scope'
    investigation_date: Optional[datetime] = None
    investigation_type: Optional[str] = None  # 'NACLC', 'SSBI', etc.
    adjudication_date: Optional[datetime] = None
    
    def has_access(self, required_level: ClearanceLevel, 
                   compartments: Optional[Set[str]] = None) -> bool:
        """Check if clearance permits access to resource"""
        if self.level < required_level:
            return False
        
        if compartments:
            if not compartments.issubset(self.compartments):
                return False
        
        return True
    
    def is_valid(self) -> bool:
        """Check if clearance is current and valid"""
        # Check investigation is current (typically 5-15 years depending on level)
        if self.investigation_date:
            max_age = {
                ClearanceLevel.UNCLASSIFIED: timedelta(days=365*15),
                ClearanceLevel.CONFIDENTIAL: timedelta(days=365*15),
                ClearanceLevel.SECRET: timedelta(days=365*10),
                ClearanceLevel.TOP_SECRET: timedelta(days=365*6),
                ClearanceLevel.TS_SCI: timedelta(days=365*5),
                ClearanceLevel.TS_SCI_NOFORN: timedelta(days=365*5),
            }
            if datetime.utcnow() - self.investigation_date > max_age.get(self.level, timedelta(days=365*5)):
                return False
        
        # Check polygraph is current (typically 5-7 years)
        if self.level >= ClearanceLevel.TS_SCI and self.polygraph_date:
            if datetime.utcnow() - self.polygraph_date > timedelta(days=365*7):
                return False
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            'level': self.level.to_string(),
            'level_code': self.level.to_short_string(),
            'compartments': sorted(self.compartments),
            'special_access_programs': sorted(self.special_access_programs),
            'countries_releasable': sorted(self.countries_releasable),
            'polygraph_date': self.polygraph_date.isoformat() if self.polygraph_date else None,
            'polygraph_type': self.polygraph_type,
            'investigation_date': self.investigation_date.isoformat() if self.investigation_date else None,
            'investigation_type': self.investigation_type,
            'adjudication_date': self.adjudication_date.isoformat() if self.adjudication_date else None,
            'valid': self.is_valid()
        }


class AccessControlList:
    """Resource-level access control"""
    
    def __init__(self):
        self.resources: Dict[str, Dict[str, Any]] = {}
    
    def define_resource(self, resource_id: str, 
                       min_clearance: ClearanceLevel,
                       required_compartments: Optional[Set[str]] = None,
                       time_restricted: bool = False,
                       two_person_integrity: bool = False,
                       witness_required: bool = False):
        """Define access requirements for a resource"""
        self.resources[resource_id] = {
            'min_clearance': min_clearance,
            'required_compartments': required_compartments or set(),
            'time_restricted': time_restricted,
            'two_person_integrity': two_person_integrity,
            'witness_required': witness_required,
            'access_log': []
        }
    
    def check_access(self, resource_id: str, 
                    user_clearance: ClearanceAttributes,
                    session_context: Optional[Dict] = None) -> tuple[bool, str]:
        """Check if user can access resource, returns (allowed, reason)"""
        if resource_id not in self.resources:
            return False, "RESOURCE_NOT_FOUND"
        
        resource = self.resources[resource_id]
        
        # Check clearance level
        if user_clearance.level < resource['min_clearance']:
            return False, f"INSUFFICIENT_CLEARANCE:{resource['min_clearance'].to_short_string()}"
        
        # Check compartments
        if resource['required_compartments']:
            missing = resource['required_compartments'] - user_clearance.compartments
            if missing:
                return False, f"MISSING_COMPARTMENTS:{','.join(missing)}"
        
        # Check time restrictions (business hours, etc.)
        if resource['time_restricted']:
            now = datetime.utcnow()
            # Example: restrict to 0600-1800 UTC
            if now.hour < 6 or now.hour >= 18:
                return False, "OUTSIDE_AUTHORIZED_HOURS"
        
        # Check two-person integrity
        if resource['two_person_integrity']:
            if not session_context or not session_context.get('witness_present'):
                return False, "TWO_PERSON_INTEGRITY_REQUIRED"
        
        # Check witness requirement (for TS/SCI+)
        if resource['witness_required']:
            if not session_context or not session_context.get('witness_verified'):
                return False, "WITNESS_VERIFICATION_REQUIRED"
        
        return True, "ACCESS_GRANTED"
    
    def log_access(self, resource_id: str, user_id: str, 
                   granted: bool, reason: str, session_id: str):
        """Log access attempt"""
        if resource_id in self.resources:
            self.resources[resource_id]['access_log'].append({
                'timestamp': datetime.utcnow().isoformat(),
                'user_id': user_id,
                'granted': granted,
                'reason': reason,
                'session_id': session_id
            })


# Standard compartment definitions
STANDARD_COMPARTMENTS = {
    'HCS': Compartment('HCS', 'HUMINT Control System', 'Human intelligence sources and methods'),
    'KLONDIKE': Compartment('KLONDIKE', 'Klondike', 'SIGINT collection and analysis'),
    'GAMMA': Compartment('GAMMA', 'Gamma', 'Sensitive SIGINT'),
    'TALENT KEYHOLE': Compartment('TALENT KEYHOLE', 'Talent Keyhole', 'Satellite reconnaissance'),
    'ORCON': Compartment('ORCON', 'Originator Controlled', 'Dissemination control'),
    'NOFORN': Compartment('NOFORN', 'No Foreign Nationals', 'US eyes only'),
    'REL TO': Compartment('REL TO', 'Releasable To', 'Controlled foreign release'),
}


# Resource definitions for ORDL systems
ORDL_RESOURCES = {
    # Core system
    'system.login': {
        'min_clearance': ClearanceLevel.UNCLASSIFIED,
        'description': 'System authentication'
    },
    'system.status': {
        'min_clearance': ClearanceLevel.UNCLASSIFIED,
        'description': 'View system status'
    },
    
    # Agents
    'agents.list': {
        'min_clearance': ClearanceLevel.CONFIDENTIAL,
        'description': 'List agent fleet'
    },
    'agents.control': {
        'min_clearance': ClearanceLevel.SECRET,
        'description': 'Control agent operations'
    },
    'agents.deploy': {
        'min_clearance': ClearanceLevel.TOP_SECRET,
        'description': 'Deploy new agents'
    },
    
    # Intelligence
    'intel.search': {
        'min_clearance': ClearanceLevel.CONFIDENTIAL,
        'description': 'Search intelligence databases'
    },
    'intel.osint': {
        'min_clearance': ClearanceLevel.SECRET,
        'description': 'Open source intelligence'
    },
    'intel.humint': {
        'min_clearance': ClearanceLevel.TS_SCI,
        'required_compartments': {'HCS'},
        'description': 'Human intelligence'
    },
    'intel.sigint': {
        'min_clearance': ClearanceLevel.TS_SCI,
        'required_compartments': {'KLONDIKE', 'GAMMA'},
        'description': 'Signals intelligence'
    },
    'intel.imint': {
        'min_clearance': ClearanceLevel.TS_SCI,
        'required_compartments': {'TALENT KEYHOLE'},
        'description': 'Imagery intelligence'
    },
    
    # Network Operations
    'netops.monitor': {
        'min_clearance': ClearanceLevel.SECRET,
        'description': 'Network monitoring'
    },
    'netops.capture': {
        'min_clearance': ClearanceLevel.TOP_SECRET,
        'time_restricted': True,
        'description': 'Packet capture'
    },
    'netops.exploit': {
        'min_clearance': ClearanceLevel.TS_SCI,
        'two_person_integrity': True,
        'description': 'Network exploitation'
    },
    
    # Red Team
    'redteam.recon': {
        'min_clearance': ClearanceLevel.SECRET,
        'description': 'Target reconnaissance'
    },
    'redteam.scan': {
        'min_clearance': ClearanceLevel.TOP_SECRET,
        'time_restricted': True,
        'description': 'Vulnerability scanning'
    },
    'redteam.exploit': {
        'min_clearance': ClearanceLevel.TS_SCI,
        'two_person_integrity': True,
        'witness_required': True,
        'description': 'Deploy exploits'
    },
    'redteam.payload': {
        'min_clearance': ClearanceLevel.TS_SCI,
        'two_person_integrity': True,
        'description': 'Generate payloads'
    },
    
    # Blue Team
    'blueteam.monitor': {
        'min_clearance': ClearanceLevel.SECRET,
        'description': 'SIEM monitoring'
    },
    'blueteam.respond': {
        'min_clearance': ClearanceLevel.TOP_SECRET,
        'time_restricted': True,
        'description': 'Incident response'
    },
    'blueteam.forensics': {
        'min_clearance': ClearanceLevel.TS_SCI,
        'two_person_integrity': True,
        'description': 'Digital forensics'
    },
    
    # Admin
    'admin.users': {
        'min_clearance': ClearanceLevel.TS_SCI_NOFORN,
        'two_person_integrity': True,
        'witness_required': True,
        'description': 'User administration'
    },
    'admin.audit': {
        'min_clearance': ClearanceLevel.TS_SCI_NOFORN,
        'two_person_integrity': True,
        'description': 'Audit log access'
    },
    'admin.clearance': {
        'min_clearance': ClearanceLevel.TS_SCI_NOFORN,
        'two_person_integrity': True,
        'witness_required': True,
        'description': 'Modify clearances'
    },
}


def initialize_acl() -> AccessControlList:
    """Initialize ORDL access control list"""
    acl = AccessControlList()
    
    for resource_id, config in ORDL_RESOURCES.items():
        acl.define_resource(
            resource_id=resource_id,
            min_clearance=config['min_clearance'],
            required_compartments=config.get('required_compartments'),
            time_restricted=config.get('time_restricted', False),
            two_person_integrity=config.get('two_person_integrity', False),
            witness_required=config.get('witness_required', False)
        )
    
    return acl


# Global ACL instance
_ordl_acl = None

def get_acl() -> AccessControlList:
    """Get ORDL access control list singleton"""
    global _ordl_acl
    if _ordl_acl is None:
        _ordl_acl = initialize_acl()
    return _ordl_acl
