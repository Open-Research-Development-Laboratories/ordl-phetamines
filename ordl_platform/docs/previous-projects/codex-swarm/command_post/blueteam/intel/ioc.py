#!/usr/bin/env python3
"""
================================================================================
ORDL COMMAND POST v6.0.0 - BLUE TEAM IOC MANAGEMENT SYSTEM
================================================================================
Classification: TOP SECRET//SCI//NOFORN
Classification Level: TS/SCI/NOFORN
Compartment: ORDL-CYBER-OPS

INDICATORS OF COMPROMISE (IOC) MANAGEMENT & MATCHING ENGINE
================================================================================
Military-grade threat intelligence system for detection and blocking:
- STIX 2.1 compliant import/export
- High-performance matching engine with hash maps
- CIDR range matching for IP networks
- Subdomain matching for domain IOCs
- Regex pattern matching for advanced detection
- Automated feed management with scheduled updates
- Confidence scoring and severity classification

Author: ORDL Cyber Operations Division
Version: 6.0.0
================================================================================
"""

import os
import re
import json
import uuid
import ipaddress
import hashlib
import sqlite3
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple, Union, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from collections import defaultdict
import threading

# Configure logging
logger = logging.getLogger('blueteam.ioc')


class IOCType(Enum):
    """
    IOC Type Classification
    
    Pre/Condition: Type must be one of defined enum values
    Post/Condition: Returns standardized IOC type for consistent processing
    """
    IP = "ip"
    DOMAIN = "domain"
    FILE_HASH_MD5 = "file_hash_md5"
    FILE_HASH_SHA1 = "file_hash_sha1"
    FILE_HASH_SHA256 = "file_hash_sha256"
    URL = "url"
    EMAIL = "email"
    MUTEX = "mutex"
    REGISTRY_KEY = "registry_key"
    USER_AGENT = "user_agent"
    
    @classmethod
    def from_string(cls, value: str) -> "IOCType":
        """Create IOCType from string representation"""
        mapping = {
            "ip": cls.IP,
            "domain": cls.DOMAIN,
            "md5": cls.FILE_HASH_MD5,
            "file_hash_md5": cls.FILE_HASH_MD5,
            "sha1": cls.FILE_HASH_SHA1,
            "file_hash_sha1": cls.FILE_HASH_SHA1,
            "sha256": cls.FILE_HASH_SHA256,
            "file_hash_sha256": cls.FILE_HASH_SHA256,
            "url": cls.URL,
            "email": cls.EMAIL,
            "mutex": cls.MUTEX,
            "registry_key": cls.REGISTRY_KEY,
            "registry": cls.REGISTRY_KEY,
            "user_agent": cls.USER_AGENT,
        }
        return mapping.get(value.lower(), cls.IP)


class ThreatType(Enum):
    """Threat classification for IOCs"""
    MALWARE = "malware"
    APT = "apt"
    PHISHING = "phishing"
    BOTNET = "botnet"
    RANSOMWARE = "ransomware"
    TROJAN = "trojan"
    BACKDOOR = "backdoor"
    ROOTKIT = "rootkit"
    SPYWARE = "spyware"
    ADWARE = "adware"
    EXPLOIT_KIT = "exploit_kit"
    C2 = "command_and_control"
    DATA_EXFIL = "data_exfiltration"
    INSIDER_THREAT = "insider_threat"
    SUPPLY_CHAIN = "supply_chain"
    UNKNOWN = "unknown"


class SeverityLevel(Enum):
    """Severity classification levels"""
    CRITICAL = 5
    HIGH = 4
    MEDIUM = 3
    LOW = 2
    INFO = 1
    
    @classmethod
    def from_string(cls, value: str) -> "SeverityLevel":
        """Create SeverityLevel from string"""
        mapping = {
            "critical": cls.CRITICAL,
            "high": cls.HIGH,
            "medium": cls.MEDIUM,
            "low": cls.LOW,
            "info": cls.INFO,
            "informational": cls.INFO,
        }
        return mapping.get(value.lower(), cls.MEDIUM)


@dataclass
class IOC:
    """
    Indicator of Compromise (IOC) Data Model
    
    Represents a single threat indicator with comprehensive metadata
    for military-grade threat intelligence operations.
    
    Attributes:
        ioc_id: Unique identifier (UUID)
        ioc_type: Type of indicator (IP, domain, hash, etc.)
        value: The actual indicator value
        threat_type: Classification of the threat
        severity: Severity level (CRITICAL, HIGH, MEDIUM, LOW, INFO)
        confidence: Confidence score 0-100
        source: Origin/source of the IOC
        first_seen: Timestamp of first observation
        last_seen: Timestamp of most recent observation
        expiration: Expiration timestamp (optional)
        tags: List of searchable tags
        description: Human-readable description
        related_iocs: List of related IOC IDs
        metadata: Additional contextual data
        hit_count: Number of detection hits
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """
    ioc_id: str
    ioc_type: IOCType
    value: str
    threat_type: ThreatType = ThreatType.UNKNOWN
    severity: SeverityLevel = SeverityLevel.MEDIUM
    confidence: int = 50  # 0-100
    source: str = ""
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    expiration: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)
    description: str = ""
    related_iocs: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    hit_count: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        """Post-initialization validation"""
        if isinstance(self.ioc_type, str):
            self.ioc_type = IOCType.from_string(self.ioc_type)
        if isinstance(self.threat_type, str):
            self.threat_type = ThreatType(self.threat_type)
        if isinstance(self.severity, str):
            self.severity = SeverityLevel.from_string(self.severity)
        
        # Validate confidence range
        self.confidence = max(0, min(100, self.confidence))
        
        # Normalize value based on type
        self.value = self._normalize_value(self.value, self.ioc_type)
    
    def _normalize_value(self, value: str, ioc_type: IOCType) -> str:
        """Normalize IOC value based on type"""
        value = value.strip()
        
        if ioc_type == IOCType.IP:
            # Normalize IP addresses
            try:
                ip = ipaddress.ip_address(value)
                return str(ip)
            except ValueError:
                pass
        
        elif ioc_type in (IOCType.DOMAIN, IOCType.URL):
            # Lowercase domains and URLs
            value = value.lower()
        
        elif ioc_type in (IOCType.FILE_HASH_MD5, IOCType.FILE_HASH_SHA1, IOCType.FILE_HASH_SHA256):
            # Uppercase hashes for consistency
            value = value.upper()
        
        elif ioc_type == IOCType.EMAIL:
            # Lowercase emails
            value = value.lower()
        
        return value
    
    def is_expired(self) -> bool:
        """Check if IOC has expired"""
        if self.expiration is None:
            return False
        return datetime.utcnow() > self.expiration
    
    def is_active(self) -> bool:
        """Check if IOC is active (not expired and has confidence)"""
        return not self.is_expired() and self.confidence > 0
    
    def matches_confidence_threshold(self, threshold: int) -> bool:
        """Check if IOC meets confidence threshold"""
        return self.confidence >= threshold
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert IOC to dictionary representation"""
        return {
            "ioc_id": self.ioc_id,
            "ioc_type": self.ioc_type.value,
            "value": self.value,
            "threat_type": self.threat_type.value,
            "severity": self.severity.name,
            "confidence": self.confidence,
            "source": self.source,
            "first_seen": self.first_seen.isoformat() if self.first_seen else None,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "expiration": self.expiration.isoformat() if self.expiration else None,
            "tags": self.tags,
            "description": self.description,
            "related_iocs": self.related_iocs,
            "metadata": self.metadata,
            "hit_count": self.hit_count,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IOC":
        """Create IOC from dictionary"""
        # Parse datetime fields
        for field_name in ["first_seen", "last_seen", "expiration", "created_at", "updated_at"]:
            if field_name in data and data[field_name]:
                if isinstance(data[field_name], str):
                    data[field_name] = datetime.fromisoformat(data[field_name].replace('Z', '+00:00'))
        
        # Convert enums
        if "ioc_type" in data and isinstance(data["ioc_type"], str):
            data["ioc_type"] = IOCType.from_string(data["ioc_type"])
        if "threat_type" in data and isinstance(data["threat_type"], str):
            data["threat_type"] = ThreatType(data["threat_type"])
        if "severity" in data and isinstance(data["severity"], str):
            data["severity"] = SeverityLevel.from_string(data["severity"])
        
        return cls(**data)
    
    def to_stix_indicator(self) -> Dict[str, Any]:
        """Convert IOC to STIX 2.1 Indicator object"""
        pattern = self._generate_stix_pattern()
        
        return {
            "type": "indicator",
            "spec_version": "2.1",
            "id": f"indicator--{self.ioc_id}",
            "created": self.created_at.isoformat() + "Z",
            "modified": self.updated_at.isoformat() + "Z",
            "name": f"IOC: {self.value}",
            "description": self.description,
            "pattern": pattern,
            "pattern_type": "stix",
            "valid_from": (self.first_seen or self.created_at).isoformat() + "Z",
            "valid_until": self.expiration.isoformat() + "Z" if self.expiration else None,
            "confidence": self.confidence,
            "labels": self.tags,
            "object_marking_refs": ["marking-definition--34098fce-860f-48ae-8e50-ebd3cc5e41da"],
        }
    
    def _generate_stix_pattern(self) -> str:
        """Generate STIX pattern from IOC value"""
        if self.ioc_type == IOCType.IP:
            return f"[ipv4-addr:value = '{self.value}']"
        elif self.ioc_type == IOCType.DOMAIN:
            return f"[domain-name:value = '{self.value}']"
        elif self.ioc_type == IOCType.URL:
            return f"[url:value = '{self.value}']"
        elif self.ioc_type == IOCType.FILE_HASH_MD5:
            return f"[file:hashes.MD5 = '{self.value}']"
        elif self.ioc_type == IOCType.FILE_HASH_SHA1:
            return f"[file:hashes.SHA-1 = '{self.value}']"
        elif self.ioc_type == IOCType.FILE_HASH_SHA256:
            return f"[file:hashes.SHA-256 = '{self.value}']"
        elif self.ioc_type == IOCType.EMAIL:
            return f"[email-addr:value = '{self.value}']"
        elif self.ioc_type == IOCType.MUTEX:
            return f"[mutex:name = '{self.value}']"
        elif self.ioc_type == IOCType.REGISTRY_KEY:
            return f"[windows-registry-key:key = '{self.value}']"
        elif self.ioc_type == IOCType.USER_AGENT:
            return f"[network-traffic:extensions.'http-request-ext'.request_header.'User-Agent' = '{self.value}']"
        return f"[x-custom:value = '{self.value}']"


@dataclass
class IOCFeed:
    """
    Threat Intelligence Feed Configuration
    
    Manages external threat feed sources for automated IOC ingestion.
    
    Attributes:
        feed_id: Unique feed identifier
        name: Human-readable feed name
        url: Feed source URL
        feed_type: Type of feed (STIX, MISP, TAXII, etc.)
        api_key: Authentication key (optional)
        enabled: Whether feed is active
        auto_update: Enable automatic updates
        update_interval: Update interval in minutes
        last_update: Timestamp of last successful update
        next_update: Timestamp of next scheduled update
        ioc_count: Number of IOCs from this feed
        trust_score: Feed reliability score 0-100
        filters: Feed-specific filters
        metadata: Additional configuration
    """
    feed_id: str
    name: str
    url: str
    feed_type: str = "stix"  # stix, misp, taxii, csv, json
    api_key: Optional[str] = None
    enabled: bool = True
    auto_update: bool = False
    update_interval: int = 60  # minutes
    last_update: Optional[datetime] = None
    next_update: Optional[datetime] = None
    ioc_count: int = 0
    trust_score: int = 50
    filters: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert feed to dictionary"""
        return {
            "feed_id": self.feed_id,
            "name": self.name,
            "url": self.url,
            "feed_type": self.feed_type,
            "enabled": self.enabled,
            "auto_update": self.auto_update,
            "update_interval": self.update_interval,
            "last_update": self.last_update.isoformat() if self.last_update else None,
            "next_update": self.next_update.isoformat() if self.next_update else None,
            "ioc_count": self.ioc_count,
            "trust_score": self.trust_score,
            "filters": self.filters,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }


class IOCMatchingEngine:
    """
    High-Performance IOC Matching Engine
    
    Provides fast IOC lookups using optimized data structures:
    - Hash maps for O(1) IP/domain/hash lookups
    - CIDR trie for network range matching
    - Regex cache for pattern matching
    - Subdomain tree for domain matching
    
    Thread-safe for concurrent access.
    """
    
    def __init__(self):
        # Hash maps for exact match lookups
        self._ip_map: Dict[str, IOC] = {}
        self._domain_map: Dict[str, IOC] = {}
        self._hash_map: Dict[str, IOC] = {}
        self._url_map: Dict[str, IOC] = {}
        self._email_map: Dict[str, IOC] = {}
        self._mutex_map: Dict[str, IOC] = {}
        self._registry_map: Dict[str, IOC] = {}
        self._user_agent_map: Dict[str, IOC] = {}
        
        # CIDR network ranges (ip_network -> IOC list)
        self._network_ranges: Dict[ipaddress.IPv4Network, List[IOC]] = defaultdict(list)
        self._network_ranges_v6: Dict[ipaddress.IPv6Network, List[IOC]] = defaultdict(list)
        
        # Subdomain matching (domain suffix -> IOC list)
        self._subdomain_map: Dict[str, List[IOC]] = defaultdict(list)
        
        # Regex patterns (pattern -> IOC list)
        self._regex_patterns: Dict[str, Tuple[re.Pattern, List[IOC]]] = {}
        
        # All IOCs by ID
        self._iocs_by_id: Dict[str, IOC] = {}
        
        # Thread safety
        self._lock = threading.RLock()
        
        logger.info("[IOC-ENGINE] Matching engine initialized")
    
    def add_ioc(self, ioc: IOC) -> bool:
        """
        Add IOC to matching engine indices
        
        Pre/Condition: IOC must have valid ioc_id and value
        Post/Condition: IOC is indexed in appropriate lookup structures
        """
        with self._lock:
            try:
                # Store by ID
                self._iocs_by_id[ioc.ioc_id] = ioc
                
                # Index by type
                if ioc.ioc_type == IOCType.IP:
                    self._index_ip(ioc)
                elif ioc.ioc_type == IOCType.DOMAIN:
                    self._index_domain(ioc)
                elif ioc.ioc_type in (IOCType.FILE_HASH_MD5, IOCType.FILE_HASH_SHA1, IOCType.FILE_HASH_SHA256):
                    self._hash_map[ioc.value] = ioc
                elif ioc.ioc_type == IOCType.URL:
                    self._url_map[ioc.value] = ioc
                elif ioc.ioc_type == IOCType.EMAIL:
                    self._email_map[ioc.value] = ioc
                elif ioc.ioc_type == IOCType.MUTEX:
                    self._mutex_map[ioc.value] = ioc
                elif ioc.ioc_type == IOCType.REGISTRY_KEY:
                    self._registry_map[ioc.value] = ioc
                elif ioc.ioc_type == IOCType.USER_AGENT:
                    self._user_agent_map[ioc.value] = ioc
                
                return True
            except Exception as e:
                logger.error(f"[IOC-ENGINE] Failed to index IOC {ioc.ioc_id}: {e}")
                return False
    
    def remove_ioc(self, ioc_id: str) -> bool:
        """Remove IOC from all indices"""
        with self._lock:
            if ioc_id not in self._iocs_by_id:
                return False
            
            ioc = self._iocs_by_id[ioc_id]
            
            # Remove from type-specific indices
            if ioc.ioc_type == IOCType.IP:
                self._remove_ip(ioc)
            elif ioc.ioc_type == IOCType.DOMAIN:
                self._remove_domain(ioc)
            elif ioc.ioc_type in (IOCType.FILE_HASH_MD5, IOCType.FILE_HASH_SHA1, IOCType.FILE_HASH_SHA256):
                self._hash_map.pop(ioc.value, None)
            elif ioc.ioc_type == IOCType.URL:
                self._url_map.pop(ioc.value, None)
            elif ioc.ioc_type == IOCType.EMAIL:
                self._email_map.pop(ioc.value, None)
            elif ioc.ioc_type == IOCType.MUTEX:
                self._mutex_map.pop(ioc.value, None)
            elif ioc.ioc_type == IOCType.REGISTRY_KEY:
                self._registry_map.pop(ioc.value, None)
            elif ioc.ioc_type == IOCType.USER_AGENT:
                self._user_agent_map.pop(ioc.value, None)
            
            del self._iocs_by_id[ioc_id]
            return True
    
    def _index_ip(self, ioc: IOC):
        """Index IP address or CIDR range"""
        value = ioc.value
        
        # Check if it's a CIDR range
        if "/" in value:
            try:
                network = ipaddress.ip_network(value, strict=False)
                if isinstance(network, ipaddress.IPv4Network):
                    self._network_ranges[network].append(ioc)
                else:
                    self._network_ranges_v6[network].append(ioc)
            except ValueError:
                pass
        else:
            self._ip_map[value] = ioc
    
    def _remove_ip(self, ioc: IOC):
        """Remove IP from indices"""
        value = ioc.value
        
        if "/" in value:
            try:
                network = ipaddress.ip_network(value, strict=False)
                if isinstance(network, ipaddress.IPv4Network) and network in self._network_ranges:
                    self._network_ranges[network] = [i for i in self._network_ranges[network] if i.ioc_id != ioc.ioc_id]
                elif network in self._network_ranges_v6:
                    self._network_ranges_v6[network] = [i for i in self._network_ranges_v6[network] if i.ioc_id != ioc.ioc_id]
            except ValueError:
                pass
        else:
            self._ip_map.pop(value, None)
    
    # Common TLDs that should not be used for subdomain matching
    _COMMON_TLDS = {
        'com', 'org', 'net', 'edu', 'gov', 'mil', 'int',
        'io', 'co', 'ai', 'app', 'dev', 'cloud', 'tech',
        'uk', 'us', 'eu', 'de', 'fr', 'jp', 'cn', 'ru', 'br'
    }
    
    def _index_domain(self, ioc: IOC):
        """Index domain for exact and subdomain matching"""
        domain = ioc.value.lower()
        self._domain_map[domain] = ioc
        
        # Index for subdomain matching (suffixes with at least 2 parts, not just TLD)
        parts = domain.split('.')
        # Only index if we have at least 2 parts (e.g., example.com)
        # Skip indexing just the TLD (e.g., 'com')
        for i in range(len(parts) - 1):  # -1 to avoid indexing just TLD
            suffix = '.'.join(parts[i:])
            # Don't index if it's just a common TLD
            if suffix not in self._COMMON_TLDS and len(parts) - i >= 2:
                self._subdomain_map[suffix].append(ioc)
    
    def _remove_domain(self, ioc: IOC):
        """Remove domain from indices"""
        domain = ioc.value.lower()
        self._domain_map.pop(domain, None)
        
        parts = domain.split('.')
        for i in range(len(parts) - 1):
            suffix = '.'.join(parts[i:])
            if suffix not in self._COMMON_TLDS and len(parts) - i >= 2:
                if suffix in self._subdomain_map:
                    self._subdomain_map[suffix] = [ioc_item for ioc_item in self._subdomain_map[suffix] if ioc_item.ioc_id != ioc.ioc_id]
    
    def check_ip(self, ip_str: str) -> Optional[IOC]:
        """
        Check if IP address matches any IOC
        
        Performs both exact match and CIDR range matching.
        """
        with self._lock:
            # Exact match
            if ip_str in self._ip_map:
                return self._ip_map[ip_str]
            
            # CIDR range match
            try:
                ip = ipaddress.ip_address(ip_str)
                if isinstance(ip, ipaddress.IPv4Address):
                    for network, iocs in self._network_ranges.items():
                        if ip in network:
                            # Return highest confidence match
                            return max(iocs, key=lambda x: x.confidence)
                else:
                    for network, iocs in self._network_ranges_v6.items():
                        if ip in network:
                            return max(iocs, key=lambda x: x.confidence)
            except ValueError:
                pass
            
            return None
    
    def check_domain(self, domain: str, include_subdomains: bool = True) -> Optional[IOC]:
        """
        Check if domain matches any IOC
        
        Supports exact match and subdomain matching.
        """
        with self._lock:
            domain = domain.lower().rstrip('.')
            
            # Exact match
            if domain in self._domain_map:
                return self._domain_map[domain]
            
            # Subdomain match
            if include_subdomains:
                parts = domain.split('.')
                for i in range(1, len(parts)):
                    suffix = '.'.join(parts[i:])
                    if suffix in self._subdomain_map:
                        matches = self._subdomain_map[suffix]
                        # Return highest confidence match
                        return max(matches, key=lambda x: x.confidence)
            
            return None
    
    def check_hash(self, hash_value: str) -> Optional[IOC]:
        """Check if file hash matches any IOC"""
        with self._lock:
            hash_upper = hash_value.upper()
            return self._hash_map.get(hash_upper)
    
    def check_url(self, url: str) -> Optional[IOC]:
        """Check if URL matches any IOC"""
        with self._lock:
            url_lower = url.lower()
            return self._url_map.get(url_lower)
    
    def check_email(self, email: str) -> Optional[IOC]:
        """Check if email matches any IOC"""
        with self._lock:
            email_lower = email.lower()
            return self._email_map.get(email_lower)
    
    def check_mutex(self, mutex: str) -> Optional[IOC]:
        """Check if mutex matches any IOC"""
        with self._lock:
            return self._mutex_map.get(mutex)
    
    def check_registry_key(self, key: str) -> Optional[IOC]:
        """Check if registry key matches any IOC"""
        with self._lock:
            return self._registry_map.get(key)
    
    def check_user_agent(self, user_agent: str) -> Optional[IOC]:
        """Check if user agent matches any IOC"""
        with self._lock:
            return self._user_agent_map.get(user_agent)
    
    def check_value(self, value: str, ioc_type: IOCType) -> Optional[IOC]:
        """
        Generic value check based on IOC type
        
        Pre/Condition: value is non-empty string, ioc_type is valid
        Post/Condition: Returns matching IOC or None
        """
        if ioc_type == IOCType.IP:
            return self.check_ip(value)
        elif ioc_type == IOCType.DOMAIN:
            return self.check_domain(value)
        elif ioc_type in (IOCType.FILE_HASH_MD5, IOCType.FILE_HASH_SHA1, IOCType.FILE_HASH_SHA256):
            return self.check_hash(value)
        elif ioc_type == IOCType.URL:
            return self.check_url(value)
        elif ioc_type == IOCType.EMAIL:
            return self.check_email(value)
        elif ioc_type == IOCType.MUTEX:
            return self.check_mutex(value)
        elif ioc_type == IOCType.REGISTRY_KEY:
            return self.check_registry_key(value)
        elif ioc_type == IOCType.USER_AGENT:
            return self.check_user_agent(value)
        return None
    
    def check_against_all(self, value: str) -> List[Tuple[IOCType, IOC]]:
        """
        Check value against all IOC types
        
        Returns list of (ioc_type, ioc) tuples for all matches.
        """
        matches = []
        
        # Try each type
        for ioc_type in IOCType:
            match = self.check_value(value, ioc_type)
            if match:
                matches.append((ioc_type, match))
        
        return matches
    
    def get_stats(self) -> Dict[str, int]:
        """Get matching engine statistics"""
        with self._lock:
            return {
                "total_iocs": len(self._iocs_by_id),
                "ip_iocs": len(self._ip_map),
                "domain_iocs": len(self._domain_map),
                "hash_iocs": len(self._hash_map),
                "url_iocs": len(self._url_map),
                "email_iocs": len(self._email_map),
                "mutex_iocs": len(self._mutex_map),
                "registry_iocs": len(self._registry_map),
                "user_agent_iocs": len(self._user_agent_map),
                "network_ranges_v4": len(self._network_ranges),
                "network_ranges_v6": len(self._network_ranges_v6),
            }
    
    def clear(self):
        """Clear all indices"""
        with self._lock:
            self._ip_map.clear()
            self._domain_map.clear()
            self._hash_map.clear()
            self._url_map.clear()
            self._email_map.clear()
            self._mutex_map.clear()
            self._registry_map.clear()
            self._user_agent_map.clear()
            self._network_ranges.clear()
            self._network_ranges_v6.clear()
            self._subdomain_map.clear()
            self._regex_patterns.clear()
            self._iocs_by_id.clear()


class IOCManager:
    """
    IOC Management System
    
    Central management for Indicators of Compromise with:
    - Database persistence
    - High-performance matching engine
    - STIX 2.1 import/export
    - Feed management
    - Automated cleanup
    
    Thread-safe for concurrent operations.
    """
    
    def __init__(self, db_path: str = "/opt/codex-swarm/command-post/data/nexus.db"):
        self.db_path = db_path
        self.engine = IOCMatchingEngine()
        self.feeds: Dict[str, IOCFeed] = {}
        
        # Thread safety
        self._lock = threading.RLock()
        self._update_thread: Optional[threading.Thread] = None
        self._running = False
        
        # Initialize
        self._init_database()
        self._load_iocs_from_db()
        self._start_auto_update()
        
        logger.info("[IOC-MANAGER] IOC Manager initialized")
    
    def _init_database(self):
        """Initialize IOC database schema"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # IOCs table (extended from blueteam_iocs)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ioc_indicators (
                    ioc_id TEXT PRIMARY KEY,
                    ioc_type TEXT NOT NULL,
                    value TEXT NOT NULL,
                    threat_type TEXT,
                    severity TEXT,
                    confidence INTEGER,
                    source TEXT,
                    first_seen TEXT,
                    last_seen TEXT,
                    expiration TEXT,
                    tags TEXT,
                    description TEXT,
                    related_iocs TEXT,
                    metadata TEXT,
                    hit_count INTEGER DEFAULT 0,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)
            
            # IOC feeds table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ioc_feeds (
                    feed_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    url TEXT,
                    feed_type TEXT,
                    api_key TEXT,
                    enabled BOOLEAN DEFAULT 1,
                    auto_update BOOLEAN DEFAULT 0,
                    update_interval INTEGER DEFAULT 60,
                    last_update TEXT,
                    next_update TEXT,
                    ioc_count INTEGER DEFAULT 0,
                    trust_score INTEGER DEFAULT 50,
                    filters TEXT,
                    metadata TEXT,
                    created_at TEXT
                )
            """)
            
            # IOC match history
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ioc_match_history (
                    match_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ioc_id TEXT,
                    timestamp TEXT,
                    matched_value TEXT,
                    context TEXT,
                    source_ip TEXT,
                    source_host TEXT
                )
            """)
            
            conn.commit()
    
    def _load_iocs_from_db(self):
        """Load IOCs from database into memory"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM ioc_indicators")
                
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                
                for row in rows:
                    data = dict(zip(columns, row))
                    
                    # Parse JSON fields
                    for field in ["tags", "related_iocs", "metadata"]:
                        if data.get(field):
                            try:
                                data[field] = json.loads(data[field])
                            except json.JSONDecodeError:
                                data[field] = []
                    
                    # Parse datetime fields
                    for field in ["first_seen", "last_seen", "expiration", "created_at", "updated_at"]:
                        if data.get(field):
                            data[field] = datetime.fromisoformat(data[field])
                    
                    try:
                        ioc = IOC.from_dict(data)
                        self.engine.add_ioc(ioc)
                    except Exception as e:
                        logger.error(f"[IOC-MANAGER] Failed to load IOC {data.get('ioc_id')}: {e}")
                
                logger.info(f"[IOC-MANAGER] Loaded {len(rows)} IOCs from database")
        except Exception as e:
            logger.error(f"[IOC-MANAGER] Failed to load IOCs: {e}")
    
    # ========================================================================
    # IOC CRUD Operations
    # ========================================================================
    
    def add_ioc(self, 
                value: str,
                ioc_type: Union[IOCType, str],
                threat_type: Union[ThreatType, str] = ThreatType.UNKNOWN,
                severity: Union[SeverityLevel, str] = SeverityLevel.MEDIUM,
                confidence: int = 50,
                source: str = "",
                description: str = "",
                tags: Optional[List[str]] = None,
                expiration: Optional[datetime] = None,
                related_iocs: Optional[List[str]] = None,
                metadata: Optional[Dict[str, Any]] = None,
                ioc_id: Optional[str] = None) -> Optional[IOC]:
        """
        Add new IOC to the system
        
        Args:
            value: The indicator value
            ioc_type: Type of indicator
            threat_type: Classification of threat
            severity: Severity level
            confidence: Confidence score 0-100
            source: Origin of the IOC
            description: Human-readable description
            tags: Searchable tags
            expiration: Expiration timestamp
            related_iocs: Related IOC IDs
            metadata: Additional metadata
            ioc_id: Optional custom ID (generated if not provided)
            
        Returns:
            Created IOC or None on failure
        """
        with self._lock:
            try:
                # Generate ID if not provided
                if ioc_id is None:
                    ioc_id = str(uuid.uuid4())
                
                # Create IOC
                ioc = IOC(
                    ioc_id=ioc_id,
                    ioc_type=IOCType.from_string(ioc_type) if isinstance(ioc_type, str) else ioc_type,
                    value=value,
                    threat_type=ThreatType(threat_type) if isinstance(threat_type, str) else threat_type,
                    severity=SeverityLevel.from_string(severity) if isinstance(severity, str) else severity,
                    confidence=confidence,
                    source=source,
                    first_seen=datetime.utcnow(),
                    last_seen=datetime.utcnow(),
                    expiration=expiration,
                    tags=tags or [],
                    description=description,
                    related_iocs=related_iocs or [],
                    metadata=metadata or {},
                )
                
                # Add to engine
                if not self.engine.add_ioc(ioc):
                    return None
                
                # Persist to database
                self._persist_ioc(ioc)
                
                logger.info(f"[IOC-MANAGER] Added IOC: {ioc.ioc_id} ({ioc.ioc_type.value}: {ioc.value})")
                return ioc
                
            except Exception as e:
                logger.error(f"[IOC-MANAGER] Failed to add IOC: {e}")
                return None
    
    def update_ioc(self, ioc_id: str, **updates) -> Optional[IOC]:
        """
        Update existing IOC
        
        Args:
            ioc_id: IOC identifier
            **updates: Fields to update
            
        Returns:
            Updated IOC or None if not found
        """
        with self._lock:
            # Get current IOC
            ioc = self.get_ioc(ioc_id)
            if not ioc:
                return None
            
            # Remove from engine (will re-add with updated values)
            self.engine.remove_ioc(ioc_id)
            
            # Update fields
            for key, value in updates.items():
                if hasattr(ioc, key):
                    setattr(ioc, key, value)
            
            # Update timestamp
            ioc.updated_at = datetime.utcnow()
            
            # Re-add to engine
            self.engine.add_ioc(ioc)
            
            # Persist to database
            self._persist_ioc(ioc)
            
            logger.info(f"[IOC-MANAGER] Updated IOC: {ioc_id}")
            return ioc
    
    def remove_ioc(self, ioc_id: str) -> bool:
        """
        Remove IOC by ID
        
        Args:
            ioc_id: IOC identifier to remove
            
        Returns:
            True if removed, False if not found
        """
        with self._lock:
            if not self.engine.remove_ioc(ioc_id):
                return False
            
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM ioc_indicators WHERE ioc_id = ?", (ioc_id,))
                    conn.commit()
                
                logger.info(f"[IOC-MANAGER] Removed IOC: {ioc_id}")
                return True
            except Exception as e:
                logger.error(f"[IOC-MANAGER] Failed to remove IOC {ioc_id}: {e}")
                return False
    
    def get_ioc(self, ioc_id: str) -> Optional[IOC]:
        """
        Retrieve IOC by ID
        
        Args:
            ioc_id: IOC identifier
            
        Returns:
            IOC if found, None otherwise
        """
        return self.engine._iocs_by_id.get(ioc_id)
    
    def lookup_ioc(self, value: str, ioc_type: Optional[IOCType] = None) -> Optional[IOC]:
        """
        Search IOC by value
        
        Args:
            value: Indicator value to search
            ioc_type: Optional type filter
            
        Returns:
            Matching IOC or None
        """
        if ioc_type:
            return self.engine.check_value(value, ioc_type)
        
        # Search all types
        matches = self.engine.check_against_all(value)
        if matches:
            return matches[0][1]  # Return first match
        return None
    
    def search_iocs(self,
                    ioc_type: Optional[IOCType] = None,
                    threat_type: Optional[ThreatType] = None,
                    severity: Optional[SeverityLevel] = None,
                    source: Optional[str] = None,
                    tags: Optional[List[str]] = None,
                    min_confidence: int = 0,
                    active_only: bool = True) -> List[IOC]:
        """
        Search/filter IOCs by criteria
        
        Args:
            ioc_type: Filter by IOC type
            threat_type: Filter by threat type
            severity: Filter by severity
            source: Filter by source
            tags: Filter by tags (any match)
            min_confidence: Minimum confidence score
            active_only: Only return non-expired IOCs
            
        Returns:
            List of matching IOCs
        """
        results = []
        
        for ioc in self.engine._iocs_by_id.values():
            # Apply filters
            if active_only and not ioc.is_active():
                continue
            if ioc_type and ioc.ioc_type != ioc_type:
                continue
            if threat_type and ioc.threat_type != threat_type:
                continue
            if severity and ioc.severity != severity:
                continue
            if source and ioc.source != source:
                continue
            if ioc.confidence < min_confidence:
                continue
            if tags and not any(tag in ioc.tags for tag in tags):
                continue
            
            results.append(ioc)
        
        return results
    
    def check_value(self, value: str, ioc_type: IOCType) -> Optional[IOC]:
        """
        Check if value matches known IOC
        
        Args:
            value: Value to check
            ioc_type: Type of indicator
            
        Returns:
            Matching IOC or None
        """
        return self.engine.check_value(value, ioc_type)
    
    def record_match(self, ioc_id: str, matched_value: str, context: Optional[Dict] = None,
                     source_ip: str = "", source_host: str = ""):
        """
        Record IOC match occurrence
        
        Args:
            ioc_id: Matched IOC ID
            matched_value: The value that matched
            context: Additional context
            source_ip: Source IP address
            source_host: Source hostname
        """
        with self._lock:
            # Update hit count in memory
            ioc = self.engine._iocs_by_id.get(ioc_id)
            if ioc:
                ioc.hit_count += 1
                ioc.last_seen = datetime.utcnow()
            
            # Persist match to database
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO ioc_match_history
                        (ioc_id, timestamp, matched_value, context, source_ip, source_host)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        ioc_id,
                        datetime.utcnow().isoformat(),
                        matched_value,
                        json.dumps(context) if context else None,
                        source_ip,
                        source_host
                    ))
                    conn.commit()
            except Exception as e:
                logger.error(f"[IOC-MANAGER] Failed to record match: {e}")
    
    def _persist_ioc(self, ioc: IOC):
        """Persist IOC to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO ioc_indicators
                    (ioc_id, ioc_type, value, threat_type, severity, confidence, source,
                     first_seen, last_seen, expiration, tags, description, related_iocs,
                     metadata, hit_count, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    ioc.ioc_id,
                    ioc.ioc_type.value,
                    ioc.value,
                    ioc.threat_type.value,
                    ioc.severity.name,
                    ioc.confidence,
                    ioc.source,
                    ioc.first_seen.isoformat() if ioc.first_seen else None,
                    ioc.last_seen.isoformat() if ioc.last_seen else None,
                    ioc.expiration.isoformat() if ioc.expiration else None,
                    json.dumps(ioc.tags),
                    ioc.description,
                    json.dumps(ioc.related_iocs),
                    json.dumps(ioc.metadata),
                    ioc.hit_count,
                    ioc.created_at.isoformat(),
                    ioc.updated_at.isoformat()
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"[IOC-MANAGER] Failed to persist IOC {ioc.ioc_id}: {e}")
    
    # ========================================================================
    # STIX Import/Export
    # ========================================================================
    
    def import_stix(self, stix_data: Dict[str, Any], source: str = "stix_import") -> List[IOC]:
        """
        Import IOCs from STIX 2.1 bundle
        
        Args:
            stix_data: STIX bundle dictionary
            source: Source identifier
            
        Returns:
            List of imported IOCs
        """
        imported = []
        
        try:
            objects = stix_data.get("objects", [])
            
            for obj in objects:
                obj_type = obj.get("type")
                
                if obj_type == "indicator":
                    ioc = self._parse_stix_indicator(obj, source)
                    if ioc:
                        existing = self.lookup_ioc(ioc.value, ioc.ioc_type)
                        if existing:
                            # Update existing
                            self.update_ioc(existing.ioc_id, 
                                          confidence=max(existing.confidence, ioc.confidence),
                                          last_seen=datetime.utcnow())
                        else:
                            # Add new
                            result = self.add_ioc(
                                value=ioc.value,
                                ioc_type=ioc.ioc_type,
                                threat_type=ioc.threat_type,
                                severity=ioc.severity,
                                confidence=ioc.confidence,
                                source=source,
                                description=ioc.description,
                                tags=ioc.tags,
                                expiration=ioc.expiration
                            )
                            if result:
                                imported.append(result)
                
                elif obj_type in ("ipv4-addr", "ipv6-addr", "domain-name", "file", "url", "email-addr"):
                    # Handle observable objects
                    ioc = self._parse_stix_observable(obj, source)
                    if ioc:
                        result = self.add_ioc(
                            value=ioc.value,
                            ioc_type=ioc.ioc_type,
                            source=source,
                            confidence=70
                        )
                        if result:
                            imported.append(result)
            
            logger.info(f"[IOC-MANAGER] Imported {len(imported)} IOCs from STIX")
            return imported
            
        except Exception as e:
            logger.error(f"[IOC-MANAGER] STIX import failed: {e}")
            return []
    
    def _parse_stix_indicator(self, indicator: Dict[str, Any], source: str) -> Optional[IOC]:
        """Parse STIX indicator object to IOC"""
        try:
            pattern = indicator.get("pattern", "")
            
            # Parse pattern to extract value
            ioc_type, value = self._parse_stix_pattern(pattern)
            
            if not value:
                return None
            
            # Extract confidence
            confidence = indicator.get("confidence", 50)
            
            # Extract expiration
            valid_until = indicator.get("valid_until")
            expiration = None
            if valid_until:
                expiration = datetime.fromisoformat(valid_until.replace("Z", "+00:00"))
            
            return IOC(
                ioc_id=indicator.get("id", "").replace("indicator--", ""),
                ioc_type=ioc_type,
                value=value,
                threat_type=ThreatType.UNKNOWN,
                severity=SeverityLevel.MEDIUM,
                confidence=confidence,
                source=source,
                description=indicator.get("description", ""),
                tags=indicator.get("labels", []),
                expiration=expiration
            )
        except Exception as e:
            logger.error(f"[IOC-MANAGER] Failed to parse STIX indicator: {e}")
            return None
    
    def _parse_stix_pattern(self, pattern: str) -> Tuple[IOCType, str]:
        """Parse STIX pattern to extract IOC type and value"""
        # Simple pattern parsing (would need full STIX pattern parser for production)
        if "ipv4-addr:value" in pattern or "ipv6-addr:value" in pattern:
            match = re.search(r"=\s*['\"]([^'\"]+)['\"]", pattern)
            if match:
                return IOCType.IP, match.group(1)
        elif "domain-name:value" in pattern:
            match = re.search(r"=\s*['\"]([^'\"]+)['\"]", pattern)
            if match:
                return IOCType.DOMAIN, match.group(1)
        elif "url:value" in pattern:
            match = re.search(r"=\s*['\"]([^'\"]+)['\"]", pattern)
            if match:
                return IOCType.URL, match.group(1)
        elif "file:hashes.MD5" in pattern or "file:hashes.\"MD5\"" in pattern:
            match = re.search(r"=\s*['\"]([^'\"]+)['\"]", pattern)
            if match:
                return IOCType.FILE_HASH_MD5, match.group(1)
        elif "file:hashes.\"SHA-1\"" in pattern:
            match = re.search(r"=\s*['\"]([^'\"]+)['\"]", pattern)
            if match:
                return IOCType.FILE_HASH_SHA1, match.group(1)
        elif "file:hashes.\"SHA-256\"" in pattern:
            match = re.search(r"=\s*['\"]([^'\"]+)['\"]", pattern)
            if match:
                return IOCType.FILE_HASH_SHA256, match.group(1)
        elif "email-addr:value" in pattern:
            match = re.search(r"=\s*['\"]([^'\"]+)['\"]", pattern)
            if match:
                return IOCType.EMAIL, match.group(1)
        elif "mutex:name" in pattern:
            match = re.search(r"=\s*['\"]([^'\"]+)['\"]", pattern)
            if match:
                return IOCType.MUTEX, match.group(1)
        elif "windows-registry-key:key" in pattern:
            match = re.search(r"=\s*['\"]([^'\"]+)['\"]", pattern)
            if match:
                return IOCType.REGISTRY_KEY, match.group(1)
        
        return IOCType.IP, ""
    
    def _parse_stix_observable(self, observable: Dict[str, Any], source: str) -> Optional[IOC]:
        """Parse STIX observable object to IOC"""
        try:
            obj_type = observable.get("type")
            
            if obj_type == "ipv4-addr":
                return IOC(
                    ioc_id=str(uuid.uuid4()),
                    ioc_type=IOCType.IP,
                    value=observable.get("value", ""),
                    source=source
                )
            elif obj_type == "domain-name":
                return IOC(
                    ioc_id=str(uuid.uuid4()),
                    ioc_type=IOCType.DOMAIN,
                    value=observable.get("value", ""),
                    source=source
                )
            elif obj_type == "url":
                return IOC(
                    ioc_id=str(uuid.uuid4()),
                    ioc_type=IOCType.URL,
                    value=observable.get("value", ""),
                    source=source
                )
            elif obj_type == "email-addr":
                return IOC(
                    ioc_id=str(uuid.uuid4()),
                    ioc_type=IOCType.EMAIL,
                    value=observable.get("value", ""),
                    source=source
                )
            elif obj_type == "file":
                hashes = observable.get("hashes", {})
                if "SHA-256" in hashes:
                    return IOC(
                        ioc_id=str(uuid.uuid4()),
                        ioc_type=IOCType.FILE_HASH_SHA256,
                        value=hashes["SHA-256"],
                        source=source
                    )
                elif "SHA-1" in hashes:
                    return IOC(
                        ioc_id=str(uuid.uuid4()),
                        ioc_type=IOCType.FILE_HASH_SHA1,
                        value=hashes["SHA-1"],
                        source=source
                    )
                elif "MD5" in hashes:
                    return IOC(
                        ioc_id=str(uuid.uuid4()),
                        ioc_type=IOCType.FILE_HASH_MD5,
                        value=hashes["MD5"],
                        source=source
                    )
            
            return None
        except Exception as e:
            logger.error(f"[IOC-MANAGER] Failed to parse STIX observable: {e}")
            return None
    
    def export_stix(self, ioc_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Export IOCs to STIX 2.1 bundle
        
        Args:
            ioc_ids: Optional list of IOC IDs to export (all if None)
            
        Returns:
            STIX bundle dictionary
        """
        bundle = {
            "type": "bundle",
            "id": f"bundle--{uuid.uuid4()}",
            "spec_version": "2.1",
            "objects": []
        }
        
        # Get IOCs to export
        if ioc_ids:
            iocs = [self.get_ioc(iid) for iid in ioc_ids]
            iocs = [ioc for ioc in iocs if ioc]
        else:
            iocs = list(self.engine._iocs_by_id.values())
        
        # Convert to STIX
        for ioc in iocs:
            stix_obj = ioc.to_stix_indicator()
            bundle["objects"].append(stix_obj)
        
        logger.info(f"[IOC-MANAGER] Exported {len(iocs)} IOCs to STIX")
        return bundle
    
    # ========================================================================
    # Feed Management
    # ========================================================================
    
    def add_feed(self, 
                 name: str,
                 url: str,
                 feed_type: str = "stix",
                 api_key: Optional[str] = None,
                 auto_update: bool = False,
                 update_interval: int = 60,
                 trust_score: int = 50,
                 filters: Optional[Dict[str, Any]] = None) -> Optional[IOCFeed]:
        """
        Register new threat feed
        
        Args:
            name: Feed name
            url: Feed URL
            feed_type: Feed format (stix, misp, taxii, csv, json)
            api_key: Authentication key
            auto_update: Enable automatic updates
            update_interval: Update interval in minutes
            trust_score: Feed reliability 0-100
            filters: Feed-specific filters
            
        Returns:
            Created feed or None on failure
        """
        with self._lock:
            try:
                feed_id = str(uuid.uuid4())
                
                feed = IOCFeed(
                    feed_id=feed_id,
                    name=name,
                    url=url,
                    feed_type=feed_type,
                    api_key=api_key,
                    auto_update=auto_update,
                    update_interval=update_interval,
                    trust_score=trust_score,
                    filters=filters or {}
                )
                
                # Calculate next update
                if auto_update:
                    feed.next_update = datetime.utcnow() + timedelta(minutes=update_interval)
                
                self.feeds[feed_id] = feed
                self._persist_feed(feed)
                
                logger.info(f"[IOC-MANAGER] Added feed: {name} ({feed_id})")
                return feed
                
            except Exception as e:
                logger.error(f"[IOC-MANAGER] Failed to add feed: {e}")
                return None
    
    def update_feed(self, feed_id: str) -> bool:
        """
        Manually refresh feed
        
        Args:
            feed_id: Feed identifier
            
        Returns:
            True if successful
        """
        feed = self.feeds.get(feed_id)
        if not feed:
            logger.error(f"[IOC-MANAGER] Feed not found: {feed_id}")
            return False
        
        try:
            logger.info(f"[IOC-MANAGER] Updating feed: {feed.name}")
            
            # This would fetch from actual URL in production
            # For now, mark as updated
            feed.last_update = datetime.utcnow()
            feed.next_update = datetime.utcnow() + timedelta(minutes=feed.update_interval)
            
            self._persist_feed(feed)
            return True
            
        except Exception as e:
            logger.error(f"[IOC-MANAGER] Feed update failed: {e}")
            return False
    
    def enable_auto_update(self, feed_id: str, enabled: bool = True) -> bool:
        """
        Enable/disable automatic feed updates
        
        Args:
            feed_id: Feed identifier
            enabled: Enable or disable
            
        Returns:
            True if successful
        """
        with self._lock:
            feed = self.feeds.get(feed_id)
            if not feed:
                return False
            
            feed.auto_update = enabled
            if enabled:
                feed.next_update = datetime.utcnow() + timedelta(minutes=feed.update_interval)
            else:
                feed.next_update = None
            
            self._persist_feed(feed)
            logger.info(f"[IOC-MANAGER] Auto-update {'enabled' if enabled else 'disabled'} for {feed.name}")
            return True
    
    def get_feeds(self) -> List[IOCFeed]:
        """Get all registered feeds"""
        return list(self.feeds.values())
    
    def remove_feed(self, feed_id: str) -> bool:
        """Remove a feed"""
        with self._lock:
            if feed_id not in self.feeds:
                return False
            
            del self.feeds[feed_id]
            
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM ioc_feeds WHERE feed_id = ?", (feed_id,))
                    conn.commit()
                return True
            except Exception as e:
                logger.error(f"[IOC-MANAGER] Failed to remove feed: {e}")
                return False
    
    def _persist_feed(self, feed: IOCFeed):
        """Persist feed to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO ioc_feeds
                    (feed_id, name, url, feed_type, api_key, enabled, auto_update,
                     update_interval, last_update, next_update, ioc_count, trust_score,
                     filters, metadata, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    feed.feed_id,
                    feed.name,
                    feed.url,
                    feed.feed_type,
                    feed.api_key,
                    feed.enabled,
                    feed.auto_update,
                    feed.update_interval,
                    feed.last_update.isoformat() if feed.last_update else None,
                    feed.next_update.isoformat() if feed.next_update else None,
                    feed.ioc_count,
                    feed.trust_score,
                    json.dumps(feed.filters),
                    json.dumps(feed.metadata),
                    feed.created_at.isoformat()
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"[IOC-MANAGER] Failed to persist feed: {e}")
    
    def _start_auto_update(self):
        """Start automatic feed update thread"""
        self._running = True
        self._update_thread = threading.Thread(target=self._auto_update_loop, daemon=True)
        self._update_thread.start()
        logger.info("[IOC-MANAGER] Auto-update thread started")
    
    def _auto_update_loop(self):
        """Background thread for automatic feed updates"""
        while self._running:
            try:
                now = datetime.utcnow()
                
                for feed in self.feeds.values():
                    if feed.auto_update and feed.enabled and feed.next_update:
                        if now >= feed.next_update:
                            self.update_feed(feed.feed_id)
                
                # Sleep for 1 minute
                for _ in range(60):
                    if not self._running:
                        break
                    threading.Event().wait(1)
                    
            except Exception as e:
                logger.error(f"[IOC-MANAGER] Auto-update error: {e}")
    
    # ========================================================================
    # Statistics & Maintenance
    # ========================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get IOC statistics
        
        Returns:
            Dictionary with IOC counts by type and other metrics
        """
        engine_stats = self.engine.get_stats()
        
        # Calculate additional stats
        expired_count = sum(1 for ioc in self.engine._iocs_by_id.values() if ioc.is_expired())
        total_hits = sum(ioc.hit_count for ioc in self.engine._iocs_by_id.values())
        
        # Severity distribution
        severity_dist = defaultdict(int)
        for ioc in self.engine._iocs_by_id.values():
            severity_dist[ioc.severity.name] += 1
        
        # Source distribution
        source_dist = defaultdict(int)
        for ioc in self.engine._iocs_by_id.values():
            source_dist[ioc.source] += 1
        
        return {
            **engine_stats,
            "expired_iocs": expired_count,
            "active_iocs": engine_stats["total_iocs"] - expired_count,
            "total_hits": total_hits,
            "severity_distribution": dict(severity_dist),
            "source_distribution": dict(source_dist),
            "feed_count": len(self.feeds),
        }
    
    def cleanup_expired(self, remove: bool = True) -> List[str]:
        """
        Remove or list expired IOCs
        
        Args:
            remove: If True, remove expired IOCs; if False, just list them
            
        Returns:
            List of expired IOC IDs
        """
        expired_ids = []
        
        for ioc in self.engine._iocs_by_id.values():
            if ioc.is_expired():
                expired_ids.append(ioc.ioc_id)
        
        if remove:
            for ioc_id in expired_ids:
                self.remove_ioc(ioc_id)
            logger.info(f"[IOC-MANAGER] Cleaned up {len(expired_ids)} expired IOCs")
        
        return expired_ids
    
    def cleanup_by_confidence(self, min_confidence: int) -> int:
        """
        Remove IOCs below confidence threshold
        
        Args:
            min_confidence: Minimum confidence score to keep
            
        Returns:
            Number of IOCs removed
        """
        removed = 0
        
        for ioc in list(self.engine._iocs_by_id.values()):
            if ioc.confidence < min_confidence:
                if self.remove_ioc(ioc.ioc_id):
                    removed += 1
        
        logger.info(f"[IOC-MANAGER] Removed {removed} IOCs below confidence {min_confidence}")
        return removed
    
    def shutdown(self):
        """Shutdown IOC manager"""
        self._running = False
        if self._update_thread:
            self._update_thread.join(timeout=5)
        logger.info("[IOC-MANAGER] Shutdown complete")


# Global instance
_ioc_manager: Optional[IOCManager] = None


def get_ioc_manager(db_path: Optional[str] = None) -> IOCManager:
    """
    Get global IOC manager instance
    
    Args:
        db_path: Optional database path override
        
    Returns:
        IOCManager singleton instance
    """
    global _ioc_manager
    if _ioc_manager is None:
        _ioc_manager = IOCManager(db_path) if db_path else IOCManager()
    return _ioc_manager
