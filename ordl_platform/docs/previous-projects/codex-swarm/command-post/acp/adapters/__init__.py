#!/usr/bin/env python3
"""
ACP Protocol Adapters

Unified adapter layer for integrating multiple agent communication protocols:
- MCP (Model Context Protocol) - Anthropic
- A2A (Agent2Agent Protocol) - Google/Linux Foundation
- Agent Client Protocol - Editor/Agent communication
"""

from .base import (
    ProtocolAdapter, AdapterConfig, AdapterState,
    Capability, ExecutionRequest, ExecutionResult
)
from .mcp_adapter import MCPAdapter, MCPServerConfig
from .a2a_adapter import A2AAdapter, A2AAgentConfig
from .registry import AdapterRegistry

__all__ = [
    # Base
    'ProtocolAdapter',
    'AdapterConfig',
    'AdapterState',
    'Capability',
    'ExecutionRequest',
    'ExecutionResult',
    # MCP
    'MCPAdapter',
    'MCPServerConfig',
    # A2A
    'A2AAdapter',
    'A2AAgentConfig',
    # Registry
    'AdapterRegistry',
]
