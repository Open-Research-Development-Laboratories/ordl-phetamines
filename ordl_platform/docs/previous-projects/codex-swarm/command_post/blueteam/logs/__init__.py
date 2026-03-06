#!/usr/bin/env python3
"""
================================================================================
ORDL COMMAND POST v6.0.0 - BLUE TEAM LOGS MODULE
================================================================================
Classification: TOP SECRET//SCI//NOFORN
Compartment: ORDL-CYBER-OPS

LOG INGESTION AND PROCESSING MODULE
================================================================================
This module provides comprehensive log ingestion capabilities:

- LogIngestionEngine: Main orchestrator for multi-source log collection
- IngestionPipeline: Async processing with queues and worker pools
- LogSource: Configuration dataclass for log sources
- Support for: Files, Syslog, APIs, AWS CloudTrail, Azure, TCP/UDP sockets

Example Usage:
    from blueteam.logs import LogIngestionEngine, LogSource, LogSourceType
    
    # Create engine
    engine = LogIngestionEngine()
    
    # Add file source
    source = LogSource(
        source_id='auth-logs',
        source_type=LogSourceType.FILE,
        config={'path': '/var/log/auth.log'}
    )
    await engine.add_source(source)
    
    # Start ingestion
    await engine.start_ingestion()
    
    # Get metrics
    metrics = await engine.get_metrics()

Author: ORDL Cyber Operations Division
Version: 6.0.0
================================================================================
"""

# Import only from ingestion module (parser.py has compatibility issues)
from .ingestion import (
    # Exceptions
    IngestionError,
    SourceConfigurationError,
    SourceConnectionError,
    ParseError,
    DetectionEngineError,
    QueueFullError,
    # Enums
    LogSourceType,
    SourceStatus,
    IngestionMode,
    # Dataclasses
    LogSource,
    RawLogEntry,
    ParsedEvent,
    IngestionMetrics,
    SourceMetrics,
    # Classes
    IngestionPipeline,
    LogIngestionEngine,
    UDPSyslogProtocol,
    # Functions
    parse_timestamp,
    create_file_source,
    create_syslog_source,
    create_cloudtrail_source,
)

# Version
__version__ = '6.0.0'

__all__ = [
    # Exceptions
    'IngestionError',
    'SourceConfigurationError',
    'SourceConnectionError',
    'ParseError',
    'DetectionEngineError',
    'QueueFullError',
    # Enums
    'LogSourceType',
    'SourceStatus',
    'IngestionMode',
    # Dataclasses
    'LogSource',
    'RawLogEntry',
    'ParsedEvent',
    'IngestionMetrics',
    'SourceMetrics',
    # Classes
    'IngestionPipeline',
    'LogIngestionEngine',
    'UDPSyslogProtocol',
    # Functions
    'parse_timestamp',
    'create_file_source',
    'create_syslog_source',
    'create_cloudtrail_source',
]
