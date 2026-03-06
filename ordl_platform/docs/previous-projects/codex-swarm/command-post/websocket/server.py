#!/usr/bin/env python3
"""
ORDL WebSocket Server - Real-time Operator Chat
Classification: TOP SECRET//NOFORN
"""
import os
import json
import jwt
import asyncio
import logging
from typing import Dict, Set, Optional, List, Any
from datetime import datetime
from dataclasses import dataclass, asdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("websocket_server")

# Try to import websockets
try:
    import websockets
    from websockets.server import WebSocketServerProtocol
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    logger.warning("websockets not installed - WebSocket server unavailable")


@dataclass
class Operator:
    """Represents a connected operator"""
    codename: str
    clearance: str
    websocket: Any  # WebSocketServerProtocol
    connected_at: str
    status: str = "online"  # online, away, busy
    current_channel: str = "general"
    last_ping: float = 0.0


@dataclass
class ChatMessage:
    """Represents a chat message"""
    id: str
    type: str  # message, system, typing, presence
    channel: str
    from_operator: str
    content: str
    timestamp: str
    clearance_required: str = "UNCLASSIFIED"
    metadata: Optional[Dict] = None


class WebSocketServer:
    """
    Real-time WebSocket server for operator coordination.
    Supports channels, direct messages, and clearance-based access.
    """
    
    # Clearance levels in ascending order
    CLEARANCE_LEVELS = ['UNCLASSIFIED', 'CONFIDENTIAL', 'SECRET', 'TOP SECRET', 'TS/SCI', 'TS/SCI/NOFORN']
    
    # Default channels with clearance requirements
    DEFAULT_CHANNELS = {
        'general': 'UNCLASSIFIED',
        'tech': 'CONFIDENTIAL',
        'ops': 'SECRET',
        'intel': 'TOP SECRET',
        'sci': 'TS/SCI',
        'noforn': 'TS/SCI/NOFORN'
    }
    
    def __init__(self, host: str = "0.0.0.0", port: int = 18011, 
                 jwt_secret: Optional[str] = None):
        self.host = host
        self.port = port
        self.jwt_secret = jwt_secret or os.getenv("JWT_SECRET_KEY", "ordl-secret-key")
        
        # Connected operators: codename -> Operator
        self.operators: Dict[str, Operator] = {}
        
        # Channel subscriptions: channel -> Set of codenames
        self.channels: Dict[str, Set[str]] = {ch: set() for ch in self.DEFAULT_CHANNELS}
        
        # Message history per channel (limited)
        self.message_history: Dict[str, List[ChatMessage]] = {ch: [] for ch in self.DEFAULT_CHANNELS}
        self.max_history = 100
        
        # Server instance
        self.server = None
        self._shutdown_event = asyncio.Event()
    
    def _has_clearance(self, operator_clearance: str, required_clearance: str) -> bool:
        """Check if operator has required clearance"""
        try:
            op_level = self.CLEARANCE_LEVELS.index(operator_clearance)
            req_level = self.CLEARANCE_LEVELS.index(required_clearance)
            return op_level >= req_level
        except ValueError:
            return False
    
    def _verify_token(self, token: str) -> Optional[Dict]:
        """Verify JWT token"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    async def _handle_connection(self, websocket: WebSocketServerProtocol, path: str):
        """Handle a new WebSocket connection"""
        operator: Optional[Operator] = None
        
        try:
            logger.info(f"New connection from {websocket.remote_address}")
            
            # Wait for authentication message
            auth_msg = await asyncio.wait_for(websocket.recv(), timeout=10.0)
            auth_data = json.loads(auth_msg)
            
            if auth_data.get("type") != "auth":
                await self._send_error(websocket, "First message must be authentication")
                return
            
            # Verify token
            token = auth_data.get("token", "")
            payload = self._verify_token(token)
            
            if not payload:
                await self._send_error(websocket, "Invalid or expired token")
                return
            
            codename = payload.get("codename", "UNKNOWN")
            clearance = payload.get("clearance", "UNCLASSIFIED")
            
            # Create operator record
            operator = Operator(
                codename=codename,
                clearance=clearance,
                websocket=websocket,
                connected_at=datetime.utcnow().isoformat(),
                last_ping=asyncio.get_event_loop().time()
            )
            
            # Check for duplicate connections
            if codename in self.operators:
                # Close existing connection
                try:
                    old_ws = self.operators[codename].websocket
                    await old_ws.close(code=1000, reason="New connection established")
                except:
                    pass
            
            self.operators[codename] = operator
            
            # Subscribe to general channel by default
            await self._join_channel(operator, "general")
            
            # Send auth success
            await self._send(websocket, {
                "type": "auth_success",
                "operator": {
                    "codename": codename,
                    "clearance": clearance,
                    "channels": list(self.DEFAULT_CHANNELS.keys())
                },
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Notify others
            await self._broadcast_presence(operator, "online")
            
            # Send recent history
            await self._send_history(operator, "general")
            
            logger.info(f"Operator {codename} authenticated (clearance: {clearance})")
            
            # Handle messages
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self._handle_message(operator, data)
                except json.JSONDecodeError:
                    await self._send_error(websocket, "Invalid JSON")
                except Exception as e:
                    logger.error(f"Error handling message: {e}")
                    await self._send_error(websocket, f"Error: {str(e)}")
                    
        except asyncio.TimeoutError:
            await self._send_error(websocket, "Authentication timeout")
        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as e:
            logger.error(f"Connection error: {e}")
        finally:
            if operator:
                await self._disconnect_operator(operator)
    
    async def _handle_message(self, operator: Operator, data: Dict):
        """Handle a message from an operator"""
        msg_type = data.get("type", "")
        
        if msg_type == "message":
            await self._handle_chat_message(operator, data)
        elif msg_type == "join_channel":
            await self._handle_join_channel(operator, data)
        elif msg_type == "leave_channel":
            await self._handle_leave_channel(operator, data)
        elif msg_type == "typing":
            await self._handle_typing(operator, data)
        elif msg_type == "direct_message":
            await self._handle_direct_message(operator, data)
        elif msg_type == "ping":
            await self._handle_ping(operator)
        elif msg_type == "status":
            await self._handle_status_change(operator, data)
        elif msg_type == "presence_query":
            await self._handle_presence_query(operator)
        else:
            await self._send_error(operator.websocket, f"Unknown message type: {msg_type}")
    
    async def _handle_chat_message(self, operator: Operator, data: Dict):
        """Handle a chat message"""
        channel = data.get("channel", operator.current_channel)
        content = data.get("content", "").strip()
        
        if not content:
            return
        
        # Check if operator can access channel
        if channel not in self.DEFAULT_CHANNELS:
            await self._send_error(operator.websocket, "Channel does not exist")
            return
        
        required_clearance = self.DEFAULT_CHANNELS[channel]
        if not self._has_clearance(operator.clearance, required_clearance):
            await self._send_error(operator.websocket, "Insufficient clearance for channel")
            return
        
        # Create message
        msg = ChatMessage(
            id=f"msg-{datetime.utcnow().timestamp()}",
            type="message",
            channel=channel,
            from_operator=operator.codename,
            content=content,
            timestamp=datetime.utcnow().isoformat(),
            clearance_required=required_clearance
        )
        
        # Store in history
        self.message_history[channel].append(msg)
        if len(self.message_history[channel]) > self.max_history:
            self.message_history[channel] = self.message_history[channel][-self.max_history:]
        
        # Broadcast to channel
        await self._broadcast_to_channel(channel, {
            "type": "message",
            "id": msg.id,
            "channel": channel,
            "from": operator.codename,
            "content": content,
            "timestamp": msg.timestamp
        }, exclude=operator.codename)
        
        # Confirm to sender
        await self._send(operator.websocket, {
            "type": "message_confirm",
            "id": msg.id,
            "channel": channel
        })
    
    async def _handle_join_channel(self, operator: Operator, data: Dict):
        """Handle channel join request"""
        channel = data.get("channel", "")
        
        if channel not in self.DEFAULT_CHANNELS:
            await self._send(operator.websocket, {
                "type": "error",
                "message": f"Channel '{channel}' does not exist"
            })
            return
        
        required_clearance = self.DEFAULT_CHANNELS[channel]
        if not self._has_clearance(operator.clearance, required_clearance):
            await self._send(operator.websocket, {
                "type": "error",
                "message": f"Insufficient clearance for '{channel}'"
            })
            return
        
        await self._join_channel(operator, channel)
        
        await self._send(operator.websocket, {
            "type": "channel_joined",
            "channel": channel,
            "operators": list(self.channels[channel])
        })
    
    async def _handle_leave_channel(self, operator: Operator, data: Dict):
        """Handle channel leave request"""
        channel = data.get("channel", "")
        await self._leave_channel(operator, channel)
        
        await self._send(operator.websocket, {
            "type": "channel_left",
            "channel": channel
        })
    
    async def _handle_typing(self, operator: Operator, data: Dict):
        """Handle typing indicator"""
        channel = data.get("channel", operator.current_channel)
        is_typing = data.get("typing", True)
        
        if channel in self.channels and operator.codename in self.channels[channel]:
            await self._broadcast_to_channel(channel, {
                "type": "typing",
                "channel": channel,
                "operator": operator.codename,
                "typing": is_typing
            }, exclude=operator.codename)
    
    async def _handle_direct_message(self, operator: Operator, data: Dict):
        """Handle direct message to another operator"""
        to_codename = data.get("to", "")
        content = data.get("content", "").strip()
        
        if to_codename not in self.operators:
            await self._send(operator.websocket, {
                "type": "error",
                "message": f"Operator '{to_codename}' is not online"
            })
            return
        
        target = self.operators[to_codename]
        
        # Send to target
        await self._send(target.websocket, {
            "type": "direct_message",
            "from": operator.codename,
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Confirm to sender
        await self._send(operator.websocket, {
            "type": "dm_confirm",
            "to": to_codename
        })
    
    async def _handle_ping(self, operator: Operator):
        """Handle ping message"""
        operator.last_ping = asyncio.get_event_loop().time()
        await self._send(operator.websocket, {
            "type": "pong",
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def _handle_status_change(self, operator: Operator, data: Dict):
        """Handle status change"""
        new_status = data.get("status", "online")
        if new_status in ["online", "away", "busy", "offline"]:
            operator.status = new_status
            await self._broadcast_presence(operator, new_status)
    
    async def _handle_presence_query(self, operator: Operator):
        """Send list of online operators"""
        online_ops = [
            {
                "codename": op.codename,
                "clearance": op.clearance,
                "status": op.status,
                "channel": op.current_channel
            }
            for op in self.operators.values()
            if op.codename != operator.codename
        ]
        
        await self._send(operator.websocket, {
            "type": "presence_list",
            "operators": online_ops
        })
    
    async def _join_channel(self, operator: Operator, channel: str):
        """Add operator to channel"""
        if channel in self.channels:
            self.channels[channel].add(operator.codename)
            operator.current_channel = channel
            
            # Notify channel
            await self._broadcast_to_channel(channel, {
                "type": "system",
                "channel": channel,
                "content": f"{operator.codename} joined the channel",
                "timestamp": datetime.utcnow().isoformat()
            }, exclude=operator.codename)
    
    async def _leave_channel(self, operator: Operator, channel: str):
        """Remove operator from channel"""
        if channel in self.channels:
            self.channels[channel].discard(operator.codename)
            
            # Notify channel
            await self._broadcast_to_channel(channel, {
                "type": "system",
                "channel": channel,
                "content": f"{operator.codename} left the channel",
                "timestamp": datetime.utcnow().isoformat()
            })
    
    async def _disconnect_operator(self, operator: Operator):
        """Clean up operator disconnection"""
        codename = operator.codename
        
        # Remove from all channels
        for channel in self.channels:
            if codename in self.channels[channel]:
                self.channels[channel].discard(codename)
        
        # Remove from operators
        if codename in self.operators:
            del self.operators[codename]
        
        # Broadcast offline status
        await self._broadcast_presence(operator, "offline")
        
        logger.info(f"Operator {codename} disconnected")
    
    async def _broadcast_to_channel(self, channel: str, message: Dict, exclude: Optional[str] = None):
        """Broadcast message to all operators in a channel"""
        if channel not in self.channels:
            return
        
        for codename in self.channels[channel]:
            if codename == exclude:
                continue
            
            if codename in self.operators:
                try:
                    await self._send(self.operators[codename].websocket, message)
                except:
                    pass
    
    async def _broadcast_presence(self, operator: Operator, status: str):
        """Broadcast presence change to all operators"""
        message = {
            "type": "presence",
            "operator": operator.codename,
            "status": status,
            "clearance": operator.clearance,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        for op in self.operators.values():
            if op.codename != operator.codename:
                try:
                    await self._send(op.websocket, message)
                except:
                    pass
    
    async def _send_history(self, operator: Operator, channel: str):
        """Send recent message history to operator"""
        if channel not in self.message_history:
            return
        
        history = [
            {
                "type": msg.type,
                "id": msg.id,
                "from": msg.from_operator,
                "content": msg.content,
                "timestamp": msg.timestamp
            }
            for msg in self.message_history[channel][-20:]  # Last 20 messages
        ]
        
        await self._send(operator.websocket, {
            "type": "history",
            "channel": channel,
            "messages": history
        })
    
    async def _send(self, websocket, message: Dict):
        """Send message to websocket"""
        await websocket.send(json.dumps(message))
    
    async def _send_error(self, websocket, error_message: str):
        """Send error message"""
        await self._send(websocket, {
            "type": "error",
            "message": error_message,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def _cleanup_task(self):
        """Periodic cleanup of stale connections"""
        while not self._shutdown_event.is_set():
            await asyncio.sleep(30)  # Check every 30 seconds
            
            now = asyncio.get_event_loop().time()
            stale_operators = []
            
            for codename, op in self.operators.items():
                # Check for stale connections (no ping for 120 seconds)
                if now - op.last_ping > 120:
                    stale_operators.append(codename)
            
            for codename in stale_operators:
                if codename in self.operators:
                    logger.warning(f"Removing stale operator: {codename}")
                    op = self.operators[codename]
                    await self._disconnect_operator(op)
    
    async def start(self):
        """Start the WebSocket server"""
        if not WEBSOCKETS_AVAILABLE:
            logger.error("websockets not installed - cannot start server")
            return
        
        # Start cleanup task
        cleanup_task = asyncio.create_task(self._cleanup_task())
        
        # Start server
        self.server = await websockets.serve(
            self._handle_connection,
            self.host,
            self.port,
            ping_interval=20,
            ping_timeout=10
        )
        
        logger.info(f"WebSocket server started on {self.host}:{self.port}")
        
        # Wait for shutdown
        await self._shutdown_event.wait()
        
        # Cleanup
        cleanup_task.cancel()
        self.server.close()
        await self.server.wait_closed()
    
    def stop(self):
        """Signal server to stop"""
        self._shutdown_event.set()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get server statistics"""
        return {
            "operators_online": len(self.operators),
            "operators": [
                {
                    "codename": op.codename,
                    "clearance": op.clearance,
                    "status": op.status,
                    "channel": op.current_channel,
                    "connected_at": op.connected_at
                }
                for op in self.operators.values()
            ],
            "channels": {
                ch: len(members) for ch, members in self.channels.items()
            }
        }


# Singleton instance
_ws_server: Optional[WebSocketServer] = None


def get_websocket_server() -> WebSocketServer:
    """Get singleton WebSocket server instance"""
    global _ws_server
    if _ws_server is None:
        _ws_server = WebSocketServer()
    return _ws_server


async def main():
    """Run WebSocket server standalone"""
    server = get_websocket_server()
    await server.start()


if __name__ == "__main__":
    if WEBSOCKETS_AVAILABLE:
        asyncio.run(main())
    else:
        print("Error: websockets not installed")
        print("Install with: pip install websockets")
