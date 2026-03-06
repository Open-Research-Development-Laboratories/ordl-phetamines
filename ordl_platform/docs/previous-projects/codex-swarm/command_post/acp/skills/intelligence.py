#!/usr/bin/env python3
"""
Intelligence Skills - 20 Skills
OSINT, threat intel, reconnaissance
"""

INTELLIGENCE_SKILLS = [
    # Tier 1 - OSINT
    {
        "id": "int_osint_shodan",
        "name": "Shodan Intelligence",
        "description": "Search Shodan for exposed systems",
        "category": "intelligence",
        "tier": 1,
        "params_schema": {
            "query": {"type": "string", "required": True},
            "facets": {"type": "list", "default": ["ip", "port", "org"]},
            "limit": {"type": "integer", "default": 100}
        }
    },
    {
        "id": "int_osint_censys",
        "name": "Censys Intelligence",
        "description": "Search Censys for internet assets",
        "category": "intelligence",
        "tier": 1,
        "params_schema": {
            "query": {"type": "string", "required": True},
            "fields": {"type": "list", "default": []},
            "limit": {"type": "integer", "default": 100}
        }
    },
    {
        "id": "int_osint_theharvester",
        "name": "Email Harvesting",
        "description": "Gather emails and names",
        "category": "intelligence",
        "tier": 1,
        "params_schema": {
            "domain": {"type": "string", "required": True},
            "sources": {"type": "list", "default": ["all"]},
            "limit": {"type": "integer", "default": 500}
        }
    },
    {
        "id": "int_osint_sherlock",
        "name": "Username Enumeration",
        "description": "Find social media accounts by username",
        "category": "intelligence",
        "tier": 1,
        "params_schema": {
            "username": {"type": "string", "required": True},
            "sites": {"type": "list", "default": []}
        }
    },
    
    # Tier 1 - Domain Intel
    {
        "id": "int_domain_whois",
        "name": "WHOIS Intelligence",
        "description": "Domain registration history",
        "category": "intelligence",
        "tier": 1,
        "params_schema": {
            "domain": {"type": "string", "required": True},
            "history": {"type": "boolean", "default": False}
        }
    },
    {
        "id": "int_domain_passive",
        "name": "Passive DNS",
        "description": "Passive DNS data analysis",
        "category": "intelligence",
        "tier": 1,
        "params_schema": {
            "indicator": {"type": "string", "required": True},
            "type": {"type": "string", "default": "domain"}
        }
    },
    
    # Tier 2 - Dark Web
    {
        "id": "int_dark_search",
        "name": "Dark Web Search",
        "description": "Search dark web sources",
        "category": "intelligence",
        "tier": 2,
        "params_schema": {
            "query": {"type": "string", "required": True},
            "sources": {"type": "list", "default": ["tor"]}
        }
    },
    {
        "id": "int_dark_leak",
        "name": "Data Leak Detection",
        "description": "Monitor for data breaches",
        "category": "intelligence",
        "tier": 2,
        "params_schema": {
            "domain": {"type": "string", "required": True},
            "check_credentials": {"type": "boolean", "default": True}
        }
    },
    
    # Tier 2 - Code & Git
    {
        "id": "int_git_search",
        "name": "GitHub/GitLab Search",
        "description": "Search code repositories",
        "category": "intelligence",
        "tier": 2,
        "params_schema": {
            "query": {"type": "string", "required": True},
            "platform": {"type": "string", "default": "github"},
            "scope": {"type": "string", "default": "code"}
        }
    },
    {
        "id": "int_git_leak",
        "name": "Secret Detection",
        "description": "Find leaked credentials in repos",
        "category": "intelligence",
        "tier": 2,
        "params_schema": {
            "repo": {"type": "string", "required": True},
            "depth": {"type": "string", "default": "full"}
        }
    },
    
    # Tier 2 - Infrastructure
    {
        "id": "int_infra_cloud",
        "name": "Cloud Enumeration",
        "description": "AWS/Azure/GCP asset discovery",
        "category": "intelligence",
        "tier": 2,
        "params_schema": {
            "target": {"type": "string", "required": True},
            "providers": {"type": "list", "default": ["aws", "azure", "gcp"]}
        }
    },
    {
        "id": "int_infra_cert",
        "name": "Certificate Transparency",
        "description": "CT log analysis for subdomains",
        "category": "intelligence",
        "tier": 2,
        "params_schema": {
            "domain": {"type": "string", "required": True},
            "include_expired": {"type": "boolean", "default": False}
        }
    },
    
    # Tier 3 - Advanced Intel
    {
        "id": "int_adv_correlate",
        "name": "Intelligence Correlation",
        "description": "Cross-reference multiple intel sources",
        "category": "intelligence",
        "tier": 3,
        "params_schema": {
            "indicators": {"type": "list", "required": True},
            "sources": {"type": "list", "default": ["all"]}
        }
    },
    {
        "id": "int_adv_track",
        "name": "Threat Actor Tracking",
        "description": "Track APT group activities",
        "category": "intelligence",
        "tier": 3,
        "params_schema": {
            "actor": {"type": "string", "required": True},
            "timeframe": {"type": "string", "default": "1y"}
        }
    },
    {
        "id": "int_adv_malware",
        "name": "Malware Intelligence",
        "description": "Malware family attribution",
        "category": "intelligence",
        "tier": 3,
        "params_schema": {
            "hash": {"type": "string", "default": ""},
            "sample": {"type": "string", "default": ""}
        }
    },
    {
        "id": "int_adv_geoint",
        "name": "Geospatial Intel",
        "description": "Location-based intelligence",
        "category": "intelligence",
        "tier": 3,
        "params_schema": {
            "coordinates": {"type": "string", "required": True},
            "radius": {"type": "integer", "default": 10}
        }
    },
    {
        "id": "int_adv_network",
        "name": "Network Graph Analysis",
        "description": "Visualize infrastructure relationships",
        "category": "intelligence",
        "tier": 3,
        "params_schema": {
            "seed": {"type": "string", "required": True},
            "depth": {"type": "integer", "default": 3}
        }
    },
    
    # Tier 3 - Specialized
    {
        "id": "int_spec_financial",
        "name": "Financial Intelligence",
        "description": "Crypto wallet analysis",
        "category": "intelligence",
        "tier": 3,
        "params_schema": {
            "wallet": {"type": "string", "required": True},
            "blockchain": {"type": "string", "default": "bitcoin"}
        }
    },
    {
        "id": "int_spec_mobile",
        "name": "Mobile App Intel",
        "description": "Mobile application analysis",
        "category": "intelligence",
        "tier": 3,
        "params_schema": {
            "app": {"type": "string", "required": True},
            "store": {"type": "string", "default": "play"}
        }
    },
    {
        "id": "int_spec_image",
        "name": "Image Intelligence",
        "description": "Reverse image search and EXIF",
        "category": "intelligence",
        "tier": 3,
        "params_schema": {
            "image": {"type": "string", "required": True},
            "extract_exif": {"type": "boolean", "default": True}
        }
    },
    {
        "id": "int_spec_document",
        "name": "Document Metadata",
        "description": "Extract metadata from documents",
        "category": "intelligence",
        "tier": 3,
        "params_schema": {
            "document": {"type": "string", "required": True},
            "deep_analysis": {"type": "boolean", "default": False}
        }
    }
]
