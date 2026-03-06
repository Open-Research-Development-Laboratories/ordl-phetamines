#!/usr/bin/env python3
"""
Configuration Management for ACP Adapters

Handles loading and validation of adapter configurations from
YAML, JSON, or Python dictionaries.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

from .base import AdapterConfig
from .mcp_adapter import MCPServerConfig
from .a2a_adapter import A2AAgentConfig

logger = logging.getLogger('acp.adapters.config')


@dataclass
class AdapterProfile:
    """Profile containing multiple adapter configurations"""
    name: str
    description: str = ""
    adapters: List[Union[MCPServerConfig, A2AAgentConfig]] = field(default_factory=list)
    defaults: Dict[str, Any] = field(default_factory=dict)


class ConfigLoader:
    """Load adapter configurations from various sources"""
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> AdapterProfile:
        """Load configuration from dictionary"""
        profile = AdapterProfile(
            name=data.get('name', 'default'),
            description=data.get('description', ''),
            defaults=data.get('defaults', {})
        )
        
        # Load adapter configs
        for adapter_data in data.get('adapters', []):
            adapter_type = adapter_data.get('protocol', '').lower()
            
            if adapter_type == 'mcp':
                config = MCPServerConfig(
                    name=adapter_data['name'],
                    protocol='mcp',
                    enabled=adapter_data.get('enabled', True),
                    timeout=adapter_data.get('timeout', 30),
                    retry_count=adapter_data.get('retry_count', 3),
                    transport=adapter_data.get('transport', 'stdio'),
                    command=adapter_data.get('command'),
                    args=adapter_data.get('args', []),
                    env=adapter_data.get('env', {}),
                    url=adapter_data.get('url'),
                    headers=adapter_data.get('headers', {}),
                    auth_token=adapter_data.get('auth_token') or os.getenv(adapter_data.get('auth_token_env', '')),
                    protocol_version=adapter_data.get('protocol_version', '2025-11-25')
                )
                profile.adapters.append(config)
                
            elif adapter_type == 'a2a':
                config = A2AAgentConfig(
                    name=adapter_data['name'],
                    protocol='a2a',
                    enabled=adapter_data.get('enabled', True),
                    timeout=adapter_data.get('timeout', 30),
                    retry_count=adapter_data.get('retry_count', 3),
                    url=adapter_data['url'],
                    auth_token=adapter_data.get('auth_token') or os.getenv(adapter_data.get('auth_token_env', '')),
                    api_key=adapter_data.get('api_key') or os.getenv(adapter_data.get('api_key_env', '')),
                    protocol_version=adapter_data.get('protocol_version', '0.3.0'),
                    streaming_enabled=adapter_data.get('streaming_enabled', True)
                )
                profile.adapters.append(config)
            
            else:
                logger.warning(f"Unknown adapter protocol: {adapter_type}")
        
        return profile
    
    @staticmethod
    def from_json(path: Union[str, Path]) -> AdapterProfile:
        """Load configuration from JSON file"""
        with open(path, 'r') as f:
            data = json.load(f)
        return ConfigLoader.from_dict(data)
    
    @staticmethod
    def from_yaml(path: Union[str, Path]) -> AdapterProfile:
        """Load configuration from YAML file"""
        if not YAML_AVAILABLE:
            raise ImportError("PyYAML required for YAML config loading")
        
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
        return ConfigLoader.from_dict(data)
    
    @staticmethod
    def from_file(path: Union[str, Path]) -> AdapterProfile:
        """Auto-detect and load configuration from file"""
        path = Path(path)
        
        if path.suffix in ['.yaml', '.yml']:
            return ConfigLoader.from_yaml(path)
        elif path.suffix == '.json':
            return ConfigLoader.from_json(path)
        else:
            raise ValueError(f"Unsupported config format: {path.suffix}")


class ConfigValidator:
    """Validate adapter configurations"""
    
    @staticmethod
    def validate_mcp_config(config: MCPServerConfig) -> List[str]:
        """Validate MCP configuration and return list of errors"""
        errors = []
        
        if not config.name:
            errors.append("MCP adapter requires a name")
        
        if config.transport == 'stdio':
            if not config.command:
                errors.append(f"MCP adapter '{config.name}' requires command for stdio transport")
        elif config.transport == 'http':
            if not config.url:
                errors.append(f"MCP adapter '{config.name}' requires URL for HTTP transport")
        else:
            errors.append(f"MCP adapter '{config.name}' has invalid transport: {config.transport}")
        
        return errors
    
    @staticmethod
    def validate_a2a_config(config: A2AAgentConfig) -> List[str]:
        """Validate A2A configuration and return list of errors"""
        errors = []
        
        if not config.name:
            errors.append("A2A adapter requires a name")
        
        if not config.url:
            errors.append(f"A2A adapter '{config.name}' requires URL")
        
        return errors
    
    @staticmethod
    def validate_profile(profile: AdapterProfile) -> Dict[str, List[str]]:
        """Validate entire profile and return errors by adapter"""
        errors = {}
        
        for adapter in profile.adapters:
            if isinstance(adapter, MCPServerConfig):
                adapter_errors = ConfigValidator.validate_mcp_config(adapter)
                if adapter_errors:
                    errors[adapter.name] = adapter_errors
            elif isinstance(adapter, A2AAgentConfig):
                adapter_errors = ConfigValidator.validate_a2a_config(adapter)
                if adapter_errors:
                    errors[adapter.name] = adapter_errors
        
        return errors


# Example configuration templates

EXAMPLE_MCP_CONFIG = {
    "name": "filesystem-server",
    "protocol": "mcp",
    "transport": "stdio",
    "command": "python",
    "args": ["-m", "mcp_server_filesystem", "/path/to/allowed/files"],
    "env": {
        "MCP_DEBUG": "1"
    },
    "timeout": 30,
    "enabled": True
}

EXAMPLE_A2A_CONFIG = {
    "name": "weather-agent",
    "protocol": "a2a",
    "url": "https://weather-agent.example.com/a2a",
    "auth_token_env": "WEATHER_AGENT_TOKEN",
    "streaming_enabled": True,
    "timeout": 60,
    "enabled": True
}

EXAMPLE_PROFILE = {
    "name": "production",
    "description": "Production adapter configuration",
    "defaults": {
        "timeout": 30,
        "retry_count": 3
    },
    "adapters": [
        EXAMPLE_MCP_CONFIG,
        EXAMPLE_A2A_CONFIG
    ]
}
