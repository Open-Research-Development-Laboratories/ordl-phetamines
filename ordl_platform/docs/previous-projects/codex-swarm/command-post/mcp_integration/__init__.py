#!/usr/bin/env python3
"""
ORDL MCP Integration Module
===========================
Provides MCP client and tool registry for AI agent integration.
"""

# Use the new v2 implementation with proper JSON-RPC
from .tools_v2 import MCPToolRegistry, get_mcp_registry, MCPResult
from .client import MCPClient, MCPClientPool, get_mcp_pool

__all__ = [
    'MCPToolRegistry',
    'get_mcp_registry',
    'MCPResult',
    'MCPClient',
    'MCPClientPool',
    'get_mcp_pool'
]
