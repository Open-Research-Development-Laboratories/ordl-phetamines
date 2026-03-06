#!/usr/bin/env python3
"""
================================================================================
ORDL BLUE TEAM LOG INGESTION UNIT TESTS
================================================================================
Classification: TOP SECRET//SCI//NOFORN
================================================================================
"""

import pytest
import asyncio
import tempfile
import os
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from typing import Generator

import sys
sys.path.insert(0, '/opt/codex-swarm/command-post')

from blueteam.logs import (
    LogIngestionEngine,
    IngestionPipeline,
    LogSource,
    LogSourceType,
    SourceStatus,
    IngestionMode,
    IngestionMetrics,
    SourceMetrics,
    RawLogEntry,
    ParsedEvent,
    IngestionError,
    SourceConfigurationError,
    SourceConnectionError,
    ParseError,
    create_file_source,
    create_syslog_source,
    create_cloudtrail_source,
    parse_timestamp,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_detection_engine():
    """Mock detection engine for testing."""
    engine = Mock()
    engine.submit_event = Mock(return_value=True)
    return engine


@pytest.fixture
def temp_log_file() -> Generator[str, None, None]:
    """Create temporary log file with test data."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
        f.write('2024-01-15T10:00:00Z INFO System started\n')
        f.write('2024-01-15T10:01:00Z WARN High memory usage\n')
        f.write('2024-01-15T10:02:00Z ERROR Connection failed\n')
        f.write('{"timestamp": "2024-01-15T10:03:00Z", "level": "INFO", "msg": "JSON log"}\n')
        path = f.name
    yield path
    os.unlink(path)


@pytest.fixture
def sample_log_source():
    """Sample log source for testing."""
    return LogSource(
        source_id='test-source-001',
        source_type=LogSourceType.FILE,
        config={'path': '/tmp/test.log'},
        mode=IngestionMode.BATCH,
        tags=['test']
    )


@pytest.fixture
async def ingestion_pipeline(mock_detection_engine):
    """Create ingestion pipeline for testing."""
    pipeline = IngestionPipeline(
        detection_engine=mock_detection_engine,
        max_queue_size=1000,
        num_workers=2
    )
    await pipeline.start()
    yield pipeline
    await pipeline.stop()


@pytest.fixture
async def log_ingestion_engine(mock_detection_engine, tmp_path):
    """Create log ingestion engine for testing."""
    engine = LogIngestionEngine(
        detection_engine=mock_detection_engine,
        max_queue_size=1000,
        num_workers=2,
        data_dir=str(tmp_path)
    )
    yield engine
    await engine.stop_ingestion()


# =============================================================================
# LOG SOURCE TESTS
# =============================================================================

class TestLogSource:
    """Test LogSource dataclass."""
    
    def test_log_source_creation(self):
        """Test creating a valid log source."""
        source = LogSource(
            source_id='test-001',
            source_type=LogSourceType.FILE,
            config={'path': '/var/log/test.log'},
            enabled=True,
            priority=5,
            mode=IngestionMode.REALTIME,
            tags=['test', 'auth']
        )
        
        assert source.source_id == 'test-001'
        assert source.source_type == LogSourceType.FILE
        assert source.config['path'] == '/var/log/test.log'
        assert source.enabled is True
        assert source.priority == 5
        assert source.mode == IngestionMode.REALTIME
        assert source.tags == ['test', 'auth']
    
    def test_log_source_validation_missing_path(self):
        """Test validation fails for file source without path."""
        with pytest.raises(SourceConfigurationError) as exc_info:
            LogSource(
                source_id='test-001',
                source_type=LogSourceType.FILE,
                config={}  # Missing 'path'
            )
        assert 'path' in str(exc_info.value).lower()
    
    def test_log_source_validation_missing_syslog_port(self):
        """Test validation fails for syslog source without port."""
        with pytest.raises(SourceConfigurationError) as exc_info:
            LogSource(
                source_id='test-001',
                source_type=LogSourceType.SYSLOG,
                config={'address': '127.0.0.1'}  # Missing 'port'
            )
        assert 'port' in str(exc_info.value).lower()
    
    def test_log_source_validation_empty_id(self):
        """Test validation fails for empty source_id."""
        with pytest.raises(SourceConfigurationError):
            LogSource(
                source_id='',
                source_type=LogSourceType.FILE,
                config={'path': '/tmp/test.log'}
            )
    
    def test_log_source_filter_matching(self):
        """Test log source filter matching (all patterns must match)."""
        source = LogSource(
            source_id='filtered-source',
            source_type=LogSourceType.FILE,
            config={'path': '/tmp/test.log'},
            filters=['ERROR']  # Single pattern
        )
        
        assert source.matches_filters('ERROR: Something went wrong') is True
        assert source.matches_filters('INFO: Normal operation') is False
        
        # Test with multiple patterns (AND logic - all must match)
        source_multi = LogSource(
            source_id='filtered-source-multi',
            source_type=LogSourceType.FILE,
            config={'path': '/tmp/test.log'},
            filters=['ERROR', 'failed']  # Both must be present
        )
        
        assert source_multi.matches_filters('ERROR: Something failed') is True
        assert source_multi.matches_filters('ERROR: Success') is False  # Missing 'failed'
    
    def test_log_source_filter_no_filters(self):
        """Test log source with no filters matches everything."""
        source = LogSource(
            source_id='unfiltered-source',
            source_type=LogSourceType.FILE,
            config={'path': '/tmp/test.log'}
        )
        
        assert source.matches_filters('anything') is True
        assert source.matches_filters('') is True
    
    def test_log_source_to_dict(self):
        """Test LogSource serialization."""
        source = LogSource(
            source_id='test-001',
            source_type=LogSourceType.FILE,
            config={'path': '/tmp/test.log'},
            tags=['test']
        )
        
        data = source.to_dict()
        assert data['source_id'] == 'test-001'
        assert data['source_type'] == 'file'
        assert data['config']['path'] == '/tmp/test.log'
        assert data['tags'] == ['test']


class TestLogSourceType:
    """Test LogSourceType enum."""
    
    def test_all_source_types(self):
        """Test all defined source types."""
        expected = [
            'file', 'syslog', 'api', 'cloud_aws', 'cloud_azure',
            'kafka', 'tcp_socket', 'udp_socket'
        ]
        actual = [e.value for e in LogSourceType]
        assert sorted(actual) == sorted(expected)


class TestSourceStatus:
    """Test SourceStatus enum."""
    
    def test_all_status_values(self):
        """Test all defined status values."""
        expected = ['pending', 'running', 'paused', 'error', 'disabled', 'stopped']
        actual = [e.value for e in SourceStatus]
        assert sorted(actual) == sorted(expected)


class TestIngestionMode:
    """Test IngestionMode enum."""
    
    def test_all_modes(self):
        """Test all defined ingestion modes."""
        expected = ['realtime', 'batch', 'hybrid']
        actual = [e.value for e in IngestionMode]
        assert actual == expected


# =============================================================================
# HELPER FUNCTION TESTS
# =============================================================================

class TestHelperFunctions:
    """Test helper functions."""
    
    def test_create_file_source(self):
        """Test create_file_source helper."""
        source = create_file_source(
            path='/var/log/messages',
            source_id='messages-log',
            mode=IngestionMode.REALTIME,
            tags=['system']
        )
        
        assert source.source_id == 'messages-log'
        assert source.source_type == LogSourceType.FILE
        assert source.config['path'] == '/var/log/messages'
        assert source.mode == IngestionMode.REALTIME
        assert source.tags == ['system']
    
    def test_create_file_source_auto_id(self):
        """Test create_file_source with auto-generated ID."""
        source = create_file_source('/var/log/syslog')
        assert source.source_id == 'file-syslog'
        assert source.source_type == LogSourceType.FILE
    
    def test_create_syslog_source(self):
        """Test create_syslog_source helper."""
        source = create_syslog_source(
            address='0.0.0.0',
            port=514,
            protocol='tcp',
            source_id='syslog-tcp',
            tags=['network']
        )
        
        assert source.source_id == 'syslog-tcp'
        assert source.source_type == LogSourceType.SYSLOG
        assert source.config['address'] == '0.0.0.0'
        assert source.config['port'] == 514
        assert source.config['protocol'] == 'tcp'
        assert 'syslog' in source.tags
    
    def test_create_syslog_source_defaults(self):
        """Test create_syslog_source with default values."""
        source = create_syslog_source()
        assert source.config['address'] == '0.0.0.0'
        assert source.config['port'] == 514
        assert source.config['protocol'] == 'udp'
    
    def test_create_cloudtrail_source(self):
        """Test create_cloudtrail_source helper."""
        source = create_cloudtrail_source(
            bucket='my-cloudtrail-bucket',
            region='us-west-2',
            prefix='logs/',
            source_id='my-ct',
            poll_interval=600
        )
        
        assert source.source_id == 'my-ct'
        assert source.source_type == LogSourceType.CLOUD_AWS
        assert source.config['bucket'] == 'my-cloudtrail-bucket'
        assert source.config['region'] == 'us-west-2'
        assert source.config['prefix'] == 'logs/'
        assert source.config['poll_interval'] == 600
        assert 'cloudtrail' in source.tags
    
    def test_parse_timestamp_iso(self):
        """Test parsing ISO format timestamp."""
        result = parse_timestamp('2024-01-15T10:30:00Z')
        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15
    
    def test_parse_timestamp_standard(self):
        """Test parsing standard format timestamp."""
        result = parse_timestamp('2024-01-15 10:30:00')
        assert result is not None
        assert result.year == 2024
    
    def test_parse_timestamp_invalid(self):
        """Test parsing invalid timestamp."""
        result = parse_timestamp('not-a-timestamp')
        assert result is None


# =============================================================================
# DATACLASS TESTS
# =============================================================================

class TestRawLogEntry:
    """Test RawLogEntry dataclass."""
    
    def test_raw_log_entry_creation(self):
        """Test creating raw log entry."""
        entry = RawLogEntry(
            entry_id='TEST-001',
            source_id='source-001',
            raw_line='Test log message',
            timestamp=datetime(2024, 1, 15, 10, 0, 0),
            metadata={'key': 'value'}
        )
        
        assert entry.entry_id == 'TEST-001'
        assert entry.source_id == 'source-001'
        assert entry.raw_line == 'Test log message'
        assert entry.timestamp.year == 2024
        assert entry.metadata['key'] == 'value'


class TestIngestionMetrics:
    """Test IngestionMetrics dataclass."""
    
    def test_metrics_initialization(self):
        """Test metrics start at zero."""
        metrics = IngestionMetrics()
        assert metrics.lines_received == 0
        assert metrics.lines_parsed == 0
        assert metrics.events_submitted == 0
    
    def test_metrics_increment(self):
        """Test incrementing metrics."""
        metrics = IngestionMetrics()
        metrics.increment('lines_received', 10)
        assert metrics.lines_received == 10
        
        metrics.increment('lines_received')
        assert metrics.lines_received == 11
    
    def test_metrics_update_processing_time(self):
        """Test updating processing time."""
        metrics = IngestionMetrics()
        metrics.update_processing_time(100)
        metrics.update_processing_time(200)
        
        assert metrics.total_processing_time_ms == 300
        assert metrics.max_processing_time_ms == 200
    
    def test_metrics_average_latency(self):
        """Test calculating average latency."""
        metrics = IngestionMetrics()
        metrics.increment('lines_parsed', 2)
        metrics.update_processing_time(100)
        metrics.update_processing_time(200)
        
        avg = metrics.get_average_latency_ms()
        assert avg == 150.0
    
    def test_metrics_average_latency_no_events(self):
        """Test average latency with no events."""
        metrics = IngestionMetrics()
        avg = metrics.get_average_latency_ms()
        assert avg == 0.0
    
    def test_metrics_to_dict(self):
        """Test metrics serialization."""
        metrics = IngestionMetrics()
        metrics.increment('lines_received', 100)
        
        data = metrics.to_dict()
        assert data['lines_received'] == 100
        assert 'average_latency_ms' in data
        assert 'timestamp' in data


class TestSourceMetrics:
    """Test SourceMetrics dataclass."""
    
    def test_source_metrics_creation(self):
        """Test creating source metrics."""
        metrics = SourceMetrics(
            source_id='test-source',
            status=SourceStatus.RUNNING,
            lines_received=1000,
            lines_parsed=950,
            lines_failed=50
        )
        
        assert metrics.source_id == 'test-source'
        assert metrics.status == SourceStatus.RUNNING
        assert metrics.lines_received == 1000
    
    def test_source_metrics_to_dict(self):
        """Test source metrics serialization."""
        metrics = SourceMetrics(source_id='test-source')
        data = metrics.to_dict()
        
        assert data['source_id'] == 'test-source'
        assert data['status'] == 'pending'
        assert 'lines_received' in data


# =============================================================================
# INGESTION PIPELINE TESTS
# =============================================================================

@pytest.mark.asyncio
class TestIngestionPipeline:
    """Test IngestionPipeline class."""
    
    async def test_pipeline_start_stop(self, mock_detection_engine):
        """Test starting and stopping pipeline."""
        pipeline = IngestionPipeline(
            detection_engine=mock_detection_engine,
            num_workers=2
        )
        
        await pipeline.start()
        assert pipeline._running is True
        assert len(pipeline._workers) == 2
        
        await pipeline.stop()
        assert pipeline._running is False
    
    async def test_pipeline_enqueue(self, ingestion_pipeline):
        """Test enqueuing log entries."""
        entry = RawLogEntry(
            entry_id='TEST-001',
            source_id='source-001',
            raw_line='Test message',
            timestamp=datetime.utcnow()
        )
        
        result = await ingestion_pipeline.enqueue(entry)
        assert result is True
        assert ingestion_pipeline.metrics.lines_received == 1
    
    async def test_pipeline_source_registration(self, ingestion_pipeline):
        """Test registering sources for metrics."""
        ingestion_pipeline.register_source('test-source')
        ingestion_pipeline.update_source_status('test-source', SourceStatus.RUNNING)
        
        metrics = ingestion_pipeline.get_source_metrics('test-source')
        assert metrics['source_id'] == 'test-source'
        assert metrics['status'] == 'running'


# =============================================================================
# LOG INGESTION ENGINE TESTS
# =============================================================================

@pytest.mark.asyncio
class TestLogIngestionEngine:
    """Test LogIngestionEngine class."""
    
    async def test_engine_initialization(self, mock_detection_engine, tmp_path):
        """Test engine initialization."""
        engine = LogIngestionEngine(
            detection_engine=mock_detection_engine,
            data_dir=str(tmp_path)
        )
        
        assert engine.detection_engine == mock_detection_engine
        assert engine.pipeline is not None
        assert len(engine._sources) == 0
    
    async def test_add_source(self, log_ingestion_engine, sample_log_source):
        """Test adding a log source."""
        result = await log_ingestion_engine.add_source(sample_log_source)
        
        assert result is True
        assert sample_log_source.source_id in log_ingestion_engine._sources
    
    async def test_add_duplicate_source(self, log_ingestion_engine, sample_log_source):
        """Test adding duplicate source raises error."""
        await log_ingestion_engine.add_source(sample_log_source)
        
        with pytest.raises(SourceConfigurationError) as exc_info:
            await log_ingestion_engine.add_source(sample_log_source)
        
        assert 'already exists' in str(exc_info.value)
    
    async def test_remove_source(self, log_ingestion_engine, sample_log_source):
        """Test removing a log source."""
        await log_ingestion_engine.add_source(sample_log_source)
        
        result = await log_ingestion_engine.remove_source(sample_log_source.source_id)
        
        assert result is True
        assert sample_log_source.source_id not in log_ingestion_engine._sources
    
    async def test_remove_nonexistent_source(self, log_ingestion_engine):
        """Test removing non-existent source returns False."""
        result = await log_ingestion_engine.remove_source('nonexistent')
        assert result is False
    
    async def test_get_metrics(self, log_ingestion_engine):
        """Test getting engine metrics."""
        metrics = await log_ingestion_engine.get_metrics()
        
        assert 'engine_status' in metrics
        assert 'sources_total' in metrics
        assert 'pipeline_metrics' in metrics
    
    async def test_start_stop_ingestion(self, log_ingestion_engine):
        """Test starting and stopping ingestion."""
        await log_ingestion_engine.start_ingestion()
        assert log_ingestion_engine._running is True
        
        await log_ingestion_engine.stop_ingestion()
        assert log_ingestion_engine._running is False


# =============================================================================
# EXCEPTION TESTS
# =============================================================================

class TestExceptions:
    """Test custom exception classes."""
    
    def test_ingestion_error_base(self):
        """Test base ingestion error."""
        with pytest.raises(IngestionError):
            raise IngestionError("Base error")
    
    def test_source_configuration_error(self):
        """Test source configuration error."""
        with pytest.raises(SourceConfigurationError):
            raise SourceConfigurationError("Invalid config")
    
    def test_source_connection_error(self):
        """Test source connection error."""
        with pytest.raises(SourceConnectionError):
            raise SourceConnectionError("Connection failed")
    
    def test_parse_error(self):
        """Test parse error."""
        with pytest.raises(ParseError):
            raise ParseError("Parse failed")
    
    def test_exception_inheritance(self):
        """Test that all exceptions inherit from IngestionError."""
        assert issubclass(SourceConfigurationError, IngestionError)
        assert issubclass(SourceConnectionError, IngestionError)
        assert issubclass(ParseError, IngestionError)
