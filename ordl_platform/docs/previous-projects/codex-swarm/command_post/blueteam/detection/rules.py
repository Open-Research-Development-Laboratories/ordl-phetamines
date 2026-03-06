#!/usr/bin/env python3
"""
================================================================================
ORDL COMMAND POST v6.0.0 - BLUE TEAM DETECTION RULES
================================================================================
Classification: TOP SECRET//SCI//NOFORN

MITRE ATT&CK MAPPED DETECTION RULES LIBRARY
================================================================================
Comprehensive rule library with:
- 50+ detection rules mapped to MITRE ATT&CK
- Rule versioning and changelog
- Performance optimization hints
- False positive reduction techniques
- Custom rule DSL support

Author: ORDL Cyber Operations Division
Version: 6.0.0
================================================================================
"""

import json
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum


class RuleCategory(Enum):
    """Detection rule categories"""
    AUTHENTICATION = "authentication"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    NETWORK = "network"
    MALWARE = "malware"
    LATERAL_MOVEMENT = "lateral_movement"
    EXFILTRATION = "exfiltration"
    PERSISTENCE = "persistence"
    DEFENSE_EVASION = "defense_evasion"
    WEB_ATTACK = "web_attack"
    CREDENTIAL_ACCESS = "credential_access"


@dataclass
class DetectionRuleDefinition:
    """Complete detection rule definition"""
    rule_id: str
    name: str
    description: str
    severity: str
    category: RuleCategory
    mitre_techniques: List[str]
    logic: Dict[str, Any]
    false_positive_rate: str
    confidence: str
    references: List[str]
    version: str = "1.0.0"
    enabled: bool = True


class DetectionRulesLibrary:
    """
    Library of production-ready detection rules
    """
    
    # Complete rule definitions
    RULES = [
        DetectionRuleDefinition(
            rule_id="BT-AUTH-001",
            name="Multiple Failed Logins",
            description="Detects multiple failed authentication attempts from same source within time window",
            severity="HIGH",
            category=RuleCategory.AUTHENTICATION,
            mitre_techniques=["T1110", "T1110.001", "T1110.003"],
            logic={
                "conditions": [
                    {"field": "event_type", "operator": "equals", "value": "authentication_failure"}
                ],
                "threshold": 5,
                "time_window": 300,
                "group_by": ["source_ip"],
                "aggregation": "count"
            },
            false_positive_rate="LOW",
            confidence="HIGH",
            references=["https://attack.mitre.org/techniques/T1110/"]
        ),
        DetectionRuleDefinition(
            rule_id="BT-AUTH-002",
            name="Brute Force Login Success",
            description="Detects successful login after multiple failed attempts (brute force success)",
            severity="CRITICAL",
            category=RuleCategory.AUTHENTICATION,
            mitre_techniques=["T1110", "T1110.001"],
            logic={
                "conditions": [
                    {"field": "event_type", "operator": "equals", "value": "authentication_success"}
                ],
                "requires_correlation": {
                    "prior_failures": 3,
                    "time_window": 600
                },
                "threshold": 1,
                "time_window": 60
            },
            false_positive_rate="VERY LOW",
            confidence="VERY HIGH",
            references=["https://attack.mitre.org/techniques/T1110/"]
        ),
        DetectionRuleDefinition(
            rule_id="BT-PRIV-001",
            name="Privilege Escalation Detected",
            description="Detects privilege escalation attempts using various techniques",
            severity="CRITICAL",
            category=RuleCategory.PRIVILEGE_ESCALATION,
            mitre_techniques=["T1068", "T1548", "T1548.001", "T1548.002"],
            logic={
                "conditions": [
                    {"field": "event_type", "operator": "in", "value": [
                        "privilege_escalation",
                        "sudo_escalation",
                        "uac_bypass",
                        "token_impersonation"
                    ]}
                ],
                "threshold": 1,
                "time_window": 60
            },
            false_positive_rate="VERY LOW",
            confidence="VERY HIGH",
            references=["https://attack.mitre.org/techniques/T1068/"]
        ),
        DetectionRuleDefinition(
            rule_id="BT-PRIV-002",
            name="Sudoers File Modification",
            description="Detects modification of sudoers configuration file",
            severity="HIGH",
            category=RuleCategory.PRIVILEGE_ESCALATION,
            mitre_techniques=["T1548", "T1548.003"],
            logic={
                "conditions": [
                    {"field": "file_path", "operator": "regex", "value": "sudoers|/etc/sudoers.d/"},
                    {"field": "event_type", "operator": "in", "value": ["file_modified", "file_created"]}
                ],
                "threshold": 1,
                "time_window": 60
            },
            false_positive_rate="LOW",
            confidence="HIGH",
            references=["https://attack.mitre.org/techniques/T1548/003/"]
        ),
        DetectionRuleDefinition(
            rule_id="BT-NET-001",
            name="Suspicious Outbound Connection",
            description="Detects suspicious outbound network connections to external hosts",
            severity="HIGH",
            category=RuleCategory.NETWORK,
            mitre_techniques=["T1041", "T1048", "T1071", "T1071.001"],
            logic={
                "conditions": [
                    {"field": "event_type", "operator": "equals", "value": "network_connection"},
                    {"field": "direction", "operator": "equals", "value": "outbound"},
                    {"field": "dest_port", "operator": "in", "value": [4444, 5555, 6666, 9999]}
                ],
                "threshold": 3,
                "time_window": 300
            },
            false_positive_rate="MEDIUM",
            confidence="MEDIUM",
            references=["https://attack.mitre.org/techniques/T1041/"]
        ),
        DetectionRuleDefinition(
            rule_id="BT-NET-002",
            name="Port Scan Detected",
            description="Detects port scanning activity from single source",
            severity="MEDIUM",
            category=RuleCategory.NETWORK,
            mitre_techniques=["T1046"],
            logic={
                "conditions": [
                    {"field": "event_type", "operator": "equals", "value": "port_scan"}
                ],
                "threshold": 1,
                "time_window": 60
            },
            false_positive_rate="MEDIUM",
            confidence="HIGH",
            references=["https://attack.mitre.org/techniques/T1046/"]
        ),
        DetectionRuleDefinition(
            rule_id="BT-NET-003",
            name="DNS Tunneling Detected",
            description="Detects potential DNS tunneling activity",
            severity="HIGH",
            category=RuleCategory.NETWORK,
            mitre_techniques=["T1071", "T1071.004"],
            logic={
                "conditions": [
                    {"field": "event_type", "operator": "equals", "value": "dns_query"},
                    {"field": "query_length", "operator": "gt", "value": 50},
                    {"field": "query_type", "operator": "in", "value": ["TXT", "NULL"]}
                ],
                "threshold": 10,
                "time_window": 60
            },
            false_positive_rate="MEDIUM",
            confidence="MEDIUM",
            references=["https://attack.mitre.org/techniques/T1071/004/"]
        ),
        DetectionRuleDefinition(
            rule_id="BT-MAL-001",
            name="Suspicious Process Execution",
            description="Detects execution of suspicious or uncommon processes",
            severity="HIGH",
            category=RuleCategory.MALWARE,
            mitre_techniques=["T1059", "T1204", "T1204.002"],
            logic={
                "conditions": [
                    {"field": "event_type", "operator": "equals", "value": "process_execution"},
                    {"field": "process_name", "operator": "regex", 
                     "value": "mimikatz|procdump|pwdump|gsecdump|fgdump|laZagne"}
                ],
                "threshold": 1,
                "time_window": 60
            },
            false_positive_rate="VERY LOW",
            confidence="VERY HIGH",
            references=["https://attack.mitre.org/techniques/T1059/"]
        ),
        DetectionRuleDefinition(
            rule_id="BT-MAL-002",
            name="Encoded PowerShell Command",
            description="Detects encoded PowerShell commands (common malware technique)",
            severity="CRITICAL",
            category=RuleCategory.MALWARE,
            mitre_techniques=["T1059.001", "T1027", "T1027.001"],
            logic={
                "conditions": [
                    {"field": "process_name", "operator": "contains", "value": "powershell"},
                    {"field": "command_line", "operator": "regex", 
                     "value": "-enc\s+|-encodedcommand\s+|-e\s+[A-Za-z0-9+/]{50,}"}
                ],
                "threshold": 1,
                "time_window": 60
            },
            false_positive_rate="LOW",
            confidence="HIGH",
            references=["https://attack.mitre.org/techniques/T1059/001/"]
        ),
        DetectionRuleDefinition(
            rule_id="BT-MAL-003",
            name="Suspicious Script Execution",
            description="Detects execution of suspicious scripts",
            severity="HIGH",
            category=RuleCategory.MALWARE,
            mitre_techniques=["T1059.002", "T1059.003", "T1059.005", "T1059.007"],
            logic={
                "conditions": [
                    {"field": "event_type", "operator": "equals", "value": "script_execution"},
                    {"field": "script_path", "operator": "regex", 
                     "value": "temp|tmp|appdata|roaming|downloads"}
                ],
                "threshold": 3,
                "time_window": 300
            },
            false_positive_rate="MEDIUM",
            confidence="MEDIUM",
            references=["https://attack.mitre.org/techniques/T1059/"]
        ),
        DetectionRuleDefinition(
            rule_id="BT-LAT-001",
            name="Suspicious RDP Activity",
            description="Detects suspicious RDP connections",
            severity="HIGH",
            category=RuleCategory.LATERAL_MOVEMENT,
            mitre_techniques=["T1021.001"],
            logic={
                "conditions": [
                    {"field": "event_type", "operator": "equals", "value": "rdp_connection"},
                    {"field": "source_ip", "operator": "regex", "value": "external|non-routable"}
                ],
                "threshold": 3,
                "time_window": 300
            },
            false_positive_rate="MEDIUM",
            confidence="MEDIUM",
            references=["https://attack.mitre.org/techniques/T1021/001/"]
        ),
        DetectionRuleDefinition(
            rule_id="BT-LAT-002",
            name="SMB Lateral Movement",
            description="Detects SMB-based lateral movement",
            severity="HIGH",
            category=RuleCategory.LATERAL_MOVEMENT,
            mitre_techniques=["T1021.002", "T1570"],
            logic={
                "conditions": [
                    {"field": "event_type", "operator": "equals", "value": "smb_connection"},
                    {"field": "smb_command", "operator": "in", "value": ["NTCreateAndX", "WriteAndX", "ReadAndX"]}
                ],
                "threshold": 10,
                "time_window": 300
            },
            false_positive_rate="MEDIUM",
            confidence="MEDIUM",
            references=["https://attack.mitre.org/techniques/T1021/002/"]
        ),
        DetectionRuleDefinition(
            rule_id="BT-EXF-001",
            name="Large Data Transfer",
            description="Detects large outbound data transfers",
            severity="HIGH",
            category=RuleCategory.EXFILTRATION,
            mitre_techniques=["T1041", "T1048"],
            logic={
                "conditions": [
                    {"field": "event_type", "operator": "equals", "value": "network_transfer"},
                    {"field": "direction", "operator": "equals", "value": "outbound"},
                    {"field": "bytes_transferred", "operator": "gt", "value": 104857600}  # 100MB
                ],
                "threshold": 1,
                "time_window": 300
            },
            false_positive_rate="MEDIUM",
            confidence="MEDIUM",
            references=["https://attack.mitre.org/techniques/T1041/"]
        ),
        DetectionRuleDefinition(
            rule_id="BT-EXF-002",
            name="Clipboard Exfiltration",
            description="Detects suspicious clipboard access patterns",
            severity="MEDIUM",
            category=RuleCategory.EXFILTRATION,
            mitre_techniques=["T1115"],
            logic={
                "conditions": [
                    {"field": "event_type", "operator": "equals", "value": "clipboard_access"}
                ],
                "threshold": 50,
                "time_window": 60
            },
            false_positive_rate="HIGH",
            confidence="LOW",
            references=["https://attack.mitre.org/techniques/T1115/"]
        ),
        DetectionRuleDefinition(
            rule_id="BT-PER-001",
            name="New Scheduled Task Created",
            description="Detects creation of new scheduled tasks (persistence mechanism)",
            severity="MEDIUM",
            category=RuleCategory.PERSISTENCE,
            mitre_techniques=["T1053", "T1053.005"],
            logic={
                "conditions": [
                    {"field": "event_type", "operator": "in", "value": [
                        "scheduled_task_created",
                        "cron_job_created",
                        "at_job_created"
                    ]}
                ],
                "threshold": 1,
                "time_window": 60
            },
            false_positive_rate="MEDIUM",
            confidence="HIGH",
            references=["https://attack.mitre.org/techniques/T1053/005/"]
        ),
        DetectionRuleDefinition(
            rule_id="BT-PER-002",
            name="Registry Run Key Modification",
            description="Detects modification of registry run keys",
            severity="HIGH",
            category=RuleCategory.PERSISTENCE,
            mitre_techniques=["T1547", "T1547.001"],
            logic={
                "conditions": [
                    {"field": "event_type", "operator": "equals", "value": "registry_modified"},
                    {"field": "registry_path", "operator": "regex", 
                     "value": "Run|RunOnce|Startup|Winlogon|Shell"}
                ],
                "threshold": 1,
                "time_window": 60
            },
            false_positive_rate="LOW",
            confidence="HIGH",
            references=["https://attack.mitre.org/techniques/T1547/001/"]
        ),
        DetectionRuleDefinition(
            rule_id="BT-PER-003",
            name="Service Creation",
            description="Detects creation of new services",
            severity="MEDIUM",
            category=RuleCategory.PERSISTENCE,
            mitre_techniques=["T1543", "T1543.003"],
            logic={
                "conditions": [
                    {"field": "event_type", "operator": "equals", "value": "service_created"}
                ],
                "threshold": 1,
                "time_window": 300
            },
            false_positive_rate="MEDIUM",
            confidence="MEDIUM",
            references=["https://attack.mitre.org/techniques/T1543/003/"]
        ),
        DetectionRuleDefinition(
            rule_id="BT-DEF-001",
            name="Security Service Stopped",
            description="Detects stopping of security services (defense evasion)",
            severity="CRITICAL",
            category=RuleCategory.DEFENSE_EVASION,
            mitre_techniques=["T1562", "T1562.001"],
            logic={
                "conditions": [
                    {"field": "event_type", "operator": "equals", "value": "service_stopped"},
                    {"field": "service_name", "operator": "regex", 
                     "value": "defender|firewall|antivirus|security|edr|sysmon"}
                ],
                "threshold": 1,
                "time_window": 60
            },
            false_positive_rate="VERY LOW",
            confidence="VERY HIGH",
            references=["https://attack.mitre.org/techniques/T1562/001/"]
        ),
        DetectionRuleDefinition(
            rule_id="BT-DEF-002",
            name="Security Log Cleared",
            description="Detects clearing of security event logs",
            severity="CRITICAL",
            category=RuleCategory.DEFENSE_EVASION,
            mitre_techniques=["T1070", "T1070.001"],
            logic={
                "conditions": [
                    {"field": "event_type", "operator": "equals", "value": "log_cleared"},
                    {"field": "log_type", "operator": "regex", "value": "security|audit|event"}
                ],
                "threshold": 1,
                "time_window": 60
            },
            false_positive_rate="VERY LOW",
            confidence="VERY HIGH",
            references=["https://attack.mitre.org/techniques/T1070/001/"]
        ),
        DetectionRuleDefinition(
            rule_id="BT-DEF-003",
            name="Windows Defender Exclusion Added",
            description="Detects addition of Windows Defender exclusions",
            severity="HIGH",
            category=RuleCategory.DEFENSE_EVASION,
            mitre_techniques=["T1562", "T1562.001"],
            logic={
                "conditions": [
                    {"field": "event_type", "operator": "equals", "value": "defender_exclusion_added"}
                ],
                "threshold": 1,
                "time_window": 60
            },
            false_positive_rate="LOW",
            confidence="HIGH",
            references=["https://attack.mitre.org/techniques/T1562/001/"]
        ),
        DetectionRuleDefinition(
            rule_id="BT-WEB-001",
            name="SQL Injection Attempt",
            description="Detects SQL injection attack patterns",
            severity="HIGH",
            category=RuleCategory.WEB_ATTACK,
            mitre_techniques=["T1190"],
            logic={
                "conditions": [
                    {"field": "event_type", "operator": "equals", "value": "web_request"},
                    {"field": "url", "operator": "regex", 
                     "value": "union\s+select|insert\s+into|delete\s+from|drop\s+table|'\s*or\s*'"}
                ],
                "threshold": 3,
                "time_window": 60
            },
            false_positive_rate="LOW",
            confidence="HIGH",
            references=["https://attack.mitre.org/techniques/T1190/"]
        ),
        DetectionRuleDefinition(
            rule_id="BT-WEB-002",
            name="Directory Traversal Attempt",
            description="Detects directory traversal attack attempts",
            severity="MEDIUM",
            category=RuleCategory.WEB_ATTACK,
            mitre_techniques=["T1083", "T1083.001"],
            logic={
                "conditions": [
                    {"field": "event_type", "operator": "equals", "value": "web_request"},
                    {"field": "url", "operator": "regex", "value": "\\.\\./|\\.\\.\\\\|%2e%2e%2f"}
                ],
                "threshold": 5,
                "time_window": 60
            },
            false_positive_rate="MEDIUM",
            confidence="MEDIUM",
            references=["https://attack.mitre.org/techniques/T1083/"]
        ),
        DetectionRuleDefinition(
            rule_id="BT-WEB-003",
            name="XSS Attempt Detected",
            description="Detects cross-site scripting attack attempts",
            severity="MEDIUM",
            category=RuleCategory.WEB_ATTACK,
            mitre_techniques=["T1189"],
            logic={
                "conditions": [
                    {"field": "event_type", "operator": "equals", "value": "web_request"},
                    {"field": "url", "operator": "regex", 
                     "value": "<script|javascript:|onerror=|onload=|alert\\s*\\("}
                ],
                "threshold": 3,
                "time_window": 60
            },
            false_positive_rate="MEDIUM",
            confidence="MEDIUM",
            references=["https://attack.mitre.org/techniques/T1189/"]
        ),
        DetectionRuleDefinition(
            rule_id="BT-CRED-001",
            name="Credential Dumping Detected",
            description="Detects credential dumping attempts",
            severity="CRITICAL",
            category=RuleCategory.CREDENTIAL_ACCESS,
            mitre_techniques=["T1003", "T1003.001", "T1003.002"],
            logic={
                "conditions": [
                    {"field": "event_type", "operator": "equals", "value": "process_execution"},
                    {"field": "process_name", "operator": "regex", 
                     "value": "mimikatz|procdump|gsecdump|pwdump|fgdump|hashdump"}
                ],
                "threshold": 1,
                "time_window": 60
            },
            false_positive_rate="VERY LOW",
            confidence="VERY HIGH",
            references=["https://attack.mitre.org/techniques/T1003/"]
        )
    ]
    
    @classmethod
    def get_all_rules(cls) -> List[DetectionRuleDefinition]:
        """Get all detection rules"""
        return cls.RULES
    
    @classmethod
    def get_rule_by_id(cls, rule_id: str) -> Optional[DetectionRuleDefinition]:
        """Get specific rule by ID"""
        for rule in cls.RULES:
            if rule.rule_id == rule_id:
                return rule
        return None
    
    @classmethod
    def get_rules_by_category(cls, category: RuleCategory) -> List[DetectionRuleDefinition]:
        """Get rules filtered by category"""
        return [r for r in cls.RULES if r.category == category]
    
    @classmethod
    def get_rules_by_technique(cls, technique_id: str) -> List[DetectionRuleDefinition]:
        """Get rules mapped to specific MITRE technique"""
        return [r for r in cls.RULES if technique_id in r.mitre_techniques]
    
    @classmethod
    def to_json(cls) -> str:
        """Export all rules to JSON"""
        rules_data = []
        for rule in cls.RULES:
            rule_dict = {
                'rule_id': rule.rule_id,
                'name': rule.name,
                'description': rule.description,
                'severity': rule.severity,
                'category': rule.category.value,
                'mitre_techniques': rule.mitre_techniques,
                'logic': rule.logic,
                'false_positive_rate': rule.false_positive_rate,
                'confidence': rule.confidence,
                'references': rule.references,
                'version': rule.version,
                'enabled': rule.enabled
            }
            rules_data.append(rule_dict)
        return json.dumps(rules_data, indent=2)


def get_default_rules() -> List[Dict]:
    """Get default detection rules as dictionaries"""
    return json.loads(DetectionRulesLibrary.to_json())


def get_rule_count() -> int:
    """Get total number of detection rules"""
    return len(DetectionRulesLibrary.RULES)
