#!/usr/bin/env python3
"""
ORDL MCP (Model Context Protocol) Server
Full implementation with stdio, SSE, and HTTP transports
Classification: TOP SECRET//NOFORN
"""
import os
import sys
import json
import asyncio
import aiohttp
import logging
from typing import Dict, Any, List, Optional, Callable, AsyncIterator
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from contextlib import asynccontextmanager

# Flask imports for HTTP transport
from flask import Flask, request, jsonify, Response, stream_with_context

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp_server")


class MCPTransport(Enum):
    STDIO = "stdio"
    SSE = "sse"
    HTTP = "http"


@dataclass
class MCPTool:
    """MCP Tool definition"""
    name: str
    description: str
    input_schema: Dict[str, Any]
    handler: Optional[Callable] = None


@dataclass
class MCPResource:
    """MCP Resource definition"""
    uri: str
    name: str
    description: str
    mime_type: str = "application/json"
    handler: Optional[Callable] = None


@dataclass
class MCPPrompt:
    """MCP Prompt definition"""
    name: str
    description: str
    arguments: List[Dict[str, Any]]
    handler: Optional[Callable] = None


class MCPError(Exception):
    """MCP Protocol Error"""
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


class MCPServer:
    """
    Full MCP (Model Context Protocol) Server Implementation
    Supports stdio, SSE, and HTTP transports
    Protocol Version: 2024-11-05
    """
    
    PROTOCOL_VERSION = "2024-11-05"
    
    def __init__(self, name: str = "ordl-mcp-server", version: str = "1.0.0",
                 transport: MCPTransport = MCPTransport.STDIO):
        self.name = name
        self.version = version
        self.transport_type = transport
        
        # Registries
        self.tools: Dict[str, MCPTool] = {}
        self.resources: Dict[str, MCPResource] = {}
        self.prompts: Dict[str, MCPPrompt] = {}
        
        # Client sessions for stdio/SSE
        self.sessions: Dict[str, Dict[str, Any]] = {}
        
        # SSE clients
        self.sse_clients: set = set()
        
        # HTTP Flask app
        self.http_app: Optional[Flask] = None
        
        # Initialize default tools
        self._register_default_tools()
    
    def _register_default_tools(self):
        """Register default ORDL tools"""
        self.register_tool(
            name="system_info",
            description="Get system information",
            input_schema={
                "type": "object",
                "properties": {
                    "component": {
                        "type": "string",
                        "enum": ["cpu", "memory", "disk", "network", "all"],
                        "description": "Which component to query"
                    }
                }
            },
            handler=self._handle_system_info
        )
        
        self.register_tool(
            name="search_knowledge",
            description="Search the knowledge base",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "top_k": {"type": "integer", "default": 5}
                },
                "required": ["query"]
            },
            handler=self._handle_search_knowledge
        )
        
        self.register_tool(
            name="execute_code",
            description="Execute code in sandbox",
            input_schema={
                "type": "object",
                "properties": {
                    "language": {"type": "string", "enum": ["python", "c", "java"]},
                    "code": {"type": "string"},
                    "timeout": {"type": "integer", "default": 30}
                },
                "required": ["language", "code"]
            },
            handler=self._handle_execute_code
        )
    
    def _handle_system_info(self, params: Dict) -> Dict:
        """Handle system_info tool"""
        import psutil
        component = params.get("component", "all")
        
        result = {}
        if component in ("cpu", "all"):
            result["cpu"] = {
                "percent": psutil.cpu_percent(interval=0.1),
                "cores": psutil.cpu_count(),
                "freq": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None
            }
        if component in ("memory", "all"):
            mem = psutil.virtual_memory()
            result["memory"] = {
                "percent": mem.percent,
                "used_gb": round(mem.used / (1024**3), 2),
                "total_gb": round(mem.total / (1024**3), 2)
            }
        if component in ("disk", "all"):
            disk = psutil.disk_usage('/')
            result["disk"] = {
                "percent": disk.percent,
                "free_gb": round(disk.free / (1024**3), 2)
            }
        
        return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
    
    def _handle_search_knowledge(self, params: Dict) -> Dict:
        """Handle search_knowledge tool"""
        # This would integrate with the RAG system
        query = params.get("query", "")
        return {
            "content": [{"type": "text", "text": f"Knowledge search for: {query}"}],
            "isError": False
        }
    
    def _handle_execute_code(self, params: Dict) -> Dict:
        """Handle execute_code tool"""
        language = params.get("language", "python")
        code = params.get("code", "")
        
        # This would integrate with the sandbox
        return {
            "content": [{"type": "text", "text": f"Executed {language} code"}],
            "isError": False
        }
    
    # ==================== Registration Methods ====================
    
    def register_tool(self, name: str, description: str, input_schema: Dict,
                     handler: Optional[Callable] = None):
        """Register a tool"""
        self.tools[name] = MCPTool(
            name=name,
            description=description,
            input_schema=input_schema,
            handler=handler
        )
        logger.info(f"Registered tool: {name}")
    
    def register_resource(self, uri: str, name: str, description: str,
                         mime_type: str = "application/json",
                         handler: Optional[Callable] = None):
        """Register a resource"""
        self.resources[uri] = MCPResource(
            uri=uri,
            name=name,
            description=description,
            mime_type=mime_type,
            handler=handler
        )
        logger.info(f"Registered resource: {uri}")
    
    def register_prompt(self, name: str, description: str, arguments: List[Dict],
                       handler: Optional[Callable] = None):
        """Register a prompt"""
        self.prompts[name] = MCPPrompt(
            name=name,
            description=description,
            arguments=arguments,
            handler=handler
        )
        logger.info(f"Registered prompt: {name}")
    
    # ==================== Protocol Handlers ====================
    
    def _handle_initialize(self, params: Dict) -> Dict:
        """Handle initialize request"""
        client_info = params.get("clientInfo", {})
        protocol_version = params.get("protocolVersion", self.PROTOCOL_VERSION)
        
        logger.info(f"Client initialized: {client_info.get('name')} v{client_info.get('version')}")
        
        return {
            "protocolVersion": self.PROTOCOL_VERSION,
            "serverInfo": {
                "name": self.name,
                "version": self.version
            },
            "capabilities": {
                "tools": {"listChanged": True},
                "resources": {"listChanged": True, "subscribe": True},
                "prompts": {"listChanged": True},
                "logging": {},
                "experimental": {}
            }
        }
    
    def _handle_tools_list(self) -> Dict:
        """Handle tools/list request"""
        return {
            "tools": [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": tool.input_schema
                }
                for tool in self.tools.values()
            ]
        }
    
    def _handle_tools_call(self, params: Dict) -> Dict:
        """Handle tools/call request"""
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        
        if tool_name not in self.tools:
            raise MCPError(-32602, f"Tool not found: {tool_name}")
        
        tool = self.tools[tool_name]
        
        if tool.handler:
            try:
                result = tool.handler(arguments)
                return result
            except Exception as e:
                return {
                    "content": [{"type": "text", "text": f"Error: {str(e)}"}],
                    "isError": True
                }
        else:
            return {
                "content": [{"type": "text", "text": f"Tool {tool_name} executed with args: {arguments}"}],
                "isError": False
            }
    
    def _handle_resources_list(self) -> Dict:
        """Handle resources/list request"""
        return {
            "resources": [
                {
                    "uri": res.uri,
                    "name": res.name,
                    "description": res.description,
                    "mimeType": res.mime_type
                }
                for res in self.resources.values()
            ]
        }
    
    def _handle_resources_read(self, params: Dict) -> Dict:
        """Handle resources/read request"""
        uri = params.get("uri", "")
        
        if uri not in self.resources:
            raise MCPError(-32602, f"Resource not found: {uri}")
        
        resource = self.resources[uri]
        
        if resource.handler:
            content = resource.handler()
        else:
            content = json.dumps({"uri": uri, "status": "ok"})
        
        return {
            "contents": [{
                "uri": uri,
                "mimeType": resource.mime_type,
                "text": content if isinstance(content, str) else json.dumps(content)
            }]
        }
    
    def _handle_prompts_list(self) -> Dict:
        """Handle prompts/list request"""
        return {
            "prompts": [
                {
                    "name": prompt.name,
                    "description": prompt.description,
                    "arguments": prompt.arguments
                }
                for prompt in self.prompts.values()
            ]
        }
    
    def _handle_prompts_get(self, params: Dict) -> Dict:
        """Handle prompts/get request"""
        prompt_name = params.get("name", "")
        arguments = params.get("arguments", {})
        
        if prompt_name not in self.prompts:
            raise MCPError(-32602, f"Prompt not found: {prompt_name}")
        
        prompt = self.prompts[prompt_name]
        
        if prompt.handler:
            result = prompt.handler(arguments)
            return result
        else:
            return {
                "description": prompt.description,
                "messages": [
                    {
                        "role": "user",
                        "content": {"type": "text", "text": f"Prompt: {prompt_name}"}
                    }
                ]
            }
    
    def _handle_message(self, message: Dict) -> Optional[Dict]:
        """Handle an MCP message and return response"""
        method = message.get("method", "")
        msg_id = message.get("id")
        params = message.get("params", {})
        
        try:
            if method == "initialize":
                result = self._handle_initialize(params)
            elif method == "tools/list":
                result = self._handle_tools_list()
            elif method == "tools/call":
                result = self._handle_tools_call(params)
            elif method == "resources/list":
                result = self._handle_resources_list()
            elif method == "resources/read":
                result = self._handle_resources_read(params)
            elif method == "prompts/list":
                result = self._handle_prompts_list()
            elif method == "prompts/get":
                result = self._handle_prompts_get(params)
            elif method == "notifications/initialized":
                return None  # No response needed
            else:
                raise MCPError(-32601, f"Method not found: {method}")
            
            if msg_id is not None:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": result
                }
            return None
            
        except MCPError as e:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": e.code, "message": e.message}
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32603, "message": f"Internal error: {str(e)}"}
            }
    
    # ==================== Transport Implementations ====================
    
    async def run_stdio(self):
        """Run server with stdio transport"""
        logger.info("Starting MCP server with stdio transport")
        
        loop = asyncio.get_event_loop()
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)
        
        while True:
            try:
                # Read line from stdin
                line = await reader.readline()
                if not line:
                    break
                
                message = json.loads(line.decode('utf-8'))
                response = self._handle_message(message)
                
                if response:
                    output = json.dumps(response) + '\n'
                    sys.stdout.write(output)
                    sys.stdout.flush()
                    
            except json.JSONDecodeError:
                error_response = {
                    "jsonrpc": "2.0",
                    "error": {"code": -32700, "message": "Parse error"}
                }
                sys.stdout.write(json.dumps(error_response) + '\n')
                sys.stdout.flush()
            except Exception as e:
                logger.error(f"Error handling message: {e}")
    
    async def run_sse(self, host: str = "0.0.0.0", port: int = 18080):
        """Run server with SSE (Server-Sent Events) transport"""
        try:
            from aiohttp import web
        except ImportError:
            logger.error("aiohttp required for SSE transport")
            return
        
        logger.info(f"Starting MCP server with SSE transport on {host}:{port}")
        
        async def sse_handler(request):
            """Handle SSE connection"""
            response = web.StreamResponse()
            response.headers['Content-Type'] = 'text/event-stream'
            response.headers['Cache-Control'] = 'no-cache'
            response.headers['Connection'] = 'keep-alive'
            response.headers['Access-Control-Allow-Origin'] = '*'
            await response.prepare(request)
            
            client_id = str(datetime.utcnow().timestamp())
            self.sse_clients.add(response)
            
            try:
                # Send endpoint notification
                endpoint_msg = {
                    "jsonrpc": "2.0",
                    "method": "notifications/endpoint",
                    "params": {"endpoint": f"/mcp/message?clientId={client_id}"}
                }
                await response.write(f"data: {json.dumps(endpoint_msg)}\n\n".encode())
                
                # Keep connection alive
                while True:
                    await asyncio.sleep(30)
                    await response.write(b":\n\n")  # Keep-alive comment
            except:
                pass
            finally:
                self.sse_clients.discard(response)
            
            return response
        
        async def message_handler(request):
            """Handle message POST"""
            try:
                data = await request.json()
                response = self._handle_message(data)
                
                if response:
                    return web.json_response(response)
                return web.json_response({"status": "ok"})
            except Exception as e:
                return web.json_response(
                    {"jsonrpc": "2.0", "error": {"code": -32603, "message": str(e)}},
                    status=500
                )
        
        app = web.Application()
        app.router.add_get('/mcp/sse', sse_handler)
        app.router.add_post('/mcp/message', message_handler)
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host, port)
        await site.start()
        
        logger.info(f"SSE server running at http://{host}:{port}/mcp/sse")
        
        # Run forever
        while True:
            await asyncio.sleep(3600)
    
    def setup_http_routes(self, app: Flask):
        """Setup HTTP routes on existing Flask app"""
        
        @app.route('/mcp/health', methods=['GET'])
        def mcp_health():
            return jsonify({
                "status": "ok",
                "server": self.name,
                "version": self.version,
                "protocol": self.PROTOCOL_VERSION
            })
        
        @app.route('/mcp/message', methods=['POST'])
        def mcp_message():
            """Main MCP message endpoint"""
            data = request.get_json()
            response = self._handle_message(data)
            
            if response:
                return jsonify(response)
            return jsonify({"status": "ok"})
        
        @app.route('/mcp/sse', methods=['GET'])
        def mcp_sse():
            """SSE endpoint for streaming"""
            def event_stream():
                client_id = str(datetime.utcnow().timestamp())
                
                # Send initial endpoint
                init_msg = {
                    "jsonrpc": "2.0",
                    "method": "notifications/endpoint",
                    "params": {"clientId": client_id}
                }
                yield f"data: {json.dumps(init_msg)}\n\n"
                
                # Keep connection alive
                import time
                while True:
                    time.sleep(30)
                    yield ":\n\n"  # Keep-alive
            
            return Response(
                stream_with_context(event_stream()),
                mimetype='text/event-stream',
                headers={
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive',
                    'Access-Control-Allow-Origin': '*'
                }
            )
        
        @app.route('/mcp/tools', methods=['GET'])
        def mcp_tools_list():
            """List available tools"""
            return jsonify(self._handle_tools_list())
        
        @app.route('/mcp/resources', methods=['GET'])
        def mcp_resources_list():
            """List available resources"""
            return jsonify(self._handle_resources_list())
        
        logger.info("MCP HTTP routes registered on Flask app")
    
    async def start(self, transport: Optional[MCPTransport] = None, **kwargs):
        """Start the MCP server with specified transport"""
        transport = transport or self.transport_type
        
        if transport == MCPTransport.STDIO:
            await self.run_stdio()
        elif transport == MCPTransport.SSE:
            host = kwargs.get('host', '0.0.0.0')
            port = kwargs.get('port', 18080)
            await self.run_sse(host, port)
        elif transport == MCPTransport.HTTP:
            # HTTP mode requires external Flask app
            logger.info("HTTP transport requires Flask app integration")
        else:
            raise ValueError(f"Unknown transport: {transport}")


class MCPClient:
    """MCP Client for connecting to external MCP servers"""
    
    def __init__(self, endpoint: str, auth_token: Optional[str] = None):
        self.endpoint = endpoint
        self.auth_token = auth_token
        self.session: Optional[aiohttp.ClientSession] = None
        self.capabilities: Dict[str, Any] = {}
    
    async def connect(self) -> bool:
        """Connect and initialize with server"""
        self.session = aiohttp.ClientSession()
        
        init_msg = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "clientInfo": {"name": "ordl-mcp-client", "version": "1.0.0"},
                "capabilities": {}
            }
        }
        
        try:
            response = await self._send_request(init_msg)
            if "result" in response:
                self.capabilities = response["result"].get("capabilities", {})
                
                # Send initialized notification
                await self._send_notification("notifications/initialized", {})
                return True
        except Exception as e:
            logger.error(f"MCP connection failed: {e}")
        
        return False
    
    async def _send_request(self, message: Dict) -> Dict:
        """Send request to server"""
        headers = {}
        if self.auth_token:
            headers['Authorization'] = f'Bearer {self.auth_token}'
        
        async with self.session.post(
            self.endpoint,
            json=message,
            headers=headers
        ) as response:
            return await response.json()
    
    async def _send_notification(self, method: str, params: Dict):
        """Send notification (no response expected)"""
        message = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        }
        
        headers = {}
        if self.auth_token:
            headers['Authorization'] = f'Bearer {self.auth_token}'
        
        async with self.session.post(
            self.endpoint,
            json=message,
            headers=headers
        ):
            pass
    
    async def list_tools(self) -> List[Dict]:
        """List available tools from server"""
        response = await self._send_request({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list"
        })
        return response.get("result", {}).get("tools", [])
    
    async def call_tool(self, name: str, arguments: Dict) -> Dict:
        """Call a tool on the server"""
        response = await self._send_request({
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments}
        })
        return response.get("result", {})
    
    async def close(self):
        """Close client connection"""
        if self.session:
            await self.session.close()
            self.session = None


# Singleton instance
_mcp_server: Optional[MCPServer] = None


def get_mcp_server() -> MCPServer:
    """Get singleton MCP server instance"""
    global _mcp_server
    if _mcp_server is None:
        _mcp_server = MCPServer()
    return _mcp_server


# Convenience function to setup MCP on Flask app
def setup_mcp_on_app(app: Flask):
    """Setup MCP routes on Flask app"""
    server = get_mcp_server()
    server.setup_http_routes(app)
    return server


if __name__ == "__main__":
    # Run server based on arguments
    import argparse
    parser = argparse.ArgumentParser(description='ORDL MCP Server')
    parser.add_argument('--transport', choices=['stdio', 'sse'], default='stdio')
    parser.add_argument('--host', default='0.0.0.0')
    parser.add_argument('--port', type=int, default=18080)
    args = parser.parse_args()
    
    server = MCPServer(transport=MCPTransport(args.transport))
    
    if args.transport == 'stdio':
        asyncio.run(server.run_stdio())
    else:
        asyncio.run(server.run_sse(args.host, args.port))
