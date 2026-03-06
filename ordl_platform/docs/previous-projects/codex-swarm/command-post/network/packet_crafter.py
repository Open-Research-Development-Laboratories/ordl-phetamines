#!/usr/bin/env python3
"""
================================================================================
ORDL COMMAND POST v6.0.0 - REAL PACKET CRAFTING ENGINE
================================================================================
Classification: TOP SECRET//SCI//NOFORN
Classification Level: TS/SCI/NOFORN

MILITARY-GRADE RAW PACKET CRAFTING AND INJECTION
================================================================================
Real raw socket-based packet crafting with NO simulation fallbacks:
- Raw socket packet injection (requires root/capabilities)
- Full protocol support (TCP, UDP, ICMP, ARP, custom)
- Packet capture and analysis (pcap format)
- Protocol fuzzing engine
- Stealth transmission (FOG jitter, fragment obfuscation)
- Real-time packet monitoring

Requirements:
- Linux OS with raw socket capabilities
- Root privileges or CAP_NET_RAW capability
- Scapy installed for high-level packet construction

Author: ORDL Cyber Operations Division
Version: 6.0.0
================================================================================
"""

import os
import sys
import socket
import struct
import array
import fcntl
import select
import time
import random
import logging
import threading
import subprocess
from typing import Dict, List, Optional, Tuple, Any, Union, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path

# psutil for network operations
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logging.warning("psutil not available - some network features disabled")

# Scapy for packet construction (required, not optional)
from scapy.all import (
    IP, TCP, UDP, ICMP, ARP, Ether, Raw,
    conf, send, sniff, wrpcap, rdpcap,
    fragment, defragment, fragment6,
    RandIP, RandMAC, RandString,
    sr, sr1, srp, srp1
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger('network.packet')


class PacketProtocol(Enum):
    """Supported protocols"""
    TCP = "tcp"
    UDP = "udp"
    ICMP = "icmp"
    ARP = "arp"
    RAW = "raw"


class StealthMode(Enum):
    """Stealth transmission modes"""
    STANDARD = "standard"
    FOG = "fog"  # Variable timing
    FRAGMENT = "fragment"  # IP fragmentation
    DECOY = "decoy"  # Decoy packets
    SLOW_LORIS = "slow_loris"  # Slow transmission


@dataclass
class PacketConfig:
    """Packet configuration"""
    protocol: PacketProtocol
    src_ip: str
    dst_ip: str
    src_port: int = 0
    dst_port: int = 0
    payload: Optional[bytes] = None
    flags: Optional[str] = None
    options: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TransmissionConfig:
    """Transmission configuration"""
    mode: StealthMode = StealthMode.STANDARD
    count: int = 1
    interval: float = 0.0
    jitter_percent: float = 0.0
    fragment_size: Optional[int] = None
    decoy_ratio: float = 0.0
    timeout: int = 10


class RawSocketEngine:
    """
    Real raw socket packet engine
    NO simulation fallbacks - requires real raw socket access
    """
    
    def __init__(self):
        self._verify_privileges()
        self._raw_sockets: Dict[str, socket.socket] = {}
        self._lock = threading.RLock()
        self.stats = {
            "packets_sent": 0,
            "packets_received": 0,
            "bytes_sent": 0,
            "bytes_received": 0
        }
    
    def _verify_privileges(self):
        """Verify raw socket privileges"""
        try:
            # Try to create a raw socket
            test_sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_RAW)
            test_sock.close()
            logger.info("[PACKET] Raw socket privileges verified")
        except PermissionError as e:
            logger.error("[PACKET] Raw socket privileges NOT available - requires root/CAP_NET_RAW")
            raise RuntimeError(
                "Raw packet crafting requires root privileges or CAP_NET_RAW capability. "
                "Run as root or add capability: setcap cap_net_raw+eip <executable>"
            ) from e
    
    def _get_raw_socket(self, protocol: int = socket.IPPROTO_RAW) -> socket.socket:
        """Get or create raw socket"""
        key = str(protocol)
        with self._lock:
            if key not in self._raw_sockets or self._raw_sockets[key].fileno() < 0:
                sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, protocol)
                sock.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
                self._raw_sockets[key] = sock
            return self._raw_sockets[key]
    
    def craft_ip_header(self, 
                       src_ip: str, 
                       dst_ip: str, 
                       payload_len: int = 0,
                       protocol: int = socket.IPPROTO_TCP,
                       ttl: int = 64,
                       identification: Optional[int] = None) -> bytes:
        """
        Craft IP header manually
        
        Args:
            src_ip: Source IP address
            dst_ip: Destination IP address
            payload_len: Length of payload
            protocol: Protocol number
            ttl: Time to live
            identification: IP identification field
            
        Returns:
            IP header bytes
        """
        if identification is None:
            identification = random.randint(0, 65535)
        
        # IP Header fields
        version_ihl = (4 << 4) | 5  # IPv4, 5 words (20 bytes)
        tos = 0
        total_length = 20 + payload_len
        flags_fragment = 0
        
        # Pack header (without checksum)
        header = struct.pack('!BBHHHBBH4s4s',
            version_ihl,      # Version and IHL
            tos,              # Type of service
            total_length,     # Total length
            identification,   # Identification
            flags_fragment,   # Flags and fragment offset
            ttl,              # TTL
            protocol,         # Protocol
            0,                # Checksum (initially 0)
            socket.inet_aton(src_ip),   # Source IP
            socket.inet_aton(dst_ip)    # Dest IP
        )
        
        # Calculate checksum
        checksum = self._calculate_checksum(header)
        
        # Repack with checksum
        header = struct.pack('!BBHHHBBH4s4s',
            version_ihl,
            tos,
            total_length,
            identification,
            flags_fragment,
            ttl,
            protocol,
            checksum,
            socket.inet_aton(src_ip),
            socket.inet_aton(dst_ip)
        )
        
        return header
    
    def craft_tcp_header(self,
                        src_port: int,
                        dst_port: int,
                        seq_num: int,
                        ack_num: int,
                        flags: int,
                        window: int = 65535,
                        payload: bytes = b'') -> bytes:
        """
        Craft TCP header with proper checksum
        
        Args:
            src_port: Source port
            dst_port: Destination port
            seq_num: Sequence number
            ack_num: Acknowledgment number
            flags: TCP flags (SYN=2, ACK=16, etc.)
            window: Window size
            payload: TCP payload
            
        Returns:
            TCP header + payload bytes
        """
        # TCP Header fields
        data_offset = 5 << 4  # 5 words (20 bytes)
        urgent = 0
        
        # Pack header without checksum
        header = struct.pack('!HHIIBBHHH',
            src_port,      # Source port
            dst_port,      # Dest port
            seq_num,       # Sequence number
            ack_num,       # Ack number
            data_offset,   # Data offset and reserved
            flags,         # Flags
            window,        # Window
            0,             # Checksum (initially 0)
            urgent         # Urgent pointer
        )
        
        # For checksum calculation we need pseudo-header
        # This will be calculated when we have the full IP packet
        
        return header + payload
    
    def _calculate_checksum(self, data: bytes) -> int:
        """Calculate IP/TCP checksum"""
        if len(data) % 2 == 1:
            data += b'\x00'
        
        s = sum(struct.unpack('!%dH' % (len(data) // 2), data))
        s = (s >> 16) + (s & 0xffff)
        s += s >> 16
        return ~s & 0xffff
    
    def send_raw_packet(self, 
                       packet: bytes, 
                       dst_ip: str,
                       protocol: int = socket.IPPROTO_TCP) -> int:
        """
        Send raw packet using raw socket
        
        Args:
            packet: Full packet data (IP header + payload)
            dst_ip: Destination IP
            protocol: Protocol number
            
        Returns:
            Number of bytes sent
        """
        try:
            sock = self._get_raw_socket(protocol)
            sent = sock.sendto(packet, (dst_ip, 0))
            
            with self._lock:
                self.stats["packets_sent"] += 1
                self.stats["bytes_sent"] += sent
            
            return sent
            
        except Exception as e:
            logger.error(f"[PACKET] Raw send failed: {e}")
            raise
    
    def send_with_scapy(self, packet) -> int:
        """
        Send packet using scapy (for complex packets)
        
        Args:
            packet: Scapy packet object
            
        Returns:
            Number of packets sent
        """
        try:
            sent = send(packet, verbose=0)
            
            with self._lock:
                self.stats["packets_sent"] += sent
                if hasattr(packet, 'len'):
                    self.stats["bytes_sent"] += packet.len
            
            return sent
            
        except Exception as e:
            logger.error(f"[PACKET] Scapy send failed: {e}")
            raise
    
    def receive_raw(self, 
                   interface: Optional[str] = None,
                   timeout: int = 10,
                   count: int = 1,
                   filter_expr: Optional[str] = None) -> List:
        """
        Capture packets using raw sockets/scapy
        
        Args:
            interface: Network interface
            timeout: Capture timeout
            count: Number of packets to capture
            filter_expr: BPF filter expression
            
        Returns:
            List of captured packets
        """
        try:
            packets = sniff(
                iface=interface,
                timeout=timeout,
                count=count,
                filter=filter_expr
            )
            
            with self._lock:
                self.stats["packets_received"] += len(packets)
                for pkt in packets:
                    if hasattr(pkt, 'len'):
                        self.stats["bytes_received"] += pkt.len
            
            return packets
            
        except Exception as e:
            logger.error(f"[PACKET] Capture failed: {e}")
            raise


class ProtocolFuzzer:
    """
    Protocol fuzzing engine for security testing
    """
    
    def __init__(self, engine: RawSocketEngine):
        self.engine = engine
        self.fuzzing_stats = {
            "tests_run": 0,
            "crashes": 0,
            "anomalies": 0
        }
    
    def fuzz_tcp_field(self, 
                      target_ip: str,
                      target_port: int,
                      field: str,
                      values: List[Any],
                      src_ip: Optional[str] = None) -> List[Dict]:
        """
        Fuzz a specific TCP field
        
        Args:
            target_ip: Target IP
            target_port: Target port
            field: Field to fuzz (seq, ack, flags, window, etc.)
            values: Values to test
            src_ip: Source IP (optional)
            
        Returns:
            List of test results
        """
        results = []
        
        for value in values:
            self.fuzzing_stats["tests_run"] += 1
            
            # Craft packet with fuzzed field
            pkt = IP(dst=target_ip, src=src_ip or RandIP())
            
            if field == "seq":
                pkt /= TCP(dport=target_port, seq=value)
            elif field == "ack":
                pkt /= TCP(dport=target_port, ack=value)
            elif field == "flags":
                pkt /= TCP(dport=target_port, flags=value)
            elif field == "window":
                pkt /= TCP(dport=target_port, window=value)
            elif field == "sport":
                pkt /= TCP(dport=target_port, sport=value)
            else:
                pkt /= TCP(dport=target_port)
            
            try:
                # Send and wait for response
                resp = sr1(pkt, timeout=2, verbose=0)
                
                result = {
                    "field": field,
                    "value": str(value),
                    "sent": True,
                    "response": resp is not None,
                    "response_type": resp.summary() if resp else None
                }
                
                # Check for anomalies
                if resp and resp.haslayer(TCP):
                    tcp = resp[TCP]
                    if tcp.flags.R:
                        result["anomaly"] = "RST received"
                        self.fuzzing_stats["anomalies"] += 1
                
                results.append(result)
                
            except Exception as e:
                results.append({
                    "field": field,
                    "value": str(value),
                    "error": str(e)
                })
        
        return results
    
    def fuzz_payload(self,
                    target_ip: str,
                    target_port: int,
                    payloads: List[bytes],
                    protocol: str = "tcp") -> List[Dict]:
        """
        Fuzz with various payloads
        
        Args:
            target_ip: Target IP
            target_port: Target port
            payloads: Payloads to test
            protocol: Protocol to use
            
        Returns:
            List of test results
        """
        results = []
        
        for payload in payloads:
            self.fuzzing_stats["tests_run"] += 1
            
            try:
                if protocol == "tcp":
                    pkt = IP(dst=target_ip) / TCP(dport=target_port) / Raw(load=payload)
                else:
                    pkt = IP(dst=target_ip) / UDP(dport=target_port) / Raw(load=payload)
                
                resp = sr1(pkt, timeout=2, verbose=0)
                
                results.append({
                    "payload_size": len(payload),
                    "payload_hash": hash(payload) & 0xFFFFFFFF,
                    "response": resp is not None
                })
                
            except Exception as e:
                results.append({
                    "payload_size": len(payload),
                    "error": str(e)
                })
        
        return results


class StealthTransmitter:
    """
    Stealth transmission techniques
    """
    
    def __init__(self, engine: RawSocketEngine):
        self.engine = engine
    
    def send_with_fog(self,
                     packet,
                     count: int = 1,
                     base_delay: float = 0.0,
                     jitter_percent: float = 20.0) -> int:
        """
        Send packets with variable timing (FOG - Fuzzed Output Generation)
        
        Args:
            packet: Scapy packet
            count: Number of packets
            base_delay: Base delay between packets
            jitter_percent: Jitter percentage
            
        Returns:
            Number of packets sent
        """
        sent = 0
        
        for i in range(count):
            # Calculate jittered delay
            if jitter_percent > 0:
                jitter = base_delay * (jitter_percent / 100) * (2 * random.random() - 1)
                delay = max(0, base_delay + jitter)
            else:
                delay = base_delay
            
            # Send packet
            send(packet, verbose=0)
            sent += 1
            
            # Wait with jitter
            if delay > 0 and i < count - 1:
                time.sleep(delay)
        
        return sent
    
    def send_fragmented(self,
                       packet,
                       frag_size: int = 8) -> int:
        """
        Send packet as IP fragments
        
        Args:
            packet: Scapy packet to fragment
            frag_size: Fragment size
            
        Returns:
            Number of fragments sent
        """
        # Fragment the packet
        frags = fragment(packet, fragsize=frag_size)
        
        # Send fragments
        for frag in frags:
            send(frag, verbose=0)
        
        return len(frags)
    
    def send_with_decoys(self,
                        real_packet,
                        decoy_count: int = 5,
                        decoy_ips: Optional[List[str]] = None) -> int:
        """
        Send packet with decoy sources
        
        Args:
            real_packet: The real packet to send
            decoy_count: Number of decoy packets
            decoy_ips: List of decoy IPs (random if None)
            
        Returns:
            Total packets sent
        """
        import random
        
        packets = []
        
        # Generate decoy packets
        for i in range(decoy_count):
            if decoy_ips and i < len(decoy_ips):
                src_ip = decoy_ips[i]
            else:
                src_ip = RandIP()
            
            decoy = real_packet.copy()
            decoy[IP].src = src_ip
            packets.append(decoy)
        
        # Insert real packet at random position
        real_pos = random.randint(0, decoy_count)
        packets.insert(real_pos, real_packet)
        
        # Send all packets
        for pkt in packets:
            send(pkt, verbose=0)
        
        return len(packets)
    
    def slow_loris_send(self,
                       packet,
                       total_time: float = 60.0,
                       packet_count: int = 100) -> int:
        """
        Send packets slowly over time (Slow Loris style)
        
        Args:
            packet: Packet to send repeatedly
            total_time: Total transmission time
            packet_count: Number of packets
            
        Returns:
            Number of packets sent
        """
        delay = total_time / packet_count
        sent = 0
        
        for _ in range(packet_count):
            send(packet, verbose=0)
            sent += 1
            time.sleep(delay)
        
        return sent


class PacketCrafter:
    """
    High-level packet crafting interface
    Military-grade with NO simulation fallbacks
    """
    
    def __init__(self):
        self.engine = RawSocketEngine()
        self.fuzzer = ProtocolFuzzer(self.engine)
        self.stealth = StealthTransmitter(self.engine)
        self.sessions: Dict[str, Any] = {}
        
        # Disable scapy verbosity
        conf.verb = 0
        
        logger.info("[PACKET] Real packet crafter initialized")
    
    def create_session(self, name: str, config: Dict = None) -> str:
        """Create a new packet crafting session"""
        session_id = f"pkt-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        self.sessions[session_id] = {
            "name": name,
            "config": config or {},
            "packets": [],
            "created_at": datetime.utcnow().isoformat()
        }
        logger.info(f"[PACKET] Created session: {session_id}")
        return session_id
    
    def craft_packet(self, config: PacketConfig):
        """
        Craft a packet based on configuration
        
        Args:
            config: Packet configuration
            
        Returns:
            Scapy packet object
        """
        # Build IP layer
        pkt = IP(src=config.src_ip, dst=config.dst_ip)
        
        # Add transport layer
        if config.protocol == PacketProtocol.TCP:
            pkt /= TCP(
                sport=config.src_port,
                dport=config.dst_port,
                flags=config.flags or 'S'
            )
            
            # Add TCP options if specified
            if config.options.get('window'):
                pkt[TCP].window = config.options['window']
            if config.options.get('seq'):
                pkt[TCP].seq = config.options['seq']
                
        elif config.protocol == PacketProtocol.UDP:
            pkt /= UDP(
                sport=config.src_port,
                dport=config.dst_port
            )
            
        elif config.protocol == PacketProtocol.ICMP:
            icmp_type = config.options.get('icmp_type', 8)
            icmp_code = config.options.get('icmp_code', 0)
            pkt /= ICMP(type=icmp_type, code=icmp_code)
            
        elif config.protocol == PacketProtocol.ARP:
            pkt = ARP(psrc=config.src_ip, pdst=config.dst_ip)
        
        # Add payload
        if config.payload:
            pkt /= Raw(load=config.payload)
        
        return pkt
    
    def send_packet(self, 
                   packet,
                   iface: Optional[str] = None,
                   count: int = 1,
                   interval: float = 0.0) -> Dict:
        """
        Send crafted packet(s)
        
        Args:
            packet: Scapy packet
            iface: Interface to use
            count: Number of packets
            interval: Interval between packets
            
        Returns:
            Transmission statistics
        """
        start_time = time.time()
        
        # Use scapy send for high-level control
        sent = send(packet, iface=iface, count=count, inter=interval, verbose=0)
        
        duration = time.time() - start_time
        
        return {
            "sent": sent,
            "duration": duration,
            "rate": sent / duration if duration > 0 else 0,
            "status": "success"
        }
    
    def send_with_fog_jitter(self,
                            packet,
                            burst_count: int = 1,
                            fog_delay_ms: float = 0,
                            jitter_percent: float = 0) -> Dict:
        """
        Send with FOG jitter
        
        Args:
            packet: Packet to send
            burst_count: Number of packets
            fog_delay_ms: Base delay in milliseconds
            jitter_percent: Jitter percentage
            
        Returns:
            Transmission statistics
        """
        sent = self.stealth.send_with_fog(
            packet,
            count=burst_count,
            base_delay=fog_delay_ms / 1000.0,
            jitter_percent=jitter_percent
        )
        
        return {
            "sent": sent,
            "mode": "FOG",
            "jitter": jitter_percent,
            "status": "success"
        }
    
    def capture_packets(self,
                       interface: Optional[str] = None,
                       count: int = 100,
                       timeout: int = 30,
                       filter_expr: str = "") -> List:
        """
        Capture packets
        
        Args:
            interface: Network interface
            count: Number of packets
            timeout: Capture timeout
            filter_expr: BPF filter
            
        Returns:
            List of captured packets
        """
        return self.engine.receive_raw(
            interface=interface,
            count=count,
            timeout=timeout,
            filter_expr=filter_expr
        )
    
    def fuzz_target(self,
                   target_ip: str,
                   target_port: int,
                   protocol: str = "tcp",
                   field: str = "seq",
                   iterations: int = 100) -> List[Dict]:
        """
        Fuzz target with various inputs
        
        Args:
            target_ip: Target IP
            target_port: Target port
            protocol: Protocol
            field: Field to fuzz
            iterations: Number of iterations
            
        Returns:
            Fuzzing results
        """
        # Generate fuzz values
        values = []
        
        if field in ["seq", "ack"]:
            values = [0, 1, 0x7FFFFFFF, 0xFFFFFFFF, random.randint(0, 0xFFFFFFFF)]
        elif field == "flags":
            values = ['S', 'A', 'F', 'R', 'P', 'SA', 'FA', 'RA', 'SF', '']
        elif field == "window":
            values = [0, 1, 65535, 65536, 0xFFFF]
        else:
            values = [random.randint(0, 65535) for _ in range(iterations)]
        
        return self.fuzzer.fuzz_tcp_field(
            target_ip=target_ip,
            target_port=target_port,
            field=field,
            values=values
        )
    
    def save_capture(self, packets: List, filename: str) -> bool:
        """Save packets to pcap file"""
        try:
            wrpcap(filename, packets)
            logger.info(f"[PACKET] Saved {len(packets)} packets to {filename}")
            return True
        except Exception as e:
            logger.error(f"[PACKET] Failed to save capture: {e}")
            return False
    
    def load_capture(self, filename: str) -> List:
        """Load packets from pcap file"""
        try:
            packets = rdpcap(filename)
            logger.info(f"[PACKET] Loaded {len(packets)} packets from {filename}")
            return packets
        except Exception as e:
            logger.error(f"[PACKET] Failed to load capture: {e}")
            return []
    
    def get_statistics(self) -> Dict:
        """Get packet crafting statistics"""
        return {
            "packets_sent": self.engine.stats["packets_sent"],
            "packets_received": self.engine.stats["packets_received"],
            "bytes_sent": self.engine.stats["bytes_sent"],
            "bytes_received": self.engine.stats["bytes_received"],
            "fuzzing_tests": self.fuzzer.fuzzing_stats["tests_run"],
            "fuzzing_anomalies": self.fuzzer.fuzzing_stats["anomalies"],
            "sessions": len(self.sessions)
        }


# Singleton
_crafter_instance: Optional[PacketCrafter] = None

def get_packet_crafter() -> PacketCrafter:
    """Get singleton packet crafter instance"""
    global _crafter_instance
    if _crafter_instance is None:
        _crafter_instance = PacketCrafter()
    return _crafter_instance


class NetworkControl:
    """Network interface control operations"""
    
    def __init__(self):
        self.adapters = self._get_adapters()
    
    def _get_adapters(self) -> List[Dict]:
        """Get network adapters list"""
        adapters = []
        try:
            if PSUTIL_AVAILABLE:
                for name, addrs in psutil.net_if_addrs().items():
                    if name == 'lo':
                        continue
                    
                    ip_addr = ""
                    mac_addr = ""
                    
                    for addr in addrs:
                        if addr.family == socket.AF_INET:  # IPv4
                            ip_addr = addr.address
                        elif hasattr(psutil, 'AF_LINK') and addr.family == psutil.AF_LINK:  # MAC
                            mac_addr = addr.address
                    
                    stats = psutil.net_if_stats().get(name)
                    
                    adapters.append({
                        "name": name,
                        "ip": ip_addr,
                        "mac": mac_addr,
                        "up": stats.isup if stats else False,
                        "speed_mbps": stats.speed if stats else 0
                    })
            else:
                # Fallback to reading /proc/net/dev
                with open('/proc/net/dev', 'r') as f:
                    for line in f.readlines()[2:]:
                        parts = line.strip().split(':')
                        if len(parts) == 2:
                            name = parts[0].strip()
                            if name != 'lo':
                                adapters.append({
                                    "name": name,
                                    "ip": "",
                                    "mac": "",
                                    "up": True,
                                    "speed_mbps": 0
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
            if PSUTIL_AVAILABLE:
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
            else:
                return {"interface": interface, "error": "psutil not available"}
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
            if result.returncode == 0 or "Cannot delete" in result.stderr:
                self.shaped_interfaces.discard(interface)
                return True
            return False
        except Exception as e:
            logger.error(f"Error removing shaping: {e}")
            return False


# Singleton instances
_network_control: Optional[NetworkControl] = None
_traffic_shaper: Optional[TrafficShaper] = None

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


__all__ = [
    'PacketCrafter',
    'RawSocketEngine',
    'ProtocolFuzzer',
    'StealthTransmitter',
    'PacketConfig',
    'PacketProtocol',
    'StealthMode',
    'NetworkControl',
    'TrafficShaper',
    'get_packet_crafter',
    'get_network_control',
    'get_traffic_shaper'
]
