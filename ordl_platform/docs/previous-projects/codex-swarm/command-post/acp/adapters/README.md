# ACP Protocol Adapters

Unified adapter layer for integrating multiple agent communication protocols into the ORDL NEXUS framework.

## Supported Protocols

| Protocol | Provider | Status | Purpose |
|----------|----------|--------|---------|
| **MCP** | Anthropic | ✅ Active | Model Context Protocol - Tool/Resource integration |
| **A2A** | Google/Linux Foundation | ✅ Active | Agent2Agent Protocol - Agent communication |

## Quick Start

### 1. MCP Adapter (Model Context Protocol)

Connect to MCP servers for tool access:

```python
from command_post.acp.adapters import MCPAdapter, MCPServerConfig, ExecutionRequest

# Configure MCP filesystem server
config = MCPServerConfig(
    name="filesystem",
    protocol="mcp",
    transport="stdio",  # or "http"
    command="python",
    args=["-m", "mcp_server_filesystem", "/allowed/path"],
    timeout=30
)

# Create and use adapter
adapter = MCPAdapter(config)
await adapter.initialize()

# Discover capabilities
capabilities = await adapter.discover_capabilities()

# Execute a tool
request = ExecutionRequest(
    capability_id="tool:list_directory",
    parameters={"path": "/allowed/path"}
)
result = await adapter.execute(request)

await adapter.close()
```

### 2. A2A Adapter (Agent2Agent Protocol)

Connect to A2A agents for agent-to-agent communication:

```python
from command_post.acp.adapters import A2AAdapter, A2AAgentConfig, ExecutionRequest

# Configure A2A agent
config = A2AAgentConfig(
    name="weather-agent",
    protocol="a2a",
    url="https://weather-agent.example.com/a2a",
    streaming_enabled=True
)

# Create and use adapter
adapter = A2AAdapter(config)
await adapter.initialize()

# Get agent info
info = await adapter.get_agent_info()
print(f"Connected to: {info['name']}")

# Send message (non-streaming)
request = ExecutionRequest(
    capability_id="a2a:send_message",
    parameters={"message": "What's the weather in NYC?"}
)
result = await adapter.execute(request)

# Or stream the response
async for chunk in adapter.stream_execute(request):
    print(chunk.data)

await adapter.close()
```

### 3. Using the Registry

Manage multiple adapters with the registry:

```python
from command_post.acp.adapters import AdapterRegistry

# Get global registry
registry = AdapterRegistry()

# Register adapters
mcp_adapter = await registry.register(mcp_config)
a2a_adapter = await registry.register(a2a_config)

# Discover all capabilities
all_caps = await registry.discover_all_capabilities()

# Execute on specific adapter
result = await registry.execute("filesystem", request)

# Or find adapter by capability
result = await registry.execute_by_capability("tool:read_file", request)

# Health check
health = await registry.health_check()

# Cleanup
await registry.close_all()
```

## Configuration

### YAML Configuration

```yaml
name: production
description: Production adapter configuration
defaults:
  timeout: 30
  retry_count: 3

adapters:
  - name: filesystem
    protocol: mcp
    transport: stdio
    command: python
    args: ["-m", "mcp_server_filesystem", "/data"]
    env:
      DEBUG: "1"
  
  - name: weather-agent
    protocol: a2a
    url: https://weather.example.com/a2a
    auth_token_env: WEATHER_API_TOKEN
    streaming_enabled: true
```

Load configuration:

```python
from command_post.acp.adapters.config import ConfigLoader

profile = ConfigLoader.from_yaml("config.yaml")

for adapter_config in profile.adapters:
    await registry.register(adapter_config)
```

### Environment Variables

Sensitive configuration can be loaded from environment variables:

```yaml
adapters:
  - name: secure-agent
    protocol: a2a
    url: https://agent.example.com
    auth_token_env: AGENT_AUTH_TOKEN  # Loads from $AGENT_AUTH_TOKEN
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    AdapterRegistry                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  MCPAdapter  │  │  A2AAdapter  │  │  Future...   │       │
│  │  (stdio/HTTP)│  │  (JSON-RPC)  │  │              │       │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘       │
└─────────┼─────────────────┼─────────────────┼───────────────┘
          │                 │                 │
    ┌─────▼──────┐    ┌────▼─────┐     ┌────▼─────┐
    │ MCP Server │    │ A2A Agent│     │  etc...  │
    └────────────┘    └──────────┘     └──────────┘
```

## Adapter Interface

All adapters implement the `ProtocolAdapter` interface:

```python
class ProtocolAdapter(ABC):
    @property
    @abstractmethod
    def protocol_name(self) -> str: ...
    
    @abstractmethod
    async def initialize(self) -> bool: ...
    
    @abstractmethod
    async def close(self) -> None: ...
    
    @abstractmethod
    async def discover_capabilities(self) -> List[Capability]: ...
    
    @abstractmethod
    async def execute(self, request: ExecutionRequest) -> ExecutionResult: ...
    
    @abstractmethod
    async def stream_execute(self, request: ExecutionRequest) 
        -> AsyncGenerator[ExecutionResult, None]: ...
```

## Testing

Run tests:

```bash
cd /opt/codex-swarm
python -m pytest tests/test_acp_adapters.py -v
```

Run examples:

```bash
python examples/acp_adapters/basic_usage.py
```

## Protocol Specifications

- **MCP**: https://modelcontextprotocol.io/specification/2025-11-25
- **A2A**: https://a2a-protocol.org/latest/specification/

## Adding New Protocols

To add support for a new protocol:

1. Create a new adapter class inheriting from `ProtocolAdapter`
2. Implement all abstract methods
3. Register the adapter type:

```python
from command_post.acp.adapters import AdapterRegistry

registry = AdapterRegistry()
registry.register_adapter_type("myprotocol", MyProtocolAdapter)
```

## License

ORDL - Open Research and Development Laboratories
