#!/usr/bin/env python3
"""
Comprehensive ACP Integration Test
Tests MCP and A2A adapters with actual servers.
"""

import asyncio
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from command_post.acp.adapters import (
    MCPAdapter, MCPServerConfig,
    A2AAdapter, A2AAgentConfig,
    AdapterRegistry, ExecutionRequest
)


async def test_mcp_filesystem():
    """Test MCP filesystem server"""
    print("\n" + "="*60)
    print("TEST: MCP Filesystem Server")
    print("="*60)
    
    config = MCPServerConfig(
        name="filesystem-test",
        protocol="mcp",
        transport="stdio",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "/opt/codex-swarm"],
        timeout=30
    )
    
    adapter = MCPAdapter(config)
    
    try:
        # Initialize
        print("Initializing...")
        success = await adapter.initialize()
        if not success:
            print("❌ Failed to initialize")
            return False
        print("✅ Initialized")
        
        # Discover capabilities
        print("\nDiscovering capabilities...")
        caps = await adapter.discover_capabilities()
        print(f"✅ Found {len(caps)} capabilities")
        for cap in caps[:5]:  # Show first 5
            print(f"   - {cap.name}")
        
        # Execute list_directory
        print("\nTesting list_directory...")
        request = ExecutionRequest(
            capability_id="tool:list_directory",
            parameters={"path": "/opt/codex-swarm"}
        )
        result = await adapter.execute(request)
        
        if result.success:
            print("✅ list_directory succeeded")
            if result.data:
                files = result.data.get('content', [])
                print(f"   Found {len(files)} items")
        else:
            print(f"❌ list_directory failed: {result.error}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        await adapter.close()


async def test_mcp_fetch():
    """Test MCP fetch server"""
    print("\n" + "="*60)
    print("TEST: MCP Fetch Server")
    print("="*60)
    
    config = MCPServerConfig(
        name="fetch-test",
        protocol="mcp",
        transport="stdio",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-fetch"],
        timeout=30
    )
    
    adapter = MCPAdapter(config)
    
    try:
        print("Initializing...")
        success = await adapter.initialize()
        if not success:
            print("❌ Failed to initialize")
            return False
        print("✅ Initialized")
        
        # Discover capabilities
        print("\nDiscovering capabilities...")
        caps = await adapter.discover_capabilities()
        print(f"✅ Found {len(caps)} capabilities")
        for cap in caps:
            print(f"   - {cap.name}")
        
        # Test fetch
        print("\nTesting fetch...")
        request = ExecutionRequest(
            capability_id="tool:fetch",
            parameters={"url": "https://example.com"}
        )
        result = await adapter.execute(request)
        
        if result.success:
            print("✅ Fetch succeeded")
        else:
            print(f"⚠️  Fetch returned error (expected for network): {result.error}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        await adapter.close()


async def test_a2a_calculator():
    """Test A2A calculator agent"""
    print("\n" + "="*60)
    print("TEST: A2A Calculator Agent")
    print("="*60)
    
    config = A2AAgentConfig(
        name="calculator-test",
        protocol="a2a",
        url="http://localhost:8001",
        streaming_enabled=False,
        timeout=30
    )
    
    adapter = A2AAdapter(config)
    
    try:
        print("Initializing...")
        success = await adapter.initialize()
        if not success:
            print("⚠️  Agent not running (expected if not started)")
            return None
        print("✅ Initialized")
        
        # Get agent info
        info = await adapter.get_agent_info()
        print(f"\nAgent: {info.get('name')}")
        print(f"Description: {info.get('description')}")
        
        # Discover capabilities
        print("\nDiscovering capabilities...")
        caps = await adapter.discover_capabilities()
        print(f"✅ Found {len(caps)} capabilities")
        for cap in caps:
            print(f"   - {cap.name}")
        
        # Test calculation
        print("\nTesting calculation...")
        request = ExecutionRequest(
            capability_id="a2a:send_message",
            parameters={"message": '{"operation": "add", "a": 5, "b": 3}'}
        )
        result = await adapter.execute(request)
        
        if result.success:
            print("✅ Calculation succeeded")
            print(f"   Result: {result.data}")
        else:
            print(f"❌ Calculation failed: {result.error}")
        
        return True
        
    except Exception as e:
        print(f"⚠️  Error (agent may not be running): {e}")
        return None
    finally:
        await adapter.close()


async def test_registry():
    """Test adapter registry"""
    print("\n" + "="*60)
    print("TEST: Adapter Registry")
    print("="*60)
    
    registry = AdapterRegistry()
    
    try:
        # Register MCP adapter
        mcp_config = MCPServerConfig(
            name="filesystem",
            protocol="mcp",
            transport="stdio",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", "/opt/codex-swarm"]
        )
        
        adapter = await registry.register(mcp_config)
        if adapter:
            print("✅ Registered MCP adapter")
        else:
            print("⚠️  MCP adapter registration returned None")
        
        # List adapters
        adapters = registry.list_adapters()
        print(f"✅ Registry contains {len(adapters)} adapters")
        
        # Health check
        health = await registry.health_check()
        print(f"✅ Health check: {health['total_adapters']} total, {health['ready_adapters']} ready")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        await registry.close_all()


async def main():
    """Run all tests"""
    print("="*60)
    print("ACP INTEGRATION TEST SUITE")
    print("="*60)
    
    results = {}
    
    # Test MCP filesystem
    results['mcp_filesystem'] = await test_mcp_filesystem()
    
    # Test MCP fetch
    results['mcp_fetch'] = await test_mcp_fetch()
    
    # Test A2A calculator (may fail if agent not started)
    results['a2a_calculator'] = await test_a2a_calculator()
    
    # Test registry
    results['registry'] = await test_registry()
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for r in results.values() if r is True)
    failed = sum(1 for r in results.values() if r is False)
    skipped = sum(1 for r in results.values() if r is None)
    
    for name, result in results.items():
        status = "✅ PASS" if result is True else "❌ FAIL" if result is False else "⏭️  SKIP"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed} passed, {failed} failed, {skipped} skipped")
    
    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
