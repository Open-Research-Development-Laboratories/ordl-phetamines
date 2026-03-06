#!/usr/bin/env python3
"""
ORDL Packet Crafter - Network operations and packet crafting
Classification: TOP SECRET//NOFORN
"""
import os
import json
import time
import random
import socket
import struct
import logging
import subprocess
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("packet_crafter")

# Import scapy - REQUIRED for operation (no simulation mode)
try:
    from scapy.all import *
    from scapy.layers.inet import IP, TCP, UDP, ICMP
    from scapy.layers.l2 import ARP
    from scapy.sendrecv import sr1, send
    SCAPY_AVAILABLE = True
except ImportError as e:
    SCAPY_AVAILABLE = False
    logger.error("=" * 70)
    logger.error("CRITICAL: scapy is required for network operations")
    logger.error("Install with: pip install scapy")
    logger.error("=" * 70)
    raise RuntimeError("scapy is required for packet crafting operations") from e


class Protocol(Enum):
    TCP = "tcp"
    UDP = "udp"
    ICMP = "icmp"
    ARP = "arp"


@dataclass
class PacketConfig:
    """Packet crafting configuration"""
    protocol: Protocol
    src_ip: str = ""
    dst_ip: str = ""
    src_port: int = 0
    dst_port: int = 0
    payload: bytes = b''
    flags: str = ""
    options: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.options is None:
            self.options = {}


@dataclass
class PacketSession:
    """Packet crafting session"""
    id: str
    name: str
    packets_sent: int = 0
    packets_received: int = 0
    start_time: str = ""
    status: str = "active"
    config: Dict = None


class PacketCraftingEngine:
    """
    Advanced packet crafting and network operations engine.
    Supports raw socket operations via scapy.
    """
    
    def __init__(self):
        if not SCAPY_AVAILABLE:
            raise RuntimeError("scapy is required for packet crafting")
        
        self.sessions: Dict[str, PacketSession] = {}
        self.scapy_available = SCAPY_AVAILABLE
        self.default_timeout = 2
        
        # Disable scapy verbosity
        conf.verb = 0
        logger.info("[PACKET] Military-grade packet crafting engine initialized")
    
    def create_session(self, name: str, config: Dict = None) -> str:
        """Create a new packet crafting session"""
        session_id = f"pkt-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        session = PacketSession(
            id=session_id,
            name=name,
            start_time=datetime.utcnow().isoformat(),
            config=config or {}
        )
        self.sessions[session_id] = session
        logger.info(f"Created packet session: {session_id}")
        return session_id
    
    def get_session(self, session_id: str) -> Optional[PacketSession]:
        """Get session by ID"""
        return self.sessions.get(session_id)
    
    def craft_packet(self, config: PacketConfig) -> Any:
        """
        Craft a packet based on configuration
        Returns scapy packet object
        """
        try:
            if config.protocol == Protocol.TCP:
                # Craft TCP packet
                pkt = IP(src=config.src_ip, dst=config.dst_ip) / \
                      TCP(sport=config.src_port, dport=config.dst_port, flags=config.flags or 'S')
                
                if config.payload:
                    pkt = pkt / Raw(load=config.payload)
                
                # Add TCP options if specified
                if config.options.get('window'):
                    pkt[TCP].window = config.options['window']
                if config.options.get('seq'):
                    pkt[TCP].seq = config.options['seq']
                    
            elif config.protocol == Protocol.UDP:
                pkt = IP(src=config.src_ip, dst=config.dst_ip) / \
                      UDP(sport=config.src_port, dport=config.dst_port)
                
                if config.payload:
                    pkt = pkt / Raw(load=config.payload)
                    
            elif config.protocol == Protocol.ICMP:
                icmp_type = config.options.get('icmp_type', 8)  # Echo request default
                icmp_code = config.options.get('icmp_code', 0)
                
                pkt = IP(src=config.src_ip, dst=config.dst_ip) / \
                      ICMP(type=icmp_type, code=icmp_code)
                
                if config.payload:
                    pkt = pkt / Raw(load=config.payload)
                    
            elif config.protocol == Protocol.ARP:
                pkt = ARP(psrc=config.src_ip, pdst=config.dst_ip)
                
            else:
                raise ValueError(f"Unsupported protocol: {config.protocol}")
            
            return pkt
            
        except Exception as e:
            logger.error(f"Packet crafting error: {e}")
            raise
    
    def send_packet(self, packet: Any, iface: Optional[str] = None,
                   count: int = 1, interval: float = 0.0) -> Dict:
        """Send crafted packet(s)"""
        try:
            sent = send(packet, iface=iface, count=count, inter=interval, verbose=0)
            return {"sent": sent, "success": True}
        except Exception as e:
            logger.error(f"[PACKET] Send error: {e}")
            return {"sent": 0, "success": False, "error": str(e)}
    
    def send_with_fog_jitter(self, config: PacketConfig, 
                            burst_count: int = 1,
                            fog_delay_ms: float = 0,
                            jitter_percent: float = 0,
                            burst_interval_ms: float = 0) -> Dict[str, Any]:
        """
        Send packets with timing obfuscation (fog/jitter)
        
        Args:
            config: Packet configuration
            burst_count: Number of packets to send
            fog_delay_ms: Base delay between packets
            jitter_percent: Random variation percentage
            burst_interval_ms: Time between bursts
        """
        packet = self.craft_packet(config)
        
        sent = 0
        timings = []
        
        for i in range(burst_count):
            start = time.time()
            
            # Calculate jittered delay
            if fog_delay_ms > 0:
                jitter = fog_delay_ms * (jitter_percent / 100) * (random.random() - 0.5)
                actual_delay = max(0, (fog_delay_ms + jitter) / 1000)
                time.sleep(actual_delay)
            
            # Send packet
            result = self.send_packet(packet)
            if result.get("sent", 0) > 0:
                sent += 1
            
            # Burst interval
            if burst_interval_ms > 0 and i < burst_count - 1:
                time.sleep(burst_interval_ms / 1000)
            
            timings.append(time.time() - start)
        
        return {
            "packets_sent": sent,
            "packets_requested": burst_count,
            "avg_timing_ms": sum(timings) / len(timings) * 1000 if timings else 0,
            "fog_delay_ms": fog_delay_ms,
            "jitter_percent": jitter_percent,
            "status": "sent"
        }
    
    def port_scan(self, target: str, ports: List[int], 
                  timeout: float = 2.0) -> Dict[str, Any]:
        """
        TCP port scan
        
        Args:
            target: Target IP or hostname
            ports: List of ports to scan
            timeout: Timeout per port
        """
        open_ports = []
        closed_ports = []
        filtered_ports = []
        
        for port in ports:
            try:
                # Craft SYN packet
                pkt = IP(dst=target) / TCP(dport=port, flags='S')
                
                # Send and wait for response
                resp = sr1(pkt, timeout=timeout, verbose=0)
                
                if resp is None:
                    filtered_ports.append(port)
                elif resp.haslayer(TCP):
                    if resp[TCP].flags == 'SA':  # SYN-ACK
                        open_ports.append(port)
                        # Send RST to close connection
                        rst = IP(dst=target) / TCP(dport=port, flags='R')
                        send(rst, verbose=0)
                    elif resp[TCP].flags == 'RA':  # RST-ACK
                        closed_ports.append(port)
                else:
                    filtered_ports.append(port)
                    
            except Exception as e:
                logger.error(f"Scan error on port {port}: {e}")
                filtered_ports.append(port)
        
        return {
            "target": target,
            "scanned": len(ports),
            "open_ports": open_ports,
            "closed_ports": closed_ports,
            "filtered_ports": filtered_ports,
            "status": "completed"
        }
    
    def traceroute(self, target: str, max_hops: int = 30, 
                   timeout: float = 2.0) -> Dict[str, Any]:
        """
        Perform traceroute to target
        """
        if not self.scapy_available:
            # Fallback to system traceroute
            try:
                result = subprocess.run(
                    ['traceroute', '-n', '-m', str(max_hops), target],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                return {
                    "target": target,
                    "raw_output": result.stdout,
                    "status": "completed"
                }
            except:
                return {"error": "Traceroute unavailable"}
        
        hops = []
        
        for ttl in range(1, max_hops + 1):
            pkt = IP(dst=target, ttl=ttl) / ICMP()
            
            reply = sr1(pkt, timeout=timeout, verbose=0)
            
            if reply is None:
                hops.append({"hop": ttl, "ip": "*", "time_ms": None})
            else:
                hop_ip = reply.src
                hops.append({"hop": ttl, "ip": hop_ip, "time_ms": reply.time})
                
                # Reached target
                if reply.haslayer(ICMP) and reply[ICMP].type == 0:
                    break
        
        return {
            "target": target,
            "hops": hops,
            "total_hops": len(hops),
            "status": "completed"
        }


class NetworkControl:
    """Network interface control operations"""
    
    def __init__(self):
        self.adapters = self._get_adapters()
    
    def _get_adapters(self) -> List[Dict]:
        """Get network adapters list"""
        adapters = []
        try:
            import psutil
            for name, addrs in psutil.net_if_addrs().items():
                if name == 'lo':
                    continue
                
                ip_addr = ""
                mac_addr = ""
                
                for addr in addrs:
                    if addr.family == socket.AF_INET:  # IPv4
                        ip_addr = addr.address
                    elif addr.family == psutil.AF_LINK:  # MAC
                        mac_addr = addr.address
                
                stats = psutil.net_if_stats().get(name)
                
                adapters.append({
                    "name": name,
                    "ip": ip_addr,
                    "mac": mac_addr,
                    "up": stats.isup if stats else False,
                    "speed_mbps": stats.speed if stats else 0
                })
        except Exception as e:
            logger.error(f"Error getting adapters: {e}")
        
        return adapters
    
    def adapter_kill(self, interface: str) -> bool:
        """Disable network adapter"""
        try:
            result = subprocess.run(
                ['sudo', 'ip', 'link', 'set', interface, 'down'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Error killing adapter {interface}: {e}")
            return False
    
    def adapter_revive(self, interface: str) -> bool:
        """Enable network adapter"""
        try:
            result = subprocess.run(
                ['sudo', 'ip', 'link', 'set', interface, 'up'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Error reviving adapter {interface}: {e}")
            return False
    
    def get_adapter_stats(self, interface: str) -> Dict:
        """Get adapter statistics"""
        try:
            import psutil
            stats = psutil.net_io_counters(pernic=True).get(interface, {})
            return {
                "interface": interface,
                "bytes_sent": stats.bytes_sent if hasattr(stats, 'bytes_sent') else 0,
                "bytes_recv": stats.bytes_recv if hasattr(stats, 'bytes_recv') else 0,
                "packets_sent": stats.packets_sent if hasattr(stats, 'packets_sent') else 0,
                "packets_recv": stats.packets_recv if hasattr(stats, 'packets_recv') else 0,
                "errors_in": stats.errin if hasattr(stats, 'errin') else 0,
                "errors_out": stats.errout if hasattr(stats, 'errout') else 0
            }
        except Exception as e:
            return {"error": str(e)}


class TrafficShaper:
    """Network traffic shaping using tc (Linux traffic control)"""
    
    def __init__(self):
        self.shaped_interfaces: set = set()
    
    def add_latency(self, interface: str, delay_ms: int, 
                   jitter_ms: int = 0, loss_percent: float = 0) -> bool:
        """Add latency/jitter/loss to interface"""
        try:
            # Remove existing rules
            self.remove_shaping(interface)
            
            # Build tc command
            cmd = ['sudo', 'tc', 'qdisc', 'add', 'dev', interface, 'root', 'netem']
            
            if delay_ms > 0:
                if jitter_ms > 0:
                    cmd.extend(['delay', f'{delay_ms}ms', f'{jitter_ms}ms'])
                else:
                    cmd.extend(['delay', f'{delay_ms}ms'])
            
            if loss_percent > 0:
                cmd.extend(['loss', f'{loss_percent}%'])
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                self.shaped_interfaces.add(interface)
                return True
            else:
                logger.error(f"tc error: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Traffic shaping error: {e}")
            return False
    
    def remove_shaping(self, interface: str) -> bool:
        """Remove traffic shaping from interface"""
        try:
            result = subprocess.run(
                ['sudo', 'tc', 'qdisc', 'del', 'dev', interface, 'root'],
                capture_output=True,
                text=True,
                timeout=5
            )
            self.shaped_interfaces.discard(interface)
            return result.returncode == 0 or "No such file" in result.stderr
        except Exception as e:
            logger.error(f"Remove shaping error: {e}")
            return False
    
    def get_shaping_status(self, interface: str) -> Dict:
        """Get traffic shaping status"""
        try:
            result = subprocess.run(
                ['tc', 'qdisc', 'show', 'dev', interface],
                capture_output=True,
                text=True,
                timeout=5
            )
            return {
                "interface": interface,
                "shaped": interface in self.shaped_interfaces,
                "tc_output": result.stdout
            }
        except Exception as e:
            return {"error": str(e)}


# Singleton instances
_packet_crafter: Optional[PacketCraftingEngine] = None
_network_control: Optional[NetworkControl] = None
_traffic_shaper: Optional[TrafficShaper] = None


def get_packet_crafter() -> PacketCraftingEngine:
    """Get singleton packet crafter"""
    global _packet_crafter
    if _packet_crafter is None:
        _packet_crafter = PacketCraftingEngine()
    return _packet_crafter


def get_network_control() -> NetworkControl:
    """Get singleton network control"""
    global _network_control
    if _network_control is None:
        _network_control = NetworkControl()
    return _network_control


def get_traffic_shaper() -> TrafficShaper:
    """Get singleton traffic shaper"""
    global _traffic_shaper
    if _traffic_shaper is None:
        _traffic_shaper = TrafficShaper()
    return _traffic_shaper


if __name__ == "__main__":
    # Test packet crafter
    crafter = get_packet_crafter()
    control = get_network_control()
    shaper = get_traffic_shaper()
    
    print("Network Adapters:")
    for adapter in control._get_adapters():
        print(f"  {adapter}")
    
    print("\nPacket Crafting Test:")
    config = PacketConfig(
        protocol=Protocol.TCP,
        src_ip="192.168.1.100",
        dst_ip="192.168.1.1",
        src_port=12345,
        dst_port=80,
        flags="S"
    )
    
    packet = crafter.craft_packet(config)
    if packet:
        print(f"  Crafted: {packet.summary()}")
    else:
        print("  Simulated mode")
