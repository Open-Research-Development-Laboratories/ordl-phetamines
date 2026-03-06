"""
ORDL RED TEAM - RECONNAISSANCE MODULE
Classification: TOP SECRET//SCI//NOFORN

Network reconnaissance and intelligence gathering capabilities:
- Port scanning (TCP/UDP)
- Service detection and banner grabbing
- OS fingerprinting
- Subdomain enumeration
- WHOIS and DNS reconnaissance
- Network mapping
"""

import socket
import subprocess
import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import ipaddress

logger = logging.getLogger(__name__)


@dataclass
class PortScanResult:
    """Result of a port scan"""
    port: int
    protocol: str  # tcp or udp
    state: str  # open, closed, filtered
    service: str = ""
    version: str = ""
    banner: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "port": self.port,
            "protocol": self.protocol,
            "state": self.state,
            "service": self.service,
            "version": self.version,
            "banner": self.banner
        }


@dataclass
class HostInfo:
    """Information about a target host"""
    ip: str
    hostname: str = ""
    os_guess: str = ""
    os_confidence: int = 0  # 0-100
    ports: List[PortScanResult] = field(default_factory=list)
    mac_address: str = ""
    vendor: str = ""
    uptime: str = ""
    distance: int = 0  # Network hops
    
    def to_dict(self) -> Dict:
        return {
            "ip": self.ip,
            "hostname": self.hostname,
            "os_guess": self.os_guess,
            "os_confidence": self.os_confidence,
            "ports": [p.to_dict() for p in self.ports],
            "mac_address": self.mac_address,
            "vendor": self.vendor,
            "uptime": self.uptime,
            "distance": self.distance
        }


@dataclass
class DNSRecord:
    """DNS record information"""
    record_type: str  # A, AAAA, MX, NS, TXT, CNAME, etc.
    name: str
    value: str
    ttl: int = 0


@dataclass
class WHOISInfo:
    """WHOIS lookup result"""
    domain: str
    registrar: str = ""
    creation_date: str = ""
    expiration_date: str = ""
    name_servers: List[str] = field(default_factory=list)
    registrant: Dict = field(default_factory=dict)
    admin_contact: Dict = field(default_factory=dict)
    tech_contact: Dict = field(default_factory=dict)
    status: List[str] = field(default_factory=list)
    raw_data: str = ""


class ReconManager:
    """
    Network reconnaissance manager.
    Implements stealthy scanning techniques for authorized operations.
    """
    
    # Common ports for quick scans
    TOP_PORTS = [21, 22, 23, 25, 53, 80, 110, 135, 139, 143, 443, 445, 
                 993, 995, 1723, 3306, 3389, 5432, 5900, 8080, 8443]
    
    # Service signatures for banner detection
    SERVICE_SIGNATURES = {
        21: (b"220", "FTP"),
        22: (b"SSH-", "SSH"),
        25: (b"220", "SMTP"),
        80: (b"HTTP/1.", "HTTP"),
        110: (b"+OK", "POP3"),
        143: (b"* OK", "IMAP"),
        443: (b"HTTP/1.", "HTTPS"),
        3306: (b"4.1.", "MySQL"),
        5432: (b"R", "PostgreSQL"),
    }
    
    def __init__(self, redteam_manager=None):
        self.rt_manager = redteam_manager
        self.scan_results: Dict[str, HostInfo] = {}
        self.dns_cache: Dict[str, List[DNSRecord]] = {}
        self.whois_cache: Dict[str, WHOISInfo] = {}
        
        # Check for nmap
        self.nmap_available = self._check_nmap()
        
    def _check_nmap(self) -> bool:
        """Check if nmap is available"""
        try:
            result = subprocess.run(['nmap', '--version'], 
                                  capture_output=True, timeout=5)
            return result.returncode == 0
        except:
            return False
    
    def _is_valid_ip(self, target: str) -> bool:
        """Check if target is a valid IP address"""
        try:
            ipaddress.ip_address(target)
            return True
        except ValueError:
            return False
    
    def _is_valid_network(self, target: str) -> bool:
        """Check if target is a valid network CIDR"""
        try:
            ipaddress.ip_network(target, strict=False)
            return True
        except ValueError:
            return False
    
    def resolve_hostname(self, hostname: str) -> Optional[str]:
        """Resolve hostname to IP address"""
        try:
            return socket.gethostbyname(hostname)
        except socket.gaierror:
            logger.warning(f"[Recon] Could not resolve {hostname}")
            return None
    
    def reverse_dns(self, ip: str) -> Optional[str]:
        """Perform reverse DNS lookup"""
        try:
            return socket.gethostbyaddr(ip)[0]
        except socket.herror:
            return None
    
    def scan_port(self, target: str, port: int, protocol: str = "tcp",
                  timeout: float = 2.0, grab_banner: bool = True) -> PortScanResult:
        """
        Scan a single port on a target.
        
        Args:
            target: IP address or hostname
            port: Port number to scan
            protocol: tcp or udp
            timeout: Connection timeout in seconds
            grab_banner: Attempt to grab service banner
        
        Returns:
            PortScanResult with scan details
        """
        result = PortScanResult(port=port, protocol=protocol, state="filtered")
        
        if protocol == "tcp":
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            
            try:
                sock.connect((target, port))
                result.state = "open"
                
                # Try to identify service
                if port in self.SERVICE_SIGNATURES:
                    result.service = self.SERVICE_SIGNATURES[port][1]
                else:
                    result.service = self._guess_service(port)
                
                # Banner grabbing
                if grab_banner:
                    try:
                        # Send a probe
                        if port == 80 or port == 443:
                            sock.send(b"HEAD / HTTP/1.0\r\n\r\n")
                        else:
                            sock.send(b"\r\n")
                        
                        banner = sock.recv(1024)
                        if banner:
                            result.banner = banner.decode('utf-8', errors='ignore').strip()
                            
                            # Extract version from banner
                            result.version = self._extract_version(result.banner)
                    except:
                        pass
                
            except socket.timeout:
                result.state = "filtered"
            except ConnectionRefusedError:
                result.state = "closed"
            except Exception as e:
                result.state = "filtered"
                logger.debug(f"[Recon] Scan error on {target}:{port}: {e}")
            finally:
                sock.close()
        
        elif protocol == "udp":
            # UDP scanning is unreliable but implemented
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(timeout)
            
            try:
                sock.sendto(b"\x00", (target, port))
                data, addr = sock.recvfrom(1024)
                result.state = "open"
                result.service = self._guess_service(port)
            except socket.timeout:
                # No response could mean open or filtered
                result.state = "open|filtered"
            except ConnectionRefusedError:
                # ICMP port unreachable
                result.state = "closed"
            except Exception as e:
                result.state = "filtered"
            finally:
                sock.close()
        
        return result
    
    def _guess_service(self, port: int) -> str:
        """Guess service name from port number"""
        common_ports = {
            21: "ftp", 22: "ssh", 23: "telnet", 25: "smtp", 53: "domain",
            80: "http", 110: "pop3", 111: "rpcbind", 135: "msrpc", 139: "netbios-ssn",
            143: "imap", 443: "https", 445: "microsoft-ds", 993: "imaps",
            995: "pop3s", 1723: "pptp", 3306: "mysql", 3389: "ms-wbt-server",
            5432: "postgresql", 5900: "vnc", 8080: "http-proxy", 8443: "https-alt"
        }
        return common_ports.get(port, "unknown")
    
    def _extract_version(self, banner: str) -> str:
        """Extract version string from banner"""
        import re
        
        # Common version patterns
        patterns = [
            r'[Vv]ersion[:\s]+([\d.]+)',
            r'/(\d\.\d[^\s]*)',
            r'SSH-([\d.]+)',
            r'HTTP/(\d\.\d)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, banner)
            if match:
                return match.group(1)
        
        return ""
    
    def scan_host(self, target: str, ports: List[int] = None,
                  protocols: List[str] = None, 
                  threads: int = 50,
                  timeout: float = 2.0) -> HostInfo:
        """
        Scan a single host for open ports.
        
        Args:
            target: IP address or hostname
            ports: List of ports to scan (default: TOP_PORTS)
            protocols: List of protocols to scan (default: ["tcp"])
            threads: Number of concurrent threads
            timeout: Connection timeout per port
        
        Returns:
            HostInfo with scan results
        """
        # Resolve hostname if needed
        if not self._is_valid_ip(target):
            resolved_ip = self.resolve_hostname(target)
            if resolved_ip:
                hostname = target
                target = resolved_ip
            else:
                return HostInfo(ip=target, hostname=target)
        else:
            hostname = self.reverse_dns(target) or ""
        
        ports = ports or self.TOP_PORTS
        protocols = protocols or ["tcp"]
        
        host_info = HostInfo(ip=target, hostname=hostname)
        
        logger.info(f"[Recon] Scanning {target} ({hostname}) - {len(ports)} ports")
        
        # Thread pool for concurrent scanning
        with ThreadPoolExecutor(max_workers=threads) as executor:
            futures = []
            
            for port in ports:
                for protocol in protocols:
                    future = executor.submit(
                        self.scan_port, target, port, protocol, timeout
                    )
                    futures.append(future)
            
            # Collect results
            for future in as_completed(futures):
                result = future.result()
                if result.state in ["open", "open|filtered"]:
                    host_info.ports.append(result)
        
        # Sort ports by number
        host_info.ports.sort(key=lambda x: x.port)
        
        # OS fingerprinting based on open ports
        host_info.os_guess, host_info.os_confidence = self._fingerprint_os(host_info)
        
        # Cache result
        self.scan_results[target] = host_info
        
        logger.info(f"[Recon] Scan complete: {target} - {len(host_info.ports)} open ports")
        
        return host_info
    
    def _fingerprint_os(self, host_info: HostInfo) -> Tuple[str, int]:
        """Simple OS fingerprinting based on port patterns"""
        open_ports = {p.port for p in host_info.ports}
        
        # Windows signatures
        windows_ports = {135, 139, 445, 3389}
        if len(open_ports & windows_ports) >= 2:
            return "Windows", 85
        
        # Linux/Unix signatures
        linux_ports = {22, 111, 2049}
        if len(open_ports & linux_ports) >= 2:
            return "Linux/Unix", 80
        
        # Network device signatures
        if 23 in open_ports:
            return "Network Device (Telnet)", 70
        
        # Web server
        if 80 in open_ports or 443 in open_ports:
            return "Web Server (Unknown OS)", 40
        
        return "Unknown", 0
    
    def scan_network(self, network: str, ports: List[int] = None,
                    threads: int = 100) -> List[HostInfo]:
        """
        Scan an entire network range.
        
        Args:
            network: CIDR notation (e.g., "192.168.1.0/24")
            ports: Ports to scan (default: common ports)
            threads: Concurrent threads
        
        Returns:
            List of HostInfo for responsive hosts
        """
        if not self._is_valid_network(network):
            raise ValueError(f"Invalid network: {network}")
        
        net = ipaddress.ip_network(network, strict=False)
        hosts = [str(ip) for ip in net.hosts()]
        
        logger.info(f"[Recon] Scanning network {network} ({len(hosts)} hosts)")
        
        results = []
        
        with ThreadPoolExecutor(max_workers=threads) as executor:
            futures = {executor.submit(self._ping_host, host): host 
                      for host in hosts}
            
            for future in as_completed(futures):
                host = futures[future]
                try:
                    if future.result():
                        host_info = self.scan_host(host, ports, threads=20)
                        if host_info.ports:
                            results.append(host_info)
                except Exception as e:
                    logger.debug(f"[Recon] Error scanning {host}: {e}")
        
        logger.info(f"[Recon] Network scan complete: {len(results)} hosts with open ports")
        return results
    
    def _ping_host(self, host: str, timeout: float = 1.0) -> bool:
        """Quick ping check if host is alive"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, 80))
            sock.close()
            return result == 0
        except:
            return False
    
    def dns_lookup(self, domain: str, record_types: List[str] = None) -> List[DNSRecord]:
        """
        Perform DNS lookup for a domain.
        
        Args:
            domain: Domain name to lookup
            record_types: DNS record types (default: A, AAAA, MX, NS, TXT)
        
        Returns:
            List of DNS records
        """
        import dns.resolver
        
        record_types = record_types or ["A", "AAAA", "MX", "NS", "TXT"]
        records = []
        
        for record_type in record_types:
            try:
                answers = dns.resolver.resolve(domain, record_type)
                for rdata in answers:
                    records.append(DNSRecord(
                        record_type=record_type,
                        name=domain,
                        value=str(rdata),
                        ttl=answers.ttl
                    ))
            except Exception as e:
                logger.debug(f"[Recon] DNS lookup failed for {domain} {record_type}: {e}")
        
        self.dns_cache[domain] = records
        return records
    
    def enumerate_subdomains(self, domain: str, 
                            wordlist: List[str] = None) -> List[str]:
        """
        Enumerate subdomains using DNS brute force.
        
        Args:
            domain: Base domain
            wordlist: List of subdomain prefixes
        
        Returns:
            List of discovered subdomains
        """
        import dns.resolver
        
        if wordlist is None:
            wordlist = [
                "www", "mail", "ftp", "admin", "portal", "api", "dev", "test",
                "staging", "vpn", "remote", "blog", "shop", "support", "help",
                "docs", "cdn", "media", "static", "app", "mobile", "webmail",
                "secure", "login", "auth", "sso", "git", "jenkins", "jira",
                "confluence", "wiki", "monitor", "nagios", "zabbix", "grafana",
                "db", "database", "mysql", "postgres", "mongo", "redis",
                "backup", "archive", "old", "legacy", "v1", "v2", "beta"
            ]
        
        found = []
        
        logger.info(f"[Recon] Enumerating subdomains for {domain} ({len(wordlist)} candidates)")
        
        def check_subdomain(subdomain):
            full_domain = f"{subdomain}.{domain}"
            try:
                answers = dns.resolver.resolve(full_domain, "A")
                return full_domain
            except:
                return None
        
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(check_subdomain, sub) for sub in wordlist]
            
            for future in as_completed(futures):
                result = future.result()
                if result:
                    found.append(result)
        
        logger.info(f"[Recon] Subdomain enumeration complete: {len(found)} found")
        return sorted(found)
    
    def whois_lookup(self, domain: str) -> Optional[WHOISInfo]:
        """
        Perform WHOIS lookup for a domain.
        
        Args:
            domain: Domain name
        
        Returns:
            WHOISInfo or None if lookup fails
        """
        try:
            import whois
            
            w = whois.whois(domain)
            
            info = WHOISInfo(
                domain=domain,
                registrar=w.registrar or "",
                creation_date=str(w.creation_date[0]) if isinstance(w.creation_date, list) else str(w.creation_date),
                expiration_date=str(w.expiration_date[0]) if isinstance(w.expiration_date, list) else str(w.expiration_date),
                name_servers=w.name_servers if isinstance(w.name_servers, list) else [w.name_servers],
                status=w.status if isinstance(w.status, list) else [w.status],
                raw_data=str(w)
            )
            
            self.whois_cache[domain] = info
            return info
            
        except Exception as e:
            logger.warning(f"[Recon] WHOIS lookup failed for {domain}: {e}")
            return None
    
    def traceroute(self, target: str, max_hops: int = 30) -> List[Dict]:
        """
        Perform traceroute to target.
        
        Args:
            target: IP or hostname
            max_hops: Maximum number of hops
        
        Returns:
            List of hop information
        """
        hops = []
        
        for ttl in range(1, max_hops + 1):
            sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, 
                               socket.IPPROTO_ICMP)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_TTL, ttl)
            sock.settimeout(2.0)
            
            try:
                # Send ICMP echo request
                import struct
                icmp_id = 12345
                icmp_seq = ttl
                checksum = 0
                header = struct.pack('!BBHHH', 8, 0, checksum, icmp_id, icmp_seq)
                data = b'ORDL-Recon'
                packet = header + data
                
                sock.sendto(packet, (target, 0))
                
                recv_sock = socket.socket(socket.AF_INET, socket.SOCK_RAW,
                                        socket.IPPROTO_ICMP)
                recv_sock.settimeout(2.0)
                
                reply, addr = recv_sock.recvfrom(1024)
                
                hop_info = {
                    "hop": ttl,
                    "ip": addr[0],
                    "hostname": self.reverse_dns(addr[0]) or "",
                    "rtt": "<1ms"  # Simplified
                }
                hops.append(hop_info)
                
                if addr[0] == target:
                    break
                    
            except socket.timeout:
                hops.append({"hop": ttl, "ip": "*", "hostname": "", "rtt": "timeout"})
            except Exception as e:
                hops.append({"hop": ttl, "ip": "*", "hostname": "", "rtt": "error"})
            finally:
                sock.close()
        
        return hops
    
    def get_host_summary(self, target: str) -> Dict:
        """Get a summary of reconnaissance data for a target"""
        host_info = self.scan_results.get(target)
        
        if not host_info:
            return {"error": "No scan data for target"}
        
        return {
            "target": target,
            "hostname": host_info.hostname,
            "os_guess": host_info.os_guess,
            "open_ports": len(host_info.ports),
            "services": list(set(p.service for p in host_info.ports)),
            "scan_timestamp": datetime.utcnow().isoformat()
        }


__all__ = [
    'ReconManager',
    'PortScanResult',
    'HostInfo',
    'DNSRecord',
    'WHOISInfo'
]
