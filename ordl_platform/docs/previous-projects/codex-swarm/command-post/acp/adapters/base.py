#!/usr/bin/env python3
"""
Base Protocol Adapter Interface

Defines the contract that all protocol adapters must implement.
This enables seamless integration of any ACP-compliant protocol.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, AsyncGenerator, Callable
import asyncio
import logging

logger = logging.getLogger('acp.adapters.base')


class AdapterState(Enum):
    """Adapter lifecycle states"""
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    READY = "ready"
    ERROR = "error"
    CLOSED = "closed"


@dataclass
class AdapterConfig:
    """Base configuration for protocol adapters"""
    name: str
    protocol: str  # 'mcp', 'a2a', 'agent_client', etc.
    enabled: bool = True
    timeout: int = 30
    retry_count: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Capability:
    """Represents a discovered capability/skill/tool"""
    id: str
    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    returns: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionRequest:
    """Standardized execution request"""
    capability_id: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    streaming: bool = False
    timeout: Optional[int] = None


@dataclass
class ExecutionResult:
    """Standardized execution result"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class ProtocolAdapter(ABC):
    """
    Abstract base class for all protocol adapters.
    
    All protocol adapters must implement this interface to ensure
    seamless integration with the ORDL NEXUS framework.
    """
    
    def __init__(self, config: AdapterConfig):
        self.config = config
        self.state = AdapterState.UNINITIALIZED
        self._capabilities: List[Capability] = []
        self._stats = {
            'requests_total': 0,
            'requests_success': 0,
            'requests_failed': 0,
            'last_error': None
        }
        logger.info(f"[{self.config.name}] Adapter created ({self.config.protocol})")
    
    @property
    @abstractmethod
    def protocol_name(self) -> str:
        """Return the protocol identifier"""
        pass
    
    @property
    @abstractmethod
    def protocol_version(self) -> str:
        """Return the supported protocol version"""
        pass
    
    @property
    def is_ready(self) -> bool:
        """Check if adapter is ready for operations"""
        return self.state == AdapterState.READY
    
    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialize the adapter with configuration.
        
        Returns:
            bool: True if initialization successful
        """
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close the adapter and cleanup resources"""
        pass
    
    @abstractmethod
    async def discover_capabilities(self) -> List[Capability]:
        """
        Discover available capabilities/tools/skills.
        
        Returns:
            List of available capabilities
        """
        pass
    
    @abstractmethod
    async def execute(self, request: ExecutionRequest) -> ExecutionResult:
        """
        Execute a capability/tool with given parameters.
        
        Args:
            request: Execution request with capability ID and parameters
            
        Returns:
            Execution result
        """
        pass
    
    @abstractmethod
    async def stream_execute(self, request: ExecutionRequest) -> AsyncGenerator[ExecutionResult, None]:
        """
        Execute with streaming response.
        
        Args:
            request: Execution request with streaming enabled
            
        Yields:
            Execution results as they become available
        """
        pass
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check adapter health status.
        
        Returns:
            Health status dictionary
        """
        return {
            'name': self.config.name,
            'protocol': self.protocol_name,
            'version': self.protocol_version,
            'state': self.state.value,
            'ready': self.is_ready,
            'capabilities_count': len(self._capabilities),
            'stats': self._stats.copy()
        }
    
    def _update_stats(self, success: bool, error: Optional[str] = None):
        """Update execution statistics"""
        self._stats['requests_total'] += 1
        if success:
            self._stats['requests_success'] += 1
        else:
            self._stats['requests_failed'] += 1
            self._stats['last_error'] = error
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
