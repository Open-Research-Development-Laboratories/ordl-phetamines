#!/usr/bin/env python3
"""
================================================================================
ORDL COMMAND POST v6.0.0 - PYTEST FIXTURES
================================================================================
Classification: TOP SECRET//SCI//NOFORN
Purpose: Shared test fixtures and utilities
================================================================================
"""

import os
import sys
import json
import sqlite3
import tempfile
import pytest
import asyncio
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch
from typing import Generator, Dict, Any

# Add command-post to path
sys.path.insert(0, '/opt/codex-swarm/command-post')
sys.path.insert(0, '/opt/codex-swarm/router')


# =============================================================================
# DATABASE FIXTURES
# =============================================================================

@pytest.fixture
def temp_db_path() -> Generator[str, None, None]:
    """Create temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        path = f.name
    yield path
    os.unlink(path)


@pytest.fixture
def mock_db_connection(temp_db_path: str) -> Generator[sqlite3.Connection, None, None]:
    """Provide mock database connection."""
    conn = sqlite3.connect(temp_db_path)
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


# =============================================================================
# AUTHENTICATION FIXTURES
# =============================================================================

@pytest.fixture
def test_jwt_secret() -> str:
    """Test JWT secret key."""
    return "test-jwt-secret-key-do-not-use-in-production-32chars"


@pytest.fixture
def test_nexus_token() -> str:
    """Test Nexus API token."""
    return "TEST_NEXUS_TOKEN_FOR_TESTING_ONLY_1234567890abcdef"


@pytest.fixture
def mock_auth_headers(test_nexus_token: str) -> Dict[str, str]:
    """Mock authentication headers."""
    return {
        'Authorization': f'Bearer {test_nexus_token}',
        'X-Session-ID': 'test-session-001',
        'X-Request-ID': 'test-request-001'
    }


@pytest.fixture
def mock_user_context() -> Dict[str, Any]:
    """Mock authenticated user context."""
    return {
        'codename': 'TEST_OPERATOR',
        'clearance': 'TS/SCI/NOFORN',
        'user_id': 'user-test-001',
        'session_id': 'test-session-001'
    }


# =============================================================================
# AGENT FIXTURES
# =============================================================================

@pytest.fixture
def sample_agent_config() -> Dict[str, Any]:
    """Sample agent configuration for testing."""
    return {
        'agent_id': 'test-agent-001',
        'name': 'TEST-AGENT',
        'persona': 'Test Specialist',
        'model': 'qwen2.5-coder:14b',
        'clearance': 'SECRET',
        'capabilities': ['testing', 'debugging'],
        'max_context_length': 4096,
        'temperature': 0.7,
        'top_p': 0.9,
        'max_tokens': 2048,
        'tools_enabled': ['system_time', 'system_status'],
        'auto_tool_use': True,
        'memory_enabled': True
    }


@pytest.fixture
def mock_tool_registry() -> Mock:
    """Mock tool registry for testing."""
    registry = Mock()
    registry.list_tools.return_value = [
        {'name': 'system_time', 'description': 'Get system time'},
        {'name': 'system_status', 'description': 'Get system status'}
    ]
    registry.execute_tool.return_value = Mock(
        success=True,
        result={'timestamp': datetime.utcnow().isoformat()},
        error_message=None,
        execution_time_ms=10
    )
    return registry


# =============================================================================
# BLUE TEAM FIXTURES
# =============================================================================

@pytest.fixture
def sample_alert_data() -> Dict[str, Any]:
    """Sample security alert for testing."""
    return {
        'alert_id': 'alert-test-001',
        'timestamp': datetime.utcnow().isoformat(),
        'severity': 'HIGH',
        'title': 'Test Alert',
        'description': 'This is a test alert',
        'source': 'test_source',
        'rule_name': 'BT-TEST-001',
        'rule_id': 'BT-TEST-001',
        'raw_data': {'test': 'data'},
        'status': 'OPEN'
    }


@pytest.fixture
def sample_log_entry() -> Dict[str, Any]:
    """Sample log entry for testing."""
    return {
        'timestamp': datetime.utcnow().isoformat(),
        'source_type': 'syslog',
        'source_host': 'test-host-001',
        'message': 'Failed login attempt from 192.168.1.100',
        'severity': 'WARNING'
    }


@pytest.fixture
def sample_ioc_data() -> Dict[str, Any]:
    """Sample IOC for testing."""
    return {
        'ioc_type': 'ip',
        'value': '192.168.1.100',
        'source': 'test_intel',
        'confidence': 90,
        'severity': 'HIGH',
        'description': 'Known malicious IP'
    }


# =============================================================================
# RED TEAM FIXTURES
# =============================================================================

@pytest.fixture
def sample_operation_data() -> Dict[str, Any]:
    """Sample red team operation for testing."""
    return {
        'codename': 'TEST_OP',
        'description': 'Test operation',
        'authorization_code': 'AUTH-TEST-001',
        'operator_codename': 'TEST_OPERATOR',
        'witness_codename': 'TEST_WITNESS'
    }


@pytest.fixture
def sample_target_data() -> Dict[str, Any]:
    """Sample target for testing."""
    return {
        'name': 'Test Target',
        'target_type': 'ip_address',
        'value': '192.168.1.1',
        'description': 'Test target for scanning'
    }


# =============================================================================
# RAG FIXTURES
# =============================================================================

@pytest.fixture
def sample_document() -> Dict[str, Any]:
    """Sample document for RAG testing."""
    return {
        'title': 'Test Document',
        'content': 'This is a test document for the RAG system. ' * 50,
        'category': 'test',
        'tags': ['test', 'documentation'],
        'source': 'test'
    }


@pytest.fixture
def sample_search_query() -> str:
    """Sample search query for testing."""
    return "test document content"


# =============================================================================
# MCP FIXTURES
# =============================================================================

@pytest.fixture
def mock_mcp_client() -> Mock:
    """Mock MCP client for testing."""
    client = Mock()
    client.connect.return_value = True
    client.list_tools.return_value = [
        {'name': 'github_search_repos', 'description': 'Search GitHub'},
        {'name': 'fs_read_file', 'description': 'Read file'}
    ]
    client.call_tool.return_value = {
        'content': [{'type': 'text', 'text': 'Test result'}]
    }
    client.disconnect.return_value = None
    return client


@pytest.fixture
def mcp_server_commands() -> Dict[str, list]:
    """MCP server commands for testing."""
    return {
        'github': ['npx', '-y', '@modelcontextprotocol/server-github'],
        'context7': ['npx', '-y', '@upstash/context7-mcp'],
        'playwright': ['npx', '-y', '@playwright/mcp'],
        'filesystem': ['npx', '-y', '@modelcontextprotocol/server-filesystem'],
        'fetch': ['uvx', 'mcp-server-fetch'],
        'sequential_thinking': ['npx', '-y', '@modelcontextprotocol/server-sequential-thinking']
    }


# =============================================================================
# ASYNC FIXTURES
# =============================================================================

@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# =============================================================================
# ENVIRONMENT FIXTURES
# =============================================================================

@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch):
    """Set up test environment variables."""
    monkeypatch.setenv('JWT_SECRET_KEY', 'test-jwt-secret-32-characters-long')
    monkeypatch.setenv('NEXUS_TOKEN', 'TEST_NEXUS_TOKEN_1234567890abcdef')
    monkeypatch.setenv('DATA_DIR', '/tmp/test_data')
    monkeypatch.setenv('UPLOADS_DIR', '/tmp/test_uploads')
    monkeypatch.setenv('MODELS_DIR', '/tmp/test_models')
    monkeypatch.setenv('ROUTER_URL', 'http://localhost:18000')
    monkeypatch.setenv('LOG_LEVEL', 'DEBUG')
    
    # Create test directories
    for dir_path in ['/tmp/test_data', '/tmp/test_uploads', '/tmp/test_models']:
        os.makedirs(dir_path, exist_ok=True)
    
    yield
    
    # Cleanup
    import shutil
    for dir_path in ['/tmp/test_data', '/tmp/test_uploads', '/tmp/test_models']:
        if os.path.exists(dir_path):
            shutil.rmtree(dir_path)


# =============================================================================
# UTILITY FIXTURES
# =============================================================================

@pytest.fixture
def capture_logs(caplog):
    """Capture log output for testing."""
    caplog.set_level('INFO')
    return caplog


@pytest.fixture
def temp_file() -> Generator:
    """Create temporary file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def temp_directory() -> Generator:
    """Create temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir
