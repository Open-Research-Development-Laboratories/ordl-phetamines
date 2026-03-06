#!/usr/bin/env python3
"""
================================================================================
ORDL COMMAND POST v6.0.0 - BLUE TEAM LOG PARSER MODULE
================================================================================
Classification: TOP SECRET//SCI//NOFORN
Classification Level: TS/SCI/NOFORN
Compartment: ORDL-CYBER-OPS

MULTI-FORMAT LOG PARSER FRAMEWORK
================================================================================
Military-grade log parsing engine supporting:
- Syslog (RFC3164/RFC5424)
- JSON logs with schema detection
- Apache/Nginx access logs
- Windows Event Log (EVTX)
- AWS CloudTrail
- Kubernetes audit logs
- Suricata/Zeek IDS logs
- Generic CSV/TSV

Features:
- Auto-detection of log formats
- Normalized LogEntry output
- High-performance regex-based parsing
- Graceful handling of malformed logs
- Streaming file processing

Author: ORDL Cyber Operations Division
Version: 6.0.0
================================================================================
"""

import re
import json
import csv
import io
import hashlib
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Optional, Any, Iterator, Tuple, Union, Callable, Set
from enum import Enum, auto
from pathlib import Path
import xml.etree.ElementTree as ET

# Configure logging
logger = logging.getLogger('blueteam.logs.parser')


class LogSeverity(Enum):
    """Standardized log severity levels"""
    EMERGENCY = 0
    ALERT = 1
    CRITICAL = 2
    ERROR = 3
    WARNING = 4
    NOTICE = 5
    INFO = 6
    DEBUG = 7
    UNKNOWN = 8


@dataclass
class LogEntry:
    """
    Normalized log entry representation
    
    This dataclass provides a standardized format for all parsed logs,
    enabling uniform processing by the detection engine regardless of
    the original log source format.
    """
    # Core identification
    entry_id: str = field(default_factory=lambda: hashlib.sha256(
        f"{datetime.utcnow().isoformat()}".encode()).hexdigest()[:16])
    timestamp: datetime = field(default_factory=datetime.utcnow)
    source_format: str = "unknown"  # syslog, json, apache, etc.
    
    # Source information
    source_host: Optional[str] = None
    source_ip: Optional[str] = None
    source_port: Optional[int] = None
    
    # Actor information
    user: Optional[str] = None
    user_id: Optional[str] = None
    process_name: Optional[str] = None
    process_id: Optional[int] = None
    
    # Event details
    severity: LogSeverity = LogSeverity.UNKNOWN
    severity_label: str = "UNKNOWN"
    facility: Optional[str] = None
    message: str = ""
    message_id: Optional[str] = None
    
    # Network context (if applicable)
    dest_ip: Optional[str] = None
    dest_port: Optional[int] = None
    protocol: Optional[str] = None
    
    # Security context
    action: Optional[str] = None  # allow, deny, block, alert, etc.
    status_code: Optional[int] = None
    
    # Raw data preservation
    raw_data: str = ""
    raw_fields: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    parsed_at: datetime = field(default_factory=datetime.utcnow)
    parser_version: str = "6.0.0"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert LogEntry to dictionary"""
        return {
            'entry_id': self.entry_id,
            'timestamp': self.timestamp.isoformat(),
            'source_format': self.source_format,
            'source_host': self.source_host,
            'source_ip': self.source_ip,
            'source_port': self.source_port,
            'user': self.user,
            'user_id': self.user_id,
            'process_name': self.process_name,
            'process_id': self.process_id,
            'severity': self.severity.name,
            'severity_label': self.severity_label,
            'facility': self.facility,
            'message': self.message,
            'message_id': self.message_id,
            'dest_ip': self.dest_ip,
            'dest_port': self.dest_port,
            'protocol': self.protocol,
            'action': self.action,
            'status_code': self.status_code,
            'raw_data': self.raw_data,
            'raw_fields': self.raw_fields,
            'tags': self.tags,
            'parsed_at': self.parsed_at.isoformat(),
            'parser_version': self.parser_version
        }
    
    def to_security_event(self) -> Dict[str, Any]:
        """
        Convert LogEntry to SecurityEvent format for detection engine
        
        Returns:
            Dictionary compatible with DetectionEvent format
        """
        return {
            'event_id': self.entry_id,
            'timestamp': self.timestamp,
            'source_type': self.source_format,
            'source_host': self.source_host or 'unknown',
            'event_type': self._infer_event_type(),
            'severity': self._map_severity(),
            'raw_data': self.raw_fields,
            'normalized_data': self.to_dict()
        }
    
    def _infer_event_type(self) -> str:
        """Infer event type from log content"""
        msg_lower = self.message.lower()
        
        if any(w in msg_lower for w in ['login', 'auth', 'password', 'credential']):
            if 'fail' in msg_lower:
                return 'authentication_failure'
            elif 'success' in msg_lower:
                return 'authentication_success'
            return 'authentication'
        
        if any(w in msg_lower for w in ['privilege', 'sudo', 'elevate']):
            return 'privilege_escalation'
        
        if any(w in msg_lower for w in ['connection', 'connect', 'network']):
            return 'network_connection'
        
        if any(w in msg_lower for w in ['process', 'execution', 'exec']):
            return 'process_execution'
        
        if any(w in msg_lower for w in ['firewall', 'blocked', 'denied']):
            return 'firewall_event'
        
        return f"{self.source_format}_event"
    
    def _map_severity(self) -> str:
        """Map LogSeverity to detection engine severity"""
        mapping = {
            LogSeverity.EMERGENCY: 'CRITICAL',
            LogSeverity.ALERT: 'CRITICAL',
            LogSeverity.CRITICAL: 'CRITICAL',
            LogSeverity.ERROR: 'HIGH',
            LogSeverity.WARNING: 'MEDIUM',
            LogSeverity.NOTICE: 'LOW',
            LogSeverity.INFO: 'INFO',
            LogSeverity.DEBUG: 'INFO',
            LogSeverity.UNKNOWN: 'INFO'
        }
        return mapping.get(self.severity, 'INFO')


class LogParser(ABC):
    """
    Abstract base class for all log parsers
    
    All concrete parsers must implement:
    - parse_line(): Parse a single log line
    - can_parse(): Auto-detect if parser can handle sample
    """
    
    def __init__(self, name: str):
        self.name = name
        self.version = "6.0.0"
        self.logger = logging.getLogger(f'blueteam.logs.parser.{name}')
    
    @abstractmethod
    def parse_line(self, line: str) -> Optional[LogEntry]:
        """
        Parse a single log line into LogEntry
        
        Args:
            line: Raw log line
            
        Returns:
            LogEntry if successful, None if parsing fails
        """
        pass
    
    @abstractmethod
    def can_parse(self, sample: str) -> bool:
        """
        Check if this parser can handle the sample
        
        Args:
            sample: Sample log line for detection
            
        Returns:
            True if parser can handle this format
        """
        pass
    
    def parse_file(self, file_path: Union[str, Path]) -> Iterator[LogEntry]:
        """
        Parse an entire file, yielding LogEntry objects
        
        Args:
            file_path: Path to log file
            
        Yields:
            LogEntry objects for each successfully parsed line
        """
        path = Path(file_path)
        
        if not path.exists():
            self.logger.error(f"File not found: {file_path}")
            return
        
        self.logger.info(f"Parsing file: {file_path}")
        
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        entry = self.parse_line(line)
                        if entry:
                            yield entry
                    except Exception as e:
                        self.logger.debug(f"Failed to parse line {line_num}: {e}")
                        continue
        except Exception as e:
            self.logger.error(f"Error reading file {file_path}: {e}")
    
    def parse_lines(self, lines: List[str]) -> List[LogEntry]:
        """
        Parse multiple lines
        
        Args:
            lines: List of log lines
            
        Returns:
            List of successfully parsed LogEntry objects
        """
        entries = []
        for line in lines:
            entry = self.parse_line(line)
            if entry:
                entries.append(entry)
        return entries
    
    def _generate_entry_id(self, content: str) -> str:
        """Generate unique entry ID from content"""
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _parse_timestamp(self, ts_str: str, formats: List[str] = None) -> Optional[datetime]:
        """
        Parse timestamp string using multiple formats
        
        Args:
            ts_str: Timestamp string
            formats: List of datetime format strings to try
            
        Returns:
            datetime if successful, None otherwise
        """
        if formats is None:
            formats = [
                '%Y-%m-%dT%H:%M:%S.%fZ',
                '%Y-%m-%dT%H:%M:%SZ',
                '%Y-%m-%d %H:%M:%S.%f',
                '%Y-%m-%d %H:%M:%S',
                '%b %d %H:%M:%S',
                '%d/%b/%Y:%H:%M:%S %z',
                '%d/%b/%Y:%H:%M:%S',
                '%Y-%m-%dT%H:%M:%S.%f%z',
                '%Y-%m-%dT%H:%M:%S%z',
            ]
        
        for fmt in formats:
            try:
                return datetime.strptime(ts_str, fmt)
            except ValueError:
                continue
        
        # Try ISO format as fallback
        try:
            return datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
        except ValueError:
            pass
        
        return None
    
    def _map_syslog_severity(self, severity: Union[int, str]) -> Tuple[LogSeverity, str]:
        """Map syslog severity to LogSeverity"""
        severity_map = {
            0: (LogSeverity.EMERGENCY, 'EMERGENCY'),
            1: (LogSeverity.ALERT, 'ALERT'),
            2: (LogSeverity.CRITICAL, 'CRITICAL'),
            3: (LogSeverity.ERROR, 'ERROR'),
            4: (LogSeverity.WARNING, 'WARNING'),
            5: (LogSeverity.NOTICE, 'NOTICE'),
            6: (LogSeverity.INFO, 'INFO'),
            7: (LogSeverity.DEBUG, 'DEBUG'),
        }
        
        if isinstance(severity, str):
            try:
                severity = int(severity)
            except ValueError:
                severity_lower = severity.lower()
                for sev, (enum, label) in severity_map.items():
                    if label.lower() == severity_lower:
                        return enum, label
                return LogSeverity.UNKNOWN, severity
        
        return severity_map.get(severity, (LogSeverity.UNKNOWN, 'UNKNOWN'))


class SyslogParser(LogParser):
    """
    Parser for Syslog format (RFC3164 and RFC5424)
    
    Supports:
    - RFC3164: Traditional BSD syslog
    - RFC5424: Modern syslog protocol
    """
    
    # RFC3164 pattern: <PRI>TIMESTAMP HOST TAG: MESSAGE
    RFC3164_PATTERN = re.compile(
        r'<(?P<prival>\d{1,3})>'
        r'(?P<timestamp>[A-Za-z]{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+'
        r'(?P<host>\S+)\s+'
        r'(?P<tag>[^:]+):?\s*'
        r'(?P<message>.*)'
    )
    
    # RFC5424 pattern: <PRI>VERSION TIMESTAMP HOST APP PROCID MSGID STRUCTURED-DATA MSG
    RFC5424_PATTERN = re.compile(
        r'<(?P<prival>\d{1,3})>'
        r'(?P<version>\d+)\s+'
        r'(?P<timestamp>\S+)\s+'
        r'(?P<host>\S+)\s+'
        r'(?P<app>\S+)\s+'
        r'(?P<procid>\S+)\s+'
        r'(?P<msgid>\S+)\s+'
        r'(?P<sd>-|\[.*\])\s*'
        r'(?P<message>.*)'
    )
    
    # Simplified pattern for detection
    DETECT_PATTERN = re.compile(r'^<\d{1,3}>')
    
    def __init__(self):
        super().__init__("syslog")
        self.current_year = datetime.utcnow().year
    
    def can_parse(self, sample: str) -> bool:
        """Check if sample matches syslog format"""
        if not sample:
            return False
        return bool(self.DETECT_PATTERN.match(sample))
    
    def parse_line(self, line: str) -> Optional[LogEntry]:
        """Parse syslog line into LogEntry"""
        line = line.strip()
        if not line:
            return None
        
        # Try RFC5424 first (more specific)
        match = self.RFC5424_PATTERN.match(line)
        if match:
            return self._parse_rfc5424(match, line)
        
        # Try RFC3164
        match = self.RFC3164_PATTERN.match(line)
        if match:
            return self._parse_rfc3164(match, line)
        
        return None
    
    def _parse_rfc3164(self, match: re.Match, raw_line: str) -> LogEntry:
        """Parse RFC3164 format"""
        data = match.groupdict()
        
        # Parse priority value
        prival = int(data['prival'])
        facility = prival >> 3
        severity = prival & 0x7
        
        # Parse timestamp (RFC3164 doesn't include year)
        ts_str = data['timestamp']
        timestamp = self._parse_timestamp(
            f"{self.current_year} {ts_str}",
            ['%Y %b %d %H:%M:%S']
        )
        if not timestamp:
            timestamp = datetime.utcnow()
        
        severity_enum, severity_label = self._map_syslog_severity(severity)
        
        # Extract process ID from tag if present
        tag = data.get('tag', '')
        process_name = None
        process_id = None
        
        tag_match = re.match(r'(\S+)\[(\d+)\]', tag)
        if tag_match:
            process_name = tag_match.group(1)
            process_id = int(tag_match.group(2))
        else:
            process_name = tag if tag else None
        
        return LogEntry(
            entry_id=self._generate_entry_id(raw_line),
            timestamp=timestamp,
            source_format='syslog_rfc3164',
            source_host=data.get('host'),
            process_name=process_name,
            process_id=process_id,
            severity=severity_enum,
            severity_label=severity_label,
            facility=str(facility),
            message=data.get('message', ''),
            raw_data=raw_line,
            raw_fields={'prival': prival, 'facility': facility, 'severity': severity}
        )
    
    def _parse_rfc5424(self, match: re.Match, raw_line: str) -> LogEntry:
        """Parse RFC5424 format"""
        data = match.groupdict()
        
        # Parse priority value
        prival = int(data['prival'])
        facility = prival >> 3
        severity = prival & 0x7
        
        # Parse timestamp
        ts_str = data['timestamp']
        timestamp = self._parse_timestamp(ts_str)
        if not timestamp:
            timestamp = datetime.utcnow()
        
        severity_enum, severity_label = self._map_syslog_severity(severity)
        
        # Parse structured data if present
        structured_data = {}
        sd_str = data.get('sd', '-')
        if sd_str != '-':
            structured_data = self._parse_structured_data(sd_str)
        
        return LogEntry(
            entry_id=self._generate_entry_id(raw_line),
            timestamp=timestamp,
            source_format='syslog_rfc5424',
            source_host=data.get('host'),
            process_name=data.get('app') if data.get('app') != '-' else None,
            process_id=int(data['procid']) if data.get('procid', '-').isdigit() else None,
            severity=severity_enum,
            severity_label=severity_label,
            facility=str(facility),
            message=data.get('message', ''),
            message_id=data.get('msgid') if data.get('msgid') != '-' else None,
            raw_data=raw_line,
            raw_fields={
                'prival': prival,
                'facility': facility,
                'severity': severity,
                'version': data.get('version'),
                'structured_data': structured_data
            }
        )
    
    def _parse_structured_data(self, sd_str: str) -> Dict[str, Any]:
        """Parse RFC5424 structured data"""
        result = {}
        # Simple parser for structured data
        # Format: [id param="value" param2="value2"]
        sd_pattern = re.compile(r'\[(\S+)\s+([^\]]+)\]')
        
        for match in sd_pattern.finditer(sd_str):
            sd_id = match.group(1)
            params = match.group(2)
            result[sd_id] = {}
            
            # Parse parameters
            param_pattern = re.compile(r'(\S+)="([^"]*)"')
            for pmatch in param_pattern.finditer(params):
                result[sd_id][pmatch.group(1)] = pmatch.group(2)
        
        return result


class JSONParser(LogParser):
    """
    Parser for JSON-formatted logs
    
    Features:
    - Automatic field mapping
    - Schema detection
    - Nested field extraction
    """
    
    # Common timestamp field names
    TIMESTAMP_FIELDS = ['timestamp', 'time', '@timestamp', 'ts', 'datetime', 
                       'created_at', 'eventTime', 'event_time', 'date']
    
    # Common message field names
    MESSAGE_FIELDS = ['message', 'msg', 'text', 'log', 'event', 'description',
                     'eventName', 'event_name', 'summary']
    
    # Common severity field names
    SEVERITY_FIELDS = ['severity', 'level', 'loglevel', 'priority', 'status',
                      'eventType', 'type']
    
    # Common host field names
    HOST_FIELDS = ['host', 'hostname', 'source', 'source_host', 'computer',
                  'instance', 'server']
    
    def __init__(self, field_mapping: Optional[Dict[str, str]] = None):
        super().__init__("json")
        self.field_mapping = field_mapping or {}
    
    def can_parse(self, sample: str) -> bool:
        """Check if sample is valid JSON"""
        if not sample or not sample.strip():
            return False
        
        sample = sample.strip()
        try:
            json.loads(sample)
            return True
        except (json.JSONDecodeError, ValueError):
            return False
    
    def parse_line(self, line: str) -> Optional[LogEntry]:
        """Parse JSON log line into LogEntry"""
        line = line.strip()
        if not line:
            return None
        
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            return None
        
        if not isinstance(data, dict):
            return None
        
        # Extract fields using common patterns
        timestamp = self._extract_timestamp(data)
        message = self._extract_message(data)
        severity, severity_label = self._extract_severity(data)
        host = self._extract_host(data)
        
        # Extract additional fields
        source_ip = self._extract_nested(data, ['source_ip', 'src_ip', 'client_ip', 
                                                'remote_ip', 'source.address'])
        user = self._extract_nested(data, ['user', 'username', 'user_name', 
                                          'principalId', 'userIdentity.userName'])
        
        entry = LogEntry(
            entry_id=self._generate_entry_id(line),
            timestamp=timestamp or datetime.utcnow(),
            source_format='json',
            source_host=host,
            source_ip=source_ip,
            user=user,
            severity=severity,
            severity_label=severity_label,
            message=message or '',
            raw_data=line,
            raw_fields=data
        )
        
        # Add tags based on detected schema
        entry.tags = self._detect_schema(data)
        
        return entry
    
    def _extract_timestamp(self, data: Dict) -> Optional[datetime]:
        """Extract timestamp from data"""
        for field in self.TIMESTAMP_FIELDS:
            value = self._get_nested_value(data, field)
            if value:
                if isinstance(value, (int, float)):
                    # Assume Unix timestamp
                    return datetime.utcfromtimestamp(value)
                elif isinstance(value, str):
                    return self._parse_timestamp(value)
        return None
    
    def _extract_message(self, data: Dict) -> str:
        """Extract message from data"""
        for field in self.MESSAGE_FIELDS:
            value = self._get_nested_value(data, field)
            if value:
                return str(value)
        return json.dumps(data)
    
    def _extract_severity(self, data: Dict) -> Tuple[LogSeverity, str]:
        """Extract severity from data"""
        for field in self.SEVERITY_FIELDS:
            value = self._get_nested_value(data, field)
            if value is not None:
                return self._normalize_severity(value)
        return LogSeverity.UNKNOWN, 'UNKNOWN'
    
    def _extract_host(self, data: Dict) -> Optional[str]:
        """Extract host from data"""
        for field in self.HOST_FIELDS:
            value = self._get_nested_value(data, field)
            if value:
                return str(value)
        return None
    
    def _extract_nested(self, data: Dict, fields: List[str]) -> Optional[str]:
        """Extract value from list of possible field names"""
        for field in fields:
            value = self._get_nested_value(data, field)
            if value:
                return str(value)
        return None
    
    def _get_nested_value(self, data: Dict, path: str) -> Any:
        """Get value from nested dictionary using dot notation"""
        if '.' in path:
            parts = path.split('.')
            current = data
            for part in parts:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    return None
            return current
        return data.get(path)
    
    def _normalize_severity(self, value: Any) -> Tuple[LogSeverity, str]:
        """Normalize various severity formats to LogSeverity"""
        if isinstance(value, int):
            return self._map_syslog_severity(value)
        
        if isinstance(value, str):
            value_lower = value.lower()
            severity_map = {
                'emergency': (LogSeverity.EMERGENCY, 'EMERGENCY'),
                'alert': (LogSeverity.ALERT, 'ALERT'),
                'critical': (LogSeverity.CRITICAL, 'CRITICAL'),
                'error': (LogSeverity.ERROR, 'ERROR'),
                'warning': (LogSeverity.WARNING, 'WARNING'),
                'warn': (LogSeverity.WARNING, 'WARNING'),
                'notice': (LogSeverity.NOTICE, 'NOTICE'),
                'info': (LogSeverity.INFO, 'INFO'),
                'information': (LogSeverity.INFO, 'INFO'),
                'debug': (LogSeverity.DEBUG, 'DEBUG'),
            }
            return severity_map.get(value_lower, (LogSeverity.UNKNOWN, value.upper()))
        
        return LogSeverity.UNKNOWN, 'UNKNOWN'
    
    def _detect_schema(self, data: Dict) -> List[str]:
        """Detect schema type based on field patterns"""
        tags = []
        data_str = json.dumps(data).lower()
        
        # CloudTrail detection
        if any(f in data for f in ['eventVersion', 'eventSource', 'awsRegion']):
            tags.append('cloudtrail')
        
        # K8s audit detection
        if any(f in data for f in ['apiVersion', 'auditID', 'stage', 'requestURI']):
            tags.append('kubernetes_audit')
        
        # Suricata detection
        if 'event_type' in data and any(k in data for k in ['src_ip', 'dest_ip', 'alert']):
            tags.append('suricata')
        
        # Generic application log
        if 'message' in data or 'msg' in data:
            tags.append('application')
        
        return tags


class WebAccessParser(LogParser):
    """
    Parser for Apache/Nginx access logs
    
    Supports:
    - Combined Log Format
    - Common Log Format
    - Extended formats with additional fields
    """
    
    # Combined Log Format
    # host ident authuser date request status bytes referer user-agent
    COMBINED_PATTERN = re.compile(
        r'^(?P<remote_host>\S+)\s+'
        r'(?P<ident>\S+)\s+'
        r'(?P<auth_user>\S+)\s+'
        r'\[(?P<timestamp>[^\]]+)\]\s+'
        r'"(?P<method>\S+)\s+(?P<path>\S+)\s+(?P<protocol>[^"]*)"\s+'
        r'(?P<status>\d{3})\s+'
        r'(?P<bytes>\S+)\s+'
        r'"(?P<referer>[^"]*)"\s+'
        r'"(?P<user_agent>[^"]*)"'
    )
    
    # Common Log Format (without referer and user-agent)
    COMMON_PATTERN = re.compile(
        r'^(?P<remote_host>\S+)\s+'
        r'(?P<ident>\S+)\s+'
        r'(?P<auth_user>\S+)\s+'
        r'\[(?P<timestamp>[^\]]+)\]\s+'
        r'"(?P<method>\S+)\s+(?P<path>\S+)\s+(?P<protocol>[^"]*)"\s+'
        r'(?P<status>\d{3})\s+'
        r'(?P<bytes>\S+)'
    )
    
    # Virtual host combined format
    VHOST_COMBINED_PATTERN = re.compile(
        r'^(?P<server_name>\S+)\s+'
        r'(?P<remote_host>\S+)\s+'
        r'(?P<ident>\S+)\s+'
        r'(?P<auth_user>\S+)\s+'
        r'\[(?P<timestamp>[^\]]+)\]\s+'
        r'"(?P<method>\S+)\s+(?P<path>\S+)\s+(?P<protocol>[^"]*)"\s+'
        r'(?P<status>\d{3})\s+'
        r'(?P<bytes>\S+)\s+'
        r'"(?P<referer>[^"]*)"\s+'
        r'"(?P<user_agent>[^"]*)"'
    )
    
    def __init__(self):
        super().__init__("web_access")
    
    def can_parse(self, sample: str) -> bool:
        """Check if sample matches web access log format"""
        if not sample:
            return False
        
        # Check for common patterns
        if self.COMBINED_PATTERN.match(sample):
            return True
        if self.COMMON_PATTERN.match(sample):
            return True
        if self.VHOST_COMBINED_PATTERN.match(sample):
            return True
        
        return False
    
    def parse_line(self, line: str) -> Optional[LogEntry]:
        """Parse web access log line into LogEntry"""
        line = line.strip()
        if not line:
            return None
        
        # Try patterns in order of specificity
        for pattern_name, pattern in [
            ('vhost_combined', self.VHOST_COMBINED_PATTERN),
            ('combined', self.COMBINED_PATTERN),
            ('common', self.COMMON_PATTERN)
        ]:
            match = pattern.match(line)
            if match:
                return self._create_entry(match, line, pattern_name)
        
        return None
    
    def _create_entry(self, match: re.Match, raw_line: str, format_name: str) -> LogEntry:
        """Create LogEntry from regex match"""
        data = match.groupdict()
        
        # Parse timestamp
        ts_str = data.get('timestamp', '')
        timestamp = self._parse_timestamp(ts_str, ['%d/%b/%Y:%H:%M:%S %z', '%d/%b/%Y:%H:%M:%S'])
        if not timestamp:
            timestamp = datetime.utcnow()
        
        # Parse status code
        status = int(data.get('status', 0))
        severity = self._status_to_severity(status)
        
        # Parse bytes
        bytes_str = data.get('bytes', '-')
        bytes_sent = 0 if bytes_str == '-' else int(bytes_str)
        
        # Build message
        method = data.get('method', 'UNKNOWN')
        path = data.get('path', '/')
        protocol = data.get('protocol', '')
        message = f"{method} {path} {protocol}".strip()
        
        entry = LogEntry(
            entry_id=self._generate_entry_id(raw_line),
            timestamp=timestamp,
            source_format=f'web_access_{format_name}',
            source_host=data.get('server_name'),
            source_ip=data.get('remote_host'),
            user=data.get('auth_user') if data.get('auth_user') != '-' else None,
            severity=severity,
            severity_label=severity.name,
            message=message,
            status_code=status,
            raw_data=raw_line,
            raw_fields={
                'method': method,
                'path': path,
                'protocol': protocol,
                'status': status,
                'bytes_sent': bytes_sent,
                'referer': data.get('referer', '-'),
                'user_agent': data.get('user_agent', '-'),
                'ident': data.get('ident', '-')
            }
        )
        
        # Add tags for common attack patterns
        entry.tags = self._detect_attack_patterns(data)
        
        return entry
    
    def _status_to_severity(self, status: int) -> LogSeverity:
        """Map HTTP status to severity"""
        if status >= 500:
            return LogSeverity.ERROR
        elif status >= 400:
            if status in [401, 403]:
                return LogSeverity.WARNING
            return LogSeverity.ERROR
        elif status >= 300:
            return LogSeverity.INFO
        else:
            return LogSeverity.INFO
    
    def _detect_attack_patterns(self, data: Dict[str, str]) -> List[str]:
        """Detect potential attack patterns in request"""
        tags = []
        path = data.get('path', '').lower()
        user_agent = data.get('user_agent', '').lower()
        status = int(data.get('status', 0))
        
        # SQL injection patterns
        sql_patterns = ['union select', 'insert into', 'delete from', 'drop table',
                       '1=1', "' or '", '" or "', ';--', 'exec(']
        if any(p in path for p in sql_patterns):
            tags.append('possible_sql_injection')
        
        # Path traversal
        if '..' in path or '../' in path or '..\\' in path:
            tags.append('path_traversal')
        
        # XSS patterns
        xss_patterns = ['<script', 'javascript:', 'onerror=', 'onload=']
        if any(p in path for p in xss_patterns):
            tags.append('possible_xss')
        
        # Scanning patterns
        scan_patterns = ['admin', 'login', 'config', '.env', 'wp-admin', 
                        'phpmyadmin', '.git', '.svn']
        if any(p in path for p in scan_patterns):
            tags.append('scanning_attempt')
        
        # Brute force detection
        if status == 401:
            tags.append('auth_failure')
        
        # Suspicious user agents
        suspicious_ua = ['sqlmap', 'nikto', 'nmap', 'masscan', 'gobuster', 'dirb']
        if any(ua in user_agent for ua in suspicious_ua):
            tags.append('suspicious_scanner')
        
        return tags


class WindowsEventParser(LogParser):
    """
    Parser for Windows Event Log (EVTX) format
    
    Note: This parser expects JSON-exported EVTX data or XML format.
    For native EVTX files, use python-evtx library separately.
    """
    
    # Windows event severity mapping
    WINDOWS_LEVELS = {
        'Critical': LogSeverity.CRITICAL,
        'Error': LogSeverity.ERROR,
        'Warning': LogSeverity.WARNING,
        'Information': LogSeverity.INFO,
        'Verbose': LogSeverity.DEBUG,
        '0': LogSeverity.INFO,      # LogAlways
        '1': LogSeverity.CRITICAL,  # Critical
        '2': LogSeverity.ERROR,     # Error
        '3': LogSeverity.WARNING,   # Warning
        '4': LogSeverity.INFO,      # Information
        '5': LogSeverity.DEBUG,     # Verbose
    }
    
    def __init__(self):
        super().__init__("windows_event")
    
    def can_parse(self, sample: str) -> bool:
        """Check if sample matches Windows Event format (JSON or XML)"""
        if not sample:
            return False
        
        sample = sample.strip()
        
        # Try JSON format
        try:
            data = json.loads(sample)
            if isinstance(data, dict):
                # Check for Windows Event fields
                if any(f in data for f in ['EventID', 'EventId', 'event_id', 
                                          'ProviderName', 'Channel', 'Level']):
                    return True
        except json.JSONDecodeError:
            pass
        
        # Try XML format
        if sample.startswith('<?xml') or sample.startswith('<Event'):
            return True
        
        return False
    
    def parse_line(self, line: str) -> Optional[LogEntry]:
        """Parse Windows Event log line into LogEntry"""
        line = line.strip()
        if not line:
            return None
        
        # Try JSON first
        try:
            data = json.loads(line)
            if isinstance(data, dict):
                return self._parse_json_event(data, line)
        except json.JSONDecodeError:
            pass
        
        # Try XML format
        if line.startswith('<') or line.startswith('<?xml'):
            return self._parse_xml_event(line)
        
        return None
    
    def _parse_json_event(self, data: Dict, raw_line: str) -> LogEntry:
        """Parse JSON-formatted Windows Event"""
        # Extract Event ID
        event_id = (data.get('EventID') or data.get('EventId') or 
                   data.get('event_id') or data.get('Event', {}).get('System', {}).get('EventID', '0'))
        
        # Extract timestamp
        timestamp = None
        for field in ['TimeCreated', 'TimeCreated_SystemTime', 'timestamp', 'TimeCreated']:
            value = self._get_nested_value(data, field)
            if value:
                timestamp = self._parse_timestamp(str(value))
                if timestamp:
                    break
        
        if not timestamp:
            timestamp = datetime.utcnow()
        
        # Extract severity
        level = (data.get('Level') or data.get('level') or 
                self._get_nested_value(data, 'Event.System.Level') or '0')
        severity = self.WINDOWS_LEVELS.get(str(level), LogSeverity.UNKNOWN)
        
        # Extract computer name
        computer = (data.get('Computer') or data.get('computer') or 
                   self._get_nested_value(data, 'Event.System.Computer'))
        
        # Extract provider
        provider = (data.get('ProviderName') or data.get('Source') or 
                   self._get_nested_value(data, 'Event.System.Provider.Name'))
        
        # Extract message
        message = (data.get('Message') or data.get('message') or 
                  data.get('RenderedMessage') or 
                  self._extract_message_from_event_data(data))
        
        # Extract user
        user = self._get_nested_value(data, 'Event.System.Security.UserID')
        
        return LogEntry(
            entry_id=self._generate_entry_id(raw_line),
            timestamp=timestamp,
            source_format='windows_event_json',
            source_host=computer,
            user=user,
            severity=severity,
            severity_label=severity.name,
            facility=provider,
            message=message or f"Windows Event ID: {event_id}",
            message_id=str(event_id),
            raw_data=raw_line,
            raw_fields=data
        )
    
    def _parse_xml_event(self, xml_line: str) -> Optional[LogEntry]:
        """Parse XML-formatted Windows Event"""
        try:
            root = ET.fromstring(xml_line)
            
            # Extract namespace
            ns = {'': root.tag.split('}')[0].strip('{')} if '}' in root.tag else {}
            
            # Get System element
            system = root.find('.//System', ns) or root.find('System', ns)
            if system is None:
                return None
            
            # Extract fields
            event_id = self._get_xml_text(system, 'EventID', ns)
            level = self._get_xml_text(system, 'Level', ns) or '0'
            computer = self._get_xml_text(system, 'Computer', ns)
            provider_elem = system.find('Provider', ns)
            provider = provider_elem.get('Name') if provider_elem is not None else None
            
            # Get timestamp
            time_created = system.find('TimeCreated', ns)
            timestamp = None
            if time_created is not None:
                ts_str = time_created.get('SystemTime')
                if ts_str:
                    timestamp = self._parse_timestamp(ts_str)
            
            if not timestamp:
                timestamp = datetime.utcnow()
            
            # Get message from RenderingInfo or EventData
            message = self._get_xml_text(root, './/RenderingInfo/Message', ns)
            if not message:
                message = self._extract_event_data_message(root, ns)
            
            severity = self.WINDOWS_LEVELS.get(str(level), LogSeverity.UNKNOWN)
            
            # Get user
            security = system.find('Security', ns)
            user = security.get('UserID') if security is not None else None
            
            return LogEntry(
                entry_id=self._generate_entry_id(xml_line),
                timestamp=timestamp,
                source_format='windows_event_xml',
                source_host=computer,
                user=user,
                severity=severity,
                severity_label=severity.name,
                facility=provider,
                message=message or f"Windows Event ID: {event_id}",
                message_id=event_id,
                raw_data=xml_line,
                raw_fields={'xml_parsed': True}
            )
            
        except ET.ParseError as e:
            self.logger.debug(f"XML parse error: {e}")
            return None
    
    def _get_xml_text(self, element: ET.Element, path: str, ns: Dict) -> Optional[str]:
        """Get text content from XML element"""
        elem = element.find(path, ns)
        return elem.text if elem is not None else None
    
    def _extract_event_data_message(self, root: ET.Element, ns: Dict) -> str:
        """Extract message from EventData"""
        event_data = root.find('.//EventData', ns) or root.find('EventData', ns)
        if event_data is None:
            return ""
        
        parts = []
        for data in event_data.findall('Data', ns):
            name = data.get('Name', '')
            value = data.text or ''
            if name:
                parts.append(f"{name}: {value}")
            else:
                parts.append(value)
        
        return ' | '.join(parts)
    
    def _extract_message_from_event_data(self, data: Dict) -> str:
        """Extract message from EventData in JSON"""
        event_data = data.get('EventData') or data.get('event_data') or {}
        if isinstance(event_data, dict):
            return ' | '.join(f"{k}: {v}" for k, v in event_data.items())
        return str(event_data)
    
    def _get_nested_value(self, data: Dict, path: str) -> Any:
        """Get nested value using dot notation"""
        parts = path.split('.')
        current = data
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
        return current


class CloudTrailParser(LogParser):
    """
    Parser for AWS CloudTrail logs
    
    Parses CloudTrail JSON events with AWS-specific field extraction.
    """
    
    # CloudTrail event severity mapping
    EVENT_SEVERITY = {
        'ConsoleLogin': LogSeverity.INFO,
        'CreateAccessKey': LogSeverity.ALERT,
        'DeleteAccessKey': LogSeverity.WARNING,
        'CreateUser': LogSeverity.NOTICE,
        'DeleteUser': LogSeverity.WARNING,
        'AttachUserPolicy': LogSeverity.WARNING,
        'PutBucketPolicy': LogSeverity.WARNING,
        'PutBucketAcl': LogSeverity.WARNING,
        'AuthorizeSecurityGroupIngress': LogSeverity.WARNING,
        'AuthorizeSecurityGroupEgress': LogSeverity.WARNING,
        'ModifyInstanceAttribute': LogSeverity.NOTICE,
        'StopInstances': LogSeverity.WARNING,
        'TerminateInstances': LogSeverity.CRITICAL,
    }
    
    def __init__(self):
        super().__init__("cloudtrail")
    
    def can_parse(self, sample: str) -> bool:
        """Check if sample matches CloudTrail format"""
        if not sample:
            return False
        
        try:
            data = json.loads(sample.strip())
            if isinstance(data, dict):
                # Check for CloudTrail-specific fields
                if all(f in data for f in ['eventVersion', 'eventSource']):
                    return True
                if 'Records' in data and isinstance(data['Records'], list):
                    return True
        except (json.JSONDecodeError, ValueError):
            pass
        
        return False
    
    def parse_line(self, line: str) -> Optional[LogEntry]:
        """Parse CloudTrail event into LogEntry"""
        line = line.strip()
        if not line:
            return None
        
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            return None
        
        # Handle both single events and batch (Records)
        if 'Records' in data:
            # This is a batch file, parse first record only for single line
            if data['Records']:
                data = data['Records'][0]
            else:
                return None
        
        return self._parse_event(data, line)
    
    def parse_file(self, file_path: Union[str, Path]) -> Iterator[LogEntry]:
        """
        Parse CloudTrail file, handling both single events and batch format
        
        CloudTrail often stores logs as JSON arrays in 'Records' field.
        """
        path = Path(file_path)
        
        if not path.exists():
            self.logger.error(f"File not found: {file_path}")
            return
        
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            data = json.loads(content)
            
            # Handle batch format
            if 'Records' in data and isinstance(data['Records'], list):
                for record in data['Records']:
                    try:
                        entry = self._parse_event(record, json.dumps(record))
                        if entry:
                            yield entry
                    except Exception as e:
                        self.logger.debug(f"Failed to parse CloudTrail record: {e}")
                        continue
            else:
                # Single event
                entry = self._parse_event(data, content)
                if entry:
                    yield entry
                    
        except json.JSONDecodeError:
            # Try line-by-line parsing for NDJSON format
            yield from super().parse_file(file_path)
        except Exception as e:
            self.logger.error(f"Error parsing CloudTrail file: {e}")
    
    def _parse_event(self, data: Dict, raw_line: str) -> Optional[LogEntry]:
        """Parse a single CloudTrail event"""
        if not isinstance(data, dict):
            return None
        
        # Extract timestamp
        event_time = data.get('eventTime', '')
        timestamp = self._parse_timestamp(event_time)
        if not timestamp:
            timestamp = datetime.utcnow()
        
        # Extract event details
        event_name = data.get('eventName', 'Unknown')
        event_source = data.get('eventSource', 'unknown')
        aws_region = data.get('awsRegion', 'unknown')
        
        # Extract user identity
        user_identity = data.get('userIdentity', {})
        user_type = user_identity.get('type', 'Unknown')
        user_name = user_identity.get('userName') or user_identity.get('arn', 'Unknown')
        account_id = user_identity.get('accountId', 'Unknown')
        
        # Extract source IP
        source_ip = data.get('sourceIPAddress')
        
        # Determine severity based on event type
        severity = self.EVENT_SEVERITY.get(event_name, LogSeverity.INFO)
        
        # Build message
        error_code = data.get('errorCode')
        error_message = data.get('errorMessage', '')
        
        if error_code:
            message = f"{event_name} FAILED: {error_code} - {error_message}"
            severity = LogSeverity.ERROR
        else:
            message = f"{event_name} by {user_type}/{user_name}"
        
        # Extract resources
        resources = data.get('resources', [])
        resource_info = ', '.join([
            f"{r.get('type', 'Unknown')}: {r.get('ARN', 'Unknown')}"
            for r in resources[:3]  # Limit to first 3
        ])
        
        if resource_info:
            message += f" on {resource_info}"
        
        entry = LogEntry(
            entry_id=self._generate_entry_id(raw_line),
            timestamp=timestamp,
            source_format='cloudtrail',
            source_host=aws_region,
            source_ip=source_ip,
            user=user_name,
            user_id=account_id,
            severity=severity,
            severity_label=severity.name,
            message=message,
            raw_data=raw_line,
            raw_fields=data
        )
        
        # Add tags for suspicious activity
        entry.tags = self._classify_event(data)
        
        return entry
    
    def _classify_event(self, data: Dict) -> List[str]:
        """Classify CloudTrail event for security tags"""
        tags = []
        
        event_name = data.get('eventName', '')
        error_code = data.get('errorCode', '')
        user_identity = data.get('userIdentity', {})
        
        # Authentication events
        if event_name == 'ConsoleLogin':
            response = data.get('responseElements', {})
            if response.get('ConsoleLogin') == 'Failure':
                tags.append('failed_login')
            else:
                tags.append('successful_login')
        
        # IAM changes
        if 'User' in event_name or 'Role' in event_name or 'Policy' in event_name:
            tags.append('iam_change')
        
        # Access key operations
        if 'AccessKey' in event_name:
            tags.append('access_key_change')
        
        # Security group changes
        if 'SecurityGroup' in event_name:
            tags.append('security_group_change')
        
        # Root account usage
        if user_identity.get('type') == 'Root':
            tags.append('root_account_usage')
        
        # Errors
        if error_code:
            tags.append('api_error')
            if 'Unauthorized' in error_code or 'AccessDenied' in error_code:
                tags.append('access_denied')
        
        # MFA-related
        if 'MFA' in event_name or 'mfa' in str(data).lower():
            tags.append('mfa_event')
        
        return tags


class K8sAuditParser(LogParser):
    """
    Parser for Kubernetes audit logs
    
    Parses Kubernetes audit events with k8s-specific field extraction.
    """
    
    # K8s audit severity mapping
    VERB_SEVERITY = {
        'create': LogSeverity.NOTICE,
        'update': LogSeverity.NOTICE,
        'patch': LogSeverity.NOTICE,
        'delete': LogSeverity.WARNING,
        'deletecollection': LogSeverity.WARNING,
        'get': LogSeverity.INFO,
        'list': LogSeverity.INFO,
        'watch': LogSeverity.DEBUG,
        'proxy': LogSeverity.NOTICE,
        '*': LogSeverity.WARNING,
    }
    
    def __init__(self):
        super().__init__("kubernetes_audit")
    
    def can_parse(self, sample: str) -> bool:
        """Check if sample matches K8s audit format"""
        if not sample:
            return False
        
        try:
            data = json.loads(sample.strip())
            if isinstance(data, dict):
                # Check for K8s audit-specific fields
                if all(f in data for f in ['apiVersion', 'auditID', 'stage']):
                    return True
                if 'kind' in data and data.get('kind') == 'Event':
                    if 'requestURI' in data or 'verb' in data:
                        return True
        except (json.JSONDecodeError, ValueError):
            pass
        
        return False
    
    def parse_line(self, line: str) -> Optional[LogEntry]:
        """Parse K8s audit event into LogEntry"""
        line = line.strip()
        if not line:
            return None
        
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            return None
        
        if not isinstance(data, dict):
            return None
        
        return self._parse_event(data, line)
    
    def _parse_event(self, data: Dict, raw_line: str) -> Optional[LogEntry]:
        """Parse a single K8s audit event"""
        # Extract timestamp
        timestamp_str = data.get('requestReceivedTimestamp') or data.get('timestamp')
        timestamp = None
        if timestamp_str:
            timestamp = self._parse_timestamp(timestamp_str)
        if not timestamp:
            timestamp = datetime.utcnow()
        
        # Extract request details
        verb = data.get('verb', 'unknown')
        uri = data.get('requestURI', '/')
        stage = data.get('stage', 'Unknown')
        
        # Extract user information
        user = data.get('user', {})
        username = user.get('username', 'system:anonymous')
        user_groups = user.get('groups', [])
        
        # Extract source
        source_ips = data.get('sourceIPs', [])
        source_ip = source_ips[0] if source_ips else None
        
        # Extract object details
        object_ref = data.get('objectRef', {})
        resource = object_ref.get('resource', 'unknown')
        namespace = object_ref.get('namespace')
        name = object_ref.get('name')
        
        # Extract response status
        response_status = data.get('responseStatus', {})
        code = response_status.get('code', 0)
        status = 'success' if code < 400 else 'failure'
        
        # Determine severity
        severity = self.VERB_SEVERITY.get(verb.lower(), LogSeverity.INFO)
        if code >= 400:
            severity = LogSeverity.WARNING if code == 403 else LogSeverity.ERROR
        
        # Build message
        resource_desc = f"{resource}"
        if namespace:
            resource_desc += f"/ns:{namespace}"
        if name:
            resource_desc += f"/name:{name}"
        
        message = f"{verb.upper()} {uri} - {status} ({code})"
        
        entry = LogEntry(
            entry_id=self._generate_entry_id(raw_line),
            timestamp=timestamp,
            source_format='kubernetes_audit',
            source_host=namespace,
            source_ip=source_ip,
            user=username,
            severity=severity,
            severity_label=severity.name,
            message=message,
            raw_data=raw_line,
            raw_fields=data
        )
        
        # Add security tags
        entry.tags = self._classify_audit_event(data, verb, username)
        
        return entry
    
    def _classify_audit_event(self, data: Dict, verb: str, username: str) -> List[str]:
        """Classify K8s audit event for security tags"""
        tags = []
        
        object_ref = data.get('objectRef', {})
        resource = object_ref.get('resource', '')
        subresource = object_ref.get('subresource', '')
        
        # Privileged operations
        if verb in ['delete', 'deletecollection']:
            tags.append('deletion')
        
        # Sensitive resources
        sensitive_resources = ['secrets', 'configmaps', 'serviceaccounts', 
                              'clusterroles', 'roles', 'rolebindings', 
                              'clusterrolebindings']
        if resource in sensitive_resources:
            tags.append(f'{resource}_access')
        
        # Pod exec
        if subresource == 'exec' or 'exec' in data.get('requestURI', ''):
            tags.append('pod_exec')
        
        # Pod logs
        if subresource == 'log' or 'log' in data.get('requestURI', ''):
            tags.append('pod_logs')
        
        # Impersonation
        user_info = data.get('user', {})
        if 'impersonatedUser' in user_info or 'impersonatedGroup' in user_info:
            tags.append('impersonation')
        
        # Anonymous access
        if username == 'system:anonymous':
            tags.append('anonymous_access')
        
        # Privileged users
        if 'system:serviceaccount:kube-system' in username or username == 'system:admin':
            tags.append('privileged_user')
        
        # Authentication failures
        response = data.get('responseStatus', {})
        if response.get('code') == 401:
            tags.append('auth_failure')
        if response.get('code') == 403:
            tags.append('forbidden')
        
        return tags


class SuricataParser(LogParser):
    """
    Parser for Suricata EVE JSON logs
    
    Parses Suricata IDS/IPS events in EVE JSON format.
    Also supports Zeek/Bro JSON format.
    """
    
    # Suricata severity mapping (1=high, 3=low)
    SURICATA_SEVERITY = {
        1: LogSeverity.CRITICAL,
        2: LogSeverity.WARNING,
        3: LogSeverity.NOTICE,
    }
    
    def __init__(self):
        super().__init__("suricata")
    
    def can_parse(self, sample: str) -> bool:
        """Check if sample matches Suricata/Zeek format"""
        if not sample:
            return False
        
        try:
            data = json.loads(sample.strip())
            if isinstance(data, dict):
                # Suricata EVE format
                if 'event_type' in data:
                    if any(f in data for f in ['src_ip', 'dest_ip', 'alert', 'flow']):
                        return True
                # Zeek format (flat keys with dots or nested id object)
                if 'proto' in data:
                    if 'id' in data or any(k.startswith('id.') for k in data.keys()):
                        return True
        except (json.JSONDecodeError, ValueError):
            pass
        
        return False
    
    def parse_line(self, line: str) -> Optional[LogEntry]:
        """Parse Suricata/Zeek event into LogEntry"""
        line = line.strip()
        if not line:
            return None
        
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            return None
        
        if not isinstance(data, dict):
            return None
        
        event_type = data.get('event_type', 'unknown')
        
        # Route to appropriate parser based on event type
        if event_type == 'alert':
            return self._parse_alert(data, line)
        elif event_type in ['http', 'fileinfo', 'smtp', 'ssh', 'tls']:
            return self._parse_protocol(data, line, event_type)
        elif event_type in ['flow', 'netflow']:
            return self._parse_flow(data, line)
        elif event_type == 'stats':
            return self._parse_stats(data, line)
        elif 'proto' in data and (('id' in data) or any(k.startswith('id.') for k in data.keys())):
            # Zeek format (nested id object or flat keys like id.orig_h)
            return self._parse_zeek(data, line)
        else:
            return self._parse_generic(data, line)
    
    def _parse_alert(self, data: Dict, raw_line: str) -> LogEntry:
        """Parse Suricata alert event"""
        alert = data.get('alert', {})
        
        # Extract severity
        severity_num = alert.get('severity', 3)
        severity = self.SURICATA_SEVERITY.get(severity_num, LogSeverity.NOTICE)
        
        # Build message
        action = alert.get('action', 'allowed')
        signature = alert.get('signature', 'Unknown')
        category = alert.get('category', 'Unknown')
        
        message = f"[{action.upper()}] {signature}"
        if category != 'Unknown':
            message += f" (Category: {category})"
        
        # Extract flow info
        src_ip = data.get('src_ip')
        dest_ip = data.get('dest_ip')
        src_port = data.get('src_port')
        dest_port = data.get('dest_port')
        protocol = data.get('proto', 'unknown')
        
        # Parse timestamp
        timestamp_str = data.get('timestamp', '')
        timestamp = self._parse_timestamp(timestamp_str)
        if not timestamp:
            timestamp = datetime.utcnow()
        
        entry = LogEntry(
            entry_id=self._generate_entry_id(raw_line),
            timestamp=timestamp,
            source_format='suricata_alert',
            source_ip=src_ip,
            dest_ip=dest_ip,
            dest_port=dest_port,
            protocol=protocol,
            severity=severity,
            severity_label=severity.name,
            action=action,
            message=message,
            raw_data=raw_line,
            raw_fields=data
        )
        
        # Add tags
        entry.tags = self._classify_alert(alert, category)
        
        return entry
    
    def _parse_protocol(self, data: Dict, raw_line: str, protocol: str) -> LogEntry:
        """Parse protocol-specific event"""
        timestamp_str = data.get('timestamp', '')
        timestamp = self._parse_timestamp(timestamp_str) or datetime.utcnow()
        
        src_ip = data.get('src_ip')
        dest_ip = data.get('dest_ip')
        
        # Extract protocol-specific info
        proto_data = data.get(protocol, {})
        
        if protocol == 'http':
            hostname = proto_data.get('hostname', '')
            url = proto_data.get('url', '')
            status = proto_data.get('status')
            method = proto_data.get('http_method', '')
            message = f"HTTP {method} {hostname}{url}"
        elif protocol == 'tls':
            subject = proto_data.get('subject', '')
            message = f"TLS handshake: {subject}"
        elif protocol == 'ssh':
            client = proto_data.get('client', {}).get('software_version', '')
            server = proto_data.get('server', {}).get('software_version', '')
            message = f"SSH: {client} -> {server}"
        else:
            message = f"{protocol.upper()} traffic"
        
        return LogEntry(
            entry_id=self._generate_entry_id(raw_line),
            timestamp=timestamp,
            source_format=f'suricata_{protocol}',
            source_ip=src_ip,
            dest_ip=dest_ip,
            protocol=data.get('proto'),
            severity=LogSeverity.INFO,
            severity_label='INFO',
            message=message,
            raw_data=raw_line,
            raw_fields=data
        )
    
    def _parse_flow(self, data: Dict, raw_line: str) -> LogEntry:
        """Parse flow event"""
        timestamp_str = data.get('timestamp', '')
        timestamp = self._parse_timestamp(timestamp_str) or datetime.utcnow()
        
        flow = data.get('flow', {})
        bytes_toserver = flow.get('bytes_toserver', 0)
        bytes_toclient = flow.get('bytes_toclient', 0)
        
        message = f"Flow: {bytes_toserver}B to server, {bytes_toclient}B to client"
        
        return LogEntry(
            entry_id=self._generate_entry_id(raw_line),
            timestamp=timestamp,
            source_format='suricata_flow',
            source_ip=data.get('src_ip'),
            dest_ip=data.get('dest_ip'),
            protocol=data.get('proto'),
            severity=LogSeverity.DEBUG,
            severity_label='DEBUG',
            message=message,
            raw_data=raw_line,
            raw_fields=data
        )
    
    def _parse_stats(self, data: Dict, raw_line: str) -> LogEntry:
        """Parse stats event"""
        timestamp_str = data.get('timestamp', '')
        timestamp = self._parse_timestamp(timestamp_str) or datetime.utcnow()
        
        stats = data.get('stats', {})
        
        return LogEntry(
            entry_id=self._generate_entry_id(raw_line),
            timestamp=timestamp,
            source_format='suricata_stats',
            severity=LogSeverity.DEBUG,
            severity_label='DEBUG',
            message='Suricata statistics',
            raw_data=raw_line,
            raw_fields=data
        )
    
    def _parse_zeek(self, data: Dict, raw_line: str) -> LogEntry:
        """Parse Zeek/Bro format"""
        # Zeek uses 'ts' for timestamp (Unix epoch)
        ts = data.get('ts', 0)
        if isinstance(ts, (int, float)):
            timestamp = datetime.utcfromtimestamp(ts)
        else:
            timestamp = datetime.utcnow()
        
        # Extract connection info - Zeek can have nested 'id' object or flat keys
        conn_id = data.get('id', {})
        # Handle both nested id object and flat keys (id.orig_h, id.resp_h, etc.)
        if conn_id:
            # Nested format: id: { orig_h: ..., resp_h: ... }
            src_ip = conn_id.get('orig_h')
            dest_ip = conn_id.get('resp_h')
            src_port = conn_id.get('orig_p')
            dest_port = conn_id.get('resp_p')
        else:
            # Flat format: id.orig_h, id.resp_h, etc.
            src_ip = data.get('id.orig_h')
            dest_ip = data.get('id.resp_h')
            src_port = data.get('id.orig_p')
            dest_port = data.get('id.resp_p')
        
        protocol = data.get('proto', 'unknown')
        
        # Determine event type from fields present
        event_type = 'conn'
        if 'query' in data:
            event_type = 'dns'
        elif 'method' in data:
            event_type = 'http'
        elif 'certificate' in data or 'subject' in data:
            event_type = 'ssl'
        
        message = f"Zeek {event_type.upper()}: {src_ip} -> {dest_ip}:{dest_port}"
        
        return LogEntry(
            entry_id=self._generate_entry_id(raw_line),
            timestamp=timestamp,
            source_format='zeek',
            source_ip=src_ip,
            dest_ip=dest_ip,
            dest_port=dest_port,
            protocol=protocol,
            severity=LogSeverity.INFO,
            severity_label='INFO',
            message=message,
            raw_data=raw_line,
            raw_fields=data
        )
    
    def _parse_generic(self, data: Dict, raw_line: str) -> LogEntry:
        """Parse generic Suricata event"""
        timestamp_str = data.get('timestamp', '')
        timestamp = self._parse_timestamp(timestamp_str) or datetime.utcnow()
        
        event_type = data.get('event_type', 'unknown')
        
        return LogEntry(
            entry_id=self._generate_entry_id(raw_line),
            timestamp=timestamp,
            source_format='suricata',
            source_ip=data.get('src_ip'),
            dest_ip=data.get('dest_ip'),
            protocol=data.get('proto'),
            severity=LogSeverity.INFO,
            severity_label='INFO',
            message=f"Suricata {event_type} event",
            raw_data=raw_line,
            raw_fields=data
        )
    
    def _classify_alert(self, alert: Dict, category: str) -> List[str]:
        """Classify Suricata alert for security tags"""
        tags = ['ids_alert']
        
        signature = alert.get('signature', '').lower()
        
        # Categorize by signature content
        if any(w in signature for w in ['malware', 'trojan', 'virus', 'backdoor']):
            tags.append('malware')
        
        if any(w in signature for w in ['scan', 'reconnaissance', 'probe']):
            tags.append('reconnaissance')
        
        if any(w in signature for w in ['sql injection', 'sql-injection', 'sqli']):
            tags.append('sql_injection')
        
        if any(w in signature for w in ['xss', 'cross-site scripting']):
            tags.append('xss')
        
        if any(w in signature for w in ['brute force', 'brute-force']):
            tags.append('brute_force')
        
        if any(w in signature for w in ['denial of service', 'dos', 'ddos']):
            tags.append('dos')
        
        if any(w in signature for w in ['exploit', 'cve-', 'vulnerability']):
            tags.append('exploit')
        
        if any(w in signature for w in ['c2', 'command and control', 'callback']):
            tags.append('c2_communication')
        
        if category and 'attempted' in category.lower():
            tags.append('attempted_attack')
        
        return tags


class CSVParser(LogParser):
    """
    Configurable CSV/TSV parser
    
    Supports custom delimiters, header detection, and field mapping.
    """
    
    def __init__(self, 
                 delimiter: str = ',',
                 has_header: bool = True,
                 field_mapping: Optional[Dict[str, str]] = None,
                 timestamp_column: Optional[str] = None,
                 timestamp_format: Optional[str] = None,
                 message_columns: Optional[List[str]] = None):
        """
        Initialize CSV parser
        
        Args:
            delimiter: Field delimiter (default: ',')
            has_header: Whether file has header row
            field_mapping: Map CSV columns to LogEntry fields
            timestamp_column: Column containing timestamp
            timestamp_format: Format string for timestamp parsing
            message_columns: Columns to combine for message
        """
        super().__init__("csv")
        self.delimiter = delimiter
        self.has_header = has_header
        self.field_mapping = field_mapping or {}
        self.timestamp_column = timestamp_column
        self.timestamp_format = timestamp_format
        self.message_columns = message_columns or []
        self._headers: Optional[List[str]] = None
        self._reader: Optional[csv.DictReader] = None
    
    def can_parse(self, sample: str) -> bool:
        """Check if sample appears to be CSV/TSV"""
        if not sample:
            return False
        
        try:
            # Try to parse as CSV
            reader = csv.reader([sample], delimiter=self.delimiter)
            row = next(reader)
            # If we get multiple columns, it's likely CSV
            return len(row) > 1
        except (csv.Error, StopIteration):
            return False
    
    def parse_line(self, line: str) -> Optional[LogEntry]:
        """Parse CSV line into LogEntry"""
        line = line.strip()
        if not line:
            return None
        
        try:
            reader = csv.DictReader([line], 
                                   fieldnames=self._headers,
                                   delimiter=self.delimiter)
            row = next(reader)
            
            return self._create_entry(row, line)
            
        except (csv.Error, StopIteration) as e:
            self.logger.debug(f"CSV parse error: {e}")
            return None
    
    def parse_file(self, file_path: Union[str, Path]) -> Iterator[LogEntry]:
        """Parse CSV file, handling headers"""
        path = Path(file_path)
        
        if not path.exists():
            self.logger.error(f"File not found: {file_path}")
            return
        
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore', newline='') as f:
                # Read first line to detect or use headers
                first_line = f.readline()
                
                if self.has_header:
                    # Parse headers from first line
                    header_reader = csv.reader([first_line], 
                                              delimiter=self.delimiter)
                    self._headers = next(header_reader)
                    # Reset to beginning
                    f.seek(0)
                    reader = csv.DictReader(f, delimiter=self.delimiter)
                else:
                    # No header, use position-based or provided fieldnames
                    f.seek(0)
                    if self.field_mapping:
                        # Use provided field names
                        fieldnames = [self.field_mapping.get(str(i), f'col_{i}')
                                    for i in range(len(first_line.split(self.delimiter)))]
                        reader = csv.DictReader(f, 
                                              fieldnames=fieldnames,
                                              delimiter=self.delimiter)
                    else:
                        reader = csv.DictReader(f, 
                                              delimiter=self.delimiter)
                
                for row in reader:
                    try:
                        entry = self._create_entry(row, str(row))
                        if entry:
                            yield entry
                    except Exception as e:
                        self.logger.debug(f"Failed to parse CSV row: {e}")
                        continue
                        
        except Exception as e:
            self.logger.error(f"Error reading CSV file: {e}")
    
    def _create_entry(self, row: Dict[str, str], raw_line: str) -> LogEntry:
        """Create LogEntry from CSV row"""
        # Parse timestamp
        timestamp = datetime.utcnow()
        if self.timestamp_column and self.timestamp_column in row:
            ts_value = row[self.timestamp_column]
            parsed_ts = self._parse_timestamp(ts_value, 
                [self.timestamp_format] if self.timestamp_format else None)
            if parsed_ts:
                timestamp = parsed_ts
        
        # Build message
        message_parts = []
        for col in self.message_columns:
            if col in row and row[col]:
                message_parts.append(f"{col}={row[col]}")
        
        if message_parts:
            message = ' | '.join(message_parts)
        else:
            # Use all non-empty fields
            message = ' | '.join(f"{k}={v}" for k, v in row.items() 
                               if v and k != self.timestamp_column)
        
        # Map fields using field_mapping
        entry_data = {
            'entry_id': self._generate_entry_id(raw_line),
            'timestamp': timestamp,
            'source_format': 'csv',
            'message': message[:1000],  # Limit message length
            'raw_data': raw_line,
            'raw_fields': dict(row)
        }
        
        # Apply field mappings
        for csv_col, entry_field in self.field_mapping.items():
            if csv_col in row:
                value = row[csv_col]
                if entry_field == 'source_host':
                    entry_data['source_host'] = value
                elif entry_field == 'source_ip':
                    entry_data['source_ip'] = value
                elif entry_field == 'user':
                    entry_data['user'] = value
                elif entry_field == 'severity':
                    entry_data['severity'] = self._parse_severity(value)
                    entry_data['severity_label'] = value.upper()
        
        return LogEntry(**entry_data)
    
    def _parse_severity(self, value: str) -> LogSeverity:
        """Parse severity string"""
        value_lower = value.lower()
        severity_map = {
            'emergency': LogSeverity.EMERGENCY,
            'alert': LogSeverity.ALERT,
            'critical': LogSeverity.CRITICAL,
            'error': LogSeverity.ERROR,
            'warning': LogSeverity.WARNING,
            'warn': LogSeverity.WARNING,
            'notice': LogSeverity.NOTICE,
            'info': LogSeverity.INFO,
            'debug': LogSeverity.DEBUG,
        }
        return severity_map.get(value_lower, LogSeverity.UNKNOWN)


class ParserRegistry:
    """
    Factory and registry for log parsers
    
    Provides:
    - Parser registration
    - Auto-detection of log formats
    - Parser selection by format name
    """
    
    def __init__(self):
        self._parsers: Dict[str, LogParser] = {}
        self._logger = logging.getLogger('blueteam.logs.registry')
        self._register_defaults()
    
    def _register_defaults(self):
        """Register default parsers"""
        self.register('syslog', SyslogParser())
        self.register('json', JSONParser())
        self.register('apache', WebAccessParser())
        self.register('nginx', WebAccessParser())
        self.register('web_access', WebAccessParser())
        self.register('windows', WindowsEventParser())
        self.register('cloudtrail', CloudTrailParser())
        self.register('kubernetes', K8sAuditParser())
        self.register('k8s', K8sAuditParser())
        self.register('suricata', SuricataParser())
        self.register('zeek', SuricataParser())
        self.register('csv', CSVParser())
        self.register('tsv', CSVParser(delimiter='\t'))
    
    def register(self, name: str, parser: LogParser):
        """Register a parser"""
        self._parsers[name.lower()] = parser
        self._logger.debug(f"Registered parser: {name}")
    
    def get(self, name: str) -> Optional[LogParser]:
        """Get parser by name"""
        return self._parsers.get(name.lower())
    
    def detect_format(self, sample: str) -> Optional[str]:
        """
        Auto-detect log format from sample
        
        Args:
            sample: Sample log line
            
        Returns:
            Name of detected parser, or None if no match
        """
        if not sample:
            return None
        
        # Try each parser in order of specificity
        detection_order = [
            'syslog',       # Very specific format
            'cloudtrail',   # AWS-specific fields
            'kubernetes',   # K8s-specific fields
            'suricata',     # IDS-specific fields
            'windows',      # Windows event format
            'apache',       # Web access format
            'csv',          # Generic CSV
            'json',         # Generic JSON (fallback)
        ]
        
        for name in detection_order:
            parser = self._parsers.get(name)
            if parser and parser.can_parse(sample):
                self._logger.debug(f"Detected format: {name}")
                return name
        
        return None
    
    def get_parser(self, sample: str, preferred_format: Optional[str] = None) -> Optional[LogParser]:
        """
        Get appropriate parser for sample
        
        Args:
            sample: Sample log line
            preferred_format: Preferred format name (optional)
            
        Returns:
            Appropriate parser, or None if no match
        """
        if preferred_format:
            parser = self.get(preferred_format)
            if parser and parser.can_parse(sample):
                return parser
        
        detected = self.detect_format(sample)
        if detected:
            return self.get(detected)
        
        return None
    
    def parse(self, line: str, format_hint: Optional[str] = None) -> Optional[LogEntry]:
        """
        Parse a log line using appropriate parser
        
        Args:
            line: Log line to parse
            format_hint: Optional format hint
            
        Returns:
            LogEntry if successful, None otherwise
        """
        parser = self.get_parser(line, format_hint)
        if parser:
            return parser.parse_line(line)
        return None
    
    def list_parsers(self) -> List[str]:
        """List available parser names"""
        return list(self._parsers.keys())
    
    def create_csv_parser(self, 
                         delimiter: str = ',',
                         has_header: bool = True,
                         field_mapping: Optional[Dict[str, str]] = None,
                         timestamp_column: Optional[str] = None,
                         timestamp_format: Optional[str] = None,
                         message_columns: Optional[List[str]] = None) -> CSVParser:
        """
        Create a configured CSV parser
        
        Args:
            delimiter: Field delimiter
            has_header: Whether CSV has header row
            field_mapping: Map columns to LogEntry fields
            timestamp_column: Column with timestamp
            timestamp_format: Timestamp format string
            message_columns: Columns for message
            
        Returns:
            Configured CSVParser instance
        """
        return CSVParser(
            delimiter=delimiter,
            has_header=has_header,
            field_mapping=field_mapping,
            timestamp_column=timestamp_column,
            timestamp_format=timestamp_format,
            message_columns=message_columns
        )


# Global registry instance
_parser_registry: Optional[ParserRegistry] = None


def get_parser_registry() -> ParserRegistry:
    """Get global parser registry instance"""
    global _parser_registry
    if _parser_registry is None:
        _parser_registry = ParserRegistry()
    return _parser_registry


def parse_log_line(line: str, format_hint: Optional[str] = None) -> Optional[LogEntry]:
    """
    Convenience function to parse a log line
    
    Args:
        line: Log line to parse
        format_hint: Optional format hint
        
    Returns:
        LogEntry if successful, None otherwise
    """
    registry = get_parser_registry()
    return registry.parse(line, format_hint)


def detect_log_format(sample: str) -> Optional[str]:
    """
    Convenience function to detect log format
    
    Args:
        sample: Sample log line
        
    Returns:
        Detected format name, or None
    """
    registry = get_parser_registry()
    return registry.detect_format(sample)


# Export all public classes
__all__ = [
    'LogEntry',
    'LogSeverity',
    'LogParser',
    'SyslogParser',
    'JSONParser',
    'WebAccessParser',
    'WindowsEventParser',
    'CloudTrailParser',
    'K8sAuditParser',
    'SuricataParser',
    'CSVParser',
    'ParserRegistry',
    'get_parser_registry',
    'parse_log_line',
    'detect_log_format',
]
