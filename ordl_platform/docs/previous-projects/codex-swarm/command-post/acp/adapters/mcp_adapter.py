#!/usr/bin/env python3
"""
MCP (Model Context Protocol) Adapter

Implements ProtocolAdapter for Anthropic's Model Context Protocol.
Supports both stdio and HTTP+SSE transports.
"""

import asyncio
import json
import logging
import subprocess
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, AsyncGenerator
import aiohttp

from .base import (
    ProtocolAdapter, AdapterConfig, AdapterState,
    Capability, ExecutionRequest, ExecutionResult
)

logger = logging.getLogger('acp.adapters.mcp')


@dataclass
class MCPServerConfig(AdapterConfig):
    """Configuration for MCP server connection"""
    # Transport configuration
    transport: str = "stdio"  # "stdio" or "http"
    
    # For stdio transport
    command: Optional[str] = None
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    
    # For HTTP transport
    url: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)
    
    # Authentication
    auth_token: Optional[str] = None
    
    # Protocol version
    protocol_version: str = "2025-11-25"


class MCPAdapter(ProtocolAdapter):
    """
    Adapter for Model Context Protocol (MCP) servers.
    
    Supports:
    - stdio transport for local processes
    - HTTP+SSE transport for remote servers
    - Tool discovery and execution
    - Resource access
    - Prompt templates
    """
    
    protocol_name = "mcp"
    protocol_version = "2025-11-25"
    
    def __init__(self, config: MCPServerConfig):
        super().__init__(config)
        self.config = config
        self._process: Optional[subprocess.Process] = None
        self._session: Optional[aiohttp.ClientSession] = None
        self._request_id = 0
        self._pending_requests: Dict[int, asyncio.Future] = {}
        self._read_buffer = ""
        self._sse_session: Optional[Any] = None
        
    async def initialize(self) -> bool:
        """Initialize connection to MCP server"""
        self.state = AdapterState.INITIALIZING
        
        try:
            if self.config.transport == "stdio":
                await self._init_stdio()
            elif self.config.transport == "http":
                await self._init_http()
            else:
                raise ValueError(f"Unsupported transport: {self.config.transport}")
            
            # Perform MCP initialization handshake
            if await self._mcp_initialize():
                self.state = AdapterState.READY
                # Discover capabilities
                self._capabilities = await self.discover_capabilities()
                logger.info(f"[{self.config.name}] MCP adapter ready with {len(self._capabilities)} capabilities")
                return True
            else:
                self.state = AdapterState.ERROR
                return False
                
        except Exception as e:
            logger.error(f"[{self.config.name}] Initialization failed: {e}")
            self.state = AdapterState.ERROR
            return False
    
    async def _init_stdio(self):
        """Initialize stdio transport"""
        if not self.config.command:
            raise ValueError("Command required for stdio transport")
        
        env = {**self.config.env}
        if self.config.auth_token:
            env['MCP_AUTH_TOKEN'] = self.config.auth_token
        
        self._process = await asyncio.create_subprocess_exec(
            self.config.command,
            *self.config.args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**dict(), **env}
        )
        
        # Start reading stdout
        asyncio.create_task(self._read_stdio())
        logger.info(f"[{self.config.name}] Started stdio process: {self.config.command}")
    
    async def _init_http(self):
        """Initialize HTTP transport"""
        if not self.config.url:
            raise ValueError("URL required for HTTP transport")
        
        headers = {**self.config.headers}
        if self.config.auth_token:
            headers['Authorization'] = f'Bearer {self.config.auth_token}'
        
        self._session = aiohttp.ClientSession(headers=headers)
        logger.info(f"[{self.config.name}] HTTP session created: {self.config.url}")
    
    async def _read_stdio(self):
        """Read and process stdout from stdio process"""
        if not self._process or not self._process.stdout:
            return
        
        while True:
            try:
                line = await self._process.stdout.readline()
                if not line:
                    break
                
                data = line.decode().strip()
                if data:
                    await self._handle_message(json.loads(data))
            except json.JSONDecodeError:
                logger.warning(f"[{self.config.name}] Invalid JSON from stdio: {data}")
            except Exception as e:
                logger.error(f"[{self.config.name}] Stdio read error: {e}")
                break
    
    async def _handle_message(self, message: Dict[str, Any]):
        """Handle incoming MCP message"""
        if 'id' in message and message['id'] in self._pending_requests:
            future = self._pending_requests.pop(message['id'])
            if 'error' in message:
                future.set_exception(Exception(message['error']['message']))
            else:
                future.set_result(message.get('result'))
    
    async def _mcp_initialize(self) -> bool:
        """Perform MCP initialization handshake"""
        result = await self._send_request('initialize', {
            'protocolVersion': self.protocol_version,
            'capabilities': {
                'sampling': {},
                'roots': {'listChanged': True}
            },
            'clientInfo': {
                'name': 'ordl-nexus',
                'version': '7.0.0'
            }
        })
        return result is not None
    
    async def _send_request(self, method: str, params: Dict[str, Any]) -> Optional[Dict]:
        """Send JSON-RPC request"""
        self._request_id += 1
        request_id = self._request_id
        
        message = {
            'jsonrpc': '2.0',
            'id': request_id,
            'method': method,
            'params': params
        }
        
        if self.config.transport == "stdio":
            return await self._send_stdio_request(request_id, message)
        else:
            return await self._send_http_request(request_id, message)
    
    async def _send_stdio_request(self, request_id: int, message: Dict) -> Optional[Dict]:
        """Send request via stdio"""
        if not self._process or not self._process.stdin:
            raise RuntimeError("Stdio process not running")
        
        future = asyncio.get_event_loop().create_future()
        self._pending_requests[request_id] = future
        
        data = json.dumps(message) + '\n'
        self._process.stdin.write(data.encode())
        await self._process.stdin.drain()
        
        try:
            return await asyncio.wait_for(future, timeout=self.config.timeout)
        except asyncio.TimeoutError:
            self._pending_requests.pop(request_id, None)
            raise
    
    async def _send_http_request(self, request_id: int, message: Dict) -> Optional[Dict]:
        """Send request via HTTP"""
        if not self._session:
            raise RuntimeError("HTTP session not created")
        
        url = f"{self.config.url}/rpc"
        async with self._session.post(url, json=message) as response:
            if response.status == 200:
                return await response.json()
            else:
                text = await response.text()
                raise RuntimeError(f"HTTP {response.status}: {text}")
    
    async def close(self) -> None:
        """Close adapter and cleanup"""
        self.state = AdapterState.CLOSED
        
        if self._process:
            try:
                self._process.terminate()
                await asyncio.wait_for(self._process.wait(), timeout=5.0)
            except (ProcessLookupError, asyncio.TimeoutError):
                pass
            self._process = None
        
        if self._session:
            await self._session.close()
            self._session = None
        
        logger.info(f"[{self.config.name}] MCP adapter closed")
    
    async def discover_capabilities(self) -> List[Capability]:
        """Discover available MCP tools"""
        capabilities = []
        
        try:
            # Discover tools
            tools_result = await self._send_request('tools/list', {})
            if tools_result and 'tools' in tools_result:
                for tool in tools_result['tools']:
                    capabilities.append(Capability(
                        id=f"tool:{tool['name']}",
                        name=tool['name'],
                        description=tool.get('description', ''),
                        parameters=tool.get('inputSchema', {}),
                        metadata={'type': 'tool'}
                    ))
            
            # Discover resources
            resources_result = await self._send_request('resources/list', {})
            if resources_result and 'resources' in resources_result:
                for resource in resources_result['resources']:
                    capabilities.append(Capability(
                        id=f"resource:{resource['uri']}",
                        name=resource.get('name', resource['uri']),
                        description=resource.get('description', ''),
                        metadata={'type': 'resource', 'uri': resource['uri']}
                    ))
            
            # Discover prompts
            prompts_result = await self._send_request('prompts/list', {})
            if prompts_result and 'prompts' in prompts_result:
                for prompt in prompts_result['prompts']:
                    capabilities.append(Capability(
                        id=f"prompt:{prompt['name']}",
                        name=prompt['name'],
                        description=prompt.get('description', ''),
                        metadata={'type': 'prompt'}
                    ))
            
            self._capabilities = capabilities
            
        except Exception as e:
            logger.error(f"[{self.config.name}] Capability discovery failed: {e}")
        
        return capabilities
    
    async def execute(self, request: ExecutionRequest) -> ExecutionResult:
        """Execute MCP tool"""
        start_time = time.time()
        
        try:
            self._update_stats(success=False)  # Will update to True on success
            
            # Parse capability ID (format: "type:name")
            cap_id = request.capability_id
            if ':' in cap_id:
                cap_type, cap_name = cap_id.split(':', 1)
            else:
                cap_type, cap_name = 'tool', cap_id
            
            if cap_type == 'tool':
                result = await self._send_request('tools/call', {
                    'name': cap_name,
                    'arguments': request.parameters
                })
                
                execution_time = time.time() - start_time
                self._update_stats(success=True)
                
                return ExecutionResult(
                    success=True,
                    data=result,
                    execution_time=execution_time,
                    metadata={'type': 'tool_result'}
                )
            
            elif cap_type == 'resource':
                result = await self._send_request('resources/read', {
                    'uri': cap_name
                })
                
                execution_time = time.time() - start_time
                self._update_stats(success=True)
                
                return ExecutionResult(
                    success=True,
                    data=result,
                    execution_time=execution_time,
                    metadata={'type': 'resource_content'}
                )
            
            else:
                raise ValueError(f"Unsupported capability type: {cap_type}")
            
        except Exception as e:
            execution_time = time.time() - start_time
            self._update_stats(success=False, error=str(e))
            
            return ExecutionResult(
                success=False,
                error=str(e),
                execution_time=execution_time
            )
    
    async def stream_execute(self, request: ExecutionRequest) -> AsyncGenerator[ExecutionResult, None]:
        """Execute with streaming (if supported by server)"""
        # MCP stdio doesn't natively support streaming
        # For HTTP+SSE, we could implement streaming
        # For now, yield single result
        result = await self.execute(request)
        yield result
