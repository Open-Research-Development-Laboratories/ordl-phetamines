#!/usr/bin/env python3
"""
Unit Tests for ACP Protocol Adapters

Tests for MCPAdapter, A2AAdapter, and AdapterRegistry.
Note: Async tests are run synchronously without pytest-asyncio.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import adapters
from command_post.acp.adapters import (
    MCPAdapter, MCPServerConfig,
    A2AAdapter, A2AAgentConfig,
    AdapterRegistry, AdapterState,
    ExecutionRequest, ExecutionResult,
    Capability
)
from command_post.acp.adapters.config import ConfigLoader, ConfigValidator


def run_async(coro):
    """Helper to run async functions in sync tests"""
    return asyncio.get_event_loop().run_until_complete(coro)


# =============================================================================
# MCP Adapter Tests
# =============================================================================

class TestMCPAdapter:
    """Tests for MCPAdapter"""
    
    def test_adapter_creation(self):
        """Test MCP adapter creation"""
        config = MCPServerConfig(
            name="test-mcp",
            protocol="mcp",
            transport="stdio",
            command="echo",
            args=["test"],
            timeout=5
        )
        adapter = MCPAdapter(config)
        assert adapter.config.name == "test-mcp"
        assert adapter.protocol_name == "mcp"
        assert adapter.state == AdapterState.UNINITIALIZED
        assert not adapter.is_ready
    
    def test_protocol_properties(self):
        """Test protocol name and version properties"""
        config = MCPServerConfig(
            name="test-mcp",
            protocol="mcp",
            transport="stdio",
            command="echo"
        )
        adapter = MCPAdapter(config)
        assert adapter.protocol_name == "mcp"
        assert adapter.protocol_version == "2025-11-25"
    
    def test_health_check_uninitialized(self):
        """Test health check before initialization"""
        config = MCPServerConfig(
            name="test-mcp",
            protocol="mcp",
            transport="stdio",
            command="echo"
        )
        adapter = MCPAdapter(config)
        health = run_async(adapter.health_check())
        
        assert health['name'] == "test-mcp"
        assert health['protocol'] == "mcp"
        assert health['state'] == "uninitialized"
        assert not health['ready']


# =============================================================================
# A2A Adapter Tests
# =============================================================================

class TestA2AAdapter:
    """Tests for A2AAdapter"""
    
    def test_adapter_creation(self):
        """Test A2A adapter creation"""
        config = A2AAgentConfig(
            name="test-a2a",
            protocol="a2a",
            url="https://test-agent.example.com/a2a",
            timeout=5
        )
        adapter = A2AAdapter(config)
        assert adapter.config.name == "test-a2a"
        assert adapter.protocol_name == "a2a"
        assert adapter.state == AdapterState.UNINITIALIZED
    
    def test_protocol_properties(self):
        """Test protocol name and version properties"""
        config = A2AAgentConfig(
            name="test-a2a",
            protocol="a2a",
            url="https://test-agent.example.com/a2a"
        )
        adapter = A2AAdapter(config)
        assert adapter.protocol_name == "a2a"
        assert adapter.protocol_version == "0.3.0"
    
    def test_build_message(self):
        """Test message building from execution request"""
        config = A2AAgentConfig(
            name="test-a2a",
            protocol="a2a",
            url="https://test-agent.example.com/a2a"
        )
        adapter = A2AAdapter(config)
        
        request = ExecutionRequest(
            capability_id="a2a:send_message",
            parameters={"message": "Hello, agent!"}
        )
        
        message = adapter._build_message(request)
        
        assert message['role'] == 'user'
        assert len(message['parts']) == 1
        assert message['parts'][0]['type'] == 'text'
        assert message['parts'][0]['text'] == "Hello, agent!"
    
    def test_build_message_with_files(self):
        """Test message building with file attachments"""
        config = A2AAgentConfig(
            name="test-a2a",
            protocol="a2a",
            url="https://test-agent.example.com/a2a"
        )
        adapter = A2AAdapter(config)
        
        request = ExecutionRequest(
            capability_id="a2a:send_message",
            parameters={
                "message": "Analyze this",
                "files": [
                    {"mimeType": "image/png", "data": "base64data", "name": "test.png"}
                ]
            }
        )
        
        message = adapter._build_message(request)
        
        assert len(message['parts']) == 2
        assert message['parts'][0]['type'] == 'text'
        assert message['parts'][1]['type'] == 'file'


# =============================================================================
# Adapter Registry Tests
# =============================================================================

class TestAdapterRegistry:
    """Tests for AdapterRegistry"""
    
    def test_registry_creation(self):
        """Test registry initialization"""
        registry = AdapterRegistry()
        assert registry.list_adapters() == []
        assert registry.get("nonexistent") is None
    
    def test_register_adapter_type(self):
        """Test registering custom adapter types"""
        registry = AdapterRegistry()
        
        class MockAdapter:
            pass
        
        registry.register_adapter_type("mock", MockAdapter)
        assert "mock" in registry._adapter_types
    
    def test_get_by_protocol(self):
        """Test getting adapters by protocol"""
        registry = AdapterRegistry()
        
        # Create mock adapter
        mock_adapter = type('MockAdapter', (), {'protocol_name': 'mcp'})()
        
        registry._adapters["test1"] = mock_adapter
        registry._adapters["test2"] = mock_adapter
        
        mcp_adapters = registry.get_by_protocol("mcp")
        assert len(mcp_adapters) == 2
    
    def test_health_check_empty(self):
        """Test health check with no adapters"""
        registry = AdapterRegistry()
        health = run_async(registry.health_check())
        
        assert health['registry_status'] == 'healthy'
        assert health['total_adapters'] == 0
        assert health['ready_adapters'] == 0


# =============================================================================
# Configuration Tests
# =============================================================================

class TestConfigLoader:
    """Tests for ConfigLoader"""
    
    def test_from_dict_mcp(self):
        """Test loading MCP config from dict"""
        data = {
            "name": "test-profile",
            "adapters": [
                {
                    "name": "filesystem",
                    "protocol": "mcp",
                    "transport": "stdio",
                    "command": "python",
                    "args": ["-m", "server"],
                    "timeout": 30
                }
            ]
        }
        
        profile = ConfigLoader.from_dict(data)
        
        assert profile.name == "test-profile"
        assert len(profile.adapters) == 1
        
        adapter = profile.adapters[0]
        assert isinstance(adapter, MCPServerConfig)
        assert adapter.name == "filesystem"
        assert adapter.transport == "stdio"
        assert adapter.command == "python"
    
    def test_from_dict_a2a(self):
        """Test loading A2A config from dict"""
        data = {
            "name": "test-profile",
            "adapters": [
                {
                    "name": "weather-agent",
                    "protocol": "a2a",
                    "url": "https://agent.example.com",
                    "streaming_enabled": True
                }
            ]
        }
        
        profile = ConfigLoader.from_dict(data)
        
        assert len(profile.adapters) == 1
        
        adapter = profile.adapters[0]
        assert isinstance(adapter, A2AAgentConfig)
        assert adapter.name == "weather-agent"
        assert adapter.url == "https://agent.example.com"
        assert adapter.streaming_enabled


class TestConfigValidator:
    """Tests for ConfigValidator"""
    
    def test_validate_valid_mcp_stdio(self):
        """Test validating valid MCP stdio config"""
        config = MCPServerConfig(
            name="test",
            protocol="mcp",
            transport="stdio",
            command="python",
            args=["server.py"]
        )
        
        errors = ConfigValidator.validate_mcp_config(config)
        assert len(errors) == 0
    
    def test_validate_mcp_missing_command(self):
        """Test validating MCP stdio without command"""
        config = MCPServerConfig(
            name="test",
            protocol="mcp",
            transport="stdio"
        )
        
        errors = ConfigValidator.validate_mcp_config(config)
        assert len(errors) == 1
        assert "requires command" in errors[0]
    
    def test_validate_mcp_missing_url(self):
        """Test validating MCP HTTP without URL"""
        config = MCPServerConfig(
            name="test",
            protocol="mcp",
            transport="http"
        )
        
        errors = ConfigValidator.validate_mcp_config(config)
        assert len(errors) == 1
        assert "requires URL" in errors[0]
    
    def test_validate_valid_a2a(self):
        """Test validating valid A2A config"""
        config = A2AAgentConfig(
            name="test",
            protocol="a2a",
            url="https://agent.example.com"
        )
        
        errors = ConfigValidator.validate_a2a_config(config)
        assert len(errors) == 0
    
    def test_validate_a2a_missing_url(self):
        """Test validating A2A without URL"""
        config = A2AAgentConfig(
            name="test",
            protocol="a2a"
        )
        
        errors = ConfigValidator.validate_a2a_config(config)
        assert len(errors) == 1
        assert "requires URL" in errors[0]


# =============================================================================
# Integration Tests
# =============================================================================

class TestAdapterIntegration:
    """Integration tests for adapter system"""
    
    def test_full_lifecycle(self):
        """Test complete adapter lifecycle"""
        registry = AdapterRegistry()
        
        # This test would require actual MCP/A2A servers
        # For now, just test the registry operations
        
        health = run_async(registry.health_check())
        assert health['total_adapters'] == 0
        
        # Cleanup
        run_async(registry.close_all())
    
    def test_capability_discovery_flow(self):
        """Test capability discovery across adapters"""
        registry = AdapterRegistry()
        
        # Mock capabilities
        all_caps = run_async(registry.discover_all_capabilities())
        assert isinstance(all_caps, dict)
        
        run_async(registry.close_all())


# =============================================================================
# Execution Request/Result Tests
# =============================================================================

class TestExecutionTypes:
    """Tests for ExecutionRequest and ExecutionResult"""
    
    def test_execution_request_creation(self):
        """Test creating execution request"""
        request = ExecutionRequest(
            capability_id="tool:test",
            parameters={"arg1": "value1"},
            context={"session": "123"},
            streaming=True,
            timeout=60
        )
        
        assert request.capability_id == "tool:test"
        assert request.parameters["arg1"] == "value1"
        assert request.context["session"] == "123"
        assert request.streaming
        assert request.timeout == 60
    
    def test_execution_result_success(self):
        """Test successful execution result"""
        result = ExecutionResult(
            success=True,
            data={"result": "ok"},
            execution_time=1.5
        )
        
        assert result.success
        assert result.data["result"] == "ok"
        assert result.execution_time == 1.5
        assert result.error is None
    
    def test_execution_result_failure(self):
        """Test failed execution result"""
        result = ExecutionResult(
            success=False,
            error="Something went wrong",
            execution_time=0.5
        )
        
        assert not result.success
        assert result.error == "Something went wrong"
        assert result.data is None


# =============================================================================
# Capability Tests
# =============================================================================

class TestCapability:
    """Tests for Capability dataclass"""
    
    def test_capability_creation(self):
        """Test creating capability"""
        cap = Capability(
            id="tool:read_file",
            name="Read File",
            description="Reads a file from disk",
            parameters={"path": {"type": "string"}},
            returns={"content": {"type": "string"}},
            metadata={"category": "filesystem"}
        )
        
        assert cap.id == "tool:read_file"
        assert cap.name == "Read File"
        assert cap.metadata["category"] == "filesystem"


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    import sys
    
    # Run all tests
    print("=" * 60)
    print("Running ACP Adapter Tests")
    print("=" * 60)
    
    test_classes = [
        TestMCPAdapter,
        TestA2AAdapter,
        TestAdapterRegistry,
        TestConfigLoader,
        TestConfigValidator,
        TestAdapterIntegration,
        TestExecutionTypes,
        TestCapability
    ]
    
    passed = 0
    failed = 0
    
    for test_class in test_classes:
        print(f"\n{test_class.__name__}:")
        instance = test_class()
        
        for method_name in dir(instance):
            if method_name.startswith('test_'):
                try:
                    method = getattr(instance, method_name)
                    method()
                    print(f"  ✓ {method_name}")
                    passed += 1
                except Exception as e:
                    print(f"  ✗ {method_name}: {e}")
                    failed += 1
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    sys.exit(0 if failed == 0 else 1)
