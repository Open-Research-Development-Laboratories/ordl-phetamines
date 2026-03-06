#!/usr/bin/env python3
"""
ORDL AGENT TOOLS - Extended Tool Suite
Military-grade tool implementations for AI agents
"""

import os
import json
import time
import uuid
import sqlite3
import requests
from datetime import datetime
from typing import Dict, Any, List, Optional

# Import core modules
import sys
sys.path.insert(0, '/opt/codex-swarm/command-post')


def tool_system_status() -> Dict[str, Any]:
    """Get comprehensive system status"""
    import psutil
    
    cpu = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    return {
        'timestamp': datetime.utcnow().isoformat(),
        'cpu': {
            'percent': cpu,
            'cores': psutil.cpu_count()
        },
        'memory': {
            'percent': memory.percent,
            'used_gb': round(memory.used / (1024**3), 2),
            'total_gb': round(memory.total / (1024**3), 2)
        },
        'disk': {
            'percent': disk.percent,
            'free_gb': round(disk.free / (1024**3), 2)
        }
    }


def tool_system_info() -> Dict[str, Any]:
    """Get system information"""
    import platform
    
    return {
        'platform': platform.platform(),
        'python_version': platform.python_version(),
        'machine': platform.machine(),
        'processor': platform.processor(),
        'hostname': platform.node()
    }


def tool_list_agents() -> List[Dict]:
    """List all active agents"""
    try:
        from agents import get_agent_manager
        manager = get_agent_manager()
        return manager.list_agents()
    except Exception as e:
        return {'error': str(e)}


def tool_send_agent_message(agent_id: str, message: str) -> Dict:
    """Send message to an agent"""
    try:
        from agents import get_agent_manager
        manager = get_agent_manager()
        return manager.send_message(agent_id, message)
    except Exception as e:
        return {'error': str(e)}


def tool_create_task(description: str, priority: str = "MEDIUM", agent_id: str = None) -> Dict:
    """Create a new task"""
    try:
        from agents import get_agent_manager, TaskPriority
        manager = get_agent_manager()
        
        priority_enum = TaskPriority[priority.upper()]
        task = manager.create_task(description, priority_enum, agent_id)
        
        return {
            'task_id': task.task_id,
            'description': task.description,
            'priority': priority,
            'status': task.status
        }
    except Exception as e:
        return {'error': str(e)}


def tool_blueteam_status() -> Dict:
    """Get Blue Team SOC status"""
    try:
        from blueteam import get_blueteam_manager
        bt = get_blueteam_manager()
        return bt.get_stats()
    except Exception as e:
        return {'error': str(e)}


def tool_blueteam_alerts(severity: str = None) -> List[Dict]:
    """Get Blue Team alerts"""
    try:
        from blueteam import get_blueteam_manager, AlertSeverity
        bt = get_blueteam_manager()
        
        if severity:
            sev = AlertSeverity(severity.upper())
            alerts = bt.get_alerts(severity=sev)
        else:
            alerts = bt.get_alerts()
        
        return [a.to_dict() for a in alerts]
    except Exception as e:
        return {'error': str(e)}


def tool_rag_search(query: str, top_k: int = 5) -> List[Dict]:
    """Search RAG knowledge base"""
    try:
        from rag.vector_kb import get_knowledge_base
        kb = get_knowledge_base()
        results = kb.query(query, top_k=top_k)
        return [r.to_dict() for r in results]
    except Exception as e:
        return {'error': str(e)}


def tool_rag_ingest(content: str, title: str, category: str = "general") -> Dict:
    """Ingest document to RAG"""
    try:
        from rag.vector_kb import get_knowledge_base
        kb = get_knowledge_base()
        doc_id = kb.ingest_document(content, title, category)
        return {'document_id': doc_id, 'status': 'success'}
    except Exception as e:
        return {'error': str(e)}


def tool_network_scan(target: str, ports: str = "1-1000") -> Dict:
    """Perform network port scan"""
    try:
        from redteam import get_redteam_manager
        rt = get_redteam_manager()
        result = rt.recon.run_scan(target, ports)
        return result
    except Exception as e:
        return {'error': str(e)}


def tool_training_hardware() -> Dict:
    """Get training hardware info"""
    try:
        from training.unsloth_trainer import get_trainer
        trainer = get_trainer()
        return trainer.get_hardware_info()
    except Exception as e:
        return {'error': str(e)}


def tool_search_web(query: str, limit: int = 10) -> Dict:
    """Search the web (if search module available)"""
    try:
        from search.engine import get_search_engine
        engine = get_search_engine()
        results = engine.search(query, limit=limit)
        return {'query': query, 'results': results}
    except Exception as e:
        return {'error': str(e)}


def tool_read_file(path: str) -> Dict:
    """Read file from filesystem"""
    try:
        with open(path, 'r') as f:
            content = f.read()
        return {'path': path, 'content': content, 'size': len(content)}
    except Exception as e:
        return {'error': str(e)}


def tool_write_file(path: str, content: str) -> Dict:
    """Write file to filesystem"""
    try:
        with open(path, 'w') as f:
            f.write(content)
        return {'path': path, 'status': 'written', 'size': len(content)}
    except Exception as e:
        return {'error': str(e)}


def tool_execute_shell(command: str, timeout: int = 30) -> Dict:
    """Execute shell command (restricted)"""
    import subprocess
    
    # Security: Restrict dangerous commands
    blocked = ['rm -rf /', 'mkfs', 'dd if=', '>:', 'format']
    for b in blocked:
        if b in command:
            return {'error': f'Command blocked for security: {b}'}
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return {
            'command': command,
            'returncode': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr
        }
    except Exception as e:
        return {'error': str(e)}


# Tool registry for extended tools
EXTENDED_TOOLS = {
    'system_status': {
        'function': tool_system_status,
        'description': 'Get comprehensive system status',
        'parameters': {}
    },
    'system_info': {
        'function': tool_system_info,
        'description': 'Get system information',
        'parameters': {}
    },
    'list_agents': {
        'function': tool_list_agents,
        'description': 'List all active agents',
        'parameters': {}
    },
    'send_agent_message': {
        'function': tool_send_agent_message,
        'description': 'Send message to an agent',
        'parameters': {
            'agent_id': 'string',
            'message': 'string'
        }
    },
    'create_task': {
        'function': tool_create_task,
        'description': 'Create a new task',
        'parameters': {
            'description': 'string',
            'priority': 'string (LOW/MEDIUM/HIGH/CRITICAL)',
            'agent_id': 'string (optional)'
        }
    },
    'search_web': {
        'function': tool_search_web,
        'description': 'Search the web',
        'parameters': {
            'query': 'string',
            'limit': 'integer (optional)'
        }
    },
    'read_file': {
        'function': tool_read_file,
        'description': 'Read file from filesystem',
        'parameters': {
            'path': 'string'
        }
    },
    'write_file': {
        'function': tool_write_file,
        'description': 'Write file to filesystem',
        'parameters': {
            'path': 'string',
            'content': 'string'
        }
    },
    'execute_shell': {
        'function': tool_execute_shell,
        'description': 'Execute shell command (restricted)',
        'parameters': {
            'command': 'string',
            'timeout': 'integer (optional)'
        }
    }
}


def get_extended_tools() -> Dict[str, Any]:
    """Get extended tool definitions"""
    return EXTENDED_TOOLS


def execute_extended_tool(tool_name: str, **kwargs) -> Dict:
    """Execute an extended tool"""
    if tool_name not in EXTENDED_TOOLS:
        return {'error': f'Unknown tool: {tool_name}'}
    
    tool = EXTENDED_TOOLS[tool_name]
    func = tool['function']
    
    try:
        return func(**kwargs)
    except Exception as e:
        return {'error': str(e)}
