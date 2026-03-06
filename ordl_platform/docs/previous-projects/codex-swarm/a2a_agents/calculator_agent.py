#!/usr/bin/env python3
"""
A2A Calculator Agent Example
A simple agent that performs mathematical calculations.
"""

import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any

# Use correct a2a imports
from a2a.types import AgentCard, AgentSkill


class CalculatorHandler(BaseHTTPRequestHandler):
    """HTTP handler for A2A requests"""
    
    agent_card = AgentCard(
        name="calculator-agent",
        description="A simple calculator that performs mathematical operations",
        url="http://localhost:8001",
        version="1.0.0",
        capabilities={},
        defaultInputModes=["text"],
        defaultOutputModes=["text"],
        skills=[
            AgentSkill(
                id="add",
                name="Add",
                description="Add two numbers",
                tags=["math", "addition"]
            ),
            AgentSkill(
                id="subtract",
                name="Subtract",
                description="Subtract two numbers",
                tags=["math", "subtraction"]
            ),
            AgentSkill(
                id="multiply",
                name="Multiply",
                description="Multiply two numbers",
                tags=["math", "multiplication"]
            ),
            AgentSkill(
                id="divide",
                name="Divide",
                description="Divide two numbers",
                tags=["math", "division"]
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
        
        # Parse calculation
        try:
            data = json.loads(text) if text else {}
            operation = data.get('operation', '')
            a = float(data.get('a', 0))
            b = float(data.get('b', 0))
            
            # Calculate
            if operation == 'add':
                result = a + b
            elif operation == 'subtract':
                result = a - b
            elif operation == 'multiply':
                result = a * b
            elif operation == 'divide':
                if b == 0:
                    raise ValueError("Division by zero")
                result = a / b
            else:
                raise ValueError(f"Unknown operation: {operation}")
            
            return {
                "jsonrpc": "2.0",
                "id": request.get('id'),
                "result": {
                    "id": task_id,
                    "status": "completed",
                    "artifacts": [{
                        "parts": [{
                            "type": "text",
                            "text": json.dumps({
                                "operation": operation,
                                "a": a,
                                "b": b,
                                "result": result
                            })
                        }]
                    }]
                }
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": request.get('id'),
                "result": {
                    "id": task_id,
                    "status": "failed",
                    "error": str(e)
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
    """Start the calculator agent"""
    server = HTTPServer(('0.0.0.0', 8001), CalculatorHandler)
    print("Starting Calculator Agent on http://localhost:8001")
    print("Available operations: add, subtract, multiply, divide")
    print("Press Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()


if __name__ == "__main__":
    main()
