#!/usr/bin/env python3
"""
================================================================================
ORDL COMMAND POST v6.0.0 - MCP CLIENT
================================================================================
Classification: TOP SECRET//SCI//NOFORN

Proper MCP Client using JSON-RPC over stdio
================================================================================
"""

import json
import subprocess
import threading
import uuid
import logging
from typing import Dict, Any, Optional, Callable, List
from queue import Queue, Empty
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger('mcp_client')


@dataclass
class JSONRPCMessage:
    """JSON-RPC 2.0 message"""
    id: Optional[str]
    method: Optional[str]
    params: Optional[Dict]
    result: Optional[Any]
    error: Optional[Dict]
    
    def to_json(self) -> str:
        data = {"jsonrpc": "2.0"}
        if self.id is not None:
            data["id"] = self.id
        if self.method:
            data["method"] = self.method
            data["params"] = self.params or {}
        if self.result is not None:
            data["result"] = self.result
        if self.error is not None:
            data["error"] = self.error
        return json.dumps(data)
    
    @classmethod
    def from_json(cls, data: str) -> "JSONRPCMessage":
        parsed = json.loads(data)
        return cls(
            id=parsed.get("id"),
            method=parsed.get("method"),
            params=parsed.get("params"),
            result=parsed.get("result"),
            error=parsed.get("error")
        )


class MCPClient:
    """
    MCP Client for JSON-RPC communication with MCP servers
    """
    
    def __init__(self, command: List[str], env: Optional[Dict] = None):
        self.command = command
        self.env = env
        self.process: Optional[subprocess.Popen] = None
        self._message_queue: Queue = Queue()
        self._pending_requests: Dict[str, Callable] = {}
        self._lock = threading.Lock()
        self._reader_thread: Optional[threading.Thread] = None
        self._running = False
        self._initialized = False
        
    def connect(self) -> bool:
        """Start MCP server and establish connection"""
        try:
            logger.info(f"[MCP] Starting server: {' '.join(self.command)}")
            
            # Start the server process
            self.process = subprocess.Popen(
                self.command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=self.env,
                bufsize=1
            )
            
            self._running = True
            
            # Start reader thread
            self._reader_thread = threading.Thread(target=self._read_messages, daemon=True)
            self._reader_thread.start()
            
            # Initialize the server
            if self._initialize():
                self._initialized = True
                logger.info("[MCP] Server connected and initialized")
                return True
            else:
                logger.error("[MCP] Server initialization failed")
                self.disconnect()
                return False
                
        except Exception as e:
            logger.error(f"[MCP] Connection failed: {e}")
            return False
    
    def _initialize(self) -> bool:
        """Send initialize request"""
        init_request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "ordl-command-post",
                    "version": "6.0.0"
                }
            }
        }
        
        response = self._send_request_sync(init_request, timeout=10)
        if response and "result" in response:
            # Send initialized notification
            self._send_notification("notifications/initialized")
            return True
        return False
    
    def _read_messages(self):
        """Background thread to read messages from server"""
        while self._running and self.process:
            try:
                line = self.process.stdout.readline()
                if not line:
                    break
                
                line = line.strip()
                if not line:
                    continue
                
                try:
                    msg = JSONRPCMessage.from_json(line)
                    
                    if msg.id and msg.id in self._pending_requests:
                        # Response to a request
                        with self._lock:
                            callback = self._pending_requests.pop(msg.id)
                        callback(msg)
                    elif msg.method:
                        # Server-initiated message
                        self._handle_server_message(msg)
                        
                except json.JSONDecodeError:
                    logger.warning(f"[MCP] Invalid JSON: {line[:100]}")
                    
            except Exception as e:
                if self._running:
                    logger.error(f"[MCP] Read error: {e}")
    
    def _handle_server_message(self, msg: JSONRPCMessage):
        """Handle server-initiated messages"""
        logger.debug(f"[MCP] Server message: {msg.method}")
    
    def _send_request_sync(self, request: Dict, timeout: int = 30) -> Optional[Dict]:
        """Send a request and wait for response"""
        response_container = [None]
        event = threading.Event()
        
        def callback(msg: JSONRPCMessage):
            response_container[0] = {
                "id": msg.id,
                "result": msg.result,
                "error": msg.error
            }
            event.set()
        
        with self._lock:
            self._pending_requests[request["id"]] = callback
        
        # Send the request
        json_str = json.dumps(request)
        logger.debug(f"[MCP] Sending: {json_str[:200]}")
        
        try:
            self.process.stdin.write(json_str + "\n")
            self.process.stdin.flush()
        except Exception as e:
            logger.error(f"[MCP] Send failed: {e}")
            return None
        
        # Wait for response
        if event.wait(timeout=timeout):
            return response_container[0]
        else:
            with self._lock:
                self._pending_requests.pop(request["id"], None)
            logger.warning("[MCP] Request timeout")
            return None
    
    def _send_notification(self, method: str, params: Optional[Dict] = None):
        """Send a notification (no response expected)"""
        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {}
        }
        
        try:
            self.process.stdin.write(json.dumps(notification) + "\n")
            self.process.stdin.flush()
        except Exception as e:
            logger.error(f"[MCP] Notification failed: {e}")
    
    def call_tool(self, tool_name: str, arguments: Dict) -> Dict:
        """Call a tool on the MCP server"""
        if not self._initialized:
            return {"error": "MCP client not initialized"}
        
        request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        response = self._send_request_sync(request, timeout=60)
        
        if response is None:
            return {"error": "Request timeout or connection failed"}
        
        if response.get("error"):
            return {"error": response["error"]}
        
        return response.get("result", {})
    
    def list_tools(self) -> List[Dict]:
        """List available tools"""
        if not self._initialized:
            return []
        
        request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "tools/list"
        }
        
        response = self._send_request_sync(request, timeout=10)
        
        if response and "result" in response:
            return response["result"].get("tools", [])
        return []
    
    def disconnect(self):
        """Close connection to server"""
        self._running = False
        self._initialized = False
        
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except:
                self.process.kill()
            finally:
                self.process = None
        
        logger.info("[MCP] Disconnected")


class MCPClientPool:
    """Pool of MCP clients for different servers"""
    
    def __init__(self):
        self.clients: Dict[str, MCPClient] = {}
        self._lock = threading.Lock()
    
    def get_client(self, name: str, command: List[str]) -> Optional[MCPClient]:
        """Get or create a client"""
        with self._lock:
            if name in self.clients:
                client = self.clients[name]
                if client._initialized:
                    return client
                # Reconnect if needed
                client.disconnect()
            
            # Create new client
            client = MCPClient(command)
            if client.connect():
                self.clients[name] = client
                return client
            return None
    
    def disconnect_all(self):
        """Disconnect all clients"""
        with self._lock:
            for client in self.clients.values():
                client.disconnect()
            self.clients.clear()


# Global pool
_pool: Optional[MCPClientPool] = None

def get_mcp_pool() -> MCPClientPool:
    """Get global MCP client pool"""
    global _pool
    if _pool is None:
        _pool = MCPClientPool()
    return _pool
