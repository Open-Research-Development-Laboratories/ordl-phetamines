#!/usr/bin/env python3
"""
Defensive Skills - 25 Skills
Blue team operations, detection, incident response
"""

DEFENSIVE_SKILLS = [
    # Tier 1 - Monitoring
    {
        "id": "def_mon_sigma",
        "name": "Sigma Rule Analysis",
        "description": "Analyze logs with Sigma rules",
        "category": "defensive",
        "tier": 1,
        "params_schema": {
            "logs": {"type": "string", "required": True},
            "rules": {"type": "string", "default": "rules/"},
            "format": {"type": "string", "default": "json"}
        }
    },
    {
        "id": "def_mon_yara",
        "name": "YARA Scan",
        "description": "File analysis with YARA rules",
        "category": "defensive",
        "tier": 1,
        "params_schema": {
            "path": {"type": "string", "required": True},
            "rules": {"type": "string", "default": "rules/"},
            "recursive": {"type": "boolean", "default": True}
        }
    },
    {
        "id": "def_mon_hunt",
        "name": "Threat Hunting",
        "description": "IOC-based threat hunting",
        "category": "defensive",
        "tier": 1,
        "params_schema": {
            "iocs": {"type": "list", "required": True},
            "scope": {"type": "string", "default": "network"},
            "timeframe": {"type": "string", "default": "24h"}
        }
    },
    {
        "id": "def_mon_suricata",
        "name": "Suricata Analysis",
        "description": "IDS alert analysis and correlation",
        "category": "defensive",
        "tier": 1,
        "params_schema": {
            "eve_json": {"type": "string", "required": True},
            "severity": {"type": "list", "default": ["high", "critical"]}
        }
    },
    {
        "id": "def_mon_osquery",
        "name": "OSQuery Investigation",
        "description": "Endpoint investigation with OSQuery",
        "category": "defensive",
        "tier": 1,
        "params_schema": {
            "query": {"type": "string", "required": True},
            "hosts": {"type": "list", "default": []}
        }
    },
    
    # Tier 1 - Log Analysis
    {
        "id": "def_log_splunk",
        "name": "Splunk Query",
        "description": "Execute Splunk SPL queries",
        "category": "defensive",
        "tier": 1,
        "params_schema": {
            "query": {"type": "string", "required": True},
            "earliest": {"type": "string", "default": "-24h"},
            "latest": {"type": "string", "default": "now"}
        }
    },
    {
        "id": "def_log_elastic",
        "name": "Elasticsearch Query",
        "description": "Query Elasticsearch/Lucene",
        "category": "defensive",
        "tier": 1,
        "params_schema": {
            "index": {"type": "string", "required": True},
            "query": {"type": "dict", "required": True}
        }
    },
    {
        "id": "def_log_windows",
        "name": "Windows Event Analysis",
        "description": "Analyze Windows event logs",
        "category": "defensive",
        "tier": 1,
        "params_schema": {
            "event_ids": {"type": "list", "default": []},
            "timeframe": {"type": "string", "default": "24h"}
        }
    },
    
    # Tier 2 - Forensics
    {
        "id": "def_for_disk",
        "name": "Disk Forensics",
        "description": "Disk image analysis",
        "category": "defensive",
        "tier": 2,
        "params_schema": {
            "image": {"type": "string", "required": True},
            "format": {"type": "string", "default": "raw"},
            "operations": {"type": "list", "default": ["timeline"]}
        },
        "timeout": 1800
    },
    {
        "id": "def_for_memory",
        "name": "Memory Forensics",
        "description": "Volatility memory analysis",
        "category": "defensive",
        "tier": 2,
        "params_schema": {
            "dump": {"type": "string", "required": True},
            "plugins": {"type": "list", "default": ["pslist", "netscan", "malfind"]}
        },
        "dependencies": ["volatility"],
        "timeout": 1800
    },
    {
        "id": "def_for_network",
        "name": "Network Forensics",
        "description": "PCAP analysis and reconstruction",
        "category": "defensive",
        "tier": 2,
        "params_schema": {
            "pcap": {"type": "string", "required": True},
            "extract_objects": {"type": "boolean", "default": True},
            "protocols": {"type": "list", "default": ["http", "dns", "smtp"]}
        }
    },
    {
        "id": "def_for_timeline",
        "name": "Timeline Analysis",
        "description": "Super timeline generation",
        "category": "defensive",
        "tier": 2,
        "params_schema": {
            "source": {"type": "string", "required": True},
            "format": {"type": "string", "default": "plaso"},
            "filters": {"type": "dict", "default": {}}
        },
        "timeout": 3600
    },
    {
        "id": "def_for_malware",
        "name": "Malware Analysis",
        "description": "Static and dynamic malware analysis",
        "category": "defensive",
        "tier": 2,
        "params_schema": {
            "sample": {"type": "string", "required": True},
            "sandbox": {"type": "boolean", "default": True},
            "timeout": {"type": "integer", "default": 300}
        },
        "timeout": 600
    },
    
    # Tier 2 - Incident Response
    {
        "id": "def_ir_contain",
        "name": "System Containment",
        "description": "Isolate compromised systems",
        "category": "defensive",
        "tier": 2,
        "params_schema": {
            "hosts": {"type": "list", "required": True},
            "method": {"type": "string", "default": "network"}
        }
    },
    {
        "id": "def_ir_eradicate",
        "name": "Threat Eradication",
        "description": "Remove malware and persistence",
        "category": "defensive",
        "tier": 2,
        "params_schema": {
            "hosts": {"type": "list", "required": True},
            "indicators": {"type": "list", "required": True}
        }
    },
    {
        "id": "def_ir_recover",
        "name": "System Recovery",
        "description": "Restore from backups",
        "category": "defensive",
        "tier": 2,
        "params_schema": {
            "hosts": {"type": "list", "required": True},
            "backup_point": {"type": "string", "required": True}
        }
    },
    {
        "id": "def_ir_playbook",
        "name": "IR Playbook Execution",
        "description": "Execute incident response playbooks",
        "category": "defensive",
        "tier": 2,
        "params_schema": {
            "playbook": {"type": "string", "required": True},
            "incident_id": {"type": "string", "required": True}
        }
    },
    
    # Tier 3 - Advanced Detection
    {
        "id": "def_adv_behavior",
        "name": "Behavioral Analysis",
        "description": "UEBA and anomaly detection",
        "category": "defensive",
        "tier": 3,
        "params_schema": {
            "entity": {"type": "string", "required": True},
            "baseline": {"type": "string", "default": "30d"},
            "sensitivity": {"type": "string", "default": "medium"}
        }
    },
    {
        "id": "def_adv_ml",
        "name": "ML-Based Detection",
        "description": "Machine learning threat detection",
        "category": "defensive",
        "tier": 3,
        "params_schema": {
            "model": {"type": "string", "required": True},
            "data_source": {"type": "string", "required": True},
            "threshold": {"type": "float", "default": 0.8}
        }
    },
    {
        "id": "def_adv_deception",
        "name": "Deception Technology",
        "description": "Honeypot and deception deployment",
        "category": "defensive",
        "tier": 3,
        "params_schema": {
            "type": {"type": "string", "default": "honeypot"},
            "count": {"type": "integer", "default": 5},
            "services": {"type": "list", "default": ["ssh", "http"]}
        }
    },
    {
        "id": "def_adv_threat",
        "name": "Threat Intelligence",
        "description": "TI platform integration and analysis",
        "category": "defensive",
        "tier": 3,
        "params_schema": {
            "feed": {"type": "string", "default": "misp"},
            "iocs": {"type": "list", "default": []},
            "enrich": {"type": "boolean", "default": True}
        }
    },
    {
        "id": "def_adv_vuln",
        "name": "Vulnerability Management",
        "description": "Enterprise vulnerability scanning",
        "category": "defensive",
        "tier": 3,
        "params_schema": {
            "scope": {"type": "string", "required": True},
            "scan_type": {"type": "string", "default": "comprehensive"},
            "schedule": {"type": "string", "default": ""}
        },
        "timeout": 7200
    },
    {
        "id": "def_adv_purple",
        "name": "Purple Team Exercise",
        "description": "Coordinate purple team operations",
        "category": "defensive",
        "tier": 3,
        "params_schema": {
            "scenario": {"type": "string", "required": True},
            "duration": {"type": "string", "default": "4h"},
            "scope": {"type": "list", "required": True}
        },
        "timeout": 14400
    },
    {
        "id": "def_adv_deception",
        "name": "Active Deception",
        "description": "Deploy honeypots and deception technology",
        "category": "defensive",
        "tier": 3,
        "params_schema": {
            "type": {"type": "string", "default": "honeypot"},
            "deployment": {"type": "string", "default": "network"},
            "interaction": {"type": "string", "default": "high"},
            "alert_threshold": {"type": "integer", "default": 1}
        },
        "timeout": 1800
    },
    {
        "id": "def_adv_automation",
        "name": "Security Automation",
        "description": "SOAR playbook automation and orchestration",
        "category": "defensive",
        "tier": 3,
        "params_schema": {
            "playbook": {"type": "string", "required": True},
            "trigger": {"type": "string", "required": True},
            "conditions": {"type": "list", "default": []},
            "actions": {"type": "list", "required": True}
        },
        "timeout": 3600
    }
]
