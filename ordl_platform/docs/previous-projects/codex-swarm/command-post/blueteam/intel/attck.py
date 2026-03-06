#!/usr/bin/env python3
"""
================================================================================
ORDL COMMAND POST v6.0.0 - BLUE TEAM ATT&CK INTELLIGENCE
================================================================================
Classification: TOP SECRET//SCI//NOFORN

MITRE ATT&CK FRAMEWORK INTEGRATION
================================================================================
Military-grade threat intelligence with ATT&CK mapping providing:
- Complete technique lookup and metadata
- Tactic mapping and categorization
- Mitigation strategies and recommendations
- Detection strategy mapping
- Alert-to-technique correlation
- Coverage matrix and gap analysis
- STIX/TAXII import capabilities
- Offline-first embedded ATT&CK v14 data

Author: ORDL Cyber Operations Division
Version: 6.0.0
================================================================================
"""

import json
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple, Union


# =============================================================================
# ENUMERATIONS
# =============================================================================

class AttackPlatform(Enum):
    """MITRE ATT&CK platforms"""
    WINDOWS = "Windows"
    MACOS = "macOS"
    LINUX = "Linux"
    AWS = "AWS"
    AZURE = "Azure"
    GCP = "GCP"
    OFFICE_365 = "Office 365"
    AZURE_AD = "Azure AD"
    CONTAINERS = "Containers"
    NETWORK = "Network"
    PRE = "PRE"


class AttackDataSource(Enum):
    """MITRE ATT&CK data sources for detection"""
    COMMAND = "Command"
    FILE = "File"
    PROCESS = "Process"
    NETWORK_TRAFFIC = "Network Traffic"
    WINDOWS_REGISTRY = "Windows Registry"
    LOGON_SESSION = "Logon Session"
    USER_ACCOUNT = "User Account"
    GROUP = "Group"
    DRIVER = "Driver"
    MODULE = "Module"
    SERVICE = "Service"
    SCHEDULED_JOB = "Scheduled Job"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class AttackTechnique:
    """
    Complete MITRE ATT&CK technique information
    
    Attributes:
        id: Technique ID (e.g., "T1566", "T1566.001")
        name: Human-readable technique name
        description: Detailed technique description
        tactic: Primary tactic shortname (e.g., "initial-access")
        platforms: List of platforms where technique applies
        data_sources: Data sources for detecting this technique
        detection: Detection strategies and recommendations
        sub_techniques: List of sub-technique IDs
        mitigations: List of mitigation IDs that address this technique
        examples: Real-world usage examples
        references: External references and URLs
        created: When technique was added to framework
        modified: Last modification date
        is_subtechnique: Whether this is a sub-technique
        parent_technique: Parent technique ID if sub-technique
    """
    id: str
    name: str
    description: str
    tactic: str
    platforms: List[AttackPlatform] = field(default_factory=list)
    data_sources: List[AttackDataSource] = field(default_factory=list)
    detection: str = ""
    sub_techniques: List[str] = field(default_factory=list)
    mitigations: List[str] = field(default_factory=list)
    examples: List[Dict[str, str]] = field(default_factory=list)
    references: List[str] = field(default_factory=list)
    created: Optional[str] = None
    modified: Optional[str] = None
    is_subtechnique: bool = False
    parent_technique: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert technique to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'tactic': self.tactic,
            'platforms': [p.value for p in self.platforms],
            'data_sources': [d.value for d in self.data_sources],
            'detection': self.detection,
            'sub_techniques': self.sub_techniques,
            'mitigations': self.mitigations,
            'examples': self.examples,
            'references': self.references,
            'created': self.created,
            'modified': self.modified,
            'is_subtechnique': self.is_subtechnique,
            'parent_technique': self.parent_technique
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AttackTechnique':
        """Create technique from dictionary"""
        return cls(
            id=data['id'],
            name=data['name'],
            description=data['description'],
            tactic=data['tactic'],
            platforms=[AttackPlatform(p) for p in data.get('platforms', [])],
            data_sources=[AttackDataSource(d) for d in data.get('data_sources', [])],
            detection=data.get('detection', ''),
            sub_techniques=data.get('sub_techniques', []),
            mitigations=data.get('mitigations', []),
            examples=data.get('examples', []),
            references=data.get('references', []),
            created=data.get('created'),
            modified=data.get('modified'),
            is_subtechnique=data.get('is_subtechnique', False),
            parent_technique=data.get('parent_technique')
        )


@dataclass
class AttackTactic:
    """
    MITRE ATT&CK tactic information
    
    Attributes:
        id: Tactic ID (e.g., "TA0001")
        name: Human-readable tactic name
        description: Detailed tactic description
        shortname: Short identifier (e.g., "initial-access")
        techniques: List of technique IDs in this tactic
        url: ATT&CK URL for this tactic
    """
    id: str
    name: str
    description: str
    shortname: str
    techniques: List[str] = field(default_factory=list)
    url: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert tactic to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'shortname': self.shortname,
            'techniques': self.techniques,
            'url': self.url
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AttackTactic':
        """Create tactic from dictionary"""
        return cls(
            id=data['id'],
            name=data['name'],
            description=data['description'],
            shortname=data['shortname'],
            techniques=data.get('techniques', []),
            url=data.get('url', '')
        )


@dataclass
class AttackMitigation:
    """
    MITRE ATT&CK mitigation information
    
    Attributes:
        id: Mitigation ID (e.g., "M1036")
        name: Human-readable mitigation name
        description: Detailed mitigation description
        techniques_addressed: List of technique IDs this mitigation addresses
        references: External references
    """
    id: str
    name: str
    description: str
    techniques_addressed: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert mitigation to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'techniques_addressed': self.techniques_addressed,
            'references': self.references
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AttackMitigation':
        """Create mitigation from dictionary"""
        return cls(
            id=data['id'],
            name=data['name'],
            description=data['description'],
            techniques_addressed=data.get('techniques_addressed', []),
            references=data.get('references', [])
        )


@dataclass
class AttackPath:
    """
    Common attack path/sequence
    
    Attributes:
        name: Path identifier/name
        description: What this attack path represents
        sequence: Ordered list of technique IDs
        mitre_campaigns: Associated MITRE campaigns
        threat_actors: Known threat actors using this path
        mitigations: Recommended mitigations for this path
    """
    name: str
    description: str
    sequence: List[str]
    mitre_campaigns: List[str] = field(default_factory=list)
    threat_actors: List[str] = field(default_factory=list)
    mitigations: List[str] = field(default_factory=list)


@dataclass
class CoverageGap:
    """
    Detection coverage gap analysis result
    
    Attributes:
        technique_id: Technique with gap
        tactic: Associated tactic
        severity: Gap severity (critical, high, medium, low)
        reason: Why this gap exists
        recommendations: How to close the gap
    """
    technique_id: str
    tactic: str
    severity: str
    reason: str
    recommendations: List[str] = field(default_factory=list)


# =============================================================================
# BUILT-IN ATT&CK v14 DATA
# =============================================================================

BUILTIN_TACTICS = {
    "TA0043": AttackTactic(
        id="TA0043",
        name="Reconnaissance",
        description="The adversary is trying to gather information they can use to plan future operations.",
        shortname="reconnaissance",
        techniques=["T1595", "T1593", "T1594"],
        url="https://attack.mitre.org/tactics/TA0043/"
    ),
    "TA0042": AttackTactic(
        id="TA0042",
        name="Resource Development",
        description="The adversary is trying to establish resources they can use to support operations.",
        shortname="resource-development",
        techniques=["T1583", "T1584", "T1587"],
        url="https://attack.mitre.org/tactics/TA0042/"
    ),
    "TA0001": AttackTactic(
        id="TA0001",
        name="Initial Access",
        description="The adversary is trying to get into your network.",
        shortname="initial-access",
        techniques=["T1566", "T1190", "T1133", "T1098", "T1078", "T1566.001", "T1566.002", "T1566.003"],
        url="https://attack.mitre.org/tactics/TA0001/"
    ),
    "TA0002": AttackTactic(
        id="TA0002",
        name="Execution",
        description="The adversary is trying to run malicious code.",
        shortname="execution",
        techniques=["T1059", "T1053", "T1204", "T1059.001", "T1059.003", "T1059.005", "T1059.006", "T1053.005"],
        url="https://attack.mitre.org/tactics/TA0002/"
    ),
    "TA0003": AttackTactic(
        id="TA0003",
        name="Persistence",
        description="The adversary is trying to maintain their foothold.",
        shortname="persistence",
        techniques=["T1547", "T1136", "T1543", "T1547.001", "T1547.004", "T1136.001", "T1136.002"],
        url="https://attack.mitre.org/tactics/TA0003/"
    ),
    "TA0004": AttackTactic(
        id="TA0004",
        name="Privilege Escalation",
        description="The adversary is trying to gain higher-level permissions.",
        shortname="privilege-escalation",
        techniques=["T1055", "T1078", "T1548", "T1055.012", "T1548.001", "T1548.002"],
        url="https://attack.mitre.org/tactics/TA0004/"
    ),
    "TA0005": AttackTactic(
        id="TA0005",
        name="Defense Evasion",
        description="The adversary is trying to avoid being detected.",
        shortname="defense-evasion",
        techniques=["T1070", "T1027", "T1562", "T1070.001", "T1070.004", "T1027.001", "T1562.001"],
        url="https://attack.mitre.org/tactics/TA0005/"
    ),
    "TA0006": AttackTactic(
        id="TA0006",
        name="Credential Access",
        description="The adversary is trying to steal account names and passwords.",
        shortname="credential-access",
        techniques=["T1003", "T1110", "T1552", "T1003.001", "T1003.002", "T1110.001", "T1110.003"],
        url="https://attack.mitre.org/tactics/TA0006/"
    ),
    "TA0007": AttackTactic(
        id="TA0007",
        name="Discovery",
        description="The adversary is trying to figure out your environment.",
        shortname="discovery",
        techniques=["T1087", "T1046", "T1018", "T1087.001", "T1087.002", "T1016", "T1033"],
        url="https://attack.mitre.org/tactics/TA0007/"
    ),
    "TA0008": AttackTactic(
        id="TA0008",
        name="Lateral Movement",
        description="The adversary is trying to move through your environment.",
        shortname="lateral-movement",
        techniques=["T1021", "T1210", "T1570", "T1021.001", "T1021.002", "T1021.004"],
        url="https://attack.mitre.org/tactics/TA0008/"
    ),
    "TA0009": AttackTactic(
        id="TA0009",
        name="Collection",
        description="The adversary is trying to gather data of interest to their goal.",
        shortname="collection",
        techniques=["T1119", "T1005", "T1560", "T1113", "T1114", "T1115"],
        url="https://attack.mitre.org/tactics/TA0009/"
    ),
    "TA0011": AttackTactic(
        id="TA0011",
        name="Command and Control",
        description="The adversary is trying to communicate with compromised systems.",
        shortname="command-and-control",
        techniques=["T1071", "T1572", "T1095", "T1071.001", "T1071.004", "T1105", "T1573"],
        url="https://attack.mitre.org/tactics/TA0011/"
    ),
    "TA0010": AttackTactic(
        id="TA0010",
        name="Exfiltration",
        description="The adversary is trying to steal data.",
        shortname="exfiltration",
        techniques=["T1041", "T1567", "T1048", "T1048.001", "T1048.002", "T1048.003"],
        url="https://attack.mitre.org/tactics/TA0010/"
    ),
    "TA0040": AttackTactic(
        id="TA0040",
        name="Impact",
        description="The adversary is trying to manipulate, interrupt, or destroy systems and data.",
        shortname="impact",
        techniques=["T1496", "T1490", "T1486", "T1491", "T1565"],
        url="https://attack.mitre.org/tactics/TA0040/"
    ),
}

BUILTIN_TECHNIQUES = {
    # Initial Access
    "T1566": AttackTechnique(
        id="T1566",
        name="Phishing",
        description="Adversaries may send phishing messages to gain access to victim systems. "
                    "All forms of phishing are electronically delivered social engineering. "
                    "Phishing can be targeted, known as spearphishing.",
        tactic="initial-access",
        platforms=[AttackPlatform.WINDOWS, AttackPlatform.MACOS, AttackPlatform.LINUX],
        data_sources=[AttackDataSource.FILE, AttackDataSource.NETWORK_TRAFFIC],
        detection="Monitor for suspicious email content, unexpected attachments, and network "
                  "traffic to unknown domains. Implement email security gateways.",
        sub_techniques=["T1566.001", "T1566.002", "T1566.003"],
        mitigations=["M1049", "M1031", "M1017"],
        examples=[
            {"group": "APT28", "campaign": "Operation Pawn Storm", "description": "Spearphishing emails with malicious attachments"},
            {"group": "APT29", "campaign": "CozyBear", "description": "Phishing via legitimate web services"}
        ],
        references=["https://attack.mitre.org/techniques/T1566/"],
        is_subtechnique=False
    ),
    "T1566.001": AttackTechnique(
        id="T1566.001",
        name="Spearphishing Attachment",
        description="Adversaries may send spearphishing emails with a malicious attachment "
                    "in an attempt to gain access to victim systems.",
        tactic="initial-access",
        platforms=[AttackPlatform.WINDOWS, AttackPlatform.MACOS, AttackPlatform.LINUX],
        data_sources=[AttackDataSource.FILE, AttackDataSource.NETWORK_TRAFFIC],
        detection="Monitor for unusual attachment types (executables, scripts, macros). "
                  "Analyze email metadata for suspicious sender patterns.",
        mitigations=["M1049", "M1031", "M1017"],
        references=["https://attack.mitre.org/techniques/T1566/001/"],
        is_subtechnique=True,
        parent_technique="T1566"
    ),
    "T1566.002": AttackTechnique(
        id="T1566.002",
        name="Spearphishing Link",
        description="Adversaries may send spearphishing emails with a malicious link in "
                    "an attempt to gain access to victim systems.",
        tactic="initial-access",
        platforms=[AttackPlatform.WINDOWS, AttackPlatform.MACOS, AttackPlatform.LINUX],
        data_sources=[AttackDataSource.NETWORK_TRAFFIC, AttackDataSource.LOGON_SESSION],
        detection="Monitor for URL click events, suspicious domain resolution, and "
                  "credential submission to unknown sites.",
        mitigations=["M1049", "M1031", "M1017"],
        references=["https://attack.mitre.org/techniques/T1566/002/"],
        is_subtechnique=True,
        parent_technique="T1566"
    ),
    "T1190": AttackTechnique(
        id="T1190",
        name="Exploit Public-Facing Application",
        description="Adversaries may attempt to exploit a weakness in an Internet-facing "
                    "host or system to initially access a network.",
        tactic="initial-access",
        platforms=[AttackPlatform.WINDOWS, AttackPlatform.MACOS, AttackPlatform.LINUX, AttackPlatform.AZURE],
        data_sources=[AttackDataSource.NETWORK_TRAFFIC, AttackDataSource.PROCESS],
        detection="Monitor for unusual network traffic patterns, unexpected process execution "
                  "from web services, and web server error spikes.",
        mitigations=["M1048", "M1030", "M1016"],
        examples=[
            {"group": "APT41", "description": "Exploitation of Citrix ADC/NetScaler"},
            {"group": "HAFNIUM", "description": "Microsoft Exchange Server exploitation"}
        ],
        references=["https://attack.mitre.org/techniques/T1190/"],
        is_subtechnique=False
    ),
    
    # Execution
    "T1059": AttackTechnique(
        id="T1059",
        name="Command and Scripting Interpreter",
        description="Adversaries may abuse command and script interpreters to execute commands, "
                    "scripts, or binaries. These interfaces and languages provide ways of "
                    "interacting with computer systems.",
        tactic="execution",
        platforms=[AttackPlatform.WINDOWS, AttackPlatform.MACOS, AttackPlatform.LINUX],
        data_sources=[AttackDataSource.COMMAND, AttackDataSource.PROCESS, AttackDataSource.FILE],
        detection="Monitor command-line execution and script interpreters. Look for encoded "
                  "commands, unusual script execution patterns, and suspicious parent-child "
                  "process relationships.",
        sub_techniques=["T1059.001", "T1059.003", "T1059.005", "T1059.006", "T1059.007"],
        mitigations=["M1038", "M1026", "M1035"],
        references=["https://attack.mitre.org/techniques/T1059/"],
        is_subtechnique=False
    ),
    "T1059.001": AttackTechnique(
        id="T1059.001",
        name="PowerShell",
        description="Adversaries may abuse PowerShell commands and scripts for execution. "
                    "PowerShell is a powerful interactive command-line interface and scripting "
                    "environment included in the Windows operating system.",
        tactic="execution",
        platforms=[AttackPlatform.WINDOWS],
        data_sources=[AttackDataSource.COMMAND, AttackDataSource.PROCESS, AttackDataSource.MODULE],
        detection="Enable PowerShell logging (Module, Script Block, Transcription). Monitor for "
                  "encoded commands, suspicious cmdlets, and execution of PowerShell from "
                  "unusual parent processes.",
        mitigations=["M1042", "M1038", "M1026"],
        references=["https://attack.mitre.org/techniques/T1059/001/"],
        is_subtechnique=True,
        parent_technique="T1059"
    ),
    "T1059.003": AttackTechnique(
        id="T1059.003",
        name="Windows Command Shell",
        description="Adversaries may abuse the Windows command shell for execution. The "
                    "Windows command shell (cmd) is the primary command prompt on Windows systems.",
        tactic="execution",
        platforms=[AttackPlatform.WINDOWS],
        data_sources=[AttackDataSource.COMMAND, AttackDataSource.PROCESS],
        detection="Monitor cmd.exe execution and command-line arguments. Look for unusual "
                  "parent processes, batch file execution from suspicious locations.",
        mitigations=["M1038", "M1026"],
        references=["https://attack.mitre.org/techniques/T1059/003/"],
        is_subtechnique=True,
        parent_technique="T1059"
    ),
    "T1053": AttackTechnique(
        id="T1053",
        name="Scheduled Task/Job",
        description="Adversaries may abuse task scheduling functionality to facilitate "
                    "initial or recurring execution of malicious code. Utilities exist within "
                    "all major operating systems to schedule running applications or scripts.",
        tactic="execution",
        platforms=[AttackPlatform.WINDOWS, AttackPlatform.MACOS, AttackPlatform.LINUX],
        data_sources=[AttackDataSource.FILE, AttackDataSource.PROCESS, AttackDataSource.SCHEDULED_JOB],
        detection="Monitor task scheduler event logs for task creation/modification. Monitor "
                  "for processes spawned from task scheduler with unusual parents.",
        sub_techniques=["T1053.005", "T1053.006", "T1053.007"],
        mitigations=["M1026", "M1047"],
        references=["https://attack.mitre.org/techniques/T1053/"],
        is_subtechnique=False
    ),
    "T1053.005": AttackTechnique(
        id="T1053.005",
        name="Scheduled Task",
        description="Adversaries may abuse the Windows Task Scheduler to perform task "
                    "scheduling for initial or recurring execution of malicious code.",
        tactic="execution",
        platforms=[AttackPlatform.WINDOWS],
        data_sources=[AttackDataSource.FILE, AttackDataSource.PROCESS, AttackDataSource.SCHEDULED_JOB, 
                      AttackDataSource.WINDOWS_REGISTRY],
        detection="Monitor Windows Security logs (4698 - Scheduled task creation). Monitor "
                  "for schtasks.exe usage with suspicious arguments. Monitor Task Scheduler "
                  "service for unusual task registration.",
        mitigations=["M1026", "M1047"],
        references=["https://attack.mitre.org/techniques/T1053/005/"],
        is_subtechnique=True,
        parent_technique="T1053"
    ),
    
    # Persistence
    "T1547": AttackTechnique(
        id="T1547",
        name="Boot or Logon Autostart Execution",
        description="Adversaries may configure system settings to automatically execute a "
                    "program during system boot or logon to maintain persistence.",
        tactic="persistence",
        platforms=[AttackPlatform.WINDOWS, AttackPlatform.MACOS, AttackPlatform.LINUX],
        data_sources=[AttackDataSource.FILE, AttackDataSource.WINDOWS_REGISTRY, AttackDataSource.PROCESS],
        detection="Monitor for changes to autostart locations: Registry Run keys, startup "
                  "folders, system services. Alert on new entries in these locations.",
        sub_techniques=["T1547.001", "T1547.004", "T1547.009", "T1547.012"],
        mitigations=["M1018", "M1022", "M1047"],
        references=["https://attack.mitre.org/techniques/T1547/"],
        is_subtechnique=False
    ),
    "T1547.001": AttackTechnique(
        id="T1547.001",
        name="Registry Run Keys",
        description="Adversaries may achieve persistence by adding a program to a startup "
                    "folder or referencing it with a Registry run key.",
        tactic="persistence",
        platforms=[AttackPlatform.WINDOWS],
        data_sources=[AttackDataSource.WINDOWS_REGISTRY, AttackDataSource.FILE, AttackDataSource.PROCESS],
        detection="Monitor Registry modifications to Run and RunOnce keys. Monitor file "
                  "creation in startup folders. Correlate with process execution.",
        mitigations=["M1018", "M1022", "M1047"],
        references=["https://attack.mitre.org/techniques/T1547/001/"],
        is_subtechnique=True,
        parent_technique="T1547"
    ),
    "T1136": AttackTechnique(
        id="T1136",
        name="Create Account",
        description="Adversaries may create an account to maintain access to victim systems. "
                    "Account creation may be used to establish secondary credentialed access.",
        tactic="persistence",
        platforms=[AttackPlatform.WINDOWS, AttackPlatform.MACOS, AttackPlatform.LINUX, AttackPlatform.AZURE_AD],
        data_sources=[AttackDataSource.USER_ACCOUNT, AttackDataSource.LOGON_SESSION],
        detection="Monitor for user account creation events (Windows Event 4720). Audit "
                  "account creation in cloud environments. Monitor for accounts with "
                  "suspicious naming patterns.",
        sub_techniques=["T1136.001", "T1136.002", "T1136.003"],
        mitigations=["M1030", "M1026"],
        references=["https://attack.mitre.org/techniques/T1136/"],
        is_subtechnique=False
    ),
    "T1136.001": AttackTechnique(
        id="T1136.001",
        name="Local Account",
        description="Adversaries may create a local account to maintain access to victim systems.",
        tactic="persistence",
        platforms=[AttackPlatform.WINDOWS, AttackPlatform.MACOS, AttackPlatform.LINUX],
        data_sources=[AttackDataSource.USER_ACCOUNT, AttackDataSource.LOGON_SESSION],
        detection="Monitor for local account creation events (4720 Windows). Review user "
                  "accounts for suspicious naming conventions or unexpected privileges.",
        mitigations=["M1030", "M1026"],
        references=["https://attack.mitre.org/techniques/T1136/001/"],
        is_subtechnique=True,
        parent_technique="T1136"
    ),
    
    # Privilege Escalation
    "T1055": AttackTechnique(
        id="T1055",
        name="Process Injection",
        description="Adversaries may inject code into processes in order to evade process-based "
                    "defenses as well as possibly elevate privileges. Process injection is a "
                    "method of executing arbitrary code in the address space of a separate live process.",
        tactic="privilege-escalation",
        platforms=[AttackPlatform.WINDOWS, AttackPlatform.MACOS, AttackPlatform.LINUX],
        data_sources=[AttackDataSource.PROCESS, AttackDataSource.MODULE],
        detection="Monitor for processes accessing other process memory. Look for unusual "
                  "memory protections (RWX), process hollowing indicators, and abnormal "
                  "parent-child process relationships.",
        sub_techniques=["T1055.001", "T1055.004", "T1055.012", "T1055.013"],
        mitigations=["M1040", "M1026", "M1055"],
        references=["https://attack.mitre.org/techniques/T1055/"],
        is_subtechnique=False
    ),
    "T1055.012": AttackTechnique(
        id="T1055.012",
        name="Process Hollowing",
        description="Adversaries may inject malicious code into suspended and hollowed processes "
                    "to evade process-based defenses. Process hollowing is a method of executing "
                    "arbitrary code in the address space of a separate live process.",
        tactic="privilege-escalation",
        platforms=[AttackPlatform.WINDOWS],
        data_sources=[AttackDataSource.PROCESS, AttackDataSource.MODULE],
        detection="Monitor for processes being created in a suspended state followed by "
                  "memory modification. Look for unmapping of the original executable and "
                  "execution from unexpected memory regions.",
        mitigations=["M1040", "M1055"],
        references=["https://attack.mitre.org/techniques/T1055/012/"],
        is_subtechnique=True,
        parent_technique="T1055"
    ),
    "T1078": AttackTechnique(
        id="T1078",
        name="Valid Accounts",
        description="Adversaries may obtain and abuse credentials of existing accounts as a "
                    "means of gaining Initial Access, Persistence, Privilege Escalation, or "
                    "Defense Evasion.",
        tactic="privilege-escalation",
        platforms=[AttackPlatform.WINDOWS, AttackPlatform.MACOS, AttackPlatform.LINUX, 
                   AttackPlatform.AWS, AttackPlatform.AZURE, AttackPlatform.GCP],
        data_sources=[AttackDataSource.USER_ACCOUNT, AttackDataSource.LOGON_SESSION],
        detection="Monitor for unusual account usage patterns: logins at odd hours, from "
                  "unexpected locations, or using atypical access methods. Alert on "
                  "suspicious privilege escalation by existing accounts.",
        sub_techniques=["T1078.001", "T1078.002", "T1078.003", "T1078.004"],
        mitigations=["M1027", "M1032", "M1026"],
        references=["https://attack.mitre.org/techniques/T1078/"],
        is_subtechnique=False
    ),
    
    # Defense Evasion
    "T1070": AttackTechnique(
        id="T1070",
        name="Indicator Removal",
        description="Adversaries may delete or modify artifacts generated on a host system "
                    "to remove evidence of their presence or hinder defenses.",
        tactic="defense-evasion",
        platforms=[AttackPlatform.WINDOWS, AttackPlatform.MACOS, AttackPlatform.LINUX],
        data_sources=[AttackDataSource.COMMAND, AttackDataSource.FILE, AttackDataSource.PROCESS],
        detection="Monitor for file deletion, log clearing, and command history manipulation. "
                  "Alert on volume shadow deletion and event log service stopping.",
        sub_techniques=["T1070.001", "T1070.002", "T1070.003", "T1070.004", "T1070.006"],
        mitigations=["M1041", "M1029", "M1047"],
        references=["https://attack.mitre.org/techniques/T1070/"],
        is_subtechnique=False
    ),
    "T1070.001": AttackTechnique(
        id="T1070.001",
        name="Clear Windows Event Logs",
        description="Adversaries may clear Windows Event Logs to hide the activity of an "
                    "attack. Windows Event Logs record various events including authentication, "
                    "account logon, and security policy changes.",
        tactic="defense-evasion",
        platforms=[AttackPlatform.WINDOWS],
        data_sources=[AttackDataSource.COMMAND, AttackDataSource.FILE],
        detection="Monitor for wevtutil.exe usage with cl (clear) option. Alert on Event "
                  "Log Service stops (Event 1100) and volume shadow deletion.",
        mitigations=["M1041", "M1029", "M1047"],
        references=["https://attack.mitre.org/techniques/T1070/001/"],
        is_subtechnique=True,
        parent_technique="T1070"
    ),
    "T1070.004": AttackTechnique(
        id="T1070.004",
        name="File Deletion",
        description="Adversaries may delete files left behind by the actions of their intrusion activity.",
        tactic="defense-evasion",
        platforms=[AttackPlatform.WINDOWS, AttackPlatform.MACOS, AttackPlatform.LINUX],
        data_sources=[AttackDataSource.COMMAND, AttackDataSource.FILE, AttackDataSource.PROCESS],
        detection="Monitor for file deletion commands (del, rm, rmdir). Alert on bulk file "
                  "deletion or deletion from sensitive locations.",
        mitigations=["M1041", "M1047"],
        references=["https://attack.mitre.org/techniques/T1070/004/"],
        is_subtechnique=True,
        parent_technique="T1070"
    ),
    "T1027": AttackTechnique(
        id="T1027",
        name="Obfuscated Files or Information",
        description="Adversaries may attempt to make an executable or file difficult to discover "
                    "or analyze by encrypting, encoding, or otherwise obfuscating its contents.",
        tactic="defense-evasion",
        platforms=[AttackPlatform.WINDOWS, AttackPlatform.MACOS, AttackPlatform.LINUX],
        data_sources=[AttackDataSource.FILE, AttackDataSource.NETWORK_TRAFFIC],
        detection="Use file and signature analysis tools to detect obfuscation. Monitor for "
                  "high entropy files and unusual encoding patterns.",
        sub_techniques=["T1027.001", "T1027.002", "T1027.005", "T1027.006"],
        mitigations=["M1049", "M1040"],
        references=["https://attack.mitre.org/techniques/T1027/"],
        is_subtechnique=False
    ),
    "T1027.001": AttackTechnique(
        id="T1027.001",
        name="Binary Padding",
        description="Adversaries may use binary padding to add junk data and change the on-disk "
                    "representation of malware without affecting the functionality or behavior.",
        tactic="defense-evasion",
        platforms=[AttackPlatform.WINDOWS, AttackPlatform.MACOS, AttackPlatform.LINUX],
        data_sources=[AttackDataSource.FILE],
        detection="Compare file hashes to known good versions. Analyze for high entropy regions "
                  "or appended data in binaries.",
        mitigations=["M1049", "M1040"],
        references=["https://attack.mitre.org/techniques/T1027/001/"],
        is_subtechnique=True,
        parent_technique="T1027"
    ),
    "T1562": AttackTechnique(
        id="T1562",
        name="Impair Defenses",
        description="Adversaries may maliciously modify components of a victim environment in "
                    "order to hinder or disable defensive mechanisms.",
        tactic="defense-evasion",
        platforms=[AttackPlatform.WINDOWS, AttackPlatform.MACOS, AttackPlatform.LINUX, 
                   AttackPlatform.AZURE_AD, AttackPlatform.OFFICE_365],
        data_sources=[AttackDataSource.COMMAND, AttackDataSource.PROCESS, AttackDataSource.SERVICE],
        detection="Monitor for security service stops, configuration changes to security "
                  "products, and tampering with logging mechanisms.",
        sub_techniques=["T1562.001", "T1562.002", "T1562.004", "T1562.006"],
        mitigations=["M1022", "M1024", "M1047"],
        references=["https://attack.mitre.org/techniques/T1562/"],
        is_subtechnique=False
    ),
    "T1562.001": AttackTechnique(
        id="T1562.001",
        name="Disable or Modify Tools",
        description="Adversaries may modify and/or disable security tools to avoid possible "
                    "detection of their malware and/or tools.",
        tactic="defense-evasion",
        platforms=[AttackPlatform.WINDOWS, AttackPlatform.MACOS, AttackPlatform.LINUX],
        data_sources=[AttackDataSource.COMMAND, AttackDataSource.PROCESS, AttackDataSource.SERVICE],
        detection="Monitor for attempts to stop security services (Windows Defender, EDR agents). "
                  "Alert on registry modifications to security product configurations.",
        mitigations=["M1022", "M1024", "M1047"],
        references=["https://attack.mitre.org/techniques/T1562/001/"],
        is_subtechnique=True,
        parent_technique="T1562"
    ),
    
    # Credential Access
    "T1003": AttackTechnique(
        id="T1003",
        name="OS Credential Dumping",
        description="Adversaries may attempt to dump credentials to obtain account login and "
                    "credential material, normally in the form of a hash or a clear text password.",
        tactic="credential-access",
        platforms=[AttackPlatform.WINDOWS, AttackPlatform.MACOS, AttackPlatform.LINUX],
        data_sources=[AttackDataSource.COMMAND, AttackDataSource.PROCESS],
        detection="Monitor for credential dumping tools (Mimikatz, ProcDump). Alert on LSASS "
                  "memory access, SAM hive dumping, and security account manager access.",
        sub_techniques=["T1003.001", "T1003.002", "T1003.003", "T1003.004", "T1003.005", "T1003.006"],
        mitigations=["M1041", "M1025", "M1027"],
        references=["https://attack.mitre.org/techniques/T1003/"],
        is_subtechnique=False
    ),
    "T1003.001": AttackTechnique(
        id="T1003.001",
        name="LSASS Memory",
        description="Adversaries may attempt to access credential material stored in the "
                    "process memory of the Local Security Authority Subsystem Service (LSASS).",
        tactic="credential-access",
        platforms=[AttackPlatform.WINDOWS],
        data_sources=[AttackDataSource.PROCESS, AttackDataSource.COMMAND],
        detection="Monitor for processes accessing LSASS memory. Alert on suspicious process "
                  "handles to LSASS. Enable LSA Protection when possible.",
        mitigations=["M1041", "M1025", "M1028"],
        references=["https://attack.mitre.org/techniques/T1003/001/"],
        is_subtechnique=True,
        parent_technique="T1003"
    ),
    "T1003.002": AttackTechnique(
        id="T1003.002",
        name="Security Account Manager",
        description="Adversaries may attempt to extract credential material from the Security "
                    "Account Manager (SAM) database either through in-memory techniques or "
                    "through the Windows Registry.",
        tactic="credential-access",
        platforms=[AttackPlatform.WINDOWS],
        data_sources=[AttackDataSource.FILE, AttackDataSource.WINDOWS_REGISTRY],
        detection="Monitor for access to SAM hive files (system32\config\SAM). Alert on "
                  "registry export of SAM and SECURITY hives.",
        mitigations=["M1041", "M1027"],
        references=["https://attack.mitre.org/techniques/T1003/002/"],
        is_subtechnique=True,
        parent_technique="T1003"
    ),
    "T1110": AttackTechnique(
        id="T1110",
        name="Brute Force",
        description="Adversaries may use brute force techniques to gain access to accounts "
                    "when passwords are unknown or when password hashes are obtained.",
        tactic="credential-access",
        platforms=[AttackPlatform.WINDOWS, AttackPlatform.MACOS, AttackPlatform.LINUX, 
                   AttackPlatform.AWS, AttackPlatform.AZURE, AttackPlatform.GCP],
        data_sources=[AttackDataSource.LOGON_SESSION, AttackDataSource.USER_ACCOUNT],
        detection="Monitor for high volume of authentication failures. Alert on password "
                  "spraying patterns (many users, same password) and failed login thresholds.",
        sub_techniques=["T1110.001", "T1110.002", "T1110.003", "T1110.004"],
        mitigations=["M1036", "M1027", "M1032"],
        references=["https://attack.mitre.org/techniques/T1110/"],
        is_subtechnique=False
    ),
    "T1110.001": AttackTechnique(
        id="T1110.001",
        name="Password Guessing",
        description="Adversaries with no prior knowledge of legitimate credentials within the "
                    "system or environment may guess passwords to attempt access to accounts.",
        tactic="credential-access",
        platforms=[AttackPlatform.WINDOWS, AttackPlatform.MACOS, AttackPlatform.LINUX],
        data_sources=[AttackDataSource.LOGON_SESSION, AttackDataSource.USER_ACCOUNT],
        detection="Monitor for high frequency authentication failures from single source. "
                  "Alert on common password patterns being tried.",
        mitigations=["M1036", "M1027"],
        references=["https://attack.mitre.org/techniques/T1110/001/"],
        is_subtechnique=True,
        parent_technique="T1110"
    ),
    "T1110.003": AttackTechnique(
        id="T1110.003",
        name="Password Spraying",
        description="Adversaries may use a single or small list of commonly used passwords "
                    "against many different accounts to attempt to acquire valid account credentials.",
        tactic="credential-access",
        platforms=[AttackPlatform.WINDOWS, AttackPlatform.MACOS, AttackPlatform.LINUX, 
                   AttackPlatform.AZURE_AD, AttackPlatform.OFFICE_365],
        data_sources=[AttackDataSource.LOGON_SESSION, AttackDataSource.USER_ACCOUNT],
        detection="Monitor for authentication patterns: many different usernames with same "
                  "password from single source. Lower per-account failure rate than traditional "
                  "brute force.",
        mitigations=["M1036", "M1027", "M1032"],
        references=["https://attack.mitre.org/techniques/T1110/003/"],
        is_subtechnique=True,
        parent_technique="T1110"
    ),
    
    # Discovery
    "T1087": AttackTechnique(
        id="T1087",
        name="Account Discovery",
        description="Adversaries may attempt to get a listing of accounts on a system or within "
                    "an environment. This information can help adversaries determine which "
                    "accounts exist to aid in follow-on behavior.",
        tactic="discovery",
        platforms=[AttackPlatform.WINDOWS, AttackPlatform.MACOS, AttackPlatform.LINUX, 
                   AttackPlatform.AZURE, AttackPlatform.AZURE_AD, AttackPlatform.OFFICE_365],
        data_sources=[AttackDataSource.COMMAND, AttackDataSource.USER_ACCOUNT, AttackDataSource.GROUP],
        detection="Monitor for commands used to enumerate accounts: net user, dsquery, PowerShell "
                  "Get-LocalUser. Alert on unusual account enumeration from non-admin users.",
        sub_techniques=["T1087.001", "T1087.002", "T1087.003", "T1087.004"],
        mitigations=["M1028"],
        references=["https://attack.mitre.org/techniques/T1087/"],
        is_subtechnique=False
    ),
    "T1087.001": AttackTechnique(
        id="T1087.001",
        name="Local Account",
        description="Adversaries may attempt to get a listing of local system accounts.",
        tactic="discovery",
        platforms=[AttackPlatform.WINDOWS, AttackPlatform.MACOS, AttackPlatform.LINUX],
        data_sources=[AttackDataSource.COMMAND, AttackDataSource.USER_ACCOUNT],
        detection="Monitor for local account enumeration commands: net user, whoami, /etc/passwd "
                  "access. Correlate with other discovery activities.",
        mitigations=["M1028"],
        references=["https://attack.mitre.org/techniques/T1087/001/"],
        is_subtechnique=True,
        parent_technique="T1087"
    ),
    "T1046": AttackTechnique(
        id="T1046",
        name="Network Service Discovery",
        description="Adversaries may attempt to get a listing of services running on remote hosts "
                    "and local network infrastructure devices, including those that may be "
                    "vulnerable to remote software exploitation.",
        tactic="discovery",
        platforms=[AttackPlatform.WINDOWS, AttackPlatform.MACOS, AttackPlatform.LINUX, AttackPlatform.NETWORK],
        data_sources=[AttackDataSource.COMMAND, AttackDataSource.NETWORK_TRAFFIC],
        detection="Monitor for port scanning activity (nmap, masscan). Alert on unusual internal "
                  "network reconnaissance from endpoints.",
        mitigations=["M1042", "M1031"],
        references=["https://attack.mitre.org/techniques/T1046/"],
        is_subtechnique=False
    ),
    
    # Lateral Movement
    "T1021": AttackTechnique(
        id="T1021",
        name="Remote Services",
        description="Adversaries may use Valid Accounts to log into a service specifically designed "
                    "to accept remote connections, such as telnet, SSH, and VNC.",
        tactic="lateral-movement",
        platforms=[AttackPlatform.WINDOWS, AttackPlatform.MACOS, AttackPlatform.LINUX],
        data_sources=[AttackDataSource.LOGON_SESSION, AttackDataSource.NETWORK_TRAFFIC],
        detection="Monitor for remote service connections from unexpected sources. Alert on "
                  "concurrent logins from geographically distant locations.",
        sub_techniques=["T1021.001", "T1021.002", "T1021.004", "T1021.005", "T1021.006"],
        mitigations=["M1030", "M1042", "M1035"],
        references=["https://attack.mitre.org/techniques/T1021/"],
        is_subtechnique=False
    ),
    "T1021.001": AttackTechnique(
        id="T1021.001",
        name="Remote Desktop Protocol",
        description="Adversaries may use Valid Accounts to log into a computer using the Remote "
                    "Desktop Protocol (RDP).",
        tactic="lateral-movement",
        platforms=[AttackPlatform.WINDOWS],
        data_sources=[AttackDataSource.LOGON_SESSION, AttackDataSource.NETWORK_TRAFFIC],
        detection="Monitor RDP connections (Event 4624 Logon Type 10). Alert on RDP from external "
                  "sources or to critical systems. Monitor for unusual RDP session duration.",
        mitigations=["M1030", "M1042"],
        references=["https://attack.mitre.org/techniques/T1021/001/"],
        is_subtechnique=True,
        parent_technique="T1021"
    ),
    "T1021.002": AttackTechnique(
        id="T1021.002",
        name="SMB/Windows Admin Shares",
        description="Adversaries may use Valid Accounts to interact with a remote network share "
                    "using Server Message Block (SMB).",
        tactic="lateral-movement",
        platforms=[AttackPlatform.WINDOWS],
        data_sources=[AttackDataSource.LOGON_SESSION, AttackDataSource.NETWORK_TRAFFIC, AttackDataSource.FILE],
        detection="Monitor for SMB connections to admin shares (C$, ADMIN$). Alert on file "
                  "transfers over SMB from unexpected sources.",
        mitigations=["M1026", "M1035"],
        references=["https://attack.mitre.org/techniques/T1021/002/"],
        is_subtechnique=True,
        parent_technique="T1021"
    ),
    "T1210": AttackTechnique(
        id="T1210",
        name="Exploitation of Remote Services",
        description="Adversaries may exploit a weakness in an Internet-facing host or system "
                    "to leverage remote services to gain access to internal systems.",
        tactic="lateral-movement",
        platforms=[AttackPlatform.WINDOWS, AttackPlatform.MACOS, AttackPlatform.LINUX, AttackPlatform.NETWORK],
        data_sources=[AttackDataSource.NETWORK_TRAFFIC, AttackDataSource.PROCESS],
        detection="Monitor for unexpected network connections. Alert on exploitation indicators "
                  "such as unusual service crashes followed by network activity.",
        mitigations=["M1048", "M1030"],
        references=["https://attack.mitre.org/techniques/T1210/"],
        is_subtechnique=False
    ),
    
    # Collection
    "T1119": AttackTechnique(
        id="T1119",
        name="Automated Collection",
        description="Once established within a system or network, an adversary may use automated "
                    "techniques for collecting internal data.",
        tactic="collection",
        platforms=[AttackPlatform.WINDOWS, AttackPlatform.MACOS, AttackPlatform.LINUX],
        data_sources=[AttackDataSource.COMMAND, AttackDataSource.FILE, AttackDataSource.PROCESS],
        detection="Monitor for automated data collection scripts. Alert on bulk file copy "
                  "operations and recursive directory searches for sensitive file types.",
        mitigations=["M1041"],
        references=["https://attack.mitre.org/techniques/T1119/"],
        is_subtechnique=False
    ),
    "T1005": AttackTechnique(
        id="T1005",
        name="Data from Local System",
        description="Adversaries may search local system sources, such as file systems or local "
                    "databases, to find files of interest and sensitive data prior to Exfiltration.",
        tactic="collection",
        platforms=[AttackPlatform.WINDOWS, AttackPlatform.MACOS, AttackPlatform.LINUX],
        data_sources=[AttackDataSource.COMMAND, AttackDataSource.FILE, AttackDataSource.PROCESS],
        detection="Monitor for file access patterns to sensitive data. Alert on bulk access to "
                  "document repositories, credential stores, and configuration files.",
        mitigations=["M1057", "M1041"],
        references=["https://attack.mitre.org/techniques/T1005/"],
        is_subtechnique=False
    ),
    "T1115": AttackTechnique(
        id="T1115",
        name="Clipboard Data",
        description="Adversaries may collect data stored in the clipboard from users copying "
                    "information within or between applications.",
        tactic="collection",
        platforms=[AttackPlatform.WINDOWS, AttackPlatform.MACOS, AttackPlatform.LINUX],
        data_sources=[AttackDataSource.COMMAND, AttackDataSource.PROCESS],
        detection="Monitor for clipboard access APIs. Alert on processes accessing clipboard "
                  "data repeatedly or accessing sensitive clipboard content.",
        mitigations=["M1041", "M1057"],
        references=["https://attack.mitre.org/techniques/T1115/"],
        is_subtechnique=False
    ),
    
    # Exfiltration
    "T1041": AttackTechnique(
        id="T1041",
        name="Exfiltration Over C2 Channel",
        description="Adversaries may steal data by exfiltrating it over an existing command "
                    "and control channel. Stolen data is encoded into the normal communications "
                    "channel using the same protocol as command and control communications.",
        tactic="exfiltration",
        platforms=[AttackPlatform.WINDOWS, AttackPlatform.MACOS, AttackPlatform.LINUX],
        data_sources=[AttackDataSource.NETWORK_TRAFFIC, AttackDataSource.COMMAND],
        detection="Monitor for large data transfers over established C2 channels. Alert on "
                  "unusual outbound traffic volumes from compromised hosts.",
        mitigations=["M1031", "M1057", "M1037"],
        references=["https://attack.mitre.org/techniques/T1041/"],
        is_subtechnique=False
    ),
    "T1567": AttackTechnique(
        id="T1567",
        name="Exfiltration Over Web Service",
        description="Adversaries may use an existing, legitimate external Web service to "
                    "exfiltrate data rather than their primary command and control channel.",
        tactic="exfiltration",
        platforms=[AttackPlatform.WINDOWS, AttackPlatform.MACOS, AttackPlatform.LINUX],
        data_sources=[AttackDataSource.NETWORK_TRAFFIC, AttackDataSource.COMMAND],
        detection="Monitor for data uploads to cloud storage services (Dropbox, Google Drive, "
                  "OneDrive). Alert on unusual patterns of web service access.",
        sub_techniques=["T1567.001", "T1567.002"],
        mitigations=["M1031", "M1057", "M1041"],
        references=["https://attack.mitre.org/techniques/T1567/"],
        is_subtechnique=False
    ),
    "T1048": AttackTechnique(
        id="T1048",
        name="Exfiltration Over Alternative Protocol",
        description="Adversaries may steal data using a different, less commonly used protocol "
                    "to exfiltrate data than that of the existing command and control channel.",
        tactic="exfiltration",
        platforms=[AttackPlatform.WINDOWS, AttackPlatform.MACOS, AttackPlatform.LINUX],
        data_sources=[AttackDataSource.NETWORK_TRAFFIC, AttackDataSource.COMMAND],
        detection="Monitor for unusual outbound protocols (DNS, ICMP, FTP). Alert on DNS "
                  "queries with large payloads or tunneling indicators.",
        sub_techniques=["T1048.001", "T1048.002", "T1048.003"],
        mitigations=["M1031", "M1037"],
        references=["https://attack.mitre.org/techniques/T1048/"],
        is_subtechnique=False
    ),
}

BUILTIN_MITIGATIONS = {
    "M1049": AttackMitigation(
        id="M1049",
        name="Antivirus/Antimalware",
        description="Use signatures or heuristics to detect malicious software.",
        techniques_addressed=["T1566", "T1566.001", "T1566.002", "T1027", "T1027.001"],
        references=["https://attack.mitre.org/mitigations/M1049/"]
    ),
    "M1031": AttackMitigation(
        id="M1031",
        name="Network Intrusion Prevention",
        description="Use intrusion detection signatures to block traffic at network boundaries.",
        techniques_addressed=["T1566", "T1190", "T1046", "T1041", "T1567", "T1048"],
        references=["https://attack.mitre.org/mitigations/M1031/"]
    ),
    "M1017": AttackMitigation(
        id="M1017",
        name="User Training",
        description="Train users to be aware of access or manipulation attempts by an adversary.",
        techniques_addressed=["T1566", "T1566.001", "T1566.002", "T1204"],
        references=["https://attack.mitre.org/mitigations/M1017/"]
    ),
    "M1048": AttackMitigation(
        id="M1048",
        name="Application Isolation and Sandboxing",
        description="Restrict execution of code to a virtual environment on or in transit to "
                    "an endpoint system.",
        techniques_addressed=["T1190", "T1210"],
        references=["https://attack.mitre.org/mitigations/M1048/"]
    ),
    "M1030": AttackMitigation(
        id="M1030",
        name="Network Segmentation",
        description="Architect sections of the network to isolate critical systems, functions, "
                    "or resources.",
        techniques_addressed=["T1190", "T1021", "T1021.001", "T1210", "T1136"],
        references=["https://attack.mitre.org/mitigations/M1030/"]
    ),
    "M1038": AttackMitigation(
        id="M1038",
        name="Execution Prevention",
        description="Block execution of code on a system through application control, "
                    "script blocking, or antivirus/EDR capabilities.",
        techniques_addressed=["T1059", "T1059.001", "T1059.003"],
        references=["https://attack.mitre.org/mitigations/M1038/"]
    ),
    "M1026": AttackMitigation(
        id="M1026",
        name="Privileged Account Management",
        description="Manage the creation, modification, use, and permissions associated with "
                    "privileged accounts.",
        techniques_addressed=["T1059", "T1059.001", "T1053", "T1053.005", "T1136", "T1055",
                              "T1078", "T1053.005", "T1136.001", "T1055.012", "T1021.002", "T1110"],
        references=["https://attack.mitre.org/mitigations/M1026/"]
    ),
    "M1035": AttackMitigation(
        id="M1035",
        name="Limit Access to Resource Over Network",
        description="Prevent access to file shares, remote access, or other network resources "
                    "over the network.",
        techniques_addressed=["T1059", "T1021", "T1021.001", "T1021.002"],
        references=["https://attack.mitre.org/mitigations/M1035/"]
    ),
    "M1047": AttackMitigation(
        id="M1047",
        name="Audit",
        description="Perform audits or scans of systems, permissions, insecure software, "
                    "insecure configurations, etc. to identify potential weaknesses.",
        techniques_addressed=["T1053", "T1053.005", "T1547", "T1547.001", "T1070", "T1070.001",
                              "T1070.004", "T1562", "T1562.001"],
        references=["https://attack.mitre.org/mitigations/M1047/"]
    ),
    "M1018": AttackMitigation(
        id="M1018",
        name="User Account Management",
        description="Manage the creation, modification, and use of user accounts.",
        techniques_addressed=["T1547", "T1547.001", "T1078", "T1136", "T1136.001"],
        references=["https://attack.mitre.org/mitigations/M1018/"]
    ),
    "M1022": AttackMitigation(
        id="M1022",
        name="Restrict File and Directory Permissions",
        description="Restrict access by setting directory and file permissions that are not "
                    "specific to users or privileged accounts.",
        techniques_addressed=["T1547", "T1547.001", "T1003", "T1003.002"],
        references=["https://attack.mitre.org/mitigations/M1022/"]
    ),
    "M1040": AttackMitigation(
        id="M1040",
        name="Behavior Prevention on Endpoint",
        description="Use capabilities to prevent suspicious behavior patterns from occurring "
                    "on a system.",
        techniques_addressed=["T1055", "T1055.012", "T1027", "T1027.001"],
        references=["https://attack.mitre.org/mitigations/M1040/"]
    ),
    "M1055": AttackMitigation(
        id="M1055",
        name="Process Hollowing Detection",
        description="Detect and prevent process hollowing techniques.",
        techniques_addressed=["T1055", "T1055.012"],
        references=["https://attack.mitre.org/mitigations/M1040/"]
    ),
    "M1027": AttackMitigation(
        id="M1027",
        name="Password Policies",
        description="Set and enforce secure password policies for accounts.",
        techniques_addressed=["T1078", "T1003", "T1003.001", "T1110", "T1110.001", "T1110.003", "T1003.002"],
        references=["https://attack.mitre.org/mitigations/M1027/"]
    ),
    "M1032": AttackMitigation(
        id="M1032",
        name="Multi-factor Authentication",
        description="Use two or more pieces of evidence to authenticate a user.",
        techniques_addressed=["T1078", "T1110", "T1110.003", "T1021", "T1021.001"],
        references=["https://attack.mitre.org/mitigations/M1032/"]
    ),
    "M1041": AttackMitigation(
        id="M1041",
        name="Encrypt Sensitive Information",
        description="Protect sensitive information with encryption.",
        techniques_addressed=["T1070", "T1070.001", "T1070.004", "T1003", "T1003.001", "T1003.002",
                              "T1119", "T1005", "T1115", "T1567", "T1041"],
        references=["https://attack.mitre.org/mitigations/M1041/"]
    ),
    "M1029": AttackMitigation(
        id="M1029",
        name="Remote Data Storage",
        description="Store data in remote locations to prevent access from local system processes.",
        techniques_addressed=["T1070", "T1070.001"],
        references=["https://attack.mitre.org/mitigations/M1029/"]
    ),
    "M1025": AttackMitigation(
        id="M1025",
        name="Privileged Process Integrity",
        description="Protect processes with high privileges that can be used to interact with "
                    "critical system components.",
        techniques_addressed=["T1003", "T1003.001"],
        references=["https://attack.mitre.org/mitigations/M1025/"]
    ),
    "M1028": AttackMitigation(
        id="M1028",
        name="Operating System Configuration",
        description="Make configuration changes to harden the operating system.",
        techniques_addressed=["T1003", "T1003.001", "T1087", "T1087.001"],
        references=["https://attack.mitre.org/mitigations/M1028/"]
    ),
    "M1036": AttackMitigation(
        id="M1036",
        name="Account Use Policies",
        description="Configure features related to account use like login attempt lockouts, "
                    "specific login times, etc.",
        techniques_addressed=["T1110", "T1110.001", "T1110.003"],
        references=["https://attack.mitre.org/mitigations/M1036/"]
    ),
    "M1042": AttackMitigation(
        id="M1042",
        name="Disable or Remove Feature or Program",
        description="Remove or deny access to unnecessary and potentially vulnerable software "
                    "to prevent security risks.",
        techniques_addressed=["T1046", "T1021", "T1021.001", "T1021.002"],
        references=["https://attack.mitre.org/mitigations/M1042/"]
    ),
    "M1016": AttackMitigation(
        id="M1016",
        name="Vulnerability Scanning",
        description="Vulnerability scanning is used to find potentially exploitable software "
                    "vulnerabilities.",
        techniques_addressed=["T1190", "T1210"],
        references=["https://attack.mitre.org/mitigations/M1016/"]
    ),
    "M1024": AttackMitigation(
        id="M1024",
        name="Restrict Registry Permissions",
        description="Restrict the ability to modify certain hives or keys in the Windows Registry.",
        techniques_addressed=["T1562", "T1562.001"],
        references=["https://attack.mitre.org/mitigations/M1024/"]
    ),
    "M1057": AttackMitigation(
        id="M1057",
        name="Data Loss Prevention",
        description="Use products and capabilities to prevent data exfiltration.",
        techniques_addressed=["T1005", "T1115", "T1041", "T1567", "T1048"],
        references=["https://attack.mitre.org/mitigations/M1057/"]
    ),
    "M1037": AttackMitigation(
        id="M1037",
        name="Filter Network Traffic",
        description="Use network appliances to filter ingress or egress traffic and perform "
                    "protocol-based filtering.",
        techniques_addressed=["T1041", "T1048", "T1048.001", "T1048.002", "T1048.003"],
        references=["https://attack.mitre.org/mitigations/M1037/"]
    ),
}

# Common attack paths (APT patterns)
BUILTIN_ATTACK_PATHS = [
    AttackPath(
        name="Spearphishing to Credential Dumping",
        description="Common APT attack path starting with phishing and escalating to credential theft",
        sequence=["T1566.001", "T1059.001", "T1055", "T1055.012", "T1003", "T1003.001", "T1078"],
        threat_actors=["APT28", "APT29", "CozyBear", "FancyBear"],
        mitigations=["M1049", "M1031", "M1017", "M1038", "M1040", "M1027"]
    ),
    AttackPath(
        name="External Exploitation to Lateral Movement",
        description="Exploit public-facing application and move laterally through network",
        sequence=["T1190", "T1059", "T1053", "T1087", "T1046", "T1021", "T1021.002", "T1003"],
        threat_actors=["APT41", "HAFNIUM"],
        mitigations=["M1048", "M1030", "M1042", "M1026", "M1047"]
    ),
    AttackPath(
        name="Persistence and Privilege Escalation",
        description="Establish persistence and escalate privileges for long-term access",
        sequence=["T1547", "T1547.001", "T1055", "T1055.012", "T1078", "T1136", "T1136.001"],
        threat_actors=["Carbanak", "FIN7"],
        mitigations=["M1018", "M1040", "M1022", "M1047"]
    ),
    AttackPath(
        name="Ransomware Deployment Chain",
        description="Typical ransomware deployment attack chain",
        sequence=["T1566", "T1059", "T1055", "T1070", "T1070.001", "T1562", "T1562.001", "T1490"],
        threat_actors=["DarkSide", "REvil", "Conti"],
        mitigations=["M1049", "M1031", "M1040", "M1041", "M1029"]
    ),
    AttackPath(
        name="Data Exfiltration Pipeline",
        description="Collect and exfiltrate sensitive data",
        sequence=["T1087", "T1119", "T1005", "T1560", "T1041", "T1567"],
        threat_actors=["APT1", "APT28", "Lazarus"],
        mitigations=["M1041", "M1057", "M1031", "M1037"]
    ),
]


# =============================================================================
# MAIN FRAMEWORK CLASS
# =============================================================================

class AttackFramework:
    """
    Main interface for MITRE ATT&CK framework operations
    
    Provides comprehensive access to ATT&CK data including:
    - Technique lookup and search
    - Tactic and mitigation mapping
    - Detection recommendations
    - Coverage analysis
    - Alert-to-technique correlation
    - STIX/TAXII import support
    
    Attributes:
        techniques: Dictionary of all techniques indexed by ID
        tactics: Dictionary of all tactics indexed by ID
        mitigations: Dictionary of all mitigations indexed by ID
        attack_paths: List of known attack paths
        version: ATT&CK version in use
    """
    
    def __init__(self, data_path: Optional[str] = None):
        """
        Initialize the ATT&CK framework
        
        Args:
            data_path: Optional path to external ATT&CK JSON/STIX data
        """
        self.techniques: Dict[str, AttackTechnique] = {}
        self.tactics: Dict[str, AttackTactic] = {}
        self.mitigations: Dict[str, AttackMitigation] = {}
        self.attack_paths: List[AttackPath] = []
        self.version = "14.1"
        self.last_updated = datetime.now().isoformat()
        
        # Load built-in data
        self._load_builtin_data()
        
        # Load external data if provided
        if data_path:
            self.load_framework(data_path)
    
    def _load_builtin_data(self) -> None:
        """Load built-in ATT&CK v14 data"""
        self.techniques.update(BUILTIN_TECHNIQUES)
        self.tactics.update(BUILTIN_TACTICS)
        self.mitigations.update(BUILTIN_MITIGATIONS)
        self.attack_paths = BUILTIN_ATTACK_PATHS.copy()
    
    def load_framework(self, data_path: str, format_type: str = "auto") -> bool:
        """
        Load ATT&CK data from external source
        
        Args:
            data_path: Path to ATT&CK data file or directory
            format_type: Format of data ("json", "stix", "auto")
            
        Returns:
            True if loaded successfully, False otherwise
        """
        path = Path(data_path)
        
        if not path.exists():
            return False
        
        # Auto-detect format
        if format_type == "auto":
            if path.suffix.lower() in ['.json']:
                format_type = "json"
            elif path.suffix.lower() in ['.xml', '.stix']:
                format_type = "stix"
            else:
                format_type = "json"  # Default
        
        try:
            if format_type == "json":
                self._load_json_data(path)
            elif format_type == "stix":
                self._load_stix_data(path)
            return True
        except Exception as e:
            print(f"Error loading ATT&CK data: {e}")
            return False
    
    def _load_json_data(self, path: Path) -> None:
        """Load ATT&CK data from JSON file"""
        with open(path, 'r') as f:
            data = json.load(f)
        
        # Parse techniques
        if 'techniques' in data:
            for tech_data in data['techniques']:
                technique = AttackTechnique.from_dict(tech_data)
                self.techniques[technique.id] = technique
        
        # Parse tactics
        if 'tactics' in data:
            for tac_data in data['tactics']:
                tactic = AttackTactic.from_dict(tac_data)
                self.tactics[tactic.id] = tactic
        
        # Parse mitigations
        if 'mitigations' in data:
            for mit_data in data['mitigations']:
                mitigation = AttackMitigation.from_dict(mit_data)
                self.mitigations[mitigation.id] = mitigation
        
        # Update metadata
        if 'version' in data:
            self.version = data['version']
        if 'last_updated' in data:
            self.last_updated = data['last_updated']
    
    def _load_stix_data(self, path: Path) -> None:
        """
        Load ATT&CK data from STIX format
        
        Note: This is a simplified STIX loader. Full STIX 2.1 support
        would require additional parsing logic.
        """
        import xml.etree.ElementTree as ET
        
        tree = ET.parse(path)
        root = tree.getroot()
        
        # STIX namespace
        ns = {'stix': 'http://stix.mitre.org/stix-1'}
        
        # Parse TTPs (Tactics, Techniques, Procedures)
        for ttp in root.findall('.//stix:TTP', ns):
            # Extract technique data from STIX structure
            # This is simplified - full implementation would parse all STIX fields
            pass
    
    # -------------------------------------------------------------------------
    # LOOKUP METHODS
    # -------------------------------------------------------------------------
    
    def get_technique(self, technique_id: str) -> Optional[AttackTechnique]:
        """
        Get technique by ID
        
        Args:
            technique_id: Technique ID (e.g., "T1566", "T1566.001")
            
        Returns:
            AttackTechnique if found, None otherwise
        """
        # Normalize ID
        technique_id = technique_id.upper()
        return self.techniques.get(technique_id)
    
    def get_tactic(self, tactic_id: str) -> Optional[AttackTactic]:
        """
        Get tactic by ID
        
        Args:
            tactic_id: Tactic ID (e.g., "TA0001") or shortname (e.g., "initial-access")
            
        Returns:
            AttackTactic if found, None otherwise
        """
        tactic_id = tactic_id.upper()
        
        # Try direct ID lookup
        if tactic_id in self.tactics:
            return self.tactics[tactic_id]
        
        # Try shortname lookup
        for tactic in self.tactics.values():
            if tactic.shortname.lower() == tactic_id.lower():
                return tactic
        
        return None
    
    def get_mitigation(self, mitigation_id: str) -> Optional[AttackMitigation]:
        """
        Get mitigation by ID
        
        Args:
            mitigation_id: Mitigation ID (e.g., "M1049")
            
        Returns:
            AttackMitigation if found, None otherwise
        """
        mitigation_id = mitigation_id.upper()
        return self.mitigations.get(mitigation_id)
    
    # -------------------------------------------------------------------------
    # SEARCH METHODS
    # -------------------------------------------------------------------------
    
    def search_techniques(self, keyword: str, fields: Optional[List[str]] = None) -> List[AttackTechnique]:
        """
        Search techniques by keyword
        
        Args:
            keyword: Search term
            fields: Fields to search (default: name, description, id)
            
        Returns:
            List of matching techniques
        """
        if fields is None:
            fields = ['name', 'description', 'id']
        
        keyword_lower = keyword.lower()
        results = []
        
        for technique in self.techniques.values():
            for field_name in fields:
                value = getattr(technique, field_name, '')
                if value and keyword_lower in str(value).lower():
                    results.append(technique)
                    break
        
        return results
    
    def get_techniques_by_tactic(self, tactic: str) -> List[AttackTechnique]:
        """
        Get all techniques for a specific tactic
        
        Args:
            tactic: Tactic ID or shortname
            
        Returns:
            List of techniques in the tactic
        """
        tactic_obj = self.get_tactic(tactic)
        if not tactic_obj:
            return []
        
        # Search by tactic shortname
        return [
            tech for tech in self.techniques.values()
            if tech.tactic.lower() == tactic_obj.shortname.lower()
        ]
    
    def get_techniques_by_platform(self, platform: Union[str, AttackPlatform]) -> List[AttackTechnique]:
        """
        Get techniques applicable to a specific platform
        
        Args:
            platform: Platform name or AttackPlatform enum
            
        Returns:
            List of techniques for the platform
        """
        if isinstance(platform, str):
            platform = AttackPlatform(platform)
        
        return [
            tech for tech in self.techniques.values()
            if platform in tech.platforms
        ]
    
    def get_subtechniques(self, technique_id: str) -> List[AttackTechnique]:
        """
        Get all sub-techniques for a technique
        
        Args:
            technique_id: Parent technique ID
            
        Returns:
            List of sub-techniques
        """
        technique_id = technique_id.upper()
        parent = self.get_technique(technique_id)
        
        if not parent:
            return []
        
        subtechniques = []
        for sub_id in parent.sub_techniques:
            sub = self.get_technique(sub_id)
            if sub:
                subtechniques.append(sub)
        
        return subtechniques
    
    # -------------------------------------------------------------------------
    # DETECTION & MITIGATION METHODS
    # -------------------------------------------------------------------------
    
    def get_detection_for_technique(self, technique_id: str) -> str:
        """
        Get detection strategies for a technique
        
        Args:
            technique_id: Technique ID
            
        Returns:
            Detection recommendations
        """
        technique = self.get_technique(technique_id)
        if not technique:
            return ""
        
        detection_info = []
        
        # Add technique-specific detection
        if technique.detection:
            detection_info.append(f"Technique Detection:\n{technique.detection}")
        
        # Add data sources
        if technique.data_sources:
            sources_str = ", ".join([d.value for d in technique.data_sources])
            detection_info.append(f"Data Sources: {sources_str}")
        
        # Add parent technique detection if sub-technique
        if technique.is_subtechnique and technique.parent_technique:
            parent = self.get_technique(technique.parent_technique)
            if parent and parent.detection:
                detection_info.append(f"Parent Technique Detection:\n{parent.detection}")
        
        return "\n\n".join(detection_info)
    
    def get_mitigations_for_technique(self, technique_id: str) -> List[AttackMitigation]:
        """
        Get all mitigations that address a technique
        
        Args:
            technique_id: Technique ID
            
        Returns:
            List of applicable mitigations
        """
        technique_id = technique_id.upper()
        technique = self.get_technique(technique_id)
        
        if not technique:
            return []
        
        mitigations = []
        
        # Direct mitigations
        for mit_id in technique.mitigations:
            mitigation = self.get_mitigation(mit_id)
            if mitigation:
                mitigations.append(mitigation)
        
        # Parent technique mitigations if sub-technique
        if technique.is_subtechnique and technique.parent_technique:
            parent = self.get_technique(technique.parent_technique)
            if parent:
                for mit_id in parent.mitigations:
                    mitigation = self.get_mitigation(mit_id)
                    if mitigation and mitigation not in mitigations:
                        mitigations.append(mitigation)
        
        return mitigations
    
    def map_alert_to_technique(self, alert_data: Dict[str, Any]) -> List[Tuple[AttackTechnique, float]]:
        """
        Suggest technique mappings for an alert
        
        Args:
            alert_data: Alert information containing:
                - title/alert_name: Alert title
                - description: Alert description
                - event_type: Type of event
                - process_name: Process involved
                - command_line: Command executed
                - file_path: File affected
                
        Returns:
            List of (technique, confidence_score) tuples
        """
        suggestions = []
        
        # Extract keywords from alert
        keywords = []
        for field in ['title', 'alert_name', 'description', 'event_type', 
                      'process_name', 'command_line', 'file_path']:
            if field in alert_data and alert_data[field]:
                keywords.extend(str(alert_data[field]).lower().split())
        
        # Score techniques based on keyword matches
        for technique in self.techniques.values():
            score = 0.0
            text = f"{technique.name} {technique.description}".lower()
            
            for keyword in keywords:
                if len(keyword) > 3 and keyword in text:
                    score += 0.1
            
            # Boost score for exact process matches
            if 'process_name' in alert_data:
                proc = alert_data['process_name'].lower()
                if proc in text:
                    score += 0.3
            
            # Boost for data source matches
            if 'event_type' in alert_data:
                event = alert_data['event_type'].lower()
                for ds in technique.data_sources:
                    if event in ds.value.lower():
                        score += 0.2
            
            if score > 0.3:
                suggestions.append((technique, min(score, 1.0)))
        
        # Sort by confidence
        suggestions.sort(key=lambda x: x[1], reverse=True)
        return suggestions[:10]  # Top 10
    
    # -------------------------------------------------------------------------
    # ATTACK PATH METHODS
    # -------------------------------------------------------------------------
    
    def get_attack_path(self, path_name: Optional[str] = None, 
                        technique_id: Optional[str] = None) -> List[AttackPath]:
        """
        Get common attack paths
        
        Args:
            path_name: Specific path name to retrieve
            technique_id: Get paths containing this technique
            
        Returns:
            List of attack paths
        """
        if path_name:
            return [p for p in self.attack_paths if p.name.lower() == path_name.lower()]
        
        if technique_id:
            technique_id = technique_id.upper()
            return [
                p for p in self.attack_paths
                if technique_id in [t.upper() for t in p.sequence]
            ]
        
        return self.attack_paths
    
    def get_related_techniques(self, technique_id: str) -> List[AttackTechnique]:
        """
        Get techniques commonly used with the given technique
        
        Args:
            technique_id: Technique ID
            
        Returns:
            List of related techniques
        """
        technique_id = technique_id.upper()
        related = set()
        
        # Find techniques in same attack paths
        for path in self.attack_paths:
            if technique_id in [t.upper() for t in path.sequence]:
                for t_id in path.sequence:
                    if t_id.upper() != technique_id:
                        related.add(t_id.upper())
        
        # Return technique objects
        return [self.get_technique(tid) for tid in related if self.get_technique(tid)]
    
    # -------------------------------------------------------------------------
    # ANALYTICS METHODS
    # -------------------------------------------------------------------------
    
    def get_coverage_matrix(self, detected_techniques: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Generate detection coverage matrix
        
        Args:
            detected_techniques: List of technique IDs currently detected
            
        Returns:
            Coverage matrix by tactic
        """
        if detected_techniques is None:
            detected_techniques = []
        
        detected_set = set(t.upper() for t in detected_techniques)
        matrix = {}
        
        for tactic in self.tactics.values():
            tactic_techniques = self.get_techniques_by_tactic(tactic.shortname)
            
            covered = []
            uncovered = []
            
            for tech in tactic_techniques:
                if tech.id in detected_set:
                    covered.append(tech.id)
                else:
                    uncovered.append(tech.id)
            
            matrix[tactic.shortname] = {
                'tactic_name': tactic.name,
                'total': len(tactic_techniques),
                'covered': len(covered),
                'uncovered': len(uncovered),
                'coverage_percent': (len(covered) / len(tactic_techniques) * 100) if tactic_techniques else 0,
                'covered_techniques': covered,
                'uncovered_techniques': uncovered
            }
        
        return matrix
    
    def get_gap_analysis(self, detected_techniques: List[str], 
                         priority_tactics: Optional[List[str]] = None) -> List[CoverageGap]:
        """
        Identify detection coverage gaps
        
        Args:
            detected_techniques: List of technique IDs currently detected
            priority_tactics: Tactics to prioritize in analysis
            
        Returns:
            List of coverage gaps
        """
        detected_set = set(t.upper() for t in detected_techniques)
        gaps = []
        
        # Priority tactics (high business impact)
        if priority_tactics is None:
            priority_tactics = ['credential-access', 'lateral-movement', 'exfiltration']
        
        for tactic in self.tactics.values():
            tactic_techniques = self.get_techniques_by_tactic(tactic.shortname)
            
            for tech in tactic_techniques:
                if tech.id not in detected_set:
                    # Determine severity
                    if tactic.shortname in priority_tactics:
                        severity = "CRITICAL" if tactic.shortname == 'credential-access' else "HIGH"
                    else:
                        severity = "MEDIUM"
                    
                    # Determine reason
                    if tech.is_subtechnique:
                        reason = f"Sub-technique of {tech.parent_technique} not covered"
                    else:
                        reason = "No detection rules mapped to this technique"
                    
                    # Generate recommendations
                    recommendations = []
                    if tech.data_sources:
                        ds_list = ", ".join([d.value for d in tech.data_sources[:3]])
                        recommendations.append(f"Implement detection based on: {ds_list}")
                    
                    if tech.detection:
                        recommendations.append("Review ATT&CK detection guidance for specific rules")
                    
                    recommendations.append(f"Reference: {tech.references[0] if tech.references else 'https://attack.mitre.org/'}")
                    
                    gaps.append(CoverageGap(
                        technique_id=tech.id,
                        tactic=tactic.shortname,
                        severity=severity,
                        reason=reason,
                        recommendations=recommendations
                    ))
        
        # Sort by severity
        severity_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
        gaps.sort(key=lambda x: severity_order.get(x.severity, 4))
        
        return gaps
    
    def technique_frequency_stats(self, technique_counts: Dict[str, int]) -> Dict[str, Any]:
        """
        Analyze technique frequency in environment
        
        Args:
            technique_counts: Dictionary of technique_id -> count
            
        Returns:
            Statistics about technique frequency
        """
        if not technique_counts:
            return {
                'most_common': [],
                'by_tactic': {},
                'total_detections': 0,
                'unique_techniques': 0
            }
        
        # Sort by frequency
        sorted_techniques = sorted(
            technique_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # Group by tactic
        by_tactic = {}
        for tech_id, count in technique_counts.items():
            tech = self.get_technique(tech_id)
            if tech:
                tactic = tech.tactic
                if tactic not in by_tactic:
                    by_tactic[tactic] = []
                by_tactic[tactic].append({'technique': tech_id, 'count': count})
        
        # Get technique details for top 10
        most_common = []
        for tech_id, count in sorted_techniques[:10]:
            tech = self.get_technique(tech_id)
            if tech:
                most_common.append({
                    'id': tech_id,
                    'name': tech.name,
                    'tactic': tech.tactic,
                    'count': count
                })
        
        return {
            'most_common': most_common,
            'by_tactic': by_tactic,
            'total_detections': sum(technique_counts.values()),
            'unique_techniques': len(technique_counts)
        }
    
    # -------------------------------------------------------------------------
    # SERIALIZATION METHODS
    # -------------------------------------------------------------------------
    
    def to_json(self, include_builtin: bool = True) -> str:
        """
        Export framework data to JSON
        
        Args:
            include_builtin: Include built-in data in export
            
        Returns:
            JSON string
        """
        data = {
            'version': self.version,
            'last_updated': self.last_updated,
            'techniques': [t.to_dict() for t in self.techniques.values()],
            'tactics': [t.to_dict() for t in self.tactics.values()],
            'mitigations': [m.to_dict() for m in self.mitigations.values()]
        }
        
        return json.dumps(data, indent=2)
    
    def export_coverage_report(self, detected_techniques: List[str], 
                               output_path: Optional[str] = None) -> str:
        """
        Generate a coverage report
        
        Args:
            detected_techniques: List of detected technique IDs
            output_path: Optional path to write report
            
        Returns:
            Report as string
        """
        matrix = self.get_coverage_matrix(detected_techniques)
        gaps = self.get_gap_analysis(detected_techniques)
        
        report_lines = [
            "=" * 80,
            "MITRE ATT&CK DETECTION COVERAGE REPORT",
            "=" * 80,
            f"Generated: {datetime.now().isoformat()}",
            f"ATT&CK Version: {self.version}",
            f"Total Techniques in Framework: {len(self.techniques)}",
            f"Detected Techniques: {len(detected_techniques)}",
            "",
            "-" * 80,
            "COVERAGE BY TACTIC",
            "-" * 80,
        ]
        
        for tactic_shortname, data in sorted(matrix.items()):
            report_lines.append(
                f"\n{data['tactic_name']} ({tactic_shortname}): "
                f"{data['covered']}/{data['total']} ({data['coverage_percent']:.1f}%)"
            )
            if data['uncovered_techniques']:
                report_lines.append(f"  Uncovered: {', '.join(data['uncovered_techniques'][:5])}")
        
        report_lines.extend([
            "",
            "-" * 80,
            "TOP COVERAGE GAPS",
            "-" * 80,
        ])
        
        for gap in gaps[:20]:
            report_lines.extend([
                f"\n[{gap.severity}] {gap.technique_id} ({gap.tactic})",
                f"  Reason: {gap.reason}",
                f"  Recommendations:",
            ])
            for rec in gap.recommendations:
                report_lines.append(f"    - {rec}")
        
        report_lines.append("\n" + "=" * 80)
        
        report = "\n".join(report_lines)
        
        if output_path:
            with open(output_path, 'w') as f:
                f.write(report)
        
        return report
    
    # -------------------------------------------------------------------------
    # UTILITY METHODS
    # -------------------------------------------------------------------------
    
    def get_all_techniques(self) -> List[AttackTechnique]:
        """Get all techniques"""
        return list(self.techniques.values())
    
    def get_all_tactics(self) -> List[AttackTactic]:
        """Get all tactics"""
        return list(self.tactics.values())
    
    def get_all_mitigations(self) -> List[AttackMitigation]:
        """Get all mitigations"""
        return list(self.mitigations.values())
    
    def get_technique_count(self) -> int:
        """Get total number of techniques"""
        return len(self.techniques)
    
    def get_tactic_count(self) -> int:
        """Get total number of tactics"""
        return len(self.tactics)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_framework(data_path: Optional[str] = None) -> AttackFramework:
    """Create a new ATT&CK framework instance"""
    return AttackFramework(data_path)


def get_default_framework() -> AttackFramework:
    """Get default framework with built-in data"""
    return AttackFramework()


# =============================================================================
# MODULE ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    # Demo usage
    framework = get_default_framework()
    
    print(f"MITRE ATT&CK Framework v{framework.version}")
    print(f"Techniques: {framework.get_technique_count()}")
    print(f"Tactics: {framework.get_tactic_count()}")
    print(f"Mitigations: {len(framework.mitigations)}")
    
    # Example lookup
    print("\n--- Example: Get Technique T1566 ---")
    tech = framework.get_technique("T1566")
    if tech:
        print(f"Name: {tech.name}")
        print(f"Tactic: {tech.tactic}")
        print(f"Platforms: {[p.value for p in tech.platforms]}")
        print(f"Sub-techniques: {tech.sub_techniques}")
    
    # Example search
    print("\n--- Example: Search for 'phishing' ---")
    results = framework.search_techniques("phishing")
    for r in results:
        print(f"  {r.id}: {r.name}")
    
    # Example coverage
    print("\n--- Example: Coverage Matrix ---")
    sample_detected = ["T1566", "T1059", "T1059.001", "T1003", "T1087"]
    matrix = framework.get_coverage_matrix(sample_detected)
    for tactic, data in list(matrix.items())[:3]:
        print(f"  {data['tactic_name']}: {data['coverage_percent']:.1f}%")
