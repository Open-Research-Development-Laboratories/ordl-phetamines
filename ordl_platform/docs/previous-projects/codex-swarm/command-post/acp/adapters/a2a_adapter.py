#!/usr/bin/env python3
"""
A2A (Agent2Agent Protocol) Adapter

Implements ProtocolAdapter for Google's A2A protocol.
Supports JSON-RPC over HTTP and agent-to-agent communication.
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, AsyncGenerator
import aiohttp

from .base import (
    ProtocolAdapter, AdapterConfig, AdapterState,
    Capability, ExecutionRequest, ExecutionResult
)

logger = logging.getLogger('acp.adapters.a2a')


@dataclass
class A2AAgentConfig(AdapterConfig):
    """Configuration for A2A agent connection"""
    # Agent endpoint
    url: str = ""
    
    # Authentication
    auth_token: Optional[str] = None
    api_key: Optional[str] = None
    
    # Protocol settings
    protocol_version: str = "0.3.0"
    
    # Streaming settings
    streaming_enabled: bool = True
    
    # Agent card cache
    agent_card: Optional[Dict[str, Any]] = None


class A2AAdapter(ProtocolAdapter):
    """
    Adapter for Agent2Agent (A2A) Protocol.
    
    Supports:
    - Agent Card discovery
    - Task lifecycle management
    - Streaming via SSE
    - Push notifications
    - JSON-RPC over HTTP
    """
    
    protocol_name = "a2a"
    protocol_version = "0.3.0"
    
    def __init__(self, config: A2AAgentConfig):
        super().__init__(config)
        self.config = config
        self._session: Optional[aiohttp.ClientSession] = None
        self._agent_card: Optional[Dict[str, Any]] = None
        self._request_id = 0
        
    async def initialize(self) -> bool:
        """Initialize connection to A2A agent"""
        self.state = AdapterState.INITIALIZING
        
        try:
            # Create HTTP session
            headers = {'Content-Type': 'application/json'}
            if self.config.auth_token:
                headers['Authorization'] = f'Bearer {self.config.auth_token}'
            if self.config.api_key:
                headers['X-API-Key'] = self.config.api_key
            
            self._session = aiohttp.ClientSession(headers=headers)
            
            # Fetch Agent Card if not provided
            if not self.config.agent_card:
                self._agent_card = await self._fetch_agent_card()
            else:
                self._agent_card = self.config.agent_card
            
            if self._agent_card:
                self.state = AdapterState.READY
                # Discover capabilities from Agent Card
                self._capabilities = await self.discover_capabilities()
                logger.info(f"[{self.config.name}] A2A adapter ready: {self._agent_card.get('name', 'Unknown')}")
                return True
            else:
                self.state = AdapterState.ERROR
                return False
                
        except Exception as e:
            logger.error(f"[{self.config.name}] Initialization failed: {e}")
            self.state = AdapterState.ERROR
            return False
    
    async def _fetch_agent_card(self) -> Optional[Dict[str, Any]]:
        """Fetch Agent Card from well-known endpoint"""
        if not self._session:
            return None
        
        # Try well-known endpoint first
        well_known_url = f"{self.config.url}/.well-known/agent.json"
        
        try:
            async with self._session.get(well_known_url) as response:
                if response.status == 200:
                    return await response.json()
        except Exception as e:
            logger.debug(f"Well-known endpoint failed: {e}")
        
        # Try agent card endpoint
        card_url = f"{self.config.url}/agent-card"
        
        try:
            async with self._session.get(card_url) as response:
                if response.status == 200:
                    return await response.json()
        except Exception as e:
            logger.debug(f"Agent card endpoint failed: {e}")
        
        logger.error(f"[{self.config.name}] Could not fetch Agent Card")
        return None
    
    async def close(self) -> None:
        """Close adapter and cleanup"""
        self.state = AdapterState.CLOSED
        
        if self._session:
            await self._session.close()
            self._session = None
        
        logger.info(f"[{self.config.name}] A2A adapter closed")
    
    async def discover_capabilities(self) -> List[Capability]:
        """Discover capabilities from Agent Card skills"""
        capabilities = []
        
        if not self._agent_card:
            return capabilities
        
        # Extract skills from Agent Card
        skills = self._agent_card.get('skills', [])
        for skill in skills:
            capabilities.append(Capability(
                id=skill.get('id', skill.get('name', 'unknown')),
                name=skill.get('name', 'Unknown Skill'),
                description=skill.get('description', ''),
                parameters=skill.get('parameters', {}),
                metadata={
                    'type': 'skill',
                    'tags': skill.get('tags', []),
                    'examples': skill.get('examples', [])
                }
            ))
        
        # Also add generic message capability
        capabilities.append(Capability(
            id='a2a:send_message',
            name='Send Message',
            description='Send a message to the A2A agent',
            parameters={
                'type': 'object',
                'properties': {
                    'message': {'type': 'string'},
                    'context': {'type': 'object'}
                },
                'required': ['message']
            },
            metadata={'type': 'core'}
        ))
        
        self._capabilities = capabilities
        return capabilities
    
    async def _send_jsonrpc(self, method: str, params: Dict[str, Any]) -> Optional[Dict]:
        """Send JSON-RPC request to A2A agent"""
        if not self._session:
            raise RuntimeError("HTTP session not created")
        
        self._request_id += 1
        
        message = {
            'jsonrpc': '2.0',
            'id': self._request_id,
            'method': method,
            'params': params
        }
        
        url = f"{self.config.url}"
        
        async with self._session.post(url, json=message) as response:
            if response.status == 200:
                result = await response.json()
                if 'error' in result:
                    raise RuntimeError(f"A2A Error: {result['error']}")
                return result.get('result')
            else:
                text = await response.text()
                raise RuntimeError(f"HTTP {response.status}: {text}")
    
    async def execute(self, request: ExecutionRequest) -> ExecutionResult:
        """Execute A2A task"""
        start_time = time.time()
        
        try:
            self._update_stats(success=False)
            
            # Generate unique task ID
            task_id = f"task_{int(time.time() * 1000)}"
            
            # Build message from request
            message = self._build_message(request)
            
            # Send task
            result = await self._send_jsonrpc('tasks/send', {
                'id': task_id,
                'message': message,
                'context': request.context
            })
            
            # Wait for task completion if needed
            if result and result.get('status') == 'working':
                result = await self._wait_for_task(task_id)
            
            execution_time = time.time() - start_time
            self._update_stats(success=True)
            
            return ExecutionResult(
                success=True,
                data=result,
                execution_time=execution_time,
                metadata={'task_id': task_id, 'protocol': 'a2a'}
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            self._update_stats(success=False, error=str(e))
            
            return ExecutionResult(
                success=False,
                error=str(e),
                execution_time=execution_time
            )
    
    async def stream_execute(self, request: ExecutionRequest) -> AsyncGenerator[ExecutionResult, None]:
        """Execute A2A task with streaming via SSE"""
        start_time = time.time()
        task_id = f"task_{int(time.time() * 1000)}"
        
        try:
            self._update_stats(success=False)
            
            # Build message
            message = self._build_message(request)
            
            # Send streaming request
            if not self._session:
                raise RuntimeError("HTTP session not created")
            
            self._request_id += 1
            rpc_request = {
                'jsonrpc': '2.0',
                'id': self._request_id,
                'method': 'tasks/sendSubscribe',
                'params': {
                    'id': task_id,
                    'message': message,
                    'context': request.context
                }
            }
            
            url = f"{self.config.url}"
            
            async with self._session.post(url, json=rpc_request) as response:
                if response.status != 200:
                    text = await response.text()
                    raise RuntimeError(f"HTTP {response.status}: {text}")
                
                # Read SSE stream
                async for line in response.content:
                    line = line.decode().strip()
                    if line.startswith('data:'):
                        data = line[5:].strip()
                        try:
                            event = json.loads(data)
                            
                            # Yield update
                            execution_time = time.time() - start_time
                            yield ExecutionResult(
                                success=True,
                                data=event,
                                execution_time=execution_time,
                                metadata={'task_id': task_id, 'streaming': True}
                            )
                            
                            # Check if task is complete
                            if event.get('status') in ['completed', 'failed', 'canceled']:
                                self._update_stats(success=True)
                                break
                                
                        except json.JSONDecodeError:
                            continue
            
        except Exception as e:
            execution_time = time.time() - start_time
            self._update_stats(success=False, error=str(e))
            
            yield ExecutionResult(
                success=False,
                error=str(e),
                execution_time=execution_time
            )
    
    def _build_message(self, request: ExecutionRequest) -> Dict[str, Any]:
        """Build A2A message from execution request"""
        # Extract message text from parameters
        message_text = request.parameters.get('message', '')
        if not message_text and 'input' in request.parameters:
            message_text = request.parameters['input']
        
        # Build parts
        parts = [{'type': 'text', 'text': message_text}]
        
        # Add file parts if present
        if 'files' in request.parameters:
            for file in request.parameters['files']:
                parts.append({
                    'type': 'file',
                    'file': {
                        'mimeType': file.get('mimeType', 'application/octet-stream'),
                        'data': file.get('data', ''),
                        'name': file.get('name', 'file')
                    }
                })
        
        return {
            'role': 'user',
            'parts': parts
        }
    
    async def _wait_for_task(self, task_id: str, timeout: int = 60) -> Optional[Dict]:
        """Poll task until completion"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            result = await self._send_jsonrpc('tasks/get', {'id': task_id})
            
            if result and result.get('status') in ['completed', 'failed', 'canceled']:
                return result
            
            await asyncio.sleep(1)
        
        raise TimeoutError(f"Task {task_id} did not complete within {timeout}s")
    
    async def get_agent_info(self) -> Dict[str, Any]:
        """Get information about the connected A2A agent"""
        if not self._agent_card:
            return {}
        
        return {
            'name': self._agent_card.get('name', 'Unknown'),
            'description': self._agent_card.get('description', ''),
            'version': self._agent_card.get('version', 'unknown'),
            'url': self._agent_card.get('url', self.config.url),
            'capabilities': self._agent_card.get('capabilities', {}),
            'skills_count': len(self._agent_card.get('skills', [])),
            'protocol_version': self.protocol_version
        }
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel an ongoing task"""
        try:
            await self._send_jsonrpc('tasks/cancel', {'id': task_id})
            return True
        except Exception as e:
            logger.error(f"Failed to cancel task {task_id}: {e}")
            return False
