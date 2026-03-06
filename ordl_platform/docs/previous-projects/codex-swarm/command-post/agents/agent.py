#!/usr/bin/env python3
"""
================================================================================
ORDL COMMAND POST v6.0.0 - AI AGENT SYSTEM
================================================================================
Classification: TOP SECRET//SCI//NOFORN
Classification Level: TS/SCI/NOFORN

MILITARY-GRADE AI AGENT ORCHESTRATION SYSTEM
================================================================================
Core AI agent management with real tool integration:
- Agent lifecycle management (create, run, pause, stop, destroy)
- Tool registry with all ORDL modules
- Conversation memory management
- Multi-agent swarm orchestration
- Task queue with priority scheduling
- Real-time status tracking

Author: ORDL Cyber Operations Division
Version: 6.0.0
================================================================================
"""

import os
import sys
import json
import uuid
import time
import sqlite3
import logging
import threading
from enum import Enum
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Callable, Tuple, Union
from queue import PriorityQueue, Queue
from pathlib import Path
import hashlib
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger('agents')


class AgentStatus(Enum):
    """Agent lifecycle statuses"""
    IDLE = "idle"
    INITIALIZING = "initializing"
    RUNNING = "running"
    PROCESSING = "processing"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"
    DESTROYED = "destroyed"


class TaskPriority(Enum):
    """Task priority levels (lower = higher priority)"""
    CRITICAL = 0
    HIGH = 1
    MEDIUM = 2
    LOW = 3
    BACKGROUND = 4


@dataclass
class AgentConfig:
    """Agent configuration"""
    agent_id: str
    name: str
    persona: str
    model: str = "default"
    clearance: str = "SECRET"
    capabilities: List[str] = field(default_factory=list)
    max_context_length: int = 4096
    temperature: float = 0.7
    top_p: float = 0.9
    max_tokens: int = 2048
    tools_enabled: List[str] = field(default_factory=list)
    auto_tool_use: bool = True
    memory_enabled: bool = True
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class Message:
    """Conversation message"""
    role: str  # system, user, assistant, tool
    content: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)
    tool_calls: Optional[List[Dict]] = None
    tool_call_id: Optional[str] = None


@dataclass
class ToolCall:
    """Tool call representation"""
    tool_name: str
    arguments: Dict[str, Any]
    call_id: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class ToolResult:
    """Tool execution result"""
    tool_name: str
    result: Any
    success: bool
    error_message: Optional[str] = None
    execution_time_ms: int = 0
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class Task:
    """Agent task"""
    task_id: str
    priority: TaskPriority
    description: str
    agent_id: Optional[str]
    payload: Dict[str, Any]
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    status: str = "pending"
    result: Optional[Any] = None
    error: Optional[str] = None
    
    def __lt__(self, other):
        return self.priority.value < other.priority.value


class Tool:
    """Tool definition"""
    
    def __init__(self,
                 name: str,
                 description: str,
                 function: Callable,
                 parameters: Dict[str, Any],
                 clearance_required: str = "UNCLASSIFIED",
                 category: str = "general"):
        self.name = name
        self.description = description
        self.function = function
        self.parameters = parameters
        self.clearance_required = clearance_required
        self.category = category
        self.call_count = 0
        self.last_called = None
    
    def execute(self, **kwargs) -> ToolResult:
        """Execute tool with timing, error handling, and tamper-evident audit logging"""
        start_time = time.time()
        self.call_count += 1
        self.last_called = datetime.utcnow().isoformat()
        
        # Audit logging with tamper-evident chain
        audit_entry = None
        audit = None
        try:
            from audit.tamper_evident import get_tamper_evident_audit, AuditEventType
            audit = get_tamper_evident_audit()
            audit_entry = audit.create_entry(
                event_type=AuditEventType.AGENT_TOOL_EXECUTED,
                user_id=kwargs.get("_agent_id", "system"),
                user_clearance=kwargs.get("_clearance", "SECRET"),
                resource_id=self.name,
                action="execute_tool",
                status="started",
                details={
                    "category": self.category,
                    "clearance_required": self.clearance_required,
                    "parameters": {k: v for k, v in kwargs.items() if not k.startswith('_')}
                },
                classification=self.clearance_required
            )
        except Exception as e:
            logger.debug(f"[AUDIT] Could not create audit entry: {e}")
        
        try:
            result = self.function(**kwargs)
            execution_time = int((time.time() - start_time) * 1000)
            
            # Log success to audit chain
            if audit and audit_entry:
                try:
                    audit.create_entry(
                        event_type=AuditEventType.AGENT_TOOL_EXECUTED,
                        user_id=kwargs.get("_agent_id", "system"),
                        user_clearance=kwargs.get("_clearance", "SECRET"),
                        resource_id=self.name,
                        action="tool_complete",
                        status="success",
                        details={"execution_time_ms": execution_time},
                        classification=self.clearance_required
                    )
                except:
                    pass
            
            return ToolResult(
                tool_name=self.name,
                result=result,
                success=True,
                execution_time_ms=execution_time
            )
        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            logger.error(f"Tool {self.name} failed: {e}")
            
            # Log failure to audit chain
            if audit and audit_entry:
                try:
                    audit.create_entry(
                        event_type=AuditEventType.AGENT_TOOL_EXECUTED,
                        user_id=kwargs.get("_agent_id", "system"),
                        user_clearance=kwargs.get("_clearance", "SECRET"),
                        resource_id=self.name,
                        action="tool_error",
                        status="failed",
                        details={"error": str(e), "execution_time_ms": execution_time},
                        classification=self.clearance_required
                    )
                except:
                    pass
            
            return ToolResult(
                tool_name=self.name,
                result=None,
                success=False,
                error_message=str(e),
                execution_time_ms=execution_time
            )
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for API"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "clearance_required": self.clearance_required,
            "category": self.category,
            "call_count": self.call_count,
            "last_called": self.last_called
        }


class ToolRegistry:
    """Registry of all available tools"""
    
    def __init__(self):
        self.tools: Dict[str, Tool] = {}
        self._lock = threading.RLock()
        self._initialize_tools()
    
    def _initialize_tools(self):
        """Initialize all ORDL tools"""
        # Red Team Tools
        self.register_tool(Tool(
            name="redteam_recon",
            description="Perform reconnaissance scan on target",
            function=self._redteam_recon,
            parameters={
                "target": {"type": "string", "description": "Target host/IP"},
                "ports": {"type": "string", "description": "Port range (e.g., 1-1000)"}
            },
            clearance_required="TS/SCI",
            category="redteam"
        ))
        
        self.register_tool(Tool(
            name="redteam_scan",
            description="Vulnerability scan target",
            function=self._redteam_scan,
            parameters={
                "target": {"type": "string", "description": "Target to scan"},
                "scan_type": {"type": "string", "description": "Type of scan"}
            },
            clearance_required="TS/SCI",
            category="redteam"
        ))
        
        self.register_tool(Tool(
            name="redteam_payload",
            description="Generate payload for deployment",
            function=self._redteam_payload,
            parameters={
                "platform": {"type": "string", "description": "Target platform"},
                "lhost": {"type": "string", "description": "Listener host"},
                "lport": {"type": "integer", "description": "Listener port"}
            },
            clearance_required="TS/SCI",
            category="redteam"
        ))
        
        # Blue Team Tools
        self.register_tool(Tool(
            name="blueteam_status",
            description="Get Blue Team SOC status",
            function=self._blueteam_status,
            parameters={},
            clearance_required="SECRET",
            category="blueteam"
        ))
        
        self.register_tool(Tool(
            name="blueteam_alerts",
            description="Get security alerts",
            function=self._blueteam_alerts,
            parameters={
                "severity": {"type": "string", "description": "Filter by severity"}
            },
            clearance_required="SECRET",
            category="blueteam"
        ))
        
        self.register_tool(Tool(
            name="blueteam_ingest",
            description="Ingest log for analysis",
            function=self._blueteam_ingest,
            parameters={
                "source_type": {"type": "string", "description": "Log source type"},
                "source_host": {"type": "string", "description": "Source hostname"},
                "message": {"type": "string", "description": "Log message"}
            },
            clearance_required="SECRET",
            category="blueteam"
        ))
        
        # RAG Tools
        self.register_tool(Tool(
            name="rag_search",
            description="Search knowledge base",
            function=self._rag_search,
            parameters={
                "query": {"type": "string", "description": "Search query"},
                "top_k": {"type": "integer", "description": "Number of results"}
            },
            clearance_required="CONFIDENTIAL",
            category="rag"
        ))
        
        self.register_tool(Tool(
            name="rag_ingest",
            description="Ingest document to knowledge base",
            function=self._rag_ingest,
            parameters={
                "content": {"type": "string", "description": "Document content"},
                "title": {"type": "string", "description": "Document title"},
                "category": {"type": "string", "description": "Document category"}
            },
            clearance_required="CONFIDENTIAL",
            category="rag"
        ))
        
        # Training Tools
        self.register_tool(Tool(
            name="train_hardware",
            description="Get training hardware info",
            function=self._train_hardware,
            parameters={},
            clearance_required="SECRET",
            category="training"
        ))
        
        self.register_tool(Tool(
            name="train_create_job",
            description="Create training job",
            function=self._train_create_job,
            parameters={
                "name": {"type": "string", "description": "Job name"},
                "base_model": {"type": "string", "description": "Base model"},
                "dataset": {"type": "string", "description": "Dataset path"}
            },
            clearance_required="SECRET",
            category="training"
        ))
        
        # System Tools
        self.register_tool(Tool(
            name="system_time",
            description="Get current system time",
            function=self._system_time,
            parameters={},
            clearance_required="UNCLASSIFIED",
            category="system"
        ))
        
        self.register_tool(Tool(
            name="system_status",
            description="Get system status",
            function=self._system_status,
            parameters={},
            clearance_required="CONFIDENTIAL",
            category="system"
        ))
        
        # Initialize MCP tools
        self._init_mcp_tools()
        
        logger.info(f"[AGENTS] Registered {len(self.tools)} tools (including MCP)")
    
    def _init_mcp_tools(self):
        """Initialize MCP integration tools with proper error handling"""
        try:
            from mcp_integration import get_mcp_registry
            mcp = get_mcp_registry()
            
            # Register MCP tools as agent tools
            mcp_tools = mcp.list_tools()
            
            for mcp_tool in mcp_tools:
                tool_name = f"mcp_{mcp_tool['name']}"
                
                # Create wrapper function with proper closure
                def make_mcp_wrapper(mcp_ref, tool_name_inner):
                    tool_name_clean = tool_name_inner.replace("mcp_", "")
                    def mcp_wrapper(**kwargs):
                        try:
                            result = mcp_ref.execute_tool(tool_name_clean, **kwargs)
                            if result.success:
                                return result.result if result.result else {"status": "completed"}
                            else:
                                return {"error": result.error or "Tool execution failed"}
                        except Exception as e:
                            logger.error(f"MCP tool {tool_name_clean} failed: {e}")
                            return {"error": str(e)}
                    return mcp_wrapper
                
                self.register_tool(Tool(
                    name=tool_name,
                    description=f"[MCP] {mcp_tool['description']}",
                    function=make_mcp_wrapper(mcp, tool_name),
                    parameters={"args": {"type": "object", "description": "Tool arguments"}},
                    clearance_required="SECRET",
                    category=f"mcp_{mcp_tool['category']}"
                ))
            
            logger.info(f"[AGENTS] Registered {len(mcp_tools)} MCP tools")
        except Exception as e:
            logger.warning(f"[AGENTS] MCP tools not available: {e}")
    
    # Tool implementations
    def _redteam_recon(self, target: str, ports: str = "1-1000") -> Dict:
        """Red Team reconnaissance"""
        try:
            from redteam import get_redteam_manager
            rt = get_redteam_manager()
            op_id = rt.create_operation(f"recon_{target}", "reconnaissance")
            result = rt.recon.run_scan(target, ports)
            return {"operation_id": op_id, "result": result}
        except Exception as e:
            return {"error": str(e)}
    
    def _redteam_scan(self, target: str, scan_type: str = "quick") -> Dict:
        """Red Team vulnerability scan"""
        try:
            from redteam import get_redteam_manager
            rt = get_redteam_manager()
            return {"target": target, "scan_type": scan_type, "status": "scan_initiated"}
        except Exception as e:
            return {"error": str(e)}
    
    def _redteam_payload(self, platform: str, lhost: str, lport: int) -> Dict:
        """Generate payload"""
        try:
            from redteam import get_redteam_manager
            rt = get_redteam_manager()
            from redteam.payload import PayloadPlatform
            plat = PayloadPlatform(platform.upper())
            payload = rt.payload_gen.generate_reverse_shell(plat, lhost=lhost, lport=lport)
            return {
                "payload_id": payload.payload_id,
                "md5": payload.md5_hash,
                "sha256": payload.sha256_hash,
                "content_b64": payload.content_b64[:100] + "..."
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _blueteam_status(self) -> Dict:
        """Get Blue Team status"""
        try:
            from blueteam import get_blueteam_manager
            bt = get_blueteam_manager()
            return bt.get_stats()
        except Exception as e:
            return {"error": str(e)}
    
    def _blueteam_alerts(self, severity: Optional[str] = None) -> List[Dict]:
        """Get Blue Team alerts"""
        try:
            from blueteam import get_blueteam_manager
            bt = get_blueteam_manager()
            from blueteam import AlertSeverity
            sev = AlertSeverity(severity.upper()) if severity else None
            alerts = bt.get_alerts(severity=sev)
            return [a.to_dict() for a in alerts[:10]]
        except Exception as e:
            return {"error": str(e)}
    
    def _blueteam_ingest(self, source_type: str, source_host: str, message: str) -> Dict:
        """Ingest log to Blue Team"""
        try:
            from blueteam import get_blueteam_manager
            bt = get_blueteam_manager()
            from blueteam import LogSource
            entry = bt.ingest_log(LogSource(source_type.lower()), source_host, message)
            return {"entry_id": entry.entry_id, "alert_triggered": entry.alert_triggered}
        except Exception as e:
            return {"error": str(e)}
    
    def _rag_search(self, query: str, top_k: int = 5) -> List[Dict]:
        """Search RAG knowledge base"""
        try:
            from rag.vector_kb import get_knowledge_base
            kb = get_knowledge_base()
            results = kb.query(query, top_k=top_k)
            return [r.to_dict() for r in results]
        except Exception as e:
            return {"error": str(e)}
    
    def _rag_ingest(self, content: str, title: str, category: str = "general") -> Dict:
        """Ingest document to RAG"""
        try:
            from rag.vector_kb import get_knowledge_base
            kb = get_knowledge_base()
            doc_id = kb.ingest_document(content, title, category)
            return {"document_id": doc_id}
        except Exception as e:
            return {"error": str(e)}
    
    def _train_hardware(self) -> Dict:
        """Get training hardware info"""
        try:
            from training.unsloth_trainer import get_trainer
            trainer = get_trainer()
            return trainer.get_hardware_info()
        except Exception as e:
            return {"error": str(e)}
    
    def _train_create_job(self, name: str, base_model: str, dataset: str) -> Dict:
        """Create training job"""
        try:
            from training.unsloth_trainer import get_trainer
            trainer = get_trainer()
            config = {
                "job_id": f"job-{int(time.time())}",
                "name": name,
                "base_model": base_model,
                "output_model": f"{name}-finetuned",
                "dataset_source": "huggingface",
                "dataset_path": dataset,
                "max_steps": 100
            }
            job = trainer.create_job(config)
            return job.to_dict()
        except Exception as e:
            return {"error": str(e)}
    
    def _system_time(self) -> str:
        """Get system time"""
        return datetime.utcnow().isoformat()
    
    def _system_status(self) -> Dict:
        """Get system status"""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "agents_active": 0,  # Will be updated by AgentManager
            "tasks_pending": 0,
            "memory_usage": "N/A"
        }
    
    def register_tool(self, tool: Tool):
        """Register a new tool"""
        with self._lock:
            self.tools[tool.name] = tool
            logger.info(f"[AGENTS] Registered tool: {tool.name}")
    
    def get_tool(self, name: str) -> Optional[Tool]:
        """Get tool by name"""
        return self.tools.get(name)
    
    def list_tools(self, category: Optional[str] = None) -> List[Dict]:
        """List available tools"""
        tools = self.tools.values()
        if category:
            tools = [t for t in tools if t.category == category]
        return [t.to_dict() for t in tools]
    
    def execute_tool(self, name: str, **kwargs) -> ToolResult:
        """Execute a tool by name"""
        tool = self.get_tool(name)
        if not tool:
            return ToolResult(
                tool_name=name,
                result=None,
                success=False,
                error_message=f"Tool '{name}' not found"
            )
        return tool.execute(**kwargs)


class AgentMemory:
    """Agent conversation memory"""
    
    def __init__(self, agent_id: str, db_path: str = "/opt/codex-swarm/command-post/data/nexus.db"):
        self.agent_id = agent_id
        self.db_path = db_path
        self._messages: List[Message] = []
        self._lock = threading.RLock()
        self._init_db()
    
    def _init_db(self):
        """Initialize memory database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agent_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT,
                role TEXT,
                content TEXT,
                timestamp TEXT,
                metadata TEXT,
                tool_calls TEXT,
                tool_call_id TEXT
            )
        ''')
        conn.commit()
        conn.close()
    
    def add_message(self, message: Message):
        """Add message to memory"""
        with self._lock:
            self._messages.append(message)
            
            # Persist to database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO agent_memory 
                (agent_id, role, content, timestamp, metadata, tool_calls, tool_call_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                self.agent_id,
                message.role,
                message.content,
                message.timestamp,
                json.dumps(message.metadata),
                json.dumps(message.tool_calls) if message.tool_calls else None,
                message.tool_call_id
            ))
            conn.commit()
            conn.close()
    
    def get_messages(self, limit: int = 50) -> List[Message]:
        """Get recent messages"""
        return self._messages[-limit:]
    
    def get_context(self, max_tokens: int = 4000) -> List[Dict]:
        """Get conversation context for LLM"""
        messages = []
        total_length = 0
        
        for msg in reversed(self._messages):
            msg_dict = {
                "role": msg.role,
                "content": msg.content
            }
            if msg.tool_calls:
                msg_dict["tool_calls"] = msg.tool_calls
            if msg.tool_call_id:
                msg_dict["tool_call_id"] = msg.tool_call_id
            
            msg_length = len(json.dumps(msg_dict))
            if total_length + msg_length > max_tokens:
                break
            
            messages.insert(0, msg_dict)
            total_length += msg_length
        
        return messages
    
    def clear(self):
        """Clear memory"""
        with self._lock:
            self._messages = []
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM agent_memory WHERE agent_id = ?", (self.agent_id,))
            conn.commit()
            conn.close()


class Agent:
    """
    Military-grade AI Agent
    
    Manages agent lifecycle, tool use, and conversation.
    """
    
    def __init__(self, config: AgentConfig, tool_registry: ToolRegistry):
        self.config = config
        self.status = AgentStatus.IDLE
        self.tool_registry = tool_registry
        self.memory = AgentMemory(config.agent_id)
        self.tasks_completed = 0
        self.current_task: Optional[Task] = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._lock = threading.RLock()
        self.created_at = datetime.utcnow().isoformat()
        self.last_active = None
        self.error_count = 0
        self.llm_bridge = None
        self._llm_initialized = False
        
        # Add system message
        self.memory.add_message(Message(
            role="system",
            content=f"You are {config.name}, an AI agent with {config.clearance} clearance. "
                   f"Persona: {config.persona}. You have access to tools. Use them when helpful."
        ))
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        llm_status = "connected" if (hasattr(self, 'llm_bridge') and self.llm_bridge) else "offline"
        return {
            "agent_id": self.config.agent_id,
            "name": self.config.name,
            "status": self.status.value,
            "model": self.config.model,
            "clearance": self.config.clearance,
            "capabilities": self.config.capabilities,
            "tasks_completed": self.tasks_completed,
            "current_task": self.current_task.task_id if self.current_task else None,
            "created_at": self.created_at,
            "last_active": self.last_active,
            "error_count": self.error_count,
            "memory_messages": len(self.memory._messages),
            "llm_status": llm_status
        }
    
    def process_message(self, message: str) -> Dict:
        """Process user message and generate response"""
        with self._lock:
            self.status = AgentStatus.PROCESSING
            self.last_active = datetime.utcnow().isoformat()
            
            try:
                # Add user message
                self.memory.add_message(Message(role="user", content=message))
                
                # Check for tool calls in message (simple pattern matching)
                tool_calls = self._extract_tool_calls(message)
                
                if tool_calls and self.config.auto_tool_use:
                    # Execute tools
                    tool_results = []
                    for tc in tool_calls:
                        result = self.tool_registry.execute_tool(tc["tool"], **tc["args"])
                        tool_results.append(result)
                    
                    # Generate response with tool results
                    response = self._generate_response_with_tools(message, tool_results)
                else:
                    # Generate direct response
                    response = self._generate_response(message)
                
                # Add assistant message
                self.memory.add_message(Message(role="assistant", content=response))
                
                self.tasks_completed += 1
                self.status = AgentStatus.IDLE
                self.error_count = 0
                
                return {
                    "success": True,
                    "response": response,
                    "tool_calls_executed": len(tool_calls) if tool_calls else 0
                }
                
            except Exception as e:
                logger.error(f"Agent {self.config.agent_id} error: {e}")
                self.status = AgentStatus.ERROR
                self.error_count += 1
                return {
                    "success": False,
                    "error": str(e),
                    "traceback": traceback.format_exc()
                }
    
    def _extract_tool_calls(self, message: str) -> List[Dict]:
        """Extract tool calls from message (pattern: @tool_name(args))"""
        import re
        tool_calls = []
        
        # Pattern: @tool_name(key=value, key2=value2)
        pattern = r'@(\w+)\(([^)]*)\)'
        matches = re.findall(pattern, message)
        
        for tool_name, args_str in matches:
            # Parse arguments
            args = {}
            if args_str:
                for pair in args_str.split(','):
                    if '=' in pair:
                        key, value = pair.split('=', 1)
                        args[key.strip()] = value.strip().strip('"\'')
            
            tool_calls.append({"tool": tool_name, "args": args})
        
        return tool_calls
    
    def _init_llm_bridge(self):
        """Initialize LLM bridge for real inference (lazy initialization)"""
        if self._llm_initialized:
            return self.llm_bridge is not None
        
        self._llm_initialized = True
        
        # Ensure event loop exists for this thread
        try:
            import asyncio
            asyncio.get_running_loop()
        except RuntimeError:
            # No event loop in this thread, create one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        try:
            from llm import LLMProviderFactory, LLMAgentBridge
            
            # Create provider based on config
            if self.config.model.startswith("ollama/"):
                model_name = self.config.model.replace("ollama/", "")
            else:
                model_name = "qwen2.5-coder:14b"  # Default to available model
            
            provider = LLMProviderFactory.create(
                "ollama",
                model=model_name,
                temperature=self.config.temperature
            )
            
            # Create bridge
            self.llm_bridge = LLMAgentBridge(
                provider=provider,
                tool_registry=self.tool_registry,
                system_prompt=f"You are {self.config.name}, an AI agent with {self.config.clearance} clearance. "
                             f"Persona: {self.config.persona}. You have access to tools. "
                             f"Use them when helpful to complete tasks.",
                max_context_tokens=self.config.max_context_length,
                max_tool_iterations=10
            )
            
            logger.info(f"[AGENT] LLM bridge initialized for {self.config.name} with model {model_name}")
            return True
            
        except Exception as e:
            logger.error(f"[AGENT] Failed to initialize LLM bridge: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.llm_bridge = None
            return False
    
    def _generate_response(self, message: str) -> str:
        """Generate response using LLM with tool execution loop"""
        # Initialize LLM bridge lazily
        if not self._init_llm_bridge():
            # Fallback to basic response if LLM unavailable
            return self._fallback_response(message)
        
        try:
            # Run async LLM processing in sync context
            import asyncio
            from llm.error_handler import ResponseFormatter
            
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Process message through LLM bridge
                result = loop.run_until_complete(
                    self.llm_bridge.process_message(message)
                )
                
                if result.get("success"):
                    content = result.get("content", "")
                    # Ensure content is a string
                    if not isinstance(content, str):
                        content = str(content)
                    return content
                else:
                    error_msg = result.get('error', 'Unknown error')
                    logger.error(f"[AGENT] LLM processing failed: {error_msg}")
                    return f"[SYSTEM ERROR] {error_msg}"
            finally:
                try:
                    # Cancel all pending tasks
                    pending = asyncio.all_tasks(loop)
                    for task in pending:
                        task.cancel()
                    # Close the loop
                    loop.close()
                except Exception as cleanup_e:
                    logger.debug(f"[AGENT] Loop cleanup error: {cleanup_e}")
                
        except Exception as e:
            logger.error(f"[AGENT] LLM generation failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return self._fallback_response(message)
    
    def _fallback_response(self, message: str) -> str:
        """Fallback response when LLM is unavailable"""
        lower_msg = message.lower()
        
        if "help" in lower_msg or "tools" in lower_msg:
            tools = self.tool_registry.list_tools()
            tool_list = "\n".join([f"  - {t['name']}: {t['description']}" for t in tools[:10]])
            return f"[OFFLINE MODE] Available tools:\n{tool_list}\n\nUse @tool_name(args) to call a tool."
        
        elif "status" in lower_msg:
            return f"I am {self.config.name}, status: {self.status.value} (LLM offline). Tasks completed: {self.tasks_completed}."
        
        else:
            return f"[OFFLINE MODE] I understand: '{message}'. LLM inference currently unavailable. Basic tool execution still functional."
    
    def _generate_response_with_tools(self, message: str, tool_results: List[ToolResult]) -> str:
        """Generate response incorporating tool results"""
        # Initialize and use LLM bridge if available
        if self._init_llm_bridge() and self.llm_bridge:
            try:
                import asyncio
                
                # Create new event loop for this thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    # Process through LLM which will handle tool results
                    tool_results_json = json.dumps([{
                        "tool": r.tool_name,
                        "success": r.success,
                        "result": r.result if r.success else None,
                        "error": r.error_message if not r.success else None
                    } for r in tool_results])
                    
                    result = loop.run_until_complete(
                        self.llm_bridge.process_message(
                            f"I executed tools and got these results: {tool_results_json}"
                        )
                    )
                    
                    if result["success"]:
                        return result["content"]
                finally:
                    loop.close()
                    
            except Exception as e:
                logger.error(f"[AGENT] LLM tool response failed: {e}")
        
        # Fallback: format tool results directly
        responses = []
        for result in tool_results:
            if result.success:
                responses.append(f"[{result.tool_name}] Result: {json.dumps(result.result, indent=2)[:500]}")
            else:
                responses.append(f"[{result.tool_name}] Error: {result.error_message}")
        
        return "\n\n".join(responses)
    
    def execute_task(self, task: Task) -> Any:
        """Execute a task"""
        self.current_task = task
        task.started_at = datetime.utcnow().isoformat()
        task.status = "running"
        
        try:
            # Process the task description as a message
            result = self.process_message(task.description)
            
            task.status = "completed" if result["success"] else "failed"
            task.completed_at = datetime.utcnow().isoformat()
            task.result = result
            
            return result
            
        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            task.completed_at = datetime.utcnow().isoformat()
            raise
        finally:
            self.current_task = None
    
    def stop(self):
        """Stop agent"""
        self._stop_event.set()
        self.status = AgentStatus.STOPPING
    
    def pause(self):
        """Pause agent"""
        self._pause_event.set()
        self.status = AgentStatus.PAUSED
    
    def resume(self):
        """Resume agent"""
        self._pause_event.clear()
        self.status = AgentStatus.IDLE
    
    def destroy(self):
        """Destroy agent and cleanup"""
        self.stop()
        self.memory.clear()
        self.status = AgentStatus.DESTROYED


# Export classes
__all__ = [
    'Agent',
    'AgentConfig',
    'AgentStatus',
    'AgentMemory',
    'Tool',
    'ToolRegistry',
    'ToolResult',
    'Task',
    'TaskPriority',
    'Message'
]
