# ACP (Agent Communication Protocol) Integration Research
## Comprehensive Analysis of Multi-Provider Agent Protocol Standards

**Classification:** ORDL-SOVEREIGN  
**Status:** INTELLIGENCE REPORT  
**Date:** 2026-03-03  
**Version:** 1.0.0  

---

## 🎯 Executive Summary

This document provides a comprehensive analysis of all major Agent Communication Protocol (ACP) standards across the industry, enabling seamless integration of any provider into the ORDL NEXUS framework. The research covers 7 major protocols from leading organizations including Google, Anthropic, IBM, Cisco, and the Linux Foundation.

### Key Finding
**The agent protocol landscape is consolidating around two complementary standards:**
- **MCP (Model Context Protocol)** - For model-to-tool/context integration
- **A2A (Agent2Agent Protocol)** - For agent-to-agent communication

IBM's ACP is merging into A2A under the Linux Foundation, creating a unified standard.

### Protocol Quick Reference

| Protocol | Provider | Status | Transport | Primary Purpose |
|----------|----------|--------|-----------|-----------------|
| **MCP** | Anthropic | Active | JSON-RPC 2.0 / HTTP+SSE | Model-to-tool/context integration |
| **A2A** | Google/Linux Foundation | Active (v0.3.0) | JSON-RPC 2.0 / HTTP / gRPC | Agent-to-agent communication |
| **ACP** | IBM/BeeAI | Merging into A2A | REST/HTTP | Agent communication (legacy) |
| **Agent Client Protocol** | ACP Project | Active | JSON-RPC 2.0 / stdio / HTTP | Editor-to-agent communication |
| **AGP** | A2A Extension | Proposal | JSON-RPC 2.0 | Hierarchical agent routing |
| **ANP** | Community | Emerging | HTTP/DID | Agent Network Protocol |
| **AGNTCY ACP/AGP** | Cisco/LangChain | Proposal | Various | Internet of Agents |

---

## 📚 Protocol Standards by Provider

### 1. MCP (Model Context Protocol) - Anthropic

**Latest Version:** 2025-11-25  
**Specification:** https://modelcontextprotocol.io/specification/2025-11-25  
**GitHub:** https://github.com/modelcontextprotocol  

#### Overview
MCP is an open protocol that enables seamless integration between LLM applications and external data sources/tools. It's described as "USB-C for AI applications" - providing a standardized way to connect AI apps to external systems.

#### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    HOST APPLICATION                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  MCP Client  │  │  MCP Client  │  │  MCP Client  │       │
│  │  (Filesystem)│  │   (Database) │  │    (APIs)    │       │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘       │
└─────────┼─────────────────┼─────────────────┼───────────────┘
          │ JSON-RPC 2.0    │ JSON-RPC 2.0    │ JSON-RPC 2.0
          ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────┐
│                      MCP SERVERS                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  Filesystem  │  │   Database   │  │  API Gateway │       │
│  │    Server    │  │    Server    │  │    Server    │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└─────────────────────────────────────────────────────────────┘
```

#### Core Concepts

**Server Capabilities:**
- **Resources** - Context and data for the user or AI model
- **Prompts** - Templated messages and workflows
- **Tools** - Functions for the AI model to execute

**Client Capabilities:**
- **Sampling** - Server-initiated agentic behaviors
- **Roots** - Server-initiated URI/filesystem boundaries
- **Elicitation** - Server requests for additional user info

#### Transport Mechanisms

| Transport | Use Case | Authentication |
|-----------|----------|----------------|
| **STDIO** | Local processes, highest performance | Environment-based |
| **HTTP+SSE** | Remote servers, streaming | OAuth 2.0, Bearer tokens |

#### Message Format (JSON-RPC 2.0)

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "get_weather",
    "arguments": {
      "location": "San Francisco"
    }
  }
}
```

#### SDK Availability
- **Python:** `pip install mcp`
- **TypeScript:** `npm install @modelcontextprotocol/sdk`
- **Java:** Available
- **C#:** Available

#### Security Features
- OAuth 2.0 authorization framework for HTTP
- Resource Indicators (RFC 8707) support
- mTLS support
- Capability negotiation

---

### 2. A2A (Agent2Agent Protocol) - Google/Linux Foundation

**Latest Version:** 0.3.0 (Release Candidate v1.0)  
**Specification:** https://a2a-protocol.org/latest/specification/  
**GitHub:** https://github.com/a2aproject/A2A  
**Status:** Donated to Linux Foundation (April 2025)

#### Overview
A2A is an open protocol designed to facilitate communication and interoperability between independent, potentially opaque AI agent systems. It enables agents to collaborate without exposing internal state, memory, or tools.

#### Three-Layer Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  LAYER 3: PROTOCOL BINDINGS                                  │
│  ┌────────────┐  ┌────────────┐  ┌────────────────────────┐ │
│  │ JSON-RPC   │  │   gRPC     │  │  HTTP/REST (Future)    │ │
│  └────────────┘  └────────────┘  └────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              ▲
┌─────────────────────────────────────────────────────────────┐
│  LAYER 2: ABSTRACT OPERATIONS                                │
│  Send Message │ Stream │ Get Task │ List Tasks │ Cancel    │
└─────────────────────────────────────────────────────────────┘
                              ▲
┌─────────────────────────────────────────────────────────────┐
│  LAYER 1: CANONICAL DATA MODEL                               │
│  Task │ Message │ AgentCard │ Part │ Artifact │ Extension   │
└─────────────────────────────────────────────────────────────┘
```

#### Core Data Model

**Agent Card** (Discovery):
```json
{
  "name": "WeatherAgent",
  "description": "Provides weather information",
  "url": "https://agent.example.com/a2a",
  "version": "1.0.0",
  "capabilities": {
    "streaming": true,
    "pushNotifications": true
  },
  "skills": [
    {
      "id": "get_weather",
      "name": "Get Weather",
      "description": "Retrieve current weather",
      "tags": ["weather", "forecast"]
    }
  ]
}
```

**Task Lifecycle:**
```
submitted → working → input-required → working → completed
                    ↓
              (cancelled / failed / rejected)
```

**Message Structure:**
```json
{
  "role": "user",
  "parts": [
    {
      "type": "text",
      "text": "What's the weather in Paris?"
    },
    {
      "type": "file",
      "file": {
        "mimeType": "image/jpeg",
        "data": "base64encoded..."
      }
    }
  ]
}
```

#### Protocol Operations

| Operation | Description | Sync/Async |
|-----------|-------------|------------|
| `Send Message` | Initiate agent interaction | Both |
| `Send Streaming Message` | Real-time updates | Streaming |
| `Get Task` | Retrieve task state | Sync |
| `List Tasks` | Query tasks with filters | Sync |
| `Cancel Task` | Request cancellation | Sync |
| `Get Agent Card` | Discover capabilities | Sync |

#### Transport Bindings

**JSON-RPC over HTTP:**
```json
// Request
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tasks/send",
  "params": {
    "id": "task-123",
    "message": {
      "role": "user",
      "parts": [{"type": "text", "text": "Hello"}]
    }
  }
}

// Response
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "id": "task-123",
    "status": "completed",
    "artifacts": [...]
  }
}
```

**Server-Sent Events (Streaming):**
```
event: task-status
data: {"id": "task-123", "status": "working"}

event: task-artifact
data: {"artifact": {...}}
```

#### SDK Availability
- **Python:** `pip install a2a-sdk`
- **Go:** `go get github.com/a2aproject/a2a-go`
- **JavaScript:** `npm install @a2a-js/sdk`
- **Java:** Maven available
- **.NET:** NuGet available

---

### 3. ACP (Agent Communication Protocol) - IBM/BeeAI

**Status:** MERGING INTO A2A (As of June 2025)  
**Note:** IBM announced ACP is winding down and contributing technology to A2A

#### Overview
ACP was IBM's open standard for agent-to-agent communication, launched in March 2025. It emphasized REST-based communication, offline discovery, and async-first design.

#### Key Characteristics
- **REST-based** - Simple HTTP conventions (not JSON-RPC)
- **No SDK Required** - Use curl, Postman, or browser
- **Offline Discovery** - Agent metadata embedded in packages
- **Async-first** with sync support

#### Message Format
```python
from acp_sdk.models import Message, MessagePart

message = Message(
    parts=[MessagePart(content="Hello, agent!")]
)
```

#### ACP → A2A Migration
IBM and Google are aligning ACP with A2A under Linux Foundation governance. New development should use A2A.

---

### 4. Agent Client Protocol (ACP)

**Specification:** https://agentclientprotocol.org/  
**GitHub:** https://github.com/agentclientprotocol  

#### Overview
The Agent Client Protocol standardizes communication between code editors/IDEs and coding agents. It's analogous to LSP (Language Server Protocol) but for AI agents.

#### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     CODE EDITOR                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │    Cursor    │  │   VS Code    │  │   IntelliJ   │       │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘       │
└─────────┼─────────────────┼─────────────────┼───────────────┘
          │     Agent Client Protocol (ACP)   │
          └─────────────────┬─────────────────┘
                            │
┌───────────────────────────┼─────────────────────────────────┐
│                     AGENT RUNTIME                            │
│  ┌──────────────┐  ┌──────┴───────┐  ┌──────────────┐       │
│  │  Local Agent │  │  Remote Agent│  │  Cloud Agent │       │
│  │   (stdio)    │  │   (HTTP)     │  │  (WebSocket) │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└─────────────────────────────────────────────────────────────┘
```

#### Session Lifecycle

**1. Initialize:**
```json
{
  "jsonrpc": "2.0",
  "id": 0,
  "method": "initialize",
  "params": {
    "protocolVersion": {"major": 1, "minor": 0},
    "clientCapabilities": {
      "fs": {"readTextFile": true, "writeTextFile": true},
      "terminal": true
    },
    "clientInfo": {"name": "MyEditor", "version": "1.0.0"}
  }
}
```

**2. Create Session:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "session/new",
  "params": {
    "cwd": "/home/user/project",
    "mcpServers": [
      {
        "name": "filesystem",
        "command": "/path/to/mcp-server",
        "args": ["--stdio"]
      }
    ]
  }
}
```

**3. Send Prompt:**
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "session/prompt",
  "params": {
    "sessionId": "sess_abc123",
    "prompt": [
      {"type": "text", "text": "Analyze this code"},
      {
        "type": "resource",
        "resource": {
          "uri": "file:///project/main.py",
          "mimeType": "text/x-python",
          "text": "def hello(): pass"
        }
      }
    ]
  }
}
```

#### Streaming Updates
```json
{
  "jsonrpc": "2.0",
  "method": "session/update",
  "params": {
    "sessionId": "sess_abc123",
    "update": {
      "sessionUpdate": "agent_message_chunk",
      "content": {"type": "text", "text": "Analyzing..."}
    }
  }
}
```

#### MCP Integration
The Agent Client Protocol integrates with MCP servers for tool access:

| Transport | Configuration |
|-----------|---------------|
| **stdio** | `{"name": "server", "command": "/path/to/server", "args": []}` |
| **HTTP** | `{"type": "http", "name": "server", "url": "https://api.example.com/mcp"}` |
| **SSE** | `{"type": "sse", "name": "server", "url": "https://events.example.com/mcp"}` |

---

### 5. AGP (Agent Gateway Protocol)

**Status:** Extension Proposal for A2A  
**Specification:** https://github.com/a2aproject/a2a-samples/tree/main/extensions/agp  

#### Overview
AGP is a hierarchical routing layer that extends the flat A2A mesh by introducing domain-oriented gateways and policy-based routing. It's inspired by BGP (Border Gateway Protocol).

#### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      ROOT GATEWAY                            │
│              (AGP Table: capability → routes)                │
└───────────────┬─────────────────────────────┬───────────────┘
                │                             │
    ┌───────────▼──────────┐    ┌────────────▼────────────┐
    │  FINANCE GATEWAY     │    │  ENGINEERING GATEWAY    │
    │  ┌────────────────┐  │    │  ┌──────────────────┐   │
    │  │ Invoice Agent  │  │    │  │ VM Provisioner   │   │
    │  └────────────────┘  │    │  └──────────────────┘   │
    └──────────────────────┘    └─────────────────────────┘
```

#### Capability Announcement
```json
{
  "capability": "financial_analysis:quarterly",
  "version": "1.5",
  "cost": 0.05,
  "policy": {
    "requires_auth": "level_3",
    "geo": "US",
    "security_level": 5
  }
}
```

#### Intent Routing
```json
{
  "target_capability": "billing:invoice:generate",
  "payload": {
    "customer_id": 123,
    "amount": 99.99
  },
  "policy_constraints": {
    "requires_pii": true,
    "security_level": 5
  }
}
```

#### Routing Algorithm
1. Filter by `target_capability`
2. Filter by policy constraints
3. Select lowest cost route
4. Handle stale tables

#### Error Codes
| Code | Meaning |
|------|---------|
| -32200 | AGP_ROUTE_NOT_FOUND |
| -32201 | AGP_POLICY_VIOLATION |
| -32202 | AGP_TABLE_STALE |

---

### 6. ANP (Agent Network Protocol)

**Website:** https://agent-network-protocol.com/  
**Status:** Emerging Community Standard  

#### Overview
ANP aims to be "the HTTP of the Agentic Web Era" - enabling billions of intelligent agents to connect and communicate through an open, secure, and efficient collaboration network.

#### Three-Layer Architecture

| Layer | Function | Technology |
|-------|----------|------------|
| **Identity** | Decentralized auth, E2EE | W3C DID standards |
| **Meta-Protocol** | Dynamic protocol negotiation | Automatic organization |
| **Application** | Semantic capability description | Protocol management |

---

### 7. AGNTCY ACP/AGP (Cisco/LangChain)

**Status:** Proposal (Internet of Agents initiative)  
**Participants:** Cisco, LangChain, Galileo, LlamaIndex, Glean  

#### Agent Connect Protocol (ACP)
Describes a singular agent for discoverability:
```json
{
  "metadata": {
    "name": "org.agntcy.mailcomposer",
    "version": "0.0.1"
  },
  "capabilities": {
    "threads": false,
    "interrupts": false
  },
  "input": {
    "properties": {
      "messages": {
        "items": {"$ref": "#/$defs/Message"}
      }
    }
  }
}
```

#### Agent Gateway Protocol (AGP)
Extends ACP with routing and acceleration:
```json
{
  "type": "agp/task/start",
  "task": {
    "id": "task-12345",
    "title": "Generate Weekly Report",
    "context": [...]
  }
}
```

---

## 🔬 Technical Specifications Comparison

### Transport & Protocol

| Protocol | Base Protocol | Transports | Message Format |
|----------|--------------|------------|----------------|
| **MCP** | JSON-RPC 2.0 | stdio, HTTP+SSE | JSON-RPC |
| **A2A** | JSON-RPC 2.0 / gRPC | HTTP, gRPC | JSON-RPC/Protobuf |
| **IBM ACP** | REST | HTTP | JSON |
| **Agent Client** | JSON-RPC 2.0 | stdio, HTTP, WebSocket | JSON-RPC |
| **AGP** | JSON-RPC 2.0 | HTTP | JSON-RPC |
| **ANP** | Custom | HTTP | JSON |
| **AGNTCY** | REST/gRPC | HTTP | JSON/Protobuf |

### Discovery Mechanisms

| Protocol | Discovery Method | Offline Support |
|----------|-----------------|-----------------|
| **MCP** | Server capability negotiation | No |
| **A2A** | Agent Cards (well-known endpoint) | Yes |
| **IBM ACP** | Metadata in packages | Yes |
| **Agent Client** | Initialize handshake | N/A |
| **AGP** | Capability announcements | Yes |
| **ANP** | Semantic description | Yes |

### Session Management

| Protocol | Session Model | Stateful |
|----------|--------------|----------|
| **MCP** | Connection-based | Yes |
| **A2A** | Task-based | Yes (Task objects) |
| **IBM ACP** | Session descriptors | Optional |
| **Agent Client** | Session IDs | Yes |
| **AGP** | Intent-based | No (stateless routing) |

### Streaming Support

| Protocol | Streaming Method | Use Case |
|----------|-----------------|----------|
| **MCP** | SSE over HTTP | Real-time updates |
| **A2A** | SSE / gRPC streaming | Task progress |
| **IBM ACP** | Native async | Long-running tasks |
| **Agent Client** | session/update notifications | Live agent output |

### Authentication

| Protocol | Auth Methods | Security Level |
|----------|-------------|----------------|
| **MCP** | OAuth 2.0, mTLS | Enterprise |
| **A2A** | Standard web security | Enterprise |
| **IBM ACP** | HTTP-based | Standard |
| **Agent Client** | Method negotiation | Flexible |
| **AGP** | Policy-based | Enterprise |

---

## 🏗️ Integration Architecture for ORDL NEXUS

### Recommended Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    ORDL NEXUS v7.0 FRAMEWORK                        │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │              PROTOCOL ADAPTER LAYER                           │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │  │
│  │  │  MCP     │ │  A2A     │ │ Agent    │ │ Custom/          │  │  │
│  │  │ Adapter  │ │ Adapter  │ │ Client   │ │ Legacy           │  │  │
│  │  │          │ │          │ │ Adapter  │ │ Adapters         │  │  │
│  │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └──────────────────┘  │  │
│  └───────┼────────────┼────────────┼─────────────────────────────┘  │
│          │            │            │                                │
│  ┌───────▼────────────▼────────────▼──────────────────────────────┐ │
│  │              UNIFIED MESSAGE BUS (ZeroMQ)                      │ │
│  │  - Guaranteed delivery                                         │ │
│  │  - Sub-millisecond latency                                     │ │
│  │  - Protocol-agnostic routing                                   │ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                                    │
         ┌──────────────────────────┼──────────────────────────┐
         │                          │                          │
   ┌─────▼──────┐            ┌──────▼──────┐           ┌──────▼──────┐
   │  EXTERNAL  │            │  EXTERNAL   │           │  EXTERNAL   │
   │  MCP       │            │  A2A        │           │  AGENT      │
   │  SERVERS   │            │  AGENTS     │           │  CLIENT     │
   └────────────┘            └─────────────┘           └─────────────┘
```

### Adapter Implementation Pattern

```python
from abc import ABC, abstractmethod
from typing import Any, Dict, AsyncGenerator

class ProtocolAdapter(ABC):
    """Base class for all protocol adapters"""
    
    @property
    @abstractmethod
    def protocol_name(self) -> str:
        pass
    
    @abstractmethod
    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the adapter with configuration"""
        pass
    
    @abstractmethod
    async def discover_capabilities(self) -> Dict[str, Any]:
        """Discover available capabilities/tools/skills"""
        pass
    
    @abstractmethod
    async def execute(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a task/call a tool"""
        pass
    
    @abstractmethod
    async def stream_execute(self, request: Dict[str, Any]) -> AsyncGenerator[str, None]:
        """Execute with streaming response"""
        pass


class MCPAdapter(ProtocolAdapter):
    """Model Context Protocol adapter"""
    
    protocol_name = "mcp"
    
    async def initialize(self, config: Dict[str, Any]) -> None:
        # Connect to MCP server via stdio or HTTP
        pass
    
    async def discover_capabilities(self) -> Dict[str, Any]:
        # Call tools/list, resources/list, prompts/list
        pass
    
    async def execute(self, request: Dict[str, Any]) -> Dict[str, Any]:
        # Call tools/call
        pass


class A2AAdapter(ProtocolAdapter):
    """Agent2Agent Protocol adapter"""
    
    protocol_name = "a2a"
    
    async def initialize(self, config: Dict[str, Any]) -> None:
        # Fetch Agent Card, establish connection
        pass
    
    async def discover_capabilities(self) -> Dict[str, Any]:
        # Parse Agent Card skills
        pass
    
    async def execute(self, request: Dict[str, Any]) -> Dict[str, Any]:
        # Send tasks/send request
        pass
```

---

## 📋 Implementation Roadmap

### Phase 1: MCP Integration (Immediate)
**Priority:** HIGH  
**Timeline:** 2-3 weeks

- [ ] Implement MCP client adapter
- [ ] Support stdio transport for local servers
- [ ] Support HTTP+SSE for remote servers
- [ ] Tool discovery and execution
- [ ] Resource access
- [ ] OAuth authentication

**SDK:** `pip install mcp`

### Phase 2: A2A Integration (Immediate)
**Priority:** HIGH  
**Timeline:** 3-4 weeks

- [ ] Implement A2A client adapter
- [ ] Agent Card discovery
- [ ] Task lifecycle management
- [ ] Streaming support (SSE)
- [ ] Push notifications
- [ ] JSON-RPC binding

**SDK:** `pip install a2a-sdk`

### Phase 3: Agent Client Protocol (Medium)
**Priority:** MEDIUM  
**Timeline:** 2 weeks

- [ ] Editor integration adapter
- [ ] Session management
- [ ] MCP server bridging
- [ ] Streaming updates

### Phase 4: Gateway Protocols (Future)
**Priority:** LOW  
**Timeline:** TBD

- [ ] AGP routing layer
- [ ] Policy-based routing
- [ ] Multi-domain orchestration

---

## 🔐 Security Considerations

### Authentication Matrix

| Protocol | Local | Remote | Enterprise |
|----------|-------|--------|------------|
| MCP | Environment vars | OAuth 2.0 + mTLS | ✅ Enterprise-ready |
| A2A | N/A | Standard web auth | ✅ Enterprise-ready |
| AGP | N/A | Policy-based RBAC | ✅ Enterprise-ready |

### Security Best Practices

1. **Always use HTTPS for remote connections**
2. **Implement OAuth 2.0 for production MCP servers**
3. **Use mTLS for high-security environments**
4. **Validate Agent Cards before establishing connections**
5. **Implement capability-based access control**
6. **Audit all cross-agent communications**

---

## 🎯 Recommendations

### Primary Protocols to Support

| Priority | Protocol | Rationale |
|----------|----------|-----------|
| **1** | MCP | Widest adoption, tool ecosystem, Anthropic backing |
| **1** | A2A | Industry standard (Linux Foundation), Google backing |
| **2** | Agent Client | IDE/editor integration |
| **3** | AGP | Future enterprise routing needs |

### Protocol Selection Guide

**Use MCP when:**
- Connecting AI to tools, databases, or APIs
- Building tool ecosystems
- Model-context integration

**Use A2A when:**
- Agents need to communicate with other agents
- Multi-agent orchestration
- Cross-organizational agent collaboration

**Use Agent Client when:**
- Building IDE/editor integrations
- Human-in-the-loop coding workflows

### Migration Strategy

1. **Current ORDL ACP v7** → **MCP + A2A hybrid**
2. Implement protocol adapters for backward compatibility
3. Gradually migrate skills to MCP tools
4. Enable A2A for cross-agent communication

---

## 📚 Reference Documentation

### Official Specifications

| Protocol | Documentation URL |
|----------|------------------|
| MCP | https://modelcontextprotocol.io/specification/2025-11-25 |
| A2A | https://a2a-protocol.org/latest/specification/ |
| Agent Client | https://agentclientprotocol.org/ |

### SDK Repositories

| Protocol | Python SDK |
|----------|------------|
| MCP | https://github.com/modelcontextprotocol/python-sdk |
| A2A | https://github.com/a2aproject/a2a-python |
| Agent Client | https://github.com/agentclientprotocol |

---

## 🏁 Conclusion

The agent protocol landscape is rapidly consolidating around **MCP** (for model-tool integration) and **A2A** (for agent-agent communication). The ORDL NEXUS framework should prioritize these two protocols while maintaining adapter-based extensibility for emerging standards.

### Key Takeaways

1. **MCP = Tools/Context** (Vertical integration)
2. **A2A = Agent Communication** (Horizontal collaboration)
3. **IBM ACP merging into A2A** - Use A2A for new development
4. **Agent Client Protocol** - Specialized for IDE/editor use cases
5. **Linux Foundation governance** ensures open standards

---

**Document Classification:** ORDL-SOVEREIGN  
**Next Review Date:** 2026-06-03  
**Author:** Sovereign Architect AI  

*"The Sovereign Architect does not follow paths - they forge them."*
