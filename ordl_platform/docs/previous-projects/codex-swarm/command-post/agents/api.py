#!/usr/bin/env python3
"""
ORDL Agent System REST API
"""

import json
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify

from . import get_agent_manager, AgentConfig, TaskPriority

logger = logging.getLogger('agents.api')

agents_bp = Blueprint('agents', __name__, url_prefix='/api/agents')

manager = None

def init_agents_api(agent_manager):
    """Initialize API with manager instance"""
    global manager
    manager = agent_manager
    logger.info("[AGENTS] API initialized")


@agents_bp.route('/health', methods=['GET'])
def health():
    """Agent system health check"""
    try:
        stats = manager.get_stats()
        return jsonify({
            "status": "healthy",
            "module": "agents",
            "stats": stats,
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@agents_bp.route('/agents', methods=['GET'])
def list_agents():
    """List all agents"""
    try:
        agents = manager.list_agents()
        return jsonify({
            "status": "success",
            "count": len(agents),
            "agents": agents,
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@agents_bp.route('/agents', methods=['POST'])
def create_agent():
    """Create new agent"""
    try:
        data = request.get_json()
        
        required = ['name', 'persona']
        for field in required:
            if field not in data:
                return jsonify({
                    "status": "error",
                    "message": f"Missing required field: {field}"
                }), 400
        
        agent = manager.create_agent(data)
        
        return jsonify({
            "status": "success",
            "agent": agent.to_dict(),
            "timestamp": datetime.utcnow().isoformat()
        }), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@agents_bp.route('/agents/<agent_id>', methods=['GET'])
def get_agent(agent_id):
    """Get agent details"""
    try:
        agent = manager.get_agent(agent_id)
        if not agent:
            return jsonify({
                "status": "error",
                "message": "Agent not found"
            }), 404
        
        return jsonify({
            "status": "success",
            "agent": agent.to_dict(),
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@agents_bp.route('/agents/<agent_id>', methods=['DELETE'])
def destroy_agent(agent_id):
    """Destroy agent"""
    try:
        if manager.destroy_agent(agent_id):
            return jsonify({
                "status": "success",
                "message": f"Agent {agent_id} destroyed",
                "timestamp": datetime.utcnow().isoformat()
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Agent not found"
            }), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@agents_bp.route('/agents/<agent_id>/message', methods=['POST'])
def send_message(agent_id):
    """Send message to agent"""
    try:
        data = request.get_json()
        message = data.get('message')
        
        if not message:
            return jsonify({
                "status": "error",
                "message": "Missing 'message' field"
            }), 400
        
        result = manager.send_message(agent_id, message)
        
        return jsonify({
            "status": "success" if result.get("success") else "error",
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@agents_bp.route('/agents/<agent_id>/memory', methods=['GET'])
def get_agent_memory(agent_id):
    """Get agent conversation memory"""
    try:
        agent = manager.get_agent(agent_id)
        if not agent:
            return jsonify({
                "status": "error",
                "message": "Agent not found"
            }), 404
        
        messages = agent.memory.get_messages()
        
        return jsonify({
            "status": "success",
            "agent_id": agent_id,
            "messages": [
                {
                    "role": m.role,
                    "content": m.content,
                    "timestamp": m.timestamp
                }
                for m in messages
            ],
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@agents_bp.route('/tools', methods=['GET'])
def list_tools():
    """List available tools"""
    try:
        category = request.args.get('category')
        tools = manager.get_tools()
        
        if category:
            tools = [t for t in tools if t.get('category') == category]
        
        return jsonify({
            "status": "success",
            "count": len(tools),
            "tools": tools,
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@agents_bp.route('/tools/<tool_name>/execute', methods=['POST'])
def execute_tool(tool_name):
    """Execute tool directly"""
    try:
        data = request.get_json() or {}
        result = manager.execute_tool(tool_name, **data)
        
        return jsonify({
            "status": "success" if result.get("success") else "error",
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@agents_bp.route('/tasks', methods=['POST'])
def create_task():
    """Create new task"""
    try:
        data = request.get_json()
        
        description = data.get('description')
        if not description:
            return jsonify({
                "status": "error",
                "message": "Missing 'description' field"
            }), 400
        
        priority_str = data.get('priority', 'MEDIUM')
        priority = TaskPriority[priority_str.upper()]
        
        task = manager.create_task(
            description=description,
            priority=priority,
            agent_id=data.get('agent_id'),
            payload=data.get('payload')
        )
        
        return jsonify({
            "status": "success",
            "task": {
                "task_id": task.task_id,
                "description": task.description,
                "priority": priority_str,
                "status": task.status
            },
            "timestamp": datetime.utcnow().isoformat()
        }), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@agents_bp.route('/stats', methods=['GET'])
def get_stats():
    """Get agent system statistics"""
    try:
        stats = manager.get_stats()
        return jsonify({
            "status": "success",
            "stats": stats,
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
