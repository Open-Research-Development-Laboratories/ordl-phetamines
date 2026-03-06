#!/usr/bin/env python3
"""
Offensive Skills - 25 Skills
Penetration testing, exploitation, red team operations
"""

OFFENSIVE_SKILLS = [
    # Tier 1 - Basic Reconnaissance
    {
        "id": "off_recon_nmap",
        "name": "Nmap Network Scan",
        "description": "Comprehensive network scanning with Nmap",
        "category": "offensive",
        "tier": 1,
        "params_schema": {
            "target": {"type": "string", "required": True},
            "ports": {"type": "string", "default": "1-65535"},
            "options": {"type": "string", "default": "-sV -sC"}
        },
        "dependencies": ["nmap"]
    },
    {
        "id": "off_recon_subdomain",
        "name": "Subdomain Enumeration",
        "description": "Discover subdomains using multiple techniques",
        "category": "offensive",
        "tier": 1,
        "params_schema": {
            "domain": {"type": "string", "required": True},
            "wordlist": {"type": "string", "default": "common.txt"},
            "threads": {"type": "integer", "default": 50}
        }
    },
    {
        "id": "off_recon_dns",
        "name": "DNS Enumeration",
        "description": "DNS record enumeration and zone transfers",
        "category": "offensive",
        "tier": 1,
        "params_schema": {
            "domain": {"type": "string", "required": True},
            "record_types": {"type": "list", "default": ["A", "AAAA", "MX", "NS", "TXT", "SOA"]}
        }
    },
    {
        "id": "off_recon_whois",
        "name": "WHOIS Lookup",
        "description": "Domain registration information gathering",
        "category": "offensive",
        "tier": 1,
        "params_schema": {
            "target": {"type": "string", "required": True}
        }
    },
    {
        "id": "off_recon_ssl",
        "name": "SSL/TLS Analysis",
        "description": "SSL certificate and TLS configuration analysis",
        "category": "offensive",
        "tier": 1,
        "params_schema": {
            "target": {"type": "string", "required": True},
            "port": {"type": "integer", "default": 443}
        }
    },
    
    # Tier 1 - Basic Web
    {
        "id": "off_web_dirb",
        "name": "Directory Bruteforce",
        "description": "Web directory and file discovery",
        "category": "offensive",
        "tier": 1,
        "params_schema": {
            "url": {"type": "string", "required": True},
            "wordlist": {"type": "string", "default": "common.txt"},
            "extensions": {"type": "string", "default": "php,txt,html"}
        }
    },
    {
        "id": "off_web_tech",
        "name": "Technology Detection",
        "description": "Identify web technologies and frameworks",
        "category": "offensive",
        "tier": 1,
        "params_schema": {
            "url": {"type": "string", "required": True}
        }
    },
    {
        "id": "off_web_screenshot",
        "name": "Web Screenshot",
        "description": "Capture screenshots of web applications",
        "category": "offensive",
        "tier": 1,
        "params_schema": {
            "url": {"type": "string", "required": True},
            "resolution": {"type": "string", "default": "1920x1080"}
        }
    },
    
    # Tier 2 - Web Vulnerabilities
    {
        "id": "off_web_sqlmap",
        "name": "SQLMap Injection",
        "description": "Automated SQL injection testing",
        "category": "offensive",
        "tier": 2,
        "params_schema": {
            "url": {"type": "string", "required": True},
            "data": {"type": "string", "default": ""},
            "level": {"type": "integer", "default": 1},
            "risk": {"type": "integer", "default": 1}
        },
        "dependencies": ["sqlmap"]
    },
    {
        "id": "off_web_xss",
        "name": "XSS Testing",
        "description": "Cross-site scripting vulnerability testing",
        "category": "offensive",
        "tier": 2,
        "params_schema": {
            "url": {"type": "string", "required": True},
            "parameters": {"type": "list", "default": []},
            "payloads": {"type": "list", "default": []}
        }
    },
    {
        "id": "off_web_csrf",
        "name": "CSRF Testing",
        "description": "Cross-site request forgery testing",
        "category": "offensive",
        "tier": 2,
        "params_schema": {
            "url": {"type": "string", "required": True},
            "forms": {"type": "list", "default": []}
        }
    },
    {
        "id": "off_web_lfi",
        "name": "LFI/RFI Testing",
        "description": "Local/Remote file inclusion testing",
        "category": "offensive",
        "tier": 2,
        "params_schema": {
            "url": {"type": "string", "required": True},
            "parameter": {"type": "string", "required": True}
        }
    },
    {
        "id": "off_web_nuclei",
        "name": "Nuclei Scan",
        "description": "Fast vulnerability scanner using Nuclei",
        "category": "offensive",
        "tier": 2,
        "params_schema": {
            "target": {"type": "string", "required": True},
            "templates": {"type": "string", "default": "cves/"},
            "severity": {"type": "list", "default": ["critical", "high", "medium"]}
        },
        "dependencies": ["nuclei"]
    },
    
    # Tier 2 - Network
    {
        "id": "off_net_sniff",
        "name": "Network Sniffing",
        "description": "Packet capture and analysis",
        "category": "offensive",
        "tier": 2,
        "params_schema": {
            "interface": {"type": "string", "default": "eth0"},
            "filter": {"type": "string", "default": ""},
            "duration": {"type": "integer", "default": 60}
        }
    },
    {
        "id": "off_net_responder",
        "name": "Responder Attack",
        "description": "LLMNR, NBT-NS, MDNS poisoner",
        "category": "offensive",
        "tier": 2,
        "params_schema": {
            "interface": {"type": "string", "default": "eth0"},
            "wpad": {"type": "boolean", "default": True}
        }
    },
    {
        "id": "off_net_mitm",
        "name": "MITM Attack",
        "description": "Man-in-the-middle attack framework",
        "category": "offensive",
        "tier": 2,
        "params_schema": {
            "target": {"type": "string", "required": True},
            "gateway": {"type": "string", "required": True},
            "mode": {"type": "string", "default": "arp"}
        }
    },
    
    # Tier 3 - Exploitation
    {
        "id": "off_exp_metasploit",
        "name": "Metasploit Execution",
        "description": "Execute Metasploit modules",
        "category": "offensive",
        "tier": 3,
        "params_schema": {
            "module": {"type": "string", "required": True},
            "options": {"type": "dict", "default": {}},
            "payload": {"type": "string", "default": ""}
        },
        "dependencies": ["msfconsole"],
        "timeout": 600
    },
    {
        "id": "off_exp_cve",
        "name": "CVE Exploitation",
        "description": "Targeted CVE exploitation",
        "category": "offensive",
        "tier": 3,
        "params_schema": {
            "cve": {"type": "string", "required": True},
            "target": {"type": "string", "required": True},
            "options": {"type": "dict", "default": {}}
        },
        "timeout": 600
    },
    {
        "id": "off_exp_bruteforce",
        "name": "Credential Bruteforce",
        "description": "Hydra-based credential attacks",
        "category": "offensive",
        "tier": 3,
        "params_schema": {
            "target": {"type": "string", "required": True},
            "service": {"type": "string", "required": True},
            "userlist": {"type": "string", "default": "users.txt"},
            "passlist": {"type": "string", "default": "passwords.txt"}
        },
        "timeout": 1800
    },
    {
        "id": "off_exp_password",
        "name": "Password Cracking",
        "description": "Hashcat/John password cracking",
        "category": "offensive",
        "tier": 3,
        "params_schema": {
            "hashfile": {"type": "string", "required": True},
            "hashtype": {"type": "integer", "required": True},
            "wordlist": {"type": "string", "default": "rockyou.txt"},
            "rules": {"type": "string", "default": ""}
        },
        "timeout": 3600
    },
    
    # Tier 3 - Advanced
    {
        "id": "off_adv_tunnel",
        "name": "Tunneling/Pivot",
        "description": "SSH/HTTP tunneling and pivoting",
        "category": "offensive",
        "tier": 3,
        "params_schema": {
            "target": {"type": "string", "required": True},
            "type": {"type": "string", "default": "ssh"},
            "local_port": {"type": "integer", "required": True},
            "remote_port": {"type": "integer", "required": True}
        }
    },
    {
        "id": "off_adv_phishing",
        "name": "Phishing Campaign",
        "description": "Social engineering email campaigns",
        "category": "offensive",
        "tier": 3,
        "params_schema": {
            "template": {"type": "string", "required": True},
            "targets": {"type": "list", "required": True},
            "server": {"type": "string", "default": "localhost"}
        }
    },
    {
        "id": "off_adv_payload",
        "name": "Custom Payload",
        "description": "Generate custom payloads",
        "category": "offensive",
        "tier": 3,
        "params_schema": {
            "type": {"type": "string", "required": True},
            "platform": {"type": "string", "required": True},
            "encoder": {"type": "string", "default": ""},
            "options": {"type": "dict", "default": {}}
        }
    },
    {
        "id": "off_adv_bypass",
        "name": "Security Bypass",
        "description": "AV/EDR bypass techniques",
        "category": "offensive",
        "tier": 3,
        "params_schema": {
            "payload": {"type": "string", "required": True},
            "technique": {"type": "string", "default": "encryption"},
            "target_av": {"type": "string", "default": ""}
        }
    },
    {
        "id": "off_adv_zeroday",
        "name": "Zero-Day Research",
        "description": "Fuzzing and vulnerability research for zero-days",
        "category": "offensive",
        "tier": 3,
        "params_schema": {
            "target": {"type": "string", "required": True},
            "fuzz_type": {"type": "string", "default": "network"},
            "duration": {"type": "integer", "default": 3600},
            "corpus": {"type": "string", "default": ""}
        },
        "timeout": 7200
    }
]
