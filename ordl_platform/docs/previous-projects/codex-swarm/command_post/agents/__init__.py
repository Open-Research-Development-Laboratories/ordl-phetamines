#!/usr/bin/env python3
"""
ORDL Agent System
Military-grade AI agent orchestration
"""

from .agent import (
    Agent,
    AgentConfig,
    AgentStatus,
    AgentMemory,
    Tool,
    ToolRegistry,
    ToolResult,
    Task,
    TaskPriority,
    Message
)

from .manager import AgentManager, get_agent_manager

__all__ = [
    'Agent',
    'AgentConfig',
    'AgentStatus',
    'AgentMemory',
    'Tool',
    'ToolRegistry',
    'ToolResult',
    'Task',
    'TaskPriority',
    'Message',
    'AgentManager',
    'get_agent_manager'
]
