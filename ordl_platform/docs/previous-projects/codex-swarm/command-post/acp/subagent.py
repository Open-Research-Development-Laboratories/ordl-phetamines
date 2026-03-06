#!/usr/bin/env python3
"""
ACP Subagent Base Classes
"""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable
from enum import Enum
from datetime import datetime

from .bus import ACPMessageBus, ACPMessage, ACPRequest, ACPResponse, MessageType

logger = logging.getLogger('acp.subagent')


class AgentStatus(Enum):
    """Subagent status states"""
    INITIALIZING = "initializing"
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    SHUTDOWN = "shutdown"


@dataclass
class SubagentConfig:
    """Subagent configuration"""
    agent_id: str = field(default_factory=lambda: f"subagent-{uuid.uuid4().hex[:8]}")
    name: str = "unnamed-subagent"
    clearance: str = "SECRET"
    max_concurrent_tasks: int = 5
    heartbeat_interval: int = 10
    skills: List[str] = field(default_factory=list)
    capabilities: Dict[str, Any] = field(default_factory=dict)


class ACPSubagent:
    """
    Base class for all ACP subagents
    
    Features:
    - Auto-registration with Nexus
    - Built-in skill discovery
    - Self-healing (restart on crash)
    - Resource monitoring
    - Encrypted communication ready
    """
    
    def __init__(self, bus: ACPMessageBus, config: SubagentConfig = None):
        self.bus = bus
        self.config = config or SubagentConfig()
        
        # State
        self.status = AgentStatus.INITIALIZING
        self.current_tasks: Dict[str, Any] = {}
        self.task_count = 0
        self.error_count = 0
        
        # Handlers
        self.message_handlers: Dict[str, Callable] = {}
        self.skill_handlers: Dict[str, Callable] = {}
        
        # Background tasks
        self._tasks: List[asyncio.Task] = []
        self.running = False
        
        logger.info(f"[SUBAGENT] Created: {self.config.agent_id}")
    
    async def start(self):
        """Start the subagent"""
        self.running = True
        self.status = AgentStatus.IDLE
        
        # Register with bus
        await self.bus.register_agent(
            self.config.agent_id,
            {
                'name': self.config.name,
                'skills': self.config.skills,
                'capabilities': self.config.capabilities,
                'max_tasks': self.config.max_concurrent_tasks
            }
        )
        
        # Start background tasks
        self._tasks.append(asyncio.create_task(self._heartbeat_loop()))
        self._tasks.append(asyncio.create_task(self._message_handler()))
        
        logger.info(f"[SUBAGENT] Started: {self.config.agent_id}")
    
    async def stop(self):
        """Stop the subagent gracefully"""
        self.running = False
        self.status = AgentStatus.SHUTDOWN
        
        # Cancel all tasks
        for task in self._tasks:
            task.cancel()
        
        # Unregister
        await self.bus.unregister_agent(self.config.agent_id)
        
        logger.info(f"[SUBAGENT] Stopped: {self.config.agent_id}")
    
    async def send_message(self, to_agent: str, message: dict) -> bool:
        """
        Send direct message to another agent
        
        Args:
            to_agent: Target agent ID
            message: Message payload
            
        Returns:
            True if sent successfully
        """
        msg = ACPMessage(
            from_agent=self.config.agent_id,
            to_agent=to_agent,
            payload=message
        )
        
        receipt = await self.bus.send_direct(
            self.config.agent_id,
            to_agent,
            msg
        )
        
        return receipt.delivered
    
    async def send_broadcast(self, channel: str, message: dict) -> List[bool]:
        """
        Broadcast message to channel
        
        Args:
            channel: Channel name
            message: Message payload
            
        Returns:
            List of delivery results
        """
        msg = ACPMessage(
            from_agent=self.config.agent_id,
            channel=channel,
            payload=message
        )
        
        receipts = await self.bus.broadcast(
            self.config.agent_id,
            channel,
            msg
        )
        
        return [r.delivered for r in receipts]
    
    async def request_skill(self, skill_name: str, params: dict,
                           timeout: int = 30) -> ACPResponse:
        """
        Request skill execution from another agent
        
        Args:
            skill_name: Name of skill to execute
            params: Skill parameters
            timeout: Max wait time
            
        Returns:
            Skill execution result
        """
        request = ACPRequest(
            method=skill_name,
            params=params,
            timeout=timeout
        )
        
        # Send to Nexus for routing
        return await self.bus.request_response(
            self.config.agent_id,
            'nexus',
            request,
            timeout
        )
    
    def register_message_handler(self, msg_type: str, handler: Callable):
        """Register handler for message type"""
        self.message_handlers[msg_type] = handler
    
    def register_skill_handler(self, skill_name: str, handler: Callable):
        """Register handler for skill execution"""
        self.skill_handlers[skill_name] = handler
        if skill_name not in self.config.skills:
            self.config.skills.append(skill_name)
    
    async def execute_skill(self, skill_name: str, params: dict) -> Any:
        """
        Execute a skill locally
        
        Args:
            skill_name: Skill to execute
            params: Skill parameters
            
        Returns:
            Skill result
        """
        if skill_name not in self.skill_handlers:
            raise ValueError(f"Skill not found: {skill_name}")
        
        if len(self.current_tasks) >= self.config.max_concurrent_tasks:
            raise RuntimeError("Max concurrent tasks reached")
        
        task_id = f"{skill_name}-{uuid.uuid4().hex[:8]}"
        
        try:
            self.status = AgentStatus.BUSY
            self.current_tasks[task_id] = {
                'skill': skill_name,
                'started': datetime.utcnow().isoformat()
            }
            
            handler = self.skill_handlers[skill_name]
            result = await handler(params)
            
            self.task_count += 1
            return result
            
        except Exception as e:
            self.error_count += 1
            logger.error(f"[SUBAGENT] Skill execution error: {e}")
            raise
            
        finally:
            del self.current_tasks[task_id]
            if not self.current_tasks:
                self.status = AgentStatus.IDLE
    
    async def on_message(self, message: ACPMessage):
        """
        Override to handle incoming messages
        
        Args:
            message: Incoming ACP message
        """
        pass
    
    async def _heartbeat_loop(self):
        """Send periodic heartbeats"""
        while self.running:
            try:
                heartbeat = ACPMessage(
                    msg_type=MessageType.HEARTBEAT,
                    from_agent=self.config.agent_id,
                    to_agent='nexus',
                    payload={
                        'status': self.status.value,
                        'load': len(self.current_tasks) / self.config.max_concurrent_tasks,
                        'capabilities': self.config.skills,
                        'task_count': self.task_count,
                        'error_count': self.error_count
                    },
                    ack_required=False
                )
                
                await self.bus.send_direct(
                    self.config.agent_id,
                    'nexus',
                    heartbeat
                )
                
            except Exception as e:
                logger.error(f"[SUBAGENT] Heartbeat error: {e}")
            
            await asyncio.sleep(self.config.heartbeat_interval)
    
    async def _message_handler(self):
        """Handle incoming messages"""
        while self.running:
            try:
                # Check for messages addressed to this agent
                for msg in self.bus.message_history:
                    if msg.to_agent == self.config.agent_id and not msg.delivered:
                        msg.delivered = True
                        msg.delivered_at = time.time()
                        
                        # Handle skill execution
                        if msg.msg_type == MessageType.SKILL_EXEC:
                            result = await self.execute_skill(
                                msg.skill_name,
                                msg.skill_params or {}
                            )
                            
                            # Send response
                            response = ACPResponse(
                                request_id=msg.payload.get('original_msg_id', ''),
                                success=True,
                                result=result
                            )
                            
                            await self.bus.send_direct(
                                self.config.agent_id,
                                msg.from_agent,
                                response.to_message(
                                    self.config.agent_id,
                                    msg.from_agent
                                )
                            )
                        
                        # Call custom handler
                        handler = self.message_handlers.get(msg.msg_type.value)
                        if handler:
                            await handler(msg)
                        
                        # Call generic on_message
                        await self.on_message(msg)
                
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"[SUBAGENT] Message handler error: {e}")
    
    def get_status(self) -> dict:
        """Get subagent status"""
        return {
            'agent_id': self.config.agent_id,
            'name': self.config.name,
            'status': self.status.value,
            'skills': self.config.skills,
            'current_tasks': len(self.current_tasks),
            'task_count': self.task_count,
            'error_count': self.error_count,
            'uptime': time.time() - getattr(self, '_start_time', time.time())
        }


class SpecializedSubagent(ACPSubagent):
    """
    Specialized subagent with pre-configured skills
    
    Subclasses should override skill_methods dict
    """
    
    skill_methods: Dict[str, Callable] = {}
    
    async def start(self):
        """Start with registered skills"""
        await super().start()
        
        # Auto-register skills
        for skill_name, handler in self.skill_methods.items():
            self.register_skill_handler(skill_name, handler)
        
        logger.info(f"[SUBAGENT] Specialized agent ready: {self.config.agent_id}")
