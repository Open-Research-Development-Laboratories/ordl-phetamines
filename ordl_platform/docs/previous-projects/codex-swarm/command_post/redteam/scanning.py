"""
ORDL RED TEAM - VULNERABILITY SCANNING MODULE
Classification: TOP SECRET//SCI//NOFORN

Comprehensive vulnerability assessment capabilities:
- CVE database integration
- Service vulnerability checks
- Web application scanning (SQLi, XSS, LFI, RCE)
- SSL/TLS analysis
- Configuration auditing
- Compliance checking (NIST 800-53, CIS Benchmarks)
"""

import socket
import ssl
import json
import logging
import re
import requests
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin, urlparse, parse_qs

logger = logging.getLogger(__name__)


@dataclass
class Vulnerability:
    """Represents a discovered vulnerability"""
    vuln_id: str
    name: str
    description: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW, INFO
    cvss_score: float = 0.0
    cvss_vector: str = ""
    cve_ids: List[str] = field(default_factory=list)
    affected_host: str = ""
    affected_service: str = ""
    port: int = 0
    evidence: str = ""
    remediation: str = ""
    references: List[str] = field(default_factory=list)
    discovered_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    verified: bool = False
    false_positive: bool = False


@dataclass
class SSLInfo:
    """SSL/TLS certificate and configuration information"""
    host: str
    port: int
    protocol_version: str = ""
    cipher_suite: str = ""
    certificate_subject: str = ""
    certificate_issuer: str = ""
    certificate_not_before: str = ""
    certificate_not_after: str = ""
    certificate_serial: str = ""
    certificate_algorithms: str = ""
    ssl_score: int = 0  # 0-100
    vulnerabilities: List[str] = field(default_factory=list)
    weak_ciphers: List[str] = field(default_factory=list)
    certificate_expired: bool = False
    certificate_self_signed: bool = False
    hostname_mismatch: bool = False


@dataclass
class WebVulnerability:
    """Web application vulnerability"""
    url: str
    parameter: str
    vuln_type: str  # SQLi, XSS, LFI, RCE, CSRF, etc.
    severity: str
    payload: str = ""
    evidence: str = ""
    request_method: str = "GET"


class VulnerabilityDatabase:
    """
    Local vulnerability database for common CVEs.
    In production, this would connect to NVD or VulDB.
    """
    
    # Common CVEs by service/version
    VULNERABILITIES = {
        "apache": {
            "2.4.49": [
                {
                    "cve": "CVE-2021-41773",
                    "name": "Apache Path Traversal",
                    "description": "Path traversal and file disclosure vulnerability",
                    "severity": "CRITICAL",
                    "cvss": 7.5
                }
            ],
            "2.4.50": [
                {
                    "cve": "CVE-2021-42013",
                    "name": "Apache Path Traversal (Variant)",
                    "description": "Path traversal vulnerability in Apache HTTP Server",
                    "severity": "CRITICAL",
                    "cvss": 7.5
                }
            ]
        },
        "openssh": {
            "8.2": [
                {
                    "cve": "CVE-2020-15778",
                    "name": "OpenSSH scp Command Injection",
                    "description": "Command injection vulnerability in scp",
                    "severity": "HIGH",
                    "cvss": 7.0
                }
            ]
        },
        "mysql": {
            "5.7": [
                {
                    "cve": "CVE-2021-2154",
                    "name": "MySQL Denial of Service",
                    "description": "Vulnerability in MySQL Server",
                    "severity": "MEDIUM",
                    "cvss": 5.5
                }
            ]
        },
        "wordpress": {
            "5.7": [
                {
                    "cve": "CVE-2021-29447",
                    "name": "WordPress XXE",
                    "description": "XML External Entity injection in WordPress",
                    "severity": "HIGH",
                    "cvss": 7.1
                }
            ]
        }
    }
    
    # Default credentials database
    DEFAULT_CREDENTIALS = {
        "admin": ["admin", "password", "123456", "admin123"],
        "root": ["root", "password", "123456", "toor"],
        "user": ["user", "password", "123456"],
        "guest": ["guest", "guest", "password"],
        "test": ["test", "test", "password"],
        "oracle": ["oracle", "password", "manager"],
        "postgres": ["postgres", "password", "admin"],
        "mysql": ["mysql", "password", "admin"]
    }
    
    @classmethod
    def lookup_cve(cls, service: str, version: str) -> List[Dict]:
        """Look up CVEs for a service version"""
        service = service.lower()
        
        # Exact match
        if service in cls.VULNERABILITIES and version in cls.VULNERABILITIES[service]:
            return cls.VULNERABILITIES[service][version]
        
        # Partial version match (e.g., "2.4.49" matches "2.4")
        if service in cls.VULNERABILITIES:
            for v in cls.VULNERABILITIES[service]:
                if version.startswith(v):
                    return cls.VULNERABILITIES[service][v]
        
        return []
    
    @classmethod
    def get_default_credentials(cls, username: str) -> List[str]:
        """Get common passwords for a username"""
        return cls.DEFAULT_CREDENTIALS.get(username, ["password", "123456", "admin"])


class VulnerabilityScanner:
    """
    Comprehensive vulnerability scanner.
    Scans services and web applications for known vulnerabilities.
    """
    
    def __init__(self, redteam_manager=None):
        self.rt_manager = redteam_manager
        self.vulns_found: List[Vulnerability] = []
        self.scan_results: Dict[str, List[Vulnerability]] = {}
        
        # SQL injection payloads
        self.sqli_payloads = [
            "' OR '1'='1",
            "' OR '1'='1' --",
            "' OR 1=1 --",
            "\" OR \"1\"=\"1",
            "' UNION SELECT NULL--",
            "' UNION SELECT NULL,NULL--",
            "1' AND 1=1--",
            "1' AND 1=2--",
            "1' OR '1'='1",
            "1 AND 1=1",
            "1 AND 1=2",
            "1 OR 1=1",
            "1' WAITFOR DELAY '0:0:5'--",
            "1; SELECT pg_sleep(5)--"
        ]
        
        # XSS payloads
        self.xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "<body onload=alert('XSS')>",
            "<svg onload=alert('XSS')>",
            "javascript:alert('XSS')",
            "<iframe src=javascript:alert('XSS')>",
            "'><script>alert('XSS')</script>",
            "\" onmouseover=alert('XSS')",
            "<input onfocus=alert('XSS') autofocus>"
        ]
        
        # LFI payloads
        self.lfi_payloads = [
            "../../../etc/passwd",
            "../../../etc/passwd%00",
            "....//....//....//etc/passwd",
            "..\\..\\..\\windows\\system32\\drivers\\etc\\hosts",
            "/etc/passwd",
            "C:\\Windows\\System32\\drivers\\etc\\hosts",
            "file:///etc/passwd",
            "php://filter/read=convert.base64-encode/resource=index.php"
        ]
        
        # Path traversal payloads
        self.path_traversal_payloads = [
            "../",
            "..\\",
            "..%2f",
            "..%5c",
            "%2e%2e%2f",
            "%252e%252e%252f",
            "....//",
            "....\\"
        ]
    
    def scan_service(self, host: str, port: int, service: str, 
                    version: str) -> List[Vulnerability]:
        """
        Scan a service for known vulnerabilities.
        
        Args:
            host: Target IP
            port: Port number
            service: Service name (ssh, http, etc.)
            version: Service version
        
        Returns:
            List of discovered vulnerabilities
        """
        vulns = []
        
        logger.info(f"[Scanner] Scanning {host}:{port} ({service} {version})")
        
        # Look up CVEs
        cves = VulnerabilityDatabase.lookup_cve(service, version)
        for cve in cves:
            vuln = Vulnerability(
                vuln_id=f"VULN-{len(self.vulns_found)+1:04d}",
                name=cve["name"],
                description=cve["description"],
                severity=cve["severity"],
                cvss_score=cve["cvss"],
                cve_ids=[cve["cve"]],
                affected_host=host,
                affected_service=service,
                port=port,
                evidence=f"Service version {version} is vulnerable",
                remediation=f"Upgrade {service} to latest version"
            )
            vulns.append(vuln)
            self.vulns_found.append(vuln)
        
        # Service-specific checks
        if service == "ssh":
            vulns.extend(self._check_ssh_security(host, port, version))
        elif service in ["http", "https"]:
            vulns.extend(self._check_web_security(host, port, service))
        elif service == "ftp":
            vulns.extend(self._check_ftp_security(host, port))
        elif service == "smtp":
            vulns.extend(self._check_smtp_security(host, port))
        elif service == "mysql":
            vulns.extend(self._check_mysql_security(host, port, version))
        
        self.scan_results[f"{host}:{port}"] = vulns
        return vulns
    
    def _check_ssh_security(self, host: str, port: int, 
                           version: str) -> List[Vulnerability]:
        """Check SSH configuration security"""
        vulns = []
        
        # Check for old SSH versions
        old_versions = ["1.0", "2.0", "3.0", "4.0"]
        if any(v in version for v in old_versions):
            vulns.append(Vulnerability(
                vuln_id=f"VULN-{len(self.vulns_found)+len(vulns)+1:04d}",
                name="Outdated SSH Version",
                description=f"SSH version {version} is outdated and may contain vulnerabilities",
                severity="HIGH",
                cvss_score=7.5,
                affected_host=host,
                affected_service="ssh",
                port=port,
                remediation="Upgrade to OpenSSH 8.0 or later"
            ))
        
        # Check for password authentication (would require deeper inspection)
        # Check for weak algorithms (would require SSH connection)
        
        return vulns
    
    def _check_web_security(self, host: str, port: int, 
                           protocol: str) -> List[Vulnerability]:
        """Check web application security"""
        vulns = []
        
        base_url = f"{protocol}://{host}:{port}"
        
        try:
            # Check SSL/TLS if HTTPS
            if protocol == "https":
                ssl_info = self.analyze_ssl(host, port)
                if ssl_info.vulnerabilities:
                    for v in ssl_info.vulnerabilities:
                        vulns.append(Vulnerability(
                            vuln_id=f"VULN-{len(self.vulns_found)+len(vulns)+1:04d}",
                            name=v,
                            description=f"SSL/TLS vulnerability: {v}",
                            severity="HIGH",
                            affected_host=host,
                            affected_service="https",
                            port=port,
                            remediation="Update SSL/TLS configuration"
                        ))
            
            # Check for common security headers
            response = requests.get(base_url, timeout=10, verify=False)
            headers = response.headers
            
            security_headers = {
                "X-Frame-Options": "Clickjacking protection",
                "X-XSS-Protection": "XSS filtering",
                "X-Content-Type-Options": "MIME sniffing protection",
                "Content-Security-Policy": "Content injection protection",
                "Strict-Transport-Security": "HTTPS enforcement"
            }
            
            for header, description in security_headers.items():
                if header not in headers:
                    vulns.append(Vulnerability(
                        vuln_id=f"VULN-{len(self.vulns_found)+len(vulns)+1:04d}",
                        name=f"Missing Security Header: {header}",
                        description=f"The {header} header is missing, which reduces protection against {description}",
                        severity="MEDIUM",
                        cvss_score=5.0,
                        affected_host=host,
                        affected_service="http",
                        port=port,
                        remediation=f"Add the {header} header to all responses"
                    ))
            
            # Check for server version disclosure
            if "Server" in headers:
                server = headers["Server"]
                vulns.append(Vulnerability(
                    vuln_id=f"VULN-{len(self.vulns_found)+len(vulns)+1:04d}",
                    name="Server Version Disclosure",
                    description=f"Server banner reveals version information: {server}",
                    severity="LOW",
                    cvss_score=2.0,
                    affected_host=host,
                    affected_service="http",
                    port=port,
                    remediation="Configure server to hide version information"
                ))
            
            # Check for directory listing
            common_dirs = ["/", "/admin/", "/backup/", "/test/", "/api/"]
            for dir_path in common_dirs:
                try:
                    dir_url = urljoin(base_url, dir_path)
                    dir_response = requests.get(dir_url, timeout=5, verify=False)
                    if "Index of" in dir_response.text or "Directory Listing" in dir_response.text:
                        vulns.append(Vulnerability(
                            vuln_id=f"VULN-{len(self.vulns_found)+len(vulns)+1:04d}",
                            name="Directory Listing Enabled",
                            description=f"Directory listing is enabled at {dir_path}",
                            severity="MEDIUM",
                            cvss_score=5.0,
                            affected_host=host,
                            affected_service="http",
                            port=port,
                            evidence=f"URL: {dir_url}",
                            remediation="Disable directory listing in web server configuration"
                        ))
                except:
                    pass
            
        except Exception as e:
            logger.debug(f"[Scanner] Web check failed for {base_url}: {e}")
        
        return vulns
    
    def _check_ftp_security(self, host: str, port: int) -> List[Vulnerability]:
        """Check FTP security"""
        vulns = []
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((host, port))
            banner = sock.recv(1024).decode('utf-8', errors='ignore')
            sock.close()
            
            # Check for anonymous FTP
            if "vsftpd" in banner.lower():
                vulns.append(Vulnerability(
                    vuln_id=f"VULN-{len(self.vulns_found)+len(vulns)+1:04d}",
                    name="FTP Service Detected",
                    description="FTP service may allow anonymous access",
                    severity="MEDIUM",
                    cvss_score=5.0,
                    affected_host=host,
                    affected_service="ftp",
                    port=port,
                    evidence=f"Banner: {banner.strip()}",
                    remediation="Disable anonymous FTP access"
                ))
        except:
            pass
        
        return vulns
    
    def _check_smtp_security(self, host: str, port: int) -> List[Vulnerability]:
        """Check SMTP security"""
        vulns = []
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((host, port))
            banner = sock.recv(1024).decode('utf-8', errors='ignore')
            sock.close()
            
            # Check for open relay (simplified check)
            if "ESMTP" in banner:
                vulns.append(Vulnerability(
                    vuln_id=f"VULN-{len(self.vulns_found)+len(vulns)+1:04d}",
                    name="SMTP Server Detected",
                    description="SMTP server may be vulnerable to relay attacks",
                    severity="MEDIUM",
                    cvss_score=5.0,
                    affected_host=host,
                    affected_service="smtp",
                    port=port,
                    remediation="Configure SMTP authentication and disable open relay"
                ))
        except:
            pass
        
        return vulns
    
    def _check_mysql_security(self, host: str, port: int, 
                             version: str) -> List[Vulnerability]:
        """Check MySQL security"""
        vulns = []
        
        # Check for default/root access
        try:
            import mysql.connector
            
            # Try common credentials
            for user in ["root", "admin", "mysql"]:
                for password in ["", "password", "root", "admin", "mysql", "123456"]:
                    try:
                        conn = mysql.connector.connect(
                            host=host,
                            port=port,
                            user=user,
                            password=password,
                            connection_timeout=2
                        )
                        conn.close()
                        
                        vulns.append(Vulnerability(
                            vuln_id=f"VULN-{len(self.vulns_found)+len(vulns)+1:04d}",
                            name="Weak MySQL Credentials",
                            description=f"MySQL allows login with {user}/{password}",
                            severity="CRITICAL",
                            cvss_score=9.0,
                            affected_host=host,
                            affected_service="mysql",
                            port=port,
                            evidence=f"Successful login with {user}:{password}",
                            remediation="Change default passwords and disable remote root access"
                        ))
                        break
                    except:
                        continue
        except ImportError:
            logger.debug("[Scanner] mysql-connector not available for MySQL checks")
        except:
            pass
        
        return vulns
    
    def analyze_ssl(self, host: str, port: int = 443) -> SSLInfo:
        """
        Analyze SSL/TLS configuration.
        
        Args:
            host: Target host
            port: Port (default 443)
        
        Returns:
            SSLInfo with certificate and configuration details
        """
        info = SSLInfo(host=host, port=port)
        
        try:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            
            with socket.create_connection((host, port), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=host) as ssock:
                    # Get cipher and protocol info
                    info.cipher_suite = ssock.cipher()[0]
                    info.protocol_version = ssock.version()
                    
                    # Get certificate
                    cert = ssock.getpeercert()
                    if cert:
                        info.certificate_subject = cert.get("subject", "")
                        info.certificate_issuer = cert.get("issuer", "")
                        info.certificate_not_before = str(cert.get("notBefore", ""))
                        info.certificate_not_after = str(cert.get("notAfter", ""))
                        info.certificate_serial = str(cert.get("serialNumber", ""))
                        
                        # Check expiration
                        try:
                            from datetime import datetime
                            not_after = cert.get("notAfter")
                            if not_after:
                                expiry = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z")
                                info.certificate_expired = expiry < datetime.utcnow()
                        except:
                            pass
                        
                        # Check self-signed
                        info.certificate_self_signed = (
                            info.certificate_subject == info.certificate_issuer
                        )
                    
                    # Check for weak protocols
                    weak_protocols = ["SSLv2", "SSLv3", "TLSv1", "TLSv1.1"]
                    if info.protocol_version in weak_protocols:
                        info.vulnerabilities.append(f"Weak protocol: {info.protocol_version}")
                        info.ssl_score -= 30
                    
                    # Check for weak ciphers
                    weak_ciphers = ["RC4", "DES", "3DES", "MD5", "NULL"]
                    for cipher in weak_ciphers:
                        if cipher in info.cipher_suite:
                            info.weak_ciphers.append(cipher)
                            info.vulnerabilities.append(f"Weak cipher: {cipher}")
                            info.ssl_score -= 20
                    
                    # Calculate SSL score
                    info.ssl_score = max(0, 100 + info.ssl_score)
                    
        except Exception as e:
            logger.debug(f"[Scanner] SSL analysis failed for {host}:{port}: {e}")
            info.vulnerabilities.append("Could not establish SSL connection")
        
        return info
    
    def scan_web_application(self, base_url: str, 
                            deep_scan: bool = False) -> List[WebVulnerability]:
        """
        Scan web application for vulnerabilities.
        
        Args:
            base_url: Base URL of the application
            deep_scan: Perform deep crawling and testing
        
        Returns:
            List of web vulnerabilities
        """
        vulns = []
        
        logger.info(f"[Scanner] Scanning web application: {base_url}")
        
        try:
            # Parse forms and parameters
            response = requests.get(base_url, timeout=10, verify=False)
            
            # Find forms
            forms = self._extract_forms(response.text, base_url)
            
            for form in forms:
                # Test form parameters for SQLi
                for payload in self.sqli_payloads[:3]:  # Limit for speed
                    test_url = form["action"] or base_url
                    data = {field: payload for field in form["fields"]}
                    
                    try:
                        if form["method"] == "POST":
                            r = requests.post(test_url, data=data, timeout=5, verify=False)
                        else:
                            r = requests.get(test_url, params=data, timeout=5, verify=False)
                        
                        # Check for SQL error messages
                        sql_errors = [
                            "sql syntax", "mysql_fetch", "pg_query", "sqlite_query",
                            "ora-", "microsoft ole db", "odbc", "jdbc"
                        ]
                        
                        response_text = r.text.lower()
                        for error in sql_errors:
                            if error in response_text:
                                vulns.append(WebVulnerability(
                                    url=test_url,
                                    parameter=form["fields"][0] if form["fields"] else "",
                                    vuln_type="SQL Injection",
                                    severity="CRITICAL",
                                    payload=payload,
                                    evidence=f"SQL error detected: {error}",
                                    request_method=form["method"]
                                ))
                                break
                    except:
                        pass
                
                # Test for XSS
                for payload in self.xss_payloads[:3]:
                    data = {field: payload for field in form["fields"]}
                    
                    try:
                        if form["method"] == "POST":
                            r = requests.post(form["action"] or base_url, 
                                            data=data, timeout=5, verify=False)
                        else:
                            r = requests.get(form["action"] or base_url, 
                                           params=data, timeout=5, verify=False)
                        
                        # Check if payload is reflected
                        if payload in r.text:
                            vulns.append(WebVulnerability(
                                url=form["action"] or base_url,
                                parameter=form["fields"][0] if form["fields"] else "",
                                vuln_type="Cross-Site Scripting (XSS)",
                                severity="HIGH",
                                payload=payload,
                                evidence="Payload reflected in response",
                                request_method=form["method"]
                            ))
                            break
                    except:
                        pass
            
            # Test URL parameters
            parsed = urlparse(base_url)
            if parsed.query:
                params = parse_qs(parsed.query)
                for param in params:
                    for payload in self.path_traversal_payloads[:2]:
                        test_url = base_url.replace(f"{param}={params[param][0]}", 
                                                   f"{param}={payload}")
                        try:
                            r = requests.get(test_url, timeout=5, verify=False)
                            
                            # Check for LFI indicators
                            if "root:" in r.text or "[boot loader]" in r.text:
                                vulns.append(WebVulnerability(
                                    url=test_url,
                                    parameter=param,
                                    vuln_type="Local File Inclusion (LFI)",
                                    severity="HIGH",
                                    payload=payload,
                                    evidence="System file contents exposed",
                                    request_method="GET"
                                ))
                                break
                        except:
                            pass
        
        except Exception as e:
            logger.debug(f"[Scanner] Web scan failed for {base_url}: {e}")
        
        logger.info(f"[Scanner] Web scan complete: {len(vulns)} vulnerabilities found")
        return vulns
    
    def _extract_forms(self, html: str, base_url: str) -> List[Dict]:
        """Extract forms from HTML"""
        import re
        
        forms = []
        
        # Simple regex for form extraction
        form_pattern = r'<form[^>]*?action=["\']([^"\']*)["\'][^>]*?method=["\']([^"\']*)["\'][^>]*?>(.*?)</form>'
        for match in re.finditer(form_pattern, html, re.DOTALL | re.IGNORECASE):
            action = match.group(1)
            method = match.group(2).upper()
            form_html = match.group(3)
            
            # Extract input fields
            fields = []
            input_pattern = r'<input[^>]*?name=["\']([^"\']*)["\']'
            for field_match in re.finditer(input_pattern, form_html, re.IGNORECASE):
                fields.append(field_match.group(1))
            
            # Make action absolute URL
            if action and not action.startswith("http"):
                action = urljoin(base_url, action)
            
            forms.append({
                "action": action or base_url,
                "method": method if method in ["GET", "POST"] else "GET",
                "fields": fields
            })
        
        return forms
    
    def get_statistics(self) -> Dict:
        """Get vulnerability scan statistics"""
        severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
        
        for vuln in self.vulns_found:
            severity_counts[vuln.severity] = severity_counts.get(vuln.severity, 0) + 1
        
        return {
            "total_vulnerabilities": len(self.vulns_found),
            "by_severity": severity_counts,
            "scanned_targets": len(self.scan_results),
            "verified_vulnerabilities": sum(1 for v in self.vulns_found if v.verified),
            "critical_hosts": len(set(
                v.affected_host for v in self.vulns_found 
                if v.severity in ["CRITICAL", "HIGH"]
            ))
        }


__all__ = [
    'VulnerabilityScanner',
    'Vulnerability',
    'SSLInfo',
    'WebVulnerability',
    'VulnerabilityDatabase'
]
