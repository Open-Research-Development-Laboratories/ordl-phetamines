#!/usr/bin/env python3
"""
================================================================================
ORDL COMMAND POST v6.0.0 - BLUE TEAM LOG INGESTION PIPELINE
================================================================================
Classification: TOP SECRET//SCI//NOFORN
Classification Level: TS/SCI/NOFORN
Compartment: ORDL-CYBER-OPS

MILITARY-GRADE LOG INGESTION & PROCESSING PIPELINE
================================================================================
Enterprise-grade log ingestion system with:
- Multi-source log collection (files, syslog, APIs, cloud)
- Real-time tail support for live log monitoring
- Batch processing for historical log analysis
- Async processing with configurable worker pools
- Automatic retry logic with exponential backoff
- Dead letter queue for failed events
- Comprehensive metrics and health monitoring
- Integration with DetectionEngine for real-time analysis

Architecture:
- LogIngestionEngine: Main orchestrator for all log sources
- IngestionPipeline: Async processing core with queues
- LogSource: Configuration dataclass for each source
- Source readers: Async generators for different source types

Author: ORDL Cyber Operations Division
Version: 6.0.0
================================================================================
"""

import os
import sys
import re
import json
import time
import uuid
import gzip
import asyncio
import logging
import hashlib
import threading
from enum import Enum, auto
from dataclasses import dataclass, field, asdict
from typing import (
    Dict, List, Optional, Any, Callable, Tuple, Set, 
    AsyncIterator, Union, Coroutine, Pattern
)
from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path
import queue as sync_queue

# Configure module logging
logger = logging.getLogger('blueteam.logs.ingestion')

# ==============================================================================
# EXCEPTION HIERARCHY
# ==============================================================================

class IngestionError(Exception):
    """
    Base exception for all ingestion-related errors.
    
    Pre: Error condition detected during ingestion
    Post: Exception raised with descriptive message
    """
    pass


class SourceConfigurationError(IngestionError):
    """
    Invalid log source configuration.
    
    Pre: Source configuration validation failed
    Post: Source not added, error logged
    """
    pass


class SourceConnectionError(IngestionError):
    """
    Failed to establish connection to log source.
    
    Pre: Connection attempt to source failed
    Post: Retry logic invoked or source disabled
    """
    pass


class ParseError(IngestionError):
    """
    Failed to parse log line into structured event.
    
    Pre: Log line received but parsing failed
    Post: Line sent to dead letter queue or dropped
    """
    pass


class DetectionEngineError(IngestionError):
    """
    Error submitting event to detection engine.
    
    Pre: Event parsing successful but submission failed
    Post: Event queued for retry or dropped
    """
    pass


class QueueFullError(IngestionError):
    """
    Processing queue is at capacity.
    
    Pre: Queue size exceeded maximum capacity
    Post: New events dropped or backpressure applied
    """
    pass


# ==============================================================================
# ENUMERATIONS
# ==============================================================================

class LogSourceType(Enum):
    """Supported log source types for ingestion."""
    FILE = "file"                    # Local or mounted file paths
    SYSLOG = "syslog"                # Syslog/RSyslog UDP/TCP streams
    API = "api"                      # REST API endpoints
    CLOUD_AWS = "cloud_aws"          # AWS CloudTrail, S3 logs
    CLOUD_AZURE = "cloud_azure"      # Azure Activity Logs, Storage
    KAFKA = "kafka"                  # Kafka message streams
    TCP_SOCKET = "tcp_socket"        # Raw TCP socket streams
    UDP_SOCKET = "udp_socket"        # Raw UDP socket streams


class SourceStatus(Enum):
    """Operational status of a log source."""
    PENDING = "pending"              # Configured but not started
    RUNNING = "running"              # Actively ingesting logs
    PAUSED = "paused"                # Temporarily paused
    ERROR = "error"                  # Error state, retry scheduled
    DISABLED = "disabled"            # Manually disabled
    STOPPED = "stopped"              # Gracefully stopped


class IngestionMode(Enum):
    """Ingestion mode for file-based sources."""
    REALTIME = "realtime"            # Tail mode - follow new entries
    BATCH = "batch"                  # One-time historical processing
    HYBRID = "hybrid"                # Process existing then tail


# ==============================================================================
# DATACLASSES
# ==============================================================================

@dataclass
class LogSource:
    """
    Configuration for a log ingestion source.
    
    Pre: source_id is unique within ingestion engine
    Pre: source_type is valid LogSourceType
    Pre: config contains required fields for source_type
    Post: Validated source configuration ready for ingestion
    
    Attributes:
        source_id: Unique identifier for this source
        source_type: Type of log source
        config: Source-specific configuration dictionary
        enabled: Whether source is enabled for ingestion
        priority: Processing priority (higher = processed first)
        mode: Ingestion mode (realtime/batch/hybrid)
        parser_config: Optional custom parser configuration
        filters: Optional list of regex filters to apply
        tags: Optional tags for categorization
        metadata: Optional additional metadata
    """
    source_id: str
    source_type: LogSourceType
    config: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    priority: int = 0
    mode: IngestionMode = IngestionMode.REALTIME
    parser_config: Optional[Dict[str, Any]] = None
    filters: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate source configuration."""
        if not self.source_id:
            raise SourceConfigurationError("source_id cannot be empty")
        
        if not isinstance(self.source_type, LogSourceType):
            raise SourceConfigurationError(
                f"Invalid source_type: {self.source_type}"
            )
        
        self._validate_config()
        
        # Compile filter patterns
        self._compiled_filters: List[Pattern] = []
        for pattern in self.filters:
            try:
                self._compiled_filters.append(re.compile(pattern))
            except re.error as e:
                raise SourceConfigurationError(
                    f"Invalid filter regex '{pattern}': {e}"
                )
    
    def _validate_config(self) -> None:
        """
        Validate source-specific configuration.
        
        Pre: self.config is a dictionary
        Post: Raises SourceConfigurationError if validation fails
        """
        required_fields = {
            LogSourceType.FILE: ['path'],
            LogSourceType.SYSLOG: ['address', 'port'],
            LogSourceType.API: ['url'],
            LogSourceType.CLOUD_AWS: ['bucket', 'region'],
            LogSourceType.CLOUD_AZURE: ['storage_account', 'container'],
            LogSourceType.KAFKA: ['bootstrap_servers', 'topic'],
            LogSourceType.TCP_SOCKET: ['host', 'port'],
            LogSourceType.UDP_SOCKET: ['host', 'port'],
        }
        
        required = required_fields.get(self.source_type, [])
        missing = [f for f in required if f not in self.config]
        
        if missing:
            raise SourceConfigurationError(
                f"Missing required config fields for {self.source_type.value}: {missing}"
            )
        
        # Validate file paths for security (prevent directory traversal)
        if self.source_type == LogSourceType.FILE:
            path = Path(self.config['path']).resolve()
            self.config['path'] = str(path)
    
    def matches_filters(self, line: str) -> bool:
        """
        Check if log line matches all configured filters.
        
        Pre: line is a string
        Post: Returns True if line passes all filters or no filters configured
        """
        if not self._compiled_filters:
            return True
        return all(pattern.search(line) for pattern in self._compiled_filters)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'source_id': self.source_id,
            'source_type': self.source_type.value,
            'config': self.config,
            'enabled': self.enabled,
            'priority': self.priority,
            'mode': self.mode.value,
            'parser_config': self.parser_config,
            'filters': self.filters,
            'tags': self.tags,
            'metadata': self.metadata
        }


@dataclass
class RawLogEntry:
    """
    Raw log entry before parsing.
    
    Pre: source_id and raw_line are provided
    Post: Entry ready for parsing and normalization
    """
    entry_id: str
    source_id: str
    raw_line: str
    timestamp: datetime
    received_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedEvent:
    """
    Parsed and normalized security event.
    
    Pre: Raw log entry successfully parsed
    Post: Normalized event ready for detection engine
    """
    event_id: str
    source_id: str
    timestamp: datetime
    event_type: str
    source_host: str
    severity: str
    raw_data: Dict[str, Any]
    normalized_data: Dict[str, Any]
    parsed_fields: Dict[str, Any]
    tags: List[str] = field(default_factory=list)
    ioc_matches: List[Dict] = field(default_factory=list)


@dataclass
class IngestionMetrics:
    """
    Metrics for ingestion pipeline monitoring.
    
    All counters are thread-safe using atomic operations.
    """
    # Counters (using threading.RLock for thread safety - allows re-entrancy)
    _lock: threading.RLock = field(default_factory=threading.RLock, repr=False)
    
    lines_received: int = 0
    lines_parsed: int = 0
    lines_filtered: int = 0
    lines_failed: int = 0
    events_submitted: int = 0
    events_dropped: int = 0
    events_in_dead_letter: int = 0
    bytes_ingested: int = 0
    retry_attempts: int = 0
    source_errors: int = 0
    
    # Timing (milliseconds)
    total_processing_time_ms: int = 0
    max_processing_time_ms: int = 0
    
    # Status tracking
    sources_active: int = 0
    sources_error: int = 0
    queue_depth: int = 0
    dead_letter_queue_depth: int = 0
    
    def increment(self, metric: str, value: int = 1) -> None:
        """Thread-safe increment of a metric."""
        with self._lock:
            current = getattr(self, metric, 0)
            setattr(self, metric, current + value)
    
    def update_processing_time(self, duration_ms: int) -> None:
        """Update processing time statistics."""
        with self._lock:
            self.total_processing_time_ms += duration_ms
            self.max_processing_time_ms = max(self.max_processing_time_ms, duration_ms)
    
    def get_average_latency_ms(self) -> float:
        """Calculate average processing latency."""
        with self._lock:
            if self.lines_parsed == 0:
                return 0.0
            return self.total_processing_time_ms / self.lines_parsed
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        with self._lock:
            return {
                'lines_received': self.lines_received,
                'lines_parsed': self.lines_parsed,
                'lines_filtered': self.lines_filtered,
                'lines_failed': self.lines_failed,
                'events_submitted': self.events_submitted,
                'events_dropped': self.events_dropped,
                'events_in_dead_letter': self.events_in_dead_letter,
                'bytes_ingested': self.bytes_ingested,
                'retry_attempts': self.retry_attempts,
                'source_errors': self.source_errors,
                'average_latency_ms': self.get_average_latency_ms(),
                'max_latency_ms': self.max_processing_time_ms,
                'sources_active': self.sources_active,
                'sources_error': self.sources_error,
                'queue_depth': self.queue_depth,
                'dead_letter_queue_depth': self.dead_letter_queue_depth,
                'timestamp': datetime.utcnow().isoformat()
            }


@dataclass
class SourceMetrics:
    """Per-source metrics tracking."""
    source_id: str
    status: SourceStatus = SourceStatus.PENDING
    lines_received: int = 0
    lines_parsed: int = 0
    lines_failed: int = 0
    last_error: Optional[str] = None
    last_error_time: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    started_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'source_id': self.source_id,
            'status': self.status.value,
            'lines_received': self.lines_received,
            'lines_parsed': self.lines_parsed,
            'lines_failed': self.lines_failed,
            'last_error': self.last_error,
            'last_error_time': self.last_error_time.isoformat() if self.last_error_time else None,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None,
            'started_at': self.started_at.isoformat() if self.started_at else None
        }


# ==============================================================================
# INGESTION PIPELINE
# ==============================================================================

class IngestionPipeline:
    """
    Async processing pipeline for log ingestion.
    
    Manages worker pool, queues, and event processing lifecycle.
    Bridges async ingestion with sync DetectionEngine.
    
    Pre: DetectionEngine instance provided
    Post: Pipeline ready to process log events
    """
    
    def __init__(
        self,
        detection_engine: Any,  # DetectionEngine from ..detection.engine
        max_queue_size: int = 10000,
        num_workers: int = 4,
        max_retries: int = 5,
        retry_delay_base: float = 1.0,
        batch_size: int = 100
    ):
        self.detection_engine = detection_engine
        self.max_queue_size = max_queue_size
        self.num_workers = num_workers
        self.max_retries = max_retries
        self.retry_delay_base = retry_delay_base
        self.batch_size = batch_size
        
        # Async queues
        self.input_queue: asyncio.Queue[RawLogEntry] = asyncio.Queue(
            maxsize=max_queue_size
        )
        self.dead_letter_queue: asyncio.Queue[Tuple[RawLogEntry, str]] = asyncio.Queue(
            maxsize=max_queue_size // 10
        )
        
        # Metrics
        self.metrics = IngestionMetrics()
        self._source_metrics: Dict[str, SourceMetrics] = {}
        
        # Worker management
        self._workers: List[asyncio.Task] = []
        self._running = False
        self._shutdown_event = asyncio.Event()
        
        # DetectionEngine submission thread (bridges async to sync)
        self._submission_queue: sync_queue.Queue = sync_queue.Queue(maxsize=max_queue_size)
        self._submission_thread: Optional[threading.Thread] = None
        self._submission_stop = threading.Event()
    
    async def start(self) -> None:
        """
        Start the ingestion pipeline.
        
        Pre: Pipeline not already running
        Post: Workers started, queues active
        """
        if self._running:
            logger.warning("[INGESTION] Pipeline already running")
            return
        
        self._running = True
        self._shutdown_event.clear()
        
        # Start submission thread for DetectionEngine
        self._submission_stop.clear()
        self._submission_thread = threading.Thread(
            target=self._submission_worker,
            name="DetectionEngine-Submission",
            daemon=True
        )
        self._submission_thread.start()
        
        # Start async workers
        self._workers = [
            asyncio.create_task(
                self._worker_loop(f"worker-{i}"),
                name=f"ingestion-worker-{i}"
            )
            for i in range(self.num_workers)
        ]
        
        logger.info(f"[INGESTION] Pipeline started with {self.num_workers} workers")
    
    async def stop(self, timeout: float = 30.0) -> None:
        """
        Gracefully stop the pipeline.
        
        Pre: Pipeline is running
        Post: Workers stopped, queues drained
        """
        if not self._running:
            return
        
        logger.info("[INGESTION] Stopping pipeline...")
        self._running = False
        self._shutdown_event.set()
        
        # Signal submission thread to stop
        self._submission_stop.set()
        
        # Wait for workers to finish with timeout
        if self._workers:
            await asyncio.wait_for(
                asyncio.gather(*self._workers, return_exceptions=True),
                timeout=timeout
            )
        
        # Wait for submission thread
        if self._submission_thread and self._submission_thread.is_alive():
            self._submission_thread.join(timeout=5.0)
        
        logger.info("[INGESTION] Pipeline stopped")
    
    async def enqueue(self, entry: RawLogEntry) -> bool:
        """
        Enqueue a raw log entry for processing.
        
        Pre: entry is valid RawLogEntry
        Post: Entry added to queue or dropped if full
        Returns: True if enqueued, False if dropped
        """
        try:
            self.input_queue.put_nowait(entry)
            self.metrics.increment('lines_received')
            self.metrics.increment('bytes_ingested', len(entry.raw_line))
            
            # Update per-source metrics
            if entry.source_id in self._source_metrics:
                self._source_metrics[entry.source_id].lines_received += 1
                self._source_metrics[entry.source_id].last_activity = datetime.utcnow()
            
            return True
        except asyncio.QueueFull:
            self.metrics.increment('events_dropped')
            logger.warning(f"[INGESTION] Queue full, dropping event from {entry.source_id}")
            return False
    
    async def _worker_loop(self, worker_name: str) -> None:
        """
        Main worker loop for processing log entries.
        
        Pre: Pipeline is running
        Post: Continuously processes entries until shutdown
        """
        logger.debug(f"[INGESTION] Worker {worker_name} started")
        
        while self._running and not self._shutdown_event.is_set():
            try:
                # Wait for entry with timeout to allow periodic checks
                entry = await asyncio.wait_for(
                    self.input_queue.get(),
                    timeout=1.0
                )
            except asyncio.TimeoutError:
                continue
            
            start_time = time.time()
            
            try:
                # Process with retry logic
                await self._process_with_retry(entry)
                self.metrics.increment('lines_parsed')
                
                if entry.source_id in self._source_metrics:
                    self._source_metrics[entry.source_id].lines_parsed += 1
                    
            except Exception as e:
                logger.error(f"[INGESTION] Processing error: {e}")
                self.metrics.increment('lines_failed')
                self.metrics.increment('source_errors')
                
                if entry.source_id in self._source_metrics:
                    self._source_metrics[entry.source_id].lines_failed += 1
                    self._source_metrics[entry.source_id].last_error = str(e)
                    self._source_metrics[entry.source_id].last_error_time = datetime.utcnow()
                
                # Send to dead letter queue
                try:
                    self.dead_letter_queue.put_nowait((entry, str(e)))
                    self.metrics.increment('events_in_dead_letter')
                except asyncio.QueueFull:
                    logger.error("[INGESTION] Dead letter queue full, dropping failed event")
            
            finally:
                # Update timing metrics
                duration_ms = int((time.time() - start_time) * 1000)
                self.metrics.update_processing_time(duration_ms)
                self.input_queue.task_done()
        
        logger.debug(f"[INGESTION] Worker {worker_name} stopped")
    
    async def _process_with_retry(self, entry: RawLogEntry) -> None:
        """
        Process entry with exponential backoff retry.
        
        Pre: entry is valid RawLogEntry
        Post: Entry processed or max retries exceeded
        """
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                await self._process_entry(entry)
                return
            except (SourceConnectionError, DetectionEngineError) as e:
                last_error = e
                self.metrics.increment('retry_attempts')
                
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay_base * (2 ** attempt)
                    logger.warning(
                        f"[INGESTION] Retry {attempt + 1}/{self.max_retries} "
                        f"after {delay}s: {e}"
                    )
                    await asyncio.sleep(delay)
        
        # Max retries exceeded
        if last_error:
            raise last_error
    
    async def _process_entry(self, entry: RawLogEntry) -> None:
        """
        Process a single log entry through the pipeline.
        
        Pre: entry is valid RawLogEntry
        Post: Event parsed and submitted to DetectionEngine
        """
        # Parse the log line
        parsed = self._parse_log_line(entry)
        
        if parsed is None:
            return  # Filtered out or unparsable
        
        # Convert to DetectionEvent format expected by DetectionEngine
        detection_event = self._convert_to_detection_event(parsed)
        
        # Submit to DetectionEngine via thread-safe queue
        try:
            self._submission_queue.put(detection_event, block=False)
            self.metrics.increment('events_submitted')
        except sync_queue.Full:
            raise DetectionEngineError("DetectionEngine submission queue full")
    
    def _parse_log_line(self, entry: RawLogEntry) -> Optional[ParsedEvent]:
        """
        Parse raw log line into structured event.
        
        Pre: entry contains raw_line
        Post: Returns ParsedEvent or None if filtered/unparsable
        """
        line = entry.raw_line
        
        # Apply filters
        if entry.source_id in self._source_metrics:
            # Check source-specific filters if available
            pass  # Filters applied before enqueue
        
        # Basic timestamp extraction
        timestamp = entry.timestamp
        
        # Try to parse as JSON first
        parsed_fields: Dict[str, Any] = {}
        try:
            parsed_fields = json.loads(line)
            if isinstance(parsed_fields, dict):
                # Extract timestamp if present
                for ts_field in ['timestamp', '@timestamp', 'time', 'date']:
                    if ts_field in parsed_fields:
                        try:
                            ts_val = parsed_fields[ts_field]
                            if isinstance(ts_val, str):
                                timestamp = datetime.fromisoformat(ts_val.replace('Z', '+00:00'))
                            break
                        except (ValueError, TypeError):
                            continue
        except json.JSONDecodeError:
            # Treat as plain text, extract fields with regex
            parsed_fields = self._extract_fields_from_text(line)
        
        # Determine event type and severity
        event_type = parsed_fields.get('event_type', 'unknown')
        severity = parsed_fields.get('severity', 'INFO').upper()
        source_host = parsed_fields.get('host', parsed_fields.get('source_host', 'unknown'))
        
        return ParsedEvent(
            event_id=entry.entry_id,
            source_id=entry.source_id,
            timestamp=timestamp,
            event_type=event_type,
            source_host=source_host,
            severity=severity,
            raw_data={'raw_line': line},
            normalized_data=parsed_fields,
            parsed_fields=parsed_fields,
            tags=entry.metadata.get('tags', [])
        )
    
    def _extract_fields_from_text(self, line: str) -> Dict[str, Any]:
        """
        Extract structured fields from plain text log line.
        
        Pre: line is a string
        Post: Returns dictionary of extracted fields
        """
        fields: Dict[str, Any] = {'message': line}
        
        # Common syslog pattern
        syslog_pattern = re.compile(
            r'^(?P<timestamp>\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+'
            r'(?P<host>\S+)\s+'
            r'(?P<process>\S+)(?:\[(?P<pid>\d+)\])?:\s*'
            r'(?P<message>.*)$'
        )
        
        match = syslog_pattern.match(line)
        if match:
            fields.update(match.groupdict())
        else:
            # Try to extract IP addresses
            ip_pattern = re.compile(r'\b(?P<ip>(?:\d{1,3}\.){3}\d{1,3})\b')
            ips = ip_pattern.findall(line)
            if ips:
                fields['ip_addresses'] = ips
            
            # Try to extract key=value pairs
            kv_pattern = re.compile(r'(\w+)=([^\s,]+)')
            kv_pairs = kv_pattern.findall(line)
            for key, value in kv_pairs:
                fields[key] = value
        
        return fields
    
    def _convert_to_detection_event(self, parsed: ParsedEvent) -> Any:
        """
        Convert ParsedEvent to DetectionEvent format.
        
        Pre: parsed is valid ParsedEvent
        Post: Returns DetectionEvent-compatible object
        """
        # Import here to avoid circular dependency
        from ..detection.engine import DetectionEvent, EventSeverity
        
        # Map severity string to EventSeverity enum
        severity_map = {
            'CRITICAL': EventSeverity.CRITICAL,
            'HIGH': EventSeverity.HIGH,
            'MEDIUM': EventSeverity.MEDIUM,
            'LOW': EventSeverity.LOW,
            'INFO': EventSeverity.INFO,
        }
        severity = severity_map.get(parsed.severity, EventSeverity.INFO)
        
        return DetectionEvent(
            event_id=parsed.event_id,
            timestamp=parsed.timestamp,
            source_type=parsed.source_id,
            source_host=parsed.source_host,
            event_type=parsed.event_type,
            severity=severity,
            raw_data=parsed.raw_data,
            normalized_data=parsed.normalized_data,
            ioc_matches=parsed.ioc_matches,
            correlated_events=[]
        )
    
    def _submission_worker(self) -> None:
        """
        Background thread for submitting events to DetectionEngine.
        
        Bridges async pipeline with sync DetectionEngine.
        
        Pre: _submission_queue initialized
        Post: Continuously submits events until stopped
        """
        logger.info("[INGESTION] DetectionEngine submission thread started")
        
        while not self._submission_stop.is_set():
            try:
                event = self._submission_queue.get(timeout=1.0)
            except sync_queue.Empty:
                continue
            
            try:
                success = self.detection_engine.submit_event(event)
                if not success:
                    logger.warning("[INGESTION] DetectionEngine rejected event (queue full)")
            except Exception as e:
                logger.error(f"[INGESTION] DetectionEngine submission error: {e}")
            finally:
                self._submission_queue.task_done()
        
        logger.info("[INGESTION] DetectionEngine submission thread stopped")
    
    def register_source(self, source_id: str) -> None:
        """Register a new source for metrics tracking."""
        self._source_metrics[source_id] = SourceMetrics(source_id=source_id)
    
    def update_source_status(self, source_id: str, status: SourceStatus) -> None:
        """Update status for a source."""
        if source_id in self._source_metrics:
            self._source_metrics[source_id].status = status
            
            # Update aggregate metrics
            active = sum(1 for m in self._source_metrics.values() 
                        if m.status == SourceStatus.RUNNING)
            error = sum(1 for m in self._source_metrics.values() 
                       if m.status == SourceStatus.ERROR)
            
            self.metrics.sources_active = active
            self.metrics.sources_error = error
            
            if status == SourceStatus.RUNNING:
                self._source_metrics[source_id].started_at = datetime.utcnow()
    
    def get_source_metrics(self, source_id: Optional[str] = None) -> Dict[str, Any]:
        """Get metrics for a specific source or all sources."""
        if source_id:
            if source_id in self._source_metrics:
                return self._source_metrics[source_id].to_dict()
            return {}
        
        return {sid: m.to_dict() for sid, m in self._source_metrics.items()}


# ==============================================================================
# LOG INGESTION ENGINE
# ==============================================================================

class LogIngestionEngine:
    """
    Main orchestrator for log ingestion from multiple sources.
    
    Manages log sources, coordinates ingestion pipelines, and integrates
    with the DetectionEngine for real-time security analysis.
    
    Pre: DetectionEngine instance available
    Post: Engine ready to ingest from configured sources
    
    Example:
        engine = LogIngestionEngine(detection_engine)
        
        # Add file source
        source = LogSource(
            source_id='auth-logs',
            source_type=LogSourceType.FILE,
            config={'path': '/var/log/auth.log'},
            mode=IngestionMode.REALTIME
        )
        engine.add_source(source)
        
        # Start ingestion
        await engine.start_ingestion()
        
        # Get metrics
        metrics = engine.get_metrics()
    """
    
    def __init__(
        self,
        detection_engine: Optional[Any] = None,
        max_queue_size: int = 10000,
        num_workers: int = 4,
        data_dir: str = "/opt/codex-swarm/command-post/data"
    ):
        """
        Initialize the log ingestion engine.
        
        Args:
            detection_engine: DetectionEngine instance for event analysis
            max_queue_size: Maximum size of processing queues
            num_workers: Number of pipeline workers
            data_dir: Directory for dead letter queue and state files
        """
        # Import DetectionEngine if not provided
        if detection_engine is None:
            from ..detection.engine import get_detection_engine
            detection_engine = get_detection_engine()
        
        self.detection_engine = detection_engine
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Create ingestion pipeline
        self.pipeline = IngestionPipeline(
            detection_engine=detection_engine,
            max_queue_size=max_queue_size,
            num_workers=num_workers
        )
        
        # Source management
        self._sources: Dict[str, LogSource] = {}
        self._source_tasks: Dict[str, asyncio.Task] = {}
        self._source_status: Dict[str, SourceStatus] = {}
        
        # State management
        self._running = False
        self._shutdown_event = asyncio.Event()
        self._lock = asyncio.Lock()
        
        # Dead letter queue persistence
        self._dead_letter_file = self.data_dir / "dead_letter_queue.jsonl"
    
    async def add_source(self, source: LogSource) -> bool:
        """
        Register a new log source for ingestion.
        
        Pre: source has unique source_id
        Pre: source configuration is valid
        Post: Source registered, ingestion task created if engine running
        
        Args:
            source: LogSource configuration
            
        Returns:
            True if source added successfully
            
        Raises:
            SourceConfigurationError: If source_id already exists or config invalid
        """
        async with self._lock:
            if source.source_id in self._sources:
                raise SourceConfigurationError(
                    f"Source with ID '{source.source_id}' already exists"
                )
            
            if not source.enabled:
                logger.info(f"[INGESTION] Source {source.source_id} added but disabled")
                self._sources[source.source_id] = source
                self._source_status[source.source_id] = SourceStatus.DISABLED
                return True
            
            # Register source
            self._sources[source.source_id] = source
            self._source_status[source.source_id] = SourceStatus.PENDING
            self.pipeline.register_source(source.source_id)
            
            logger.info(f"[INGESTION] Source added: {source.source_id} ({source.source_type.value})")
            
            # Start ingestion if engine is running
            if self._running:
                await self._start_source(source)
            
            return True
    
    async def remove_source(self, source_id: str, cleanup: bool = True) -> bool:
        """
        Deregister a log source.
        
        Pre: source_id exists in registered sources
        Post: Source stopped and removed from registry
        
        Args:
            source_id: ID of source to remove
            cleanup: Whether to clean up source files/state
            
        Returns:
            True if source removed, False if not found
        """
        async with self._lock:
            if source_id not in self._sources:
                return False
            
            # Stop source task if running
            if source_id in self._source_tasks:
                task = self._source_tasks[source_id]
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                del self._source_tasks[source_id]
            
            # Remove source
            source = self._sources.pop(source_id)
            self._source_status.pop(source_id, None)
            
            logger.info(f"[INGESTION] Source removed: {source_id}")
            
            return True
    
    async def start_ingestion(self) -> None:
        """
        Begin ingestion from all registered sources.
        
        Pre: Pipeline initialized
        Post: All enabled sources started, pipeline workers active
        """
        if self._running:
            logger.warning("[INGESTION] Ingestion already running")
            return
        
        logger.info("[INGESTION] Starting ingestion engine...")
        
        # Start pipeline
        await self.pipeline.start()
        
        self._running = True
        self._shutdown_event.clear()
        
        # Start all enabled sources
        for source in self._sources.values():
            if source.enabled and self._source_status.get(source.source_id) != SourceStatus.RUNNING:
                await self._start_source(source)
        
        logger.info(f"[INGESTION] Ingestion started with {len(self._sources)} sources")
    
    async def stop_ingestion(self, timeout: float = 30.0) -> None:
        """
        Gracefully stop all ingestion.
        
        Pre: Ingestion is running
        Post: All sources stopped, pipeline drained
        
        Args:
            timeout: Maximum time to wait for graceful shutdown
        """
        if not self._running:
            return
        
        logger.info("[INGESTION] Stopping ingestion engine...")
        
        self._running = False
        self._shutdown_event.set()
        
        # Cancel all source tasks
        async with self._lock:
            for source_id, task in list(self._source_tasks.items()):
                task.cancel()
                self._source_status[source_id] = SourceStatus.STOPPED
                self.pipeline.update_source_status(source_id, SourceStatus.STOPPED)
        
        # Wait for tasks to complete
        if self._source_tasks:
            await asyncio.gather(
                *self._source_tasks.values(),
                return_exceptions=True
            )
        
        # Stop pipeline
        await self.pipeline.stop(timeout=timeout)
        
        # Persist dead letter queue
        await self._persist_dead_letter_queue()
        
        self._source_tasks.clear()
        
        logger.info("[INGESTION] Ingestion engine stopped")
    
    async def get_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive ingestion metrics.
        
        Pre: Engine initialized
        Post: Returns current metrics snapshot
        
        Returns:
            Dictionary containing pipeline and per-source metrics
        """
        return {
            'engine_status': 'running' if self._running else 'stopped',
            'sources_total': len(self._sources),
            'sources_running': sum(
                1 for s in self._source_status.values() if s == SourceStatus.RUNNING
            ),
            'pipeline_metrics': self.pipeline.metrics.to_dict(),
            'source_metrics': self.pipeline.get_source_metrics()
        }
    
    async def ingest_file(
        self,
        file_path: str,
        source_id: Optional[str] = None,
        mode: IngestionMode = IngestionMode.BATCH,
        parser_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Ingest a single file (batch or realtime).
        
        Pre: file_path exists and is readable
        Post: File contents ingested into pipeline
        
        Args:
            file_path: Path to log file
            source_id: Optional source ID (auto-generated if not provided)
            mode: Ingestion mode (batch/realtime/hybrid)
            parser_config: Optional parser configuration
            
        Returns:
            Dictionary with ingestion results
        """
        path = Path(file_path)
        if not path.exists():
            raise SourceConfigurationError(f"File not found: {file_path}")
        
        if not path.is_file():
            raise SourceConfigurationError(f"Path is not a file: {file_path}")
        
        if source_id is None:
            source_id = f"file-{path.name}-{uuid.uuid4().hex[:8]}"
        
        # Create temporary source
        source = LogSource(
            source_id=source_id,
            source_type=LogSourceType.FILE,
            config={'path': str(path.resolve())},
            mode=mode,
            parser_config=parser_config
        )
        
        # Add and start source
        await self.add_source(source)
        
        if mode == IngestionMode.BATCH:
            # Wait for batch to complete
            await self._wait_for_source_completion(source_id)
            await self.remove_source(source_id, cleanup=False)
        
        return {
            'source_id': source_id,
            'file_path': str(path),
            'mode': mode.value,
            'status': 'completed' if mode == IngestionMode.BATCH else 'running'
        }
    
    async def _start_source(self, source: LogSource) -> None:
        """
        Start ingestion for a specific source.
        
        Pre: source is registered and enabled
        Post: Source task created and running
        """
        source_id = source.source_id
        
        # Create appropriate reader based on source type
        if source.source_type == LogSourceType.FILE:
            task = asyncio.create_task(
                self._read_file_source(source),
                name=f"source-{source_id}"
            )
        elif source.source_type == LogSourceType.SYSLOG:
            task = asyncio.create_task(
                self._read_syslog_source(source),
                name=f"source-{source_id}"
            )
        elif source.source_type == LogSourceType.API:
            task = asyncio.create_task(
                self._read_api_source(source),
                name=f"source-{source_id}"
            )
        elif source.source_type == LogSourceType.CLOUD_AWS:
            task = asyncio.create_task(
                self._read_cloudtrail_source(source),
                name=f"source-{source_id}"
            )
        elif source.source_type == LogSourceType.TCP_SOCKET:
            task = asyncio.create_task(
                self._read_tcp_socket_source(source),
                name=f"source-{source_id}"
            )
        elif source.source_type == LogSourceType.UDP_SOCKET:
            task = asyncio.create_task(
                self._read_udp_socket_source(source),
                name=f"source-{source_id}"
            )
        else:
            logger.error(f"[INGESTION] Unsupported source type: {source.source_type}")
            self._source_status[source_id] = SourceStatus.ERROR
            return
        
        self._source_tasks[source_id] = task
        self._source_status[source_id] = SourceStatus.RUNNING
        self.pipeline.update_source_status(source_id, SourceStatus.RUNNING)
        
        logger.info(f"[INGESTION] Started source: {source_id}")
    
    async def _read_file_source(self, source: LogSource) -> None:
        """
        Read from file source with optional tailing.
        
        Pre: source.config['path'] is valid file path
        Post: File contents read and enqueued
        """
        source_id = source.source_id
        path = Path(source.config['path'])
        mode = source.mode
        
        try:
            if mode == IngestionMode.BATCH:
                # One-time read
                await self._read_file_batch(source, path)
            elif mode == IngestionMode.REALTIME:
                # Tail mode
                await self._tail_file(source, path)
            elif mode == IngestionMode.HYBRID:
                # Read existing then tail
                await self._read_file_batch(source, path)
                await self._tail_file(source, path)
                
        except asyncio.CancelledError:
            logger.info(f"[INGESTION] File source {source_id} cancelled")
            raise
        except Exception as e:
            logger.error(f"[INGESTION] File source {source_id} error: {e}")
            self._source_status[source_id] = SourceStatus.ERROR
            self.pipeline.update_source_status(source_id, SourceStatus.ERROR)
            raise
    
    async def _read_file_batch(self, source: LogSource, path: Path) -> int:
        """
        Read file in batch mode.
        
        Pre: path exists and is readable
        Post: All lines enqueued
        Returns: Number of lines read
        """
        lines_read = 0
        batch_size = 1000
        
        # Handle compressed files
        open_func = gzip.open if str(path).endswith('.gz') else open
        mode = 'rt' if str(path).endswith('.gz') else 'r'
        
        try:
            with open_func(path, mode, encoding='utf-8', errors='replace') as f:
                while True:
                    lines = []
                    for _ in range(batch_size):
                        line = f.readline()
                        if not line:
                            break
                        lines.append(line.rstrip('\n\r'))
                    
                    if not lines:
                        break
                    
                    for line in lines:
                        if source.matches_filters(line):
                            entry = RawLogEntry(
                                entry_id=f"EVT-{uuid.uuid4().hex[:12].upper()}",
                                source_id=source.source_id,
                                raw_line=line,
                                timestamp=datetime.utcnow(),
                                metadata={'tags': source.tags}
                            )
                            await self.pipeline.enqueue(entry)
                            lines_read += 1
                    
                    # Yield control periodically
                    await asyncio.sleep(0)
        
        except Exception as e:
            logger.error(f"[INGESTION] Error reading file {path}: {e}")
            raise SourceConnectionError(f"Failed to read file {path}: {e}")
        
        logger.info(f"[INGESTION] Batch read {lines_read} lines from {path}")
        return lines_read
    
    async def _tail_file(self, source: LogSource, path: Path) -> None:
        """
        Tail a file for real-time updates.
        
        Pre: path exists
        Post: Continuously reads new lines until cancelled
        """
        source_id = source.source_id
        
        # Track file inode for rotation detection
        current_inode = None
        last_position = 0
        
        try:
            current_inode = path.stat().st_ino
            last_position = path.stat().st_size  # Start at end by default
        except OSError:
            pass
        
        while not self._shutdown_event.is_set():
            try:
                # Check if file exists
                if not path.exists():
                    logger.warning(f"[INGESTION] File not found, waiting: {path}")
                    await asyncio.sleep(1.0)
                    continue
                
                # Check for file rotation
                try:
                    new_inode = path.stat().st_ino
                    if current_inode is not None and new_inode != current_inode:
                        logger.info(f"[INGESTION] File rotated: {path}")
                        last_position = 0
                    current_inode = new_inode
                except OSError:
                    pass
                
                # Read new lines
                with open(path, 'r', encoding='utf-8', errors='replace') as f:
                    f.seek(last_position)
                    
                    while not self._shutdown_event.is_set():
                        line = f.readline()
                        if not line:
                            # No new data, update position and wait
                            last_position = f.tell()
                            break
                        
                        line = line.rstrip('\n\r')
                        if source.matches_filters(line):
                            entry = RawLogEntry(
                                entry_id=f"EVT-{uuid.uuid4().hex[:12].upper()}",
                                source_id=source_id,
                                raw_line=line,
                                timestamp=datetime.utcnow(),
                                metadata={'tags': source.tags}
                            )
                            await self.pipeline.enqueue(entry)
                
                # Small delay before next check
                await asyncio.sleep(0.1)
                
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"[INGESTION] Tail error for {source_id}: {e}")
                await asyncio.sleep(1.0)  # Back off on error
    
    async def _read_syslog_source(self, source: LogSource) -> None:
        """
        Read from syslog UDP/TCP socket.
        
        Pre: source.config contains 'address' and 'port'
        Post: Syslog messages received and enqueued
        """
        source_id = source.source_id
        address = source.config['address']
        port = source.config['port']
        protocol = source.config.get('protocol', 'udp').lower()
        
        try:
            if protocol == 'udp':
                await self._read_udp_socket(source_id, address, port, source)
            else:
                await self._read_tcp_socket(source_id, address, port, source)
        except Exception as e:
            logger.error(f"[INGESTION] Syslog source {source_id} error: {e}")
            self._source_status[source_id] = SourceStatus.ERROR
            raise
    
    async def _read_tcp_socket_source(self, source: LogSource) -> None:
        """Read from TCP socket source."""
        host = source.config['host']
        port = source.config['port']
        await self._read_tcp_socket(source.source_id, host, port, source)
    
    async def _read_udp_socket_source(self, source: LogSource) -> None:
        """Read from UDP socket source."""
        host = source.config['host']
        port = source.config['port']
        await self._read_udp_socket(source.source_id, host, port, source)
    
    async def _read_tcp_socket(
        self,
        source_id: str,
        host: str,
        port: int,
        source: LogSource
    ) -> None:
        """Generic TCP socket reader."""
        while not self._shutdown_event.is_set():
            try:
                reader, writer = await asyncio.open_connection(host, port)
                logger.info(f"[INGESTION] TCP connection established: {host}:{port}")
                
                while not self._shutdown_event.is_set():
                    try:
                        line = await asyncio.wait_for(
                            reader.readline(),
                            timeout=1.0
                        )
                        if not line:
                            break
                        
                        line = line.decode('utf-8', errors='replace').rstrip('\n\r')
                        if source.matches_filters(line):
                            entry = RawLogEntry(
                                entry_id=f"EVT-{uuid.uuid4().hex[:12].upper()}",
                                source_id=source_id,
                                raw_line=line,
                                timestamp=datetime.utcnow(),
                                metadata={'tags': source.tags}
                            )
                            await self.pipeline.enqueue(entry)
                    except asyncio.TimeoutError:
                        continue
                
                writer.close()
                await writer.wait_closed()
                
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"[INGESTION] TCP socket error for {source_id}: {e}")
                await asyncio.sleep(5.0)  # Reconnect delay
    
    async def _read_udp_socket(
        self,
        source_id: str,
        host: str,
        port: int,
        source: LogSource
    ) -> None:
        """Generic UDP socket reader."""
        try:
            transport, protocol = await asyncio.get_event_loop().create_datagram_endpoint(
                lambda: UDPSyslogProtocol(source_id, source, self.pipeline),
                local_addr=(host, port)
            )
            
            logger.info(f"[INGESTION] UDP socket listening: {host}:{port}")
            
            # Keep running until shutdown
            while not self._shutdown_event.is_set():
                await asyncio.sleep(1.0)
            
            transport.close()
            
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"[INGESTION] UDP socket error for {source_id}: {e}")
            raise
    
    async def _read_api_source(self, source: LogSource) -> None:
        """
        Read from REST API endpoint.
        
        Pre: source.config contains 'url'
        Post: API responses polled and enqueued
        """
        source_id = source.source_id
        url = source.config['url']
        poll_interval = source.config.get('poll_interval', 60)
        headers = source.config.get('headers', {})
        
        # Import aiohttp here to avoid hard dependency
        try:
            import aiohttp
        except ImportError:
            logger.error("[INGESTION] aiohttp required for API sources")
            self._source_status[source_id] = SourceStatus.ERROR
            return
        
        while not self._shutdown_event.is_set():
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=headers, timeout=30) as resp:
                        if resp.status == 200:
                            data = await resp.text()
                            
                            # Handle JSON or line-delimited
                            content_type = resp.headers.get('Content-Type', '')
                            
                            if 'application/json' in content_type:
                                # Single JSON object or array
                                try:
                                    json_data = json.loads(data)
                                    if isinstance(json_data, list):
                                        for item in json_data:
                                            line = json.dumps(item)
                                            if source.matches_filters(line):
                                                entry = RawLogEntry(
                                                    entry_id=f"EVT-{uuid.uuid4().hex[:12].upper()}",
                                                    source_id=source_id,
                                                    raw_line=line,
                                                    timestamp=datetime.utcnow(),
                                                    metadata={'tags': source.tags}
                                                )
                                                await self.pipeline.enqueue(entry)
                                    else:
                                        if source.matches_filters(data):
                                            entry = RawLogEntry(
                                                entry_id=f"EVT-{uuid.uuid4().hex[:12].upper()}",
                                                source_id=source_id,
                                                raw_line=data,
                                                timestamp=datetime.utcnow(),
                                                metadata={'tags': source.tags}
                                            )
                                            await self.pipeline.enqueue(entry)
                                except json.JSONDecodeError:
                                    pass
                            else:
                                # Line-delimited
                                for line in data.split('\n'):
                                    line = line.strip()
                                    if line and source.matches_filters(line):
                                        entry = RawLogEntry(
                                            entry_id=f"EVT-{uuid.uuid4().hex[:12].upper()}",
                                            source_id=source_id,
                                            raw_line=line,
                                            timestamp=datetime.utcnow(),
                                            metadata={'tags': source.tags}
                                        )
                                        await self.pipeline.enqueue(entry)
                        else:
                            logger.warning(f"[INGESTION] API returned status {resp.status}: {url}")
                
                # Wait before next poll
                await asyncio.wait_for(
                    self._shutdown_event.wait(),
                    timeout=poll_interval
                )
                
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"[INGESTION] API source {source_id} error: {e}")
                await asyncio.sleep(5.0)
    
    async def _read_cloudtrail_source(self, source: LogSource) -> None:
        """
        Read AWS CloudTrail logs from S3.
        
        Pre: source.config contains 'bucket' and 'region'
        Post: CloudTrail events polled and enqueued
        """
        source_id = source.source_id
        bucket = source.config['bucket']
        region = source.config['region']
        prefix = source.config.get('prefix', 'AWSLogs/')
        poll_interval = source.config.get('poll_interval', 300)
        
        # Import boto3 here to avoid hard dependency
        try:
            import boto3
            from botocore.exceptions import ClientError
        except ImportError:
            logger.error("[INGESTION] boto3 required for AWS CloudTrail sources")
            self._source_status[source_id] = SourceStatus.ERROR
            return
        
        # Track processed files
        processed_files: Set[str] = set()
        state_file = self.data_dir / f"cloudtrail_state_{source_id}.json"
        
        if state_file.exists():
            try:
                with open(state_file, 'r') as f:
                    processed_files = set(json.load(f))
            except Exception:
                pass
        
        s3 = boto3.client('s3', region_name=region)
        
        while not self._shutdown_event.is_set():
            try:
                # List objects in bucket with prefix
                paginator = s3.get_paginator('list_objects_v2')
                new_files = []
                
                for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
                    for obj in page.get('Contents', []):
                        key = obj['Key']
                        if key.endswith('.json.gz') and key not in processed_files:
                            new_files.append(key)
                
                # Process new files
                for key in new_files:
                    if self._shutdown_event.is_set():
                        break
                    
                    try:
                        response = s3.get_object(Bucket=bucket, Key=key)
                        with gzip.GzipFile(fileobj=response['Body']) as gz:
                            data = json.loads(gz.read().decode('utf-8'))
                        
                        # CloudTrail records are in 'Records' array
                        for record in data.get('Records', []):
                            line = json.dumps(record)
                            if source.matches_filters(line):
                                entry = RawLogEntry(
                                    entry_id=f"EVT-{uuid.uuid4().hex[:12].upper()}",
                                    source_id=source_id,
                                    raw_line=line,
                                    timestamp=datetime.utcnow(),
                                    metadata={
                                        'tags': source.tags + ['cloudtrail', 'aws'],
                                        's3_key': key
                                    }
                                )
                                await self.pipeline.enqueue(entry)
                        
                        processed_files.add(key)
                        
                    except Exception as e:
                        logger.error(f"[INGESTION] Error processing S3 object {key}: {e}")
                
                # Save state
                with open(state_file, 'w') as f:
                    json.dump(list(processed_files), f)
                
                # Wait before next poll
                await asyncio.wait_for(
                    self._shutdown_event.wait(),
                    timeout=poll_interval
                )
                
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                raise
            except ClientError as e:
                logger.error(f"[INGESTION] AWS API error for {source_id}: {e}")
                await asyncio.sleep(60.0)
            except Exception as e:
                logger.error(f"[INGESTION] CloudTrail source {source_id} error: {e}")
                await asyncio.sleep(30.0)
    
    async def _wait_for_source_completion(self, source_id: str, timeout: float = 300.0) -> bool:
        """Wait for a source task to complete."""
        if source_id not in self._source_tasks:
            return True
        
        try:
            await asyncio.wait_for(
                self._source_tasks[source_id],
                timeout=timeout
            )
            return True
        except asyncio.TimeoutError:
            logger.warning(f"[INGESTION] Source {source_id} did not complete within timeout")
            return False
        except asyncio.CancelledError:
            return True
    
    async def _persist_dead_letter_queue(self) -> None:
        """Persist dead letter queue to disk."""
        try:
            with open(self._dead_letter_file, 'a') as f:
                while not self.pipeline.dead_letter_queue.empty():
                    entry, error = self.pipeline.dead_letter_queue.get_nowait()
                    record = {
                        'timestamp': datetime.utcnow().isoformat(),
                        'entry': {
                            'entry_id': entry.entry_id,
                            'source_id': entry.source_id,
                            'raw_line': entry.raw_line,
                            'timestamp': entry.timestamp.isoformat()
                        },
                        'error': error
                    }
                    f.write(json.dumps(record) + '\n')
        except Exception as e:
            logger.error(f"[INGESTION] Failed to persist dead letter queue: {e}")


# ==============================================================================
# UDP PROTOCOL HANDLER
# ==============================================================================

class UDPSyslogProtocol(asyncio.DatagramProtocol):
    """
    Protocol handler for UDP syslog messages.
    
    Pre: pipeline and source configured
    Post: Received datagrams enqueued for processing
    """
    
    def __init__(self, source_id: str, source: LogSource, pipeline: IngestionPipeline):
        self.source_id = source_id
        self.source = source
        self.pipeline = pipeline
        self.transport: Optional[asyncio.DatagramTransport] = None
    
    def connection_made(self, transport: asyncio.DatagramTransport) -> None:
        self.transport = transport
    
    def datagram_received(self, data: bytes, addr: Tuple[str, int]) -> None:
        try:
            message = data.decode('utf-8', errors='replace').rstrip('\n\r')
            
            if self.source.matches_filters(message):
                entry = RawLogEntry(
                    entry_id=f"EVT-{uuid.uuid4().hex[:12].upper()}",
                    source_id=self.source_id,
                    raw_line=message,
                    timestamp=datetime.utcnow(),
                    metadata={
                        'tags': self.source.tags,
                        'remote_addr': addr[0],
                        'remote_port': addr[1]
                    }
                )
                # Use create_task to enqueue asynchronously
                asyncio.create_task(self.pipeline.enqueue(entry))
        except Exception as e:
            logger.error(f"[INGESTION] Error processing UDP datagram: {e}")
    
    def error_received(self, exc: Exception) -> None:
        logger.error(f"[INGESTION] UDP error: {exc}")


# ==============================================================================
# UTILITY FUNCTIONS
# ==============================================================================

def parse_timestamp(timestamp_str: str) -> Optional[datetime]:
    """
    Parse various timestamp formats.
    
    Pre: timestamp_str is a string
    Post: Returns datetime or None if parsing fails
    """
    formats = [
        '%Y-%m-%dT%H:%M:%S.%fZ',
        '%Y-%m-%dT%H:%M:%SZ',
        '%Y-%m-%d %H:%M:%S.%f',
        '%Y-%m-%d %H:%M:%S',
        '%b %d %H:%M:%S',
        '%d/%b/%Y:%H:%M:%S %z',
        '%Y-%m-%dT%H:%M:%S%z',
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(timestamp_str, fmt)
        except ValueError:
            continue
    
    # Try ISO format with timezone
    try:
        return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
    except (ValueError, TypeError):
        pass
    
    return None


def create_file_source(
    path: str,
    source_id: Optional[str] = None,
    mode: IngestionMode = IngestionMode.REALTIME,
    filters: Optional[List[str]] = None,
    tags: Optional[List[str]] = None
) -> LogSource:
    """
    Helper to create a file-based log source.
    
    Args:
        path: Path to log file
        source_id: Optional source ID (defaults to file name)
        mode: Ingestion mode
        filters: Optional regex filters
        tags: Optional tags
        
    Returns:
        Configured LogSource
    """
    if source_id is None:
        source_id = f"file-{Path(path).name}"
    
    return LogSource(
        source_id=source_id,
        source_type=LogSourceType.FILE,
        config={'path': path},
        mode=mode,
        filters=filters or [],
        tags=tags or []
    )


def create_syslog_source(
    address: str = '0.0.0.0',
    port: int = 514,
    protocol: str = 'udp',
    source_id: Optional[str] = None,
    filters: Optional[List[str]] = None,
    tags: Optional[List[str]] = None
) -> LogSource:
    """
    Helper to create a syslog source.
    
    Args:
        address: Bind address
        port: Port number
        protocol: 'udp' or 'tcp'
        source_id: Optional source ID
        filters: Optional regex filters
        tags: Optional tags
        
    Returns:
        Configured LogSource
    """
    if source_id is None:
        source_id = f"syslog-{protocol}-{port}"
    
    # Ensure 'syslog' tag is always present
    final_tags = tags or []
    if 'syslog' not in final_tags:
        final_tags = ['syslog'] + final_tags
    
    return LogSource(
        source_id=source_id,
        source_type=LogSourceType.SYSLOG,
        config={
            'address': address,
            'port': port,
            'protocol': protocol
        },
        filters=filters or [],
        tags=final_tags
    )


def create_cloudtrail_source(
    bucket: str,
    region: str,
    prefix: str = 'AWSLogs/',
    source_id: Optional[str] = None,
    poll_interval: int = 300,
    tags: Optional[List[str]] = None
) -> LogSource:
    """
    Helper to create an AWS CloudTrail source.
    
    Args:
        bucket: S3 bucket name
        region: AWS region
        prefix: S3 key prefix
        source_id: Optional source ID
        poll_interval: Polling interval in seconds
        tags: Optional tags
        
    Returns:
        Configured LogSource
    """
    if source_id is None:
        source_id = f"cloudtrail-{bucket}"
    
    return LogSource(
        source_id=source_id,
        source_type=LogSourceType.CLOUD_AWS,
        config={
            'bucket': bucket,
            'region': region,
            'prefix': prefix,
            'poll_interval': poll_interval
        },
        tags=tags or ['cloudtrail', 'aws', 'cloud']
    )


# ==============================================================================
# MODULE INITIALIZATION
# ==============================================================================

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

# Version
__version__ = '6.0.0'
