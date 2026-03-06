#!/usr/bin/env python3
"""
ORDL LLM Provider System
Military-grade LLM integration with multiple provider support
"""

import os
import sys
import json
import logging
from typing import Dict, Any, List, Optional, AsyncIterator, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import asyncio
import aiohttp
from abc import ABC, abstractmethod

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger('llm.provider')


class LLMProviderType(Enum):
    """Supported LLM provider types"""
    OLLAMA = "ollama"
    OPENAI = "openai"


class MessageRole(Enum):
    """Message roles for conversation"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class Message:
    """Conversation message"""
    role: MessageRole
    content: str
    tool_calls: Optional[List[Dict]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to API-compatible dictionary"""
        result = {
            "role": self.role.value,
            "content": self.content
        }
        if self.tool_calls:
            result["tool_calls"] = self.tool_calls
        if self.tool_call_id:
            result["tool_call_id"] = self.tool_call_id
        if self.name:
            result["name"] = self.name
        return result


@dataclass
class ToolDefinition:
    """Tool definition for function calling"""
    name: str
    description: str
    parameters: Dict[str, Any]
    required: List[str] = field(default_factory=list)
    
    def to_openai_schema(self) -> Dict[str, Any]:
        """Convert to OpenAI function schema"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": self.parameters,
                    "required": self.required
                }
            }
        }


@dataclass
class LLMResponse:
    """LLM response with metadata"""
    content: str
    tool_calls: List[Dict]
    model: str
    usage: Union[Dict[str, int], int]
    finish_reason: str
    latency_ms: int
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class StreamingDelta:
    """Streaming response delta"""
    content: Optional[str] = None
    tool_calls: Optional[List[Dict]] = None
    finish_reason: Optional[str] = None


class TokenCounter:
    """Estimate token counts for context management"""
    
    CHARS_PER_TOKEN = 4
    
    @classmethod
    def count_tokens(cls, text: str) -> int:
        """Estimate token count (rough approximation)"""
        return len(text) // cls.CHARS_PER_TOKEN
    
    @classmethod
    def count_message_tokens(cls, messages: List[Message]) -> int:
        """Count tokens in message list"""
        total = 0
        for msg in messages:
            total += cls.count_tokens(msg.content)
            total += 4  # Overhead for role and formatting
        return total


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    def __init__(self, model: str, temperature: float = 0.7, max_tokens: int = 4096):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session"""
        # Always create a new session to avoid event loop issues
        import aiohttp
        return aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=300),
            headers={"Content-Type": "application/json"}
        )
    
    async def _close_session(self, session: aiohttp.ClientSession):
        """Close session properly"""
        try:
            if session and not session.closed:
                await session.close()
        except Exception as e:
            logger.debug(f"[LLM] Error closing session: {e}")
    
    @abstractmethod
    async def complete(self, messages: List[Message], tools: Optional[List[ToolDefinition]] = None) -> LLMResponse:
        """Generate completion"""
        pass
    
    @abstractmethod
    async def complete_stream(self, messages: List[Message], tools: Optional[List[ToolDefinition]] = None) -> AsyncIterator[StreamingDelta]:
        """Generate streaming completion"""
        pass
    
    async def close(self):
        """Close HTTP session"""
        if self.session and not self.session.closed:
            await self.session.close()


class OllamaProvider(LLMProvider):
    """
    Ollama API provider for local LLM inference
    Supports native tool calling and streaming
    """
    
    def __init__(self, 
                 model: str = "llama3.3",
                 base_url: str = "http://localhost:11434",
                 temperature: float = 0.7,
                 max_tokens: int = 4096):
        super().__init__(model, temperature, max_tokens)
        self.base_url = base_url.rstrip('/')
        self.api_chat = f"{self.base_url}/api/chat"
        self._available_models: List[str] = []
    
    async def _check_model(self) -> bool:
        """Check if model is available, pull if not"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/api/tags") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        models = [m['name'] for m in data.get('models', [])]
                        self._available_models = models
                        if any(self.model in m for m in models):
                            return True
                        
                        # Model not found, try to pull
                        logger.info(f"[LLM] Pulling model: {self.model}")
                        async with session.post(
                            f"{self.base_url}/api/pull",
                            json={"name": self.model, "stream": False}
                        ) as pull_resp:
                            if pull_resp.status == 200:
                                logger.info(f"[LLM] Model {self.model} pulled")
                                return True
            return False
        except Exception as e:
            logger.error(f"[LLM] Model check failed: {e}")
            return False
    
    async def complete(self, messages: List[Message], tools: Optional[List[ToolDefinition]] = None) -> LLMResponse:
        """Generate completion using Ollama chat API with proper error handling"""
        import aiohttp
        start_time = asyncio.get_event_loop().time()
        session = None
        
        try:
            if not await self._check_model():
                raise RuntimeError(f"Model {self.model} not available")
            
            ollama_messages = [
                {"role": msg.role.value, "content": msg.content}
                for msg in messages
            ]
            
            payload = {
                "model": self.model,
                "messages": ollama_messages,
                "stream": False,
                "options": {
                    "temperature": self.temperature,
                    "num_predict": self.max_tokens
                }
            }
            
            if tools:
                payload["tools"] = [t.to_openai_schema()["function"] for t in tools]
            
            session = await self._get_session()
            
            try:
                async with session.post(self.api_chat, json=payload) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        raise RuntimeError(f"Ollama API error: {resp.status} - {error_text}")
                    
                    data = await resp.json()
            finally:
                # Ensure session is closed
                await self._close_session(session)
                session = None
            
            latency_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
            
            message = data.get("message", {})
            content = message.get("content", "")
            tool_calls = message.get("tool_calls", [])
            
            # Validate content
            if not isinstance(content, str):
                logger.warning(f"[LLM] Unexpected content type: {type(content)}")
                content = str(content) if content else ""
            
            formatted_tool_calls = []
            if tool_calls:
                for i, tc in enumerate(tool_calls):
                    try:
                        formatted_tool_calls.append({
                            "id": f"call_{i}",
                            "type": "function",
                            "function": {
                                "name": tc.get("function", {}).get("name", ""),
                                "arguments": json.dumps(tc.get("function", {}).get("arguments", {}))
                            }
                        })
                    except Exception as e:
                        logger.error(f"[LLM] Error formatting tool call: {e}")
            
            usage = data.get("prompt_eval_count", 0) + data.get("eval_count", 0)
            
            return LLMResponse(
                content=content,
                tool_calls=formatted_tool_calls,
                model=self.model,
                usage=usage,
                finish_reason="stop" if not tool_calls else "tool_calls",
                latency_ms=latency_ms
            )
            
        except Exception as e:
            # Ensure session is closed on error
            if session:
                try:
                    await self._close_session(session)
                except:
                    pass
            raise
    
    async def complete_stream(self, messages: List[Message], tools: Optional[List[ToolDefinition]] = None) -> AsyncIterator[StreamingDelta]:
        """Generate streaming completion"""
        if not await self._check_model():
            raise RuntimeError(f"Model {self.model} not available")
        
        ollama_messages = [
            {"role": msg.role.value, "content": msg.content}
            for msg in messages
        ]
        
        payload = {
            "model": self.model,
            "messages": ollama_messages,
            "stream": True,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_tokens
            }
        }
        
        if tools:
            payload["tools"] = [t.to_openai_schema()["function"] for t in tools]
        
        session = await self._get_session()
        async with session.post(self.api_chat, json=payload) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                raise RuntimeError(f"Ollama API error: {resp.status}")
            
            async for line in resp.content:
                line = line.decode('utf-8').strip()
                if not line:
                    continue
                
                try:
                    data = json.loads(line)
                    message = data.get("message", {})
                    
                    if data.get("done", False):
                        yield StreamingDelta(finish_reason="stop")
                        return
                    
                    content = message.get("content", "")
                    if content:
                        yield StreamingDelta(content=content)
                    
                    tool_calls = message.get("tool_calls", [])
                    if tool_calls:
                        formatted = []
                        for i, tc in enumerate(tool_calls):
                            formatted.append({
                                "id": f"call_{i}",
                                "type": "function",
                                "function": {
                                    "name": tc.get("function", {}).get("name", ""),
                                    "arguments": json.dumps(tc.get("function", {}).get("arguments", {}))
                                }
                            })
                        yield StreamingDelta(tool_calls=formatted, finish_reason="tool_calls")
                        return
                        
                except json.JSONDecodeError:
                    continue


class OpenAIProvider(LLMProvider):
    """OpenAI-compatible API provider"""
    
    def __init__(self,
                 model: str = "gpt-4",
                 api_key: Optional[str] = None,
                 base_url: str = "https://api.openai.com/v1",
                 temperature: float = 0.7,
                 max_tokens: int = 4096):
        super().__init__(model, temperature, max_tokens)
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url.rstrip('/')
        self.api_chat = f"{self.base_url}/chat/completions"
        
        if not self.api_key:
            logger.warning("[LLM] No OpenAI API key provided")
    
    async def complete(self, messages: List[Message], tools: Optional[List[ToolDefinition]] = None) -> LLMResponse:
        """Generate completion using OpenAI API"""
        start_time = asyncio.get_event_loop().time()
        
        payload = {
            "model": self.model,
            "messages": [msg.to_dict() for msg in messages],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": False
        }
        
        if tools:
            payload["tools"] = [t.to_openai_schema() for t in tools]
            payload["tool_choice"] = "auto"
        
        session = await self._get_session()
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        async with session.post(self.api_chat, json=payload, headers=headers) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                raise RuntimeError(f"OpenAI API error: {resp.status} - {error_text}")
            
            data = await resp.json()
        
        latency_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
        
        choice = data["choices"][0]
        message = choice["message"]
        
        return LLMResponse(
            content=message.get("content", ""),
            tool_calls=message.get("tool_calls", []),
            model=self.model,
            usage=data.get("usage", {}),
            finish_reason=choice.get("finish_reason", "stop"),
            latency_ms=latency_ms
        )
    
    async def complete_stream(self, messages: List[Message], tools: Optional[List[ToolDefinition]] = None) -> AsyncIterator[StreamingDelta]:
        """Generate streaming completion"""
        payload = {
            "model": self.model,
            "messages": [msg.to_dict() for msg in messages],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": True
        }
        
        if tools:
            payload["tools"] = [t.to_openai_schema() for t in tools]
            payload["tool_choice"] = "auto"
        
        session = await self._get_session()
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        async with session.post(self.api_chat, json=payload, headers=headers) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                raise RuntimeError(f"OpenAI API error: {resp.status}")
            
            async for line in resp.content:
                line = line.decode('utf-8').strip()
                if not line.startswith("data: "):
                    continue
                
                data_str = line[6:]
                if data_str == "[DONE]":
                    return
                
                try:
                    data = json.loads(data_str)
                    delta = data["choices"][0].get("delta", {})
                    finish_reason = data["choices"][0].get("finish_reason")
                    
                    yield StreamingDelta(
                        content=delta.get("content"),
                        tool_calls=delta.get("tool_calls"),
                        finish_reason=finish_reason
                    )
                except json.JSONDecodeError:
                    continue


class LLMProviderFactory:
    """Factory for creating LLM providers"""
    
    _providers: Dict[str, type] = {
        "ollama": OllamaProvider,
        "openai": OpenAIProvider,
    }
    
    @classmethod
    def create(cls, 
               provider_type: Union[str, LLMProviderType],
               **kwargs) -> LLMProvider:
        """Create LLM provider instance"""
        if isinstance(provider_type, LLMProviderType):
            provider_type = provider_type.value
        
        provider_class = cls._providers.get(provider_type.lower())
        if not provider_class:
            raise ValueError(f"Unknown provider type: {provider_type}")
        
        return provider_class(**kwargs)
    
    @classmethod
    def register(cls, name: str, provider_class: type):
        """Register a new provider type"""
        cls._providers[name.lower()] = provider_class
    
    @classmethod
    def list_providers(cls) -> List[str]:
        """List available provider types"""
        return list(cls._providers.keys())
