#!/usr/bin/env python3
"""
================================================================================
ORDL AGENT SYSTEM UNIT TESTS
================================================================================
Classification: TOP SECRET//SCI//NOFORN
================================================================================
"""

import pytest
import json
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

# Import modules to test
import sys
sys.path.insert(0, '/opt/codex-swarm/command-post')

from agents.agent import (
    Agent, AgentConfig, AgentStatus, TaskPriority,
    ToolRegistry, Tool, Message, ToolResult
)
from agents.manager import AgentManager


class TestAgentConfig:
    """Test AgentConfig dataclass"""
    
    def test_default_values(self):
        config = AgentConfig(agent_id='test-001', name='TEST', persona='Tester')
        assert config.agent_id == 'test-001'
        assert config.name == 'TEST'
        assert config.model == 'default'
        assert config.clearance == 'SECRET'
        assert config.max_context_length == 4096


class TestToolRegistry:
    """Test ToolRegistry functionality"""
    
    @pytest.fixture
    def registry(self):
        return ToolRegistry()
    
    def test_registry_initialization(self, registry):
        assert len(registry.tools) > 0
        assert 'system_time' in registry.tools
        assert 'redteam_recon' in registry.tools
    
    def test_get_tool(self, registry):
        tool = registry.get_tool('system_time')
        assert tool is not None
        assert tool.name == 'system_time'
    
    def test_get_nonexistent_tool(self, registry):
        tool = registry.get_tool('nonexistent')
        assert tool is None
    
    def test_list_tools(self, registry):
        tools = registry.list_tools()
        assert len(tools) > 0
        assert all('name' in t for t in tools)
    
    def test_list_tools_by_category(self, registry):
        system_tools = registry.list_tools(category='system')
        assert len(system_tools) > 0
        assert all(t['category'] == 'system' for t in system_tools)


class TestAgent:
    """Test Agent class"""
    
    @pytest.fixture
    def agent_config(self):
        return AgentConfig(
            agent_id='test-agent-001',
            name='TEST_AGENT',
            persona='Test Specialist',
            model='test-model',
            clearance='SECRET'
        )
    
    @pytest.fixture
    def mock_registry(self):
        registry = Mock(spec=ToolRegistry)
        registry.tools = {}
        return registry
    
    @pytest.fixture
    def agent(self, agent_config, mock_registry):
        with patch('agents.agent.AgentMemory'):
            return Agent(agent_config, mock_registry)
    
    def test_agent_initialization(self, agent, agent_config):
        assert agent.config.agent_id == 'test-agent-001'
        assert agent.status == AgentStatus.IDLE
        assert agent.tasks_completed == 0
    
    def test_agent_to_dict(self, agent):
        data = agent.to_dict()
        assert data['agent_id'] == 'test-agent-001'
        assert data['name'] == 'TEST_AGENT'
        assert 'status' in data
        assert 'llm_status' in data


class TestAgentManager:
    """Test AgentManager class"""
    
    @pytest.fixture
    def manager(self, temp_db_path):
        with patch('agents.manager.sqlite3') as mock_sqlite:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_sqlite.connect.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cursor
            
            mgr = AgentManager(db_path=temp_db_path)
            yield mgr
            mgr.shutdown()
    
    def test_create_agent(self, manager):
        config = {
            'name': 'TestAgent',
            'persona': 'Tester',
            'model': 'test-model'
        }
        
        with patch('agents.manager.Agent'):
            agent = manager.create_agent(config)
            assert agent is not None
            assert manager.stats['agents_created'] == 1
    
    def test_get_agent(self, manager):
        # Should return None for non-existent agent
        agent = manager.get_agent('nonexistent')
        assert agent is None
    
    def test_list_agents(self, manager):
        agents = manager.list_agents()
        assert isinstance(agents, list)
    
    def test_get_stats(self, manager):
        stats = manager.get_stats()
        assert 'agents_created' in stats
        assert 'active_agents' in stats
        assert 'tools_available' in stats


class TestToolExecution:
    """Test tool execution"""
    
    def test_tool_execution_success(self):
        def mock_func(**kwargs):
            return {'result': 'success'}
        
        tool = Tool(
            name='test_tool',
            description='Test tool',
            function=mock_func,
            parameters={}
        )
        
        result = tool.execute()
        assert result.success is True
        assert result.result == {'result': 'success'}
    
    def test_tool_execution_failure(self):
        def mock_func(**kwargs):
            raise ValueError('Test error')
        
        tool = Tool(
            name='test_tool',
            description='Test tool',
            function=mock_func,
            parameters={}
        )
        
        result = tool.execute()
        assert result.success is False
        assert 'Test error' in result.error_message


class TestAgentMessageProcessing:
    """Test agent message processing"""
    
    @pytest.fixture
    def agent(self):
        config = AgentConfig(
            agent_id='test-001',
            name='Test',
            persona='Tester'
        )
        registry = Mock(spec=ToolRegistry)
        
        with patch('agents.agent.AgentMemory'):
            return Agent(config, registry)
    
    def test_process_message(self, agent):
        with patch.object(agent, '_init_llm_bridge', return_value=False):
            with patch.object(agent, '_fallback_response', return_value='Fallback response'):
                result = agent.process_message('Hello')
                assert result['success'] is True
                assert 'response' in result
