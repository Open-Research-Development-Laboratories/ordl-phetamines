#!/usr/bin/env python3
"""
Nexus Router - Central Hub for ACP
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from .bus import ACPMessageBus, ACPMessage, MessageType
from .skills.registry import SkillRegistry

logger = logging.getLogger('acp.nexus')


class NexusRouter:
    """
    Central Nexus Router for ORDL
    
    Responsibilities:
    - Route messages between subagents
    - Manage skill execution
    - Monitor agent health
    - Load balance tasks
    """
    
    def __init__(self, bus: ACPMessageBus, skill_registry: SkillRegistry):
        self.bus = bus
        self.skills = skill_registry
        
        # Agent tracking
        self.agent_health: Dict[str, dict] = {}
        self.agent_load: Dict[str, float] = {}
        
        # Task queue
        self.task_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        
        # Running state
        self.running = False
        
        # Stats
        self.stats = {
            'tasks_routed': 0,
            'skills_executed': 0,
            'agents_monitored': 0
        }
    
    async def start(self):
        """Start the Nexus router"""
        self.running = True
        
        # Register message handler
        self.bus.register_handler('nexus', self._handle_message)
        
        # Start background tasks
        asyncio.create_task(self._health_monitor())
        asyncio.create_task(self._task_scheduler())
        asyncio.create_task(self._load_balancer())
        
        logger.info("[NEXUS] Router started")
    
    async def stop(self):
        """Stop the Nexus router"""
        self.running = False
        logger.info("[NEXUS] Router stopped")
    
    async def _handle_message(self, message: ACPMessage):
        """Handle incoming ACP messages"""
        try:
            if message.msg_type == MessageType.SKILL_EXEC:
                await self._route_skill_execution(message)
            
            elif message.msg_type == MessageType.DISCOVER:
                await self._handle_discovery(message)
            
            elif message.msg_type == MessageType.HEARTBEAT:
                await self._update_agent_health(message)
            
            elif message.msg_type == MessageType.REGISTER:
                await self._handle_agent_registration(message)
                
        except Exception as e:
            logger.error(f"[NEXUS] Message handling error: {e}")
    
    async def _route_skill_execution(self, message: ACPMessage):
        """Route skill execution to appropriate agent"""
        skill_name = message.skill_name
        params = message.skill_params
        
        # Find agent with skill
        capable_agents = self._find_capable_agents(skill_name)
        
        if not capable_agents:
            logger.error(f"[NEXUS] No agent found for skill: {skill_name}")
            return
        
        # Select least loaded agent
        selected_agent = min(capable_agents, key=lambda a: self.agent_load.get(a, 0))
        
        # Update load
        self.agent_load[selected_agent] = self.agent_load.get(selected_agent, 0) + 1
        
        # Forward to agent
        await self.bus.send_direct(
            'nexus',
            selected_agent,
            ACPMessage(
                msg_type=MessageType.SKILL_EXEC,
                skill_name=skill_name,
                skill_params=params,
                payload={'original_msg_id': message.msg_id}
            )
        )
        
        self.stats['tasks_routed'] += 1
        logger.info(f"[NEXUS] Routed skill {skill_name} to {selected_agent}")
    
    async def _handle_discovery(self, message: ACPMessage):
        """Handle skill discovery request"""
        from_agent = message.from_agent
        
        # Get all available skills
        all_skills = self.skills.list_skills()
        
        # Send back to requesting agent
        await self.bus.send_direct(
            'nexus',
            from_agent,
            ACPMessage(
                msg_type=MessageType.DISCOVER,
                payload={'skills': all_skills}
            )
        )
        
        logger.debug(f"[NEXUS] Sent skill discovery to {from_agent}")
    
    async def _update_agent_health(self, message: ACPMessage):
        """Update agent health status"""
        agent_id = message.from_agent
        
        self.agent_health[agent_id] = {
            'last_heartbeat': datetime.utcnow().isoformat(),
            'status': message.payload.get('status', 'unknown'),
            'load': message.payload.get('load', 0),
            'capabilities': message.payload.get('capabilities', [])
        }
        
        self.stats['agents_monitored'] = len(self.agent_health)
    
    async def _handle_agent_registration(self, message: ACPMessage):
        """Handle new agent registration"""
        agent_id = message.from_agent
        capabilities = message.payload.get('capabilities', {})
        
        await self.bus.register_agent(agent_id, capabilities)
        
        logger.info(f"[NEXUS] Registered agent: {agent_id}")
    
    def _find_capable_agents(self, skill_name: str) -> List[str]:
        """Find agents capable of executing a skill"""
        capable = []
        
        for agent_id, health in self.agent_health.items():
            if skill_name in health.get('capabilities', []):
                capable.append(agent_id)
        
        return capable
    
    async def _health_monitor(self):
        """Monitor agent health and cleanup dead agents"""
        while self.running:
            now = datetime.utcnow()
            
            for agent_id, health in list(self.agent_health.items()):
                last_seen = datetime.fromisoformat(health['last_heartbeat'])
                
                # Mark as dead if no heartbeat for 60 seconds
                if (now - last_seen).seconds > 60:
                    logger.warning(f"[NEXUS] Agent {agent_id} appears dead")
                    await self.bus.unregister_agent(agent_id)
                    del self.agent_health[agent_id]
            
            await asyncio.sleep(10)
    
    async def _task_scheduler(self):
        """Schedule tasks from queue"""
        while self.running:
            try:
                priority, task = await asyncio.wait_for(
                    self.task_queue.get(), 
                    timeout=1.0
                )
                
                # Process task
                await self._process_task(task)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"[NEXUS] Task scheduling error: {e}")
    
    async def _process_task(self, task: dict):
        """Process a queued task"""
        # Implementation depends on task type
        pass
    
    async def _load_balancer(self):
        """Periodically rebalance load across agents"""
        while self.running:
            # Decay load metrics
            for agent_id in self.agent_load:
                self.agent_load[agent_id] *= 0.9
            
            await asyncio.sleep(5)
    
    def get_system_status(self) -> dict:
        """Get overall system status"""
        return {
            'agents': {
                'total': len(self.agent_health),
                'healthy': sum(1 for h in self.agent_health.values() 
                              if h.get('status') == 'healthy'),
                'details': self.agent_health
            },
            'skills': {
                'total': len(self.skills.list_skills()),
                'categories': self.skills.get_categories()
            },
            'stats': self.stats,
            'bus_stats': self.bus.get_stats()
        }
