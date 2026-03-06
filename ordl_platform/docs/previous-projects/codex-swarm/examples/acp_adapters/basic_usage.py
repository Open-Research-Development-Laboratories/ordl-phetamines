#!/usr/bin/env python3
"""
Basic Usage Examples for ACP Protocol Adapters

Demonstrates how to use MCP and A2A adapters with the ORDL NEXUS framework.
"""

import asyncio
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('examples')

# Import adapters
from command_post.acp.adapters import (
    MCPAdapter, MCPServerConfig,
    A2AAdapter, A2AAgentConfig,
    AdapterRegistry,
    ExecutionRequest
)


async def example_mcp_stdio():
    """Example: Connect to MCP filesystem server via stdio"""
    print("\n=== MCP stdio Example ===\n")
    
    # Configuration for MCP filesystem server
    config = MCPServerConfig(
        name="filesystem",
        protocol="mcp",
        transport="stdio",
        command="python",
        args=["-m", "mcp_server_filesystem", "/tmp"],
        timeout=30
    )
    
    # Create and initialize adapter
    adapter = MCPAdapter(config)
    
    try:
        success = await adapter.initialize()
        if not success:
            print("Failed to initialize MCP adapter")
            return
        
        # Discover capabilities
        capabilities = await adapter.discover_capabilities()
        print(f"Discovered {len(capabilities)} capabilities:")
        for cap in capabilities:
            print(f"  - {cap.name}: {cap.description}")
        
        # Execute a tool (if filesystem tools available)
        request = ExecutionRequest(
            capability_id="tool:list_directory",
            parameters={"path": "/tmp"}
        )
        
        result = await adapter.execute(request)
        print(f"\nExecution result:")
        print(f"  Success: {result.success}")
        print(f"  Data: {json.dumps(result.data, indent=2)[:200]}...")
        
    finally:
        await adapter.close()


async def example_mcp_http():
    """Example: Connect to MCP server via HTTP"""
    print("\n=== MCP HTTP Example ===\n")
    
    config = MCPServerConfig(
        name="remote-mcp",
        protocol="mcp",
        transport="http",
        url="https://mcp-server.example.com",
        auth_token="your-api-token",  # Or use auth_token_env
        timeout=30
    )
    
    adapter = MCPAdapter(config)
    
    try:
        success = await adapter.initialize()
        if success:
            print("MCP HTTP adapter initialized successfully")
            # ... use adapter
        else:
            print("Failed to initialize")
    finally:
        await adapter.close()


async def example_a2a_agent():
    """Example: Connect to A2A agent"""
    print("\n=== A2A Agent Example ===\n")
    
    config = A2AAgentConfig(
        name="weather-agent",
        protocol="a2a",
        url="https://weather-agent.example.com/a2a",
        streaming_enabled=True,
        timeout=60
    )
    
    adapter = A2AAdapter(config)
    
    try:
        success = await adapter.initialize()
        if not success:
            print("Failed to initialize A2A adapter")
            return
        
        # Get agent info
        info = await adapter.get_agent_info()
        print(f"Connected to agent: {info.get('name')}")
        print(f"Description: {info.get('description')}")
        
        # Discover capabilities
        capabilities = await adapter.discover_capabilities()
        print(f"\nAvailable skills ({len(capabilities)}):")
        for cap in capabilities:
            print(f"  - {cap.name}: {cap.description}")
        
        # Send a message
        request = ExecutionRequest(
            capability_id="a2a:send_message",
            parameters={"message": "What's the weather in New York?"},
            streaming=False
        )
        
        result = await adapter.execute(request)
        print(f"\nResponse:")
        print(f"  Success: {result.success}")
        if result.success:
            print(f"  Data: {json.dumps(result.data, indent=2)[:300]}...")
        else:
            print(f"  Error: {result.error}")
        
    finally:
        await adapter.close()


async def example_a2a_streaming():
    """Example: A2A streaming execution"""
    print("\n=== A2A Streaming Example ===\n")
    
    config = A2AAgentConfig(
        name="streaming-agent",
        protocol="a2a",
        url="https://agent.example.com/a2a",
        streaming_enabled=True
    )
    
    adapter = A2AAdapter(config)
    
    try:
        await adapter.initialize()
        
        request = ExecutionRequest(
            capability_id="a2a:send_message",
            parameters={"message": "Write a long story about AI"},
            streaming=True
        )
        
        print("Streaming response:")
        async for chunk in adapter.stream_execute(request):
            if chunk.success:
                # Extract text from chunk
                data = chunk.data or {}
                if 'content' in data:
                    print(data['content'], end='', flush=True)
            else:
                print(f"\nError: {chunk.error}")
                break
        
        print("\n[Stream complete]")
        
    finally:
        await adapter.close()


async def example_registry():
    """Example: Using AdapterRegistry for multiple adapters"""
    print("\n=== Adapter Registry Example ===\n")
    
    # Get global registry
    registry = AdapterRegistry()
    
    # Register MCP adapter
    mcp_config = MCPServerConfig(
        name="filesystem",
        protocol="mcp",
        transport="stdio",
        command="python",
        args=["-m", "mcp_server_filesystem", "/tmp"]
    )
    
    mcp_adapter = await registry.register(mcp_config)
    if mcp_adapter:
        print(f"Registered MCP adapter: {mcp_adapter.config.name}")
    
    # Register A2A adapter
    a2a_config = A2AAgentConfig(
        name="weather-agent",
        protocol="a2a",
        url="https://weather-agent.example.com/a2a"
    )
    
    a2a_adapter = await registry.register(a2a_config)
    if a2a_adapter:
        print(f"Registered A2A adapter: {a2a_adapter.config.name}")
    
    # List all adapters
    print(f"\nRegistered adapters: {registry.list_adapters()}")
    
    # Health check
    health = await registry.health_check()
    print(f"\nHealth status:")
    print(f"  Total: {health['total_adapters']}")
    print(f"  Ready: {health['ready_adapters']}")
    
    # Discover all capabilities
    all_caps = await registry.discover_all_capabilities()
    print(f"\nCapabilities by adapter:")
    for adapter_name, caps in all_caps.items():
        print(f"  {adapter_name}: {len(caps)} capabilities")
    
    # Execute on specific adapter
    request = ExecutionRequest(
        capability_id="tool:list_directory",
        parameters={"path": "/tmp"}
    )
    
    result = await registry.execute("filesystem", request)
    print(f"\nExecution result from filesystem adapter:")
    print(f"  Success: {result.success}")
    
    # Cleanup
    await registry.close_all()
    print("\nAll adapters closed")


async def example_configuration():
    """Example: Loading adapters from configuration"""
    print("\n=== Configuration Loading Example ===\n")
    
    from command_post.acp.adapters.config import ConfigLoader, EXAMPLE_PROFILE
    
    # Load from dictionary
    profile = ConfigLoader.from_dict(EXAMPLE_PROFILE)
    
    print(f"Profile: {profile.name}")
    print(f"Description: {profile.description}")
    print(f"Adapters: {len(profile.adapters)}")
    
    for adapter_config in profile.adapters:
        print(f"\n  - {adapter_config.name} ({adapter_config.protocol})")
        print(f"    Enabled: {adapter_config.enabled}")
        print(f"    Timeout: {adapter_config.timeout}s")


async def main():
    """Run all examples"""
    print("=" * 60)
    print("ACP Protocol Adapter Examples")
    print("=" * 60)
    
    # Note: These examples use placeholder configurations
    # Replace with actual server URLs/commands for real testing
    
    try:
        # Configuration example (works without actual servers)
        await example_configuration()
        
        # Registry example (works without actual servers)
        # await example_registry()
        
        # These require actual MCP/A2A servers:
        # await example_mcp_stdio()
        # await example_mcp_http()
        # await example_a2a_agent()
        # await example_a2a_streaming()
        
    except Exception as e:
        logger.error(f"Example failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
