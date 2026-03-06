#!/usr/bin/env python3
"""
A2A Echo Agent Example
A simple agent that echoes back messages with metadata.
"""

import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any
from datetime import datetime

from a2a.types import AgentCard, AgentSkill


class EchoHandler(BaseHTTPRequestHandler):
    """HTTP handler for A2A echo requests"""
    
    agent_card = AgentCard(
        name="echo-agent",
        description="Echoes back messages with timestamp and metadata",
        url="http://localhost:8002",
        version="1.0.0",
        capabilities={},
        defaultInputModes=["text"],
        defaultOutputModes=["text"],
        skills=[
            AgentSkill(
                id="echo",
                name="Echo",
                description="Echo back the input message",
                tags=["utility", "echo"]
            ),
            AgentSkill(
                id="time",
                name="Current Time",
                description="Return current server time",
                tags=["utility", "time"]
            )
        ]
    )
    
    def do_GET(self):
        """Handle GET requests - return agent card"""
        if self.path == "/agent-card" or self.path == "/.well-known/agent.json":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(self.agent_card.model_dump_json().encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        """Handle POST requests - process tasks"""
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            request = json.loads(post_data)
            method = request.get('method', '')
            
            if method == 'tasks/send':
                response = self.handle_task_send(request)
            elif method == 'tasks/get':
                response = self.handle_task_get(request)
            else:
                response = {
                    "jsonrpc": "2.0",
                    "id": request.get('id'),
                    "error": {"code": -32601, "message": "Method not found"}
                }
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())
    
    def handle_task_send(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle task send request"""
        params = request.get('params', {})
        task_id = params.get('id', 'task-1')
        message = params.get('message', {})
        
        # Extract text from message
        text = ""
        if 'parts' in message:
            for part in message['parts']:
                if part.get('type') == 'text':
                    text = part.get('text', '')
                    break
        
        # Create echo response
        response_text = f"""
ECHO RESPONSE
=============
Original message: {text}
Timestamp: {datetime.now().isoformat()}
Task ID: {task_id}
Message length: {len(text)} characters
Word count: {len(text.split()) if text else 0}
"""
        
        return {
            "jsonrpc": "2.0",
            "id": request.get('id'),
            "result": {
                "id": task_id,
                "status": "completed",
                "artifacts": [{
                    "parts": [{
                        "type": "text",
                        "text": response_text
                    }]
                }]
            }
        }
    
    def handle_task_get(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle task get request"""
        return {
            "jsonrpc": "2.0",
            "id": request.get('id'),
            "result": {"status": "completed"}
        }
    
    def log_message(self, format, *args):
        """Suppress default logging"""
        pass


def main():
    """Start the echo agent"""
    server = HTTPServer(('0.0.0.0', 8002), EchoHandler)
    print("Starting Echo Agent on http://localhost:8002")
    print("Press Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()


if __name__ == "__main__":
    main()
