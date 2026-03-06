#!/usr/bin/env python3
"""
ORDL Agent Manager - Multi-Agent Orchestration
"""

import os
import json
import sqlite3
import logging
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any
from queue import PriorityQueue
from dataclasses import asdict

from .agent import (
    Agent, AgentConfig, AgentStatus, Task, TaskPriority,
    ToolRegistry, Message
)

logger = logging.getLogger('agents.manager')


class AgentManager:
    """
    Military-grade multi-agent orchestration system
    
    Manages:
    - Agent lifecycle (create, destroy, monitor)
    - Task queue with priority scheduling
    - Multi-agent swarm operations
    - Agent-to-agent communication
    """
    
    def __init__(self, db_path: str = "/opt/codex-swarm/command-post/data/nexus.db"):
        self.db_path = db_path
        self.agents: Dict[str, Agent] = {}
        self.tool_registry = ToolRegistry()
        self.task_queue: PriorityQueue = PriorityQueue()
        self.completed_tasks: List[Task] = []
        self._lock = threading.RLock()
        self._running = False
        self._worker_thread: Optional[threading.Thread] = None
        
        # Stats
        self.stats = {
            "agents_created": 0,
            "agents_destroyed": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "started_at": datetime.utcnow().isoformat()
        }
        
        self._init_db()
        self._start_worker()
    
    def _init_db(self):
        """Initialize database tables - aligned with actual schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agents (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                persona TEXT,
                model TEXT,
                clearance TEXT,
                status TEXT DEFAULT 'idle',
                created_at TEXT,
                tasks_completed INTEGER DEFAULT 0,
                capabilities TEXT,
                description TEXT,
                config TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agent_tasks (
                task_id TEXT PRIMARY KEY,
                agent_id TEXT,
                priority INTEGER,
                description TEXT,
                payload TEXT,
                status TEXT,
                created_at TEXT,
                started_at TEXT,
                completed_at TEXT,
                result TEXT,
                error TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _start_worker(self):
        """Start task processing worker"""
        self._running = True
        self._worker_thread = threading.Thread(target=self._process_tasks, daemon=True)
        self._worker_thread.start()
        logger.info("[AGENTS] Task worker started")
    
    def _process_tasks(self):
        """Background task processor"""
        while self._running:
            try:
                # Get task from queue (non-blocking with timeout)
                task = self.task_queue.get(timeout=1)
                
                # Find available agent or assign to specified agent
                agent = None
                if task.agent_id and task.agent_id in self.agents:
                    agent = self.agents[task.agent_id]
                else:
                    # Find idle agent
                    for a in self.agents.values():
                        if a.status == AgentStatus.IDLE:
                            agent = a
                            break
                
                if agent:
                    try:
                        result = agent.execute_task(task)
                        self.completed_tasks.append(task)
                        
                        if result.get("success"):
                            self.stats["tasks_completed"] += 1
                        else:
                            self.stats["tasks_failed"] += 1
                            
                    except Exception as e:
                        logger.error(f"Task execution failed: {e}")
                        task.status = "failed"
                        task.error = str(e)
                        self.stats["tasks_failed"] += 1
                else:
                    # Re-queue task
                    self.task_queue.put(task)
                    import time
                time.sleep(0.1)
                    
            except Exception as e:
                import traceback
                logger.error(f"Task processor error: {type(e).__name__}: {e}")
                logger.debug(f"Task processor traceback: {traceback.format_exc()}")
    
    def create_agent(self, config_dict: Dict) -> Agent:
        """Create new agent"""
        with self._lock:
            # Generate ID if not provided
            if 'agent_id' not in config_dict:
                config_dict['agent_id'] = f"agent-{int(datetime.utcnow().timestamp() * 1000)}"
            
            config = AgentConfig(**config_dict)
            agent = Agent(config, self.tool_registry)
            
            self.agents[config.agent_id] = agent
            self.stats["agents_created"] += 1
            
            # Persist to DB
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO agents (id, name, persona, model, clearance, status, created_at, tasks_completed)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0)
            ''', (
                config.agent_id,
                config.name,
                config.persona,
                config.model,
                config.clearance,
                agent.status.value,
                agent.created_at
            ))
            conn.commit()
            conn.close()
            
            logger.info(f"[AGENTS] Created agent: {config.agent_id} ({config.name})")
            return agent
    
    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get agent by ID"""
        return self.agents.get(agent_id)
    
    def destroy_agent(self, agent_id: str) -> bool:
        """Destroy agent"""
        with self._lock:
            if agent_id not in self.agents:
                return False
            
            agent = self.agents[agent_id]
            agent.destroy()
            del self.agents[agent_id]
            
            self.stats["agents_destroyed"] += 1
            
            # Update DB
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE agents 
                SET status = ?, tasks_completed = ?
                WHERE id = ?
            ''', (
                AgentStatus.DESTROYED.value,
                agent.tasks_completed,
                agent_id
            ))
            conn.commit()
            conn.close()
            
            logger.info(f"[AGENTS] Destroyed agent: {agent_id}")
            return True
    
    def list_agents(self) -> List[Dict]:
        """List all agents"""
        return [agent.to_dict() for agent in self.agents.values()]
    
    def send_message(self, agent_id: str, message: str) -> Dict:
        """Send message to agent with enhanced logging"""
        logger.info(f"[AGENTS] Sending message to agent {agent_id}: {message[:50]}...")
        
        # Strip quotes if present
        agent_id_clean = agent_id.strip('"\'')
        
        agent = self.get_agent(agent_id_clean)
        if not agent:
            # Try to find by name if ID lookup fails
            for aid, a in self.agents.items():
                if a.config.name == agent_id_clean:
                    agent = a
                    break
            
            if not agent:
                available = list(self.agents.keys())
                logger.error(f"[AGENTS] Agent not found: {agent_id_clean}. Available: {available}")
                return {
                    "success": False, 
                    "error": f"Agent not found: {agent_id_clean}",
                    "available_agents": available
                }
        
        result = agent.process_message(message)
        logger.info(f"[AGENTS] Message processed, success={result.get('success')}")
        return result
    
    def create_task(self, description: str, 
                   priority: TaskPriority = TaskPriority.MEDIUM,
                   agent_id: Optional[str] = None,
                   payload: Optional[Dict] = None) -> Task:
        """Create and queue a task"""
        task = Task(
            task_id=f"task-{int(datetime.utcnow().timestamp() * 1000)}",
            priority=priority,
            description=description,
            agent_id=agent_id,
            payload=payload or {}
        )
        
        self.task_queue.put(task)
        
        # Persist to DB
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO agent_tasks 
            (task_id, agent_id, priority, description, payload, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            task.task_id,
            agent_id,
            priority.value,
            description,
            json.dumps(payload or {}),
            task.status,
            task.created_at
        ))
        conn.commit()
        conn.close()
        
        return task
    
    def get_stats(self) -> Dict:
        """Get manager statistics"""
        return {
            **self.stats,
            "active_agents": len(self.agents),
            "pending_tasks": self.task_queue.qsize(),
            "completed_tasks": len(self.completed_tasks),
            "tools_available": len(self.tool_registry.tools)
        }
    
    def get_tools(self) -> List[Dict]:
        """Get available tools"""
        return self.tool_registry.list_tools()
    
    def execute_tool(self, tool_name: str, **kwargs) -> Dict:
        """Execute tool directly"""
        result = self.tool_registry.execute_tool(tool_name, **kwargs)
        return {
            "success": result.success,
            "result": result.result,
            "error": result.error_message,
            "execution_time_ms": result.execution_time_ms
        }
    
    def shutdown(self):
        """Shutdown manager"""
        self._running = False
        
        # Stop all agents
        for agent in self.agents.values():
            agent.stop()
        
        if self._worker_thread:
            self._worker_thread.join(timeout=5)
        
        logger.info("[AGENTS] Manager shutdown complete")


# Singleton
_manager_instance: Optional[AgentManager] = None

def get_agent_manager() -> AgentManager:
    """Get singleton agent manager"""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = AgentManager()
    return _manager_instance
