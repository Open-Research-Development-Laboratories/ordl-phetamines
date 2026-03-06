#!/usr/bin/env python3
"""
Adapter Registry

Central registry for managing protocol adapters.
Provides discovery, lifecycle management, and routing.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Type, Any
from dataclasses import dataclass

from .base import ProtocolAdapter, AdapterConfig, ExecutionRequest, ExecutionResult
from .mcp_adapter import MCPAdapter, MCPServerConfig
from .a2a_adapter import A2AAdapter, A2AAgentConfig

logger = logging.getLogger('acp.adapters.registry')


@dataclass
class AdapterRegistration:
    """Registered adapter information"""
    name: str
    adapter_type: str
    config: AdapterConfig
    instance: Optional[ProtocolAdapter] = None
    auto_init: bool = True


class AdapterRegistry:
    """
    Central registry for protocol adapters.
    
    Manages adapter lifecycle, provides capability discovery,
    and routes execution requests to appropriate adapters.
    """
    
    # Adapter type registry
    _adapter_types: Dict[str, Type[ProtocolAdapter]] = {
        'mcp': MCPAdapter,
        'a2a': A2AAdapter,
    }
    
    def __init__(self):
        self._adapters: Dict[str, ProtocolAdapter] = {}
        self._configs: Dict[str, AdapterConfig] = {}
        self._initialized = False
    
    def register_adapter_type(self, name: str, adapter_class: Type[ProtocolAdapter]):
        """Register a new adapter type"""
        self._adapter_types[name] = adapter_class
        logger.info(f"Registered adapter type: {name}")
    
    async def register(self, config: AdapterConfig, auto_init: bool = True) -> Optional[ProtocolAdapter]:
        """
        Register and optionally initialize an adapter.
        
        Args:
            config: Adapter configuration
            auto_init: Whether to initialize immediately
            
        Returns:
            Initialized adapter or None
        """
        if config.name in self._adapters:
            logger.warning(f"Adapter '{config.name}' already registered, skipping")
            return self._adapters[config.name]
        
        # Get adapter class
        adapter_class = self._adapter_types.get(config.protocol)
        if not adapter_class:
            logger.error(f"Unknown adapter protocol: {config.protocol}")
            return None
        
        # Create adapter instance
        try:
            adapter = adapter_class(config)
            self._configs[config.name] = config
            
            if auto_init and config.enabled:
                success = await adapter.initialize()
                if success:
                    self._adapters[config.name] = adapter
                    logger.info(f"Registered and initialized adapter: {config.name}")
                else:
                    logger.error(f"Failed to initialize adapter: {config.name}")
                    return None
            else:
                self._adapters[config.name] = adapter
                logger.info(f"Registered adapter (not initialized): {config.name}")
            
            return adapter
            
        except Exception as e:
            logger.error(f"Failed to create adapter {config.name}: {e}")
            return None
    
    async def unregister(self, name: str) -> bool:
        """Unregister and cleanup an adapter"""
        if name not in self._adapters:
            return False
        
        adapter = self._adapters.pop(name)
        self._configs.pop(name, None)
        
        try:
            await adapter.close()
            logger.info(f"Unregistered adapter: {name}")
            return True
        except Exception as e:
            logger.error(f"Error closing adapter {name}: {e}")
            return False
    
    def get(self, name: str) -> Optional[ProtocolAdapter]:
        """Get adapter by name"""
        return self._adapters.get(name)
    
    def get_by_protocol(self, protocol: str) -> List[ProtocolAdapter]:
        """Get all adapters for a protocol"""
        return [
            adapter for adapter in self._adapters.values()
            if adapter.protocol_name == protocol
        ]
    
    def list_adapters(self) -> List[str]:
        """List all registered adapter names"""
        return list(self._adapters.keys())
    
    async def discover_all_capabilities(self) -> Dict[str, List[Dict]]:
        """Discover capabilities from all adapters"""
        capabilities = {}
        
        for name, adapter in self._adapters.items():
            try:
                caps = await adapter.discover_capabilities()
                capabilities[name] = [
                    {
                        'id': cap.id,
                        'name': cap.name,
                        'description': cap.description,
                        'parameters': cap.parameters,
                        'returns': cap.returns
                    }
                    for cap in caps
                ]
            except Exception as e:
                logger.error(f"Failed to discover capabilities from {name}: {e}")
                capabilities[name] = []
        
        return capabilities
    
    async def execute(
        self,
        adapter_name: str,
        request: ExecutionRequest
    ) -> ExecutionResult:
        """
        Execute on a specific adapter.
        
        Args:
            adapter_name: Name of the adapter
            request: Execution request
            
        Returns:
            Execution result
        """
        adapter = self.get(adapter_name)
        if not adapter:
            return ExecutionResult(
                success=False,
                error=f"Adapter not found: {adapter_name}"
            )
        
        if not adapter.is_ready:
            return ExecutionResult(
                success=False,
                error=f"Adapter not ready: {adapter_name}"
            )
        
        return await adapter.execute(request)
    
    async def execute_by_capability(
        self,
        capability_id: str,
        request: ExecutionRequest
    ) -> ExecutionResult:
        """
        Find adapter with capability and execute.
        
        Args:
            capability_id: Capability ID to search for
            request: Execution request
            
        Returns:
            Execution result
        """
        # Find adapter with capability
        for name, adapter in self._adapters.items():
            if not adapter.is_ready:
                continue
            
            try:
                caps = await adapter.discover_capabilities()
                for cap in caps:
                    if cap.id == capability_id:
                        # Update request with capability ID
                        request.capability_id = capability_id
                        return await adapter.execute(request)
            except Exception as e:
                logger.error(f"Error checking capabilities of {name}: {e}")
        
        return ExecutionResult(
            success=False,
            error=f"No adapter found with capability: {capability_id}"
        )
    
    async def health_check(self) -> Dict[str, Any]:
        """Get health status of all adapters"""
        health = {
            'registry_status': 'healthy',
            'total_adapters': len(self._adapters),
            'ready_adapters': 0,
            'adapters': {}
        }
        
        for name, adapter in self._adapters.items():
            try:
                adapter_health = await adapter.health_check()
                health['adapters'][name] = adapter_health
                if adapter.is_ready:
                    health['ready_adapters'] += 1
            except Exception as e:
                health['adapters'][name] = {
                    'name': name,
                    'error': str(e),
                    'ready': False
                }
        
        return health
    
    async def initialize_all(self) -> Dict[str, bool]:
        """Initialize all registered adapters"""
        results = {}
        
        for name, adapter in list(self._adapters.items()):
            try:
                success = await adapter.initialize()
                results[name] = success
            except Exception as e:
                logger.error(f"Failed to initialize {name}: {e}")
                results[name] = False
        
        return results
    
    async def close_all(self):
        """Close all adapters"""
        for name in list(self._adapters.keys()):
            await self.unregister(name)
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close_all()


# Global registry instance
_global_registry: Optional[AdapterRegistry] = None


def get_registry() -> AdapterRegistry:
    """Get or create global adapter registry"""
    global _global_registry
    if _global_registry is None:
        _global_registry = AdapterRegistry()
    return _global_registry


def reset_registry():
    """Reset global registry (for testing)"""
    global _global_registry
    _global_registry = None
