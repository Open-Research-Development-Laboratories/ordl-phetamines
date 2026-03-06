#!/usr/bin/env python3
"""
================================================================================
ORDL COMMAND POST v6.0.0 - LLM INTEGRATION MODULE
================================================================================
Classification: TOP SECRET//SCI//NOFORN
Classification Level: TS/SCI/NOFORN

MILITARY-GRADE LARGE LANGUAGE MODEL INTEGRATION
================================================================================
Production-ready LLM provider system supporting:
- Ollama API (local inference - primary)
- OpenAI-compatible API (external providers)
- Function calling / Tool use with JSON schema
- Streaming responses (SSE format)
- Conversation context management with token counting
- Tool execution loop with LLM decision making
- Military-grade error handling and retry logic
- Async/await throughout for maximum performance

Author: ORDL Cyber Operations Division
Version: 6.0.0
================================================================================
"""

from .provider import (
    LLMProviderType,
    MessageRole,
    Message,
    ToolDefinition,
    LLMResponse,
    StreamingDelta,
    TokenCounter,
    LLMProvider,
    OllamaProvider,
    OpenAIProvider,
    LLMProviderFactory,
)

from .agent_bridge import LLMAgentBridge, ToolExecutionResult

__all__ = [
    'LLMProviderType',
    'MessageRole',
    'Message',
    'ToolDefinition',
    'LLMResponse',
    'StreamingDelta',
    'TokenCounter',
    'LLMProvider',
    'OllamaProvider',
    'OpenAIProvider',
    'LLMProviderFactory',
    'LLMAgentBridge',
    'ToolExecutionResult',
]
