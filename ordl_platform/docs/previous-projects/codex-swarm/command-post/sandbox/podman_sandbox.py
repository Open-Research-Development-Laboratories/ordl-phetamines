#!/usr/bin/env python3
"""
ORDL Podman Code Sandbox - RHEL 9.6 Compatible
Secure multi-language code execution using Podman containers
Classification: TOP SECRET//NOFORN
"""

import os
import json
import time
import hashlib
import tempfile
import subprocess
import threading
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("podman_sandbox")


class Language(Enum):
    PYTHON = "python"
    C = "c"
    CPP = "cpp"
    JAVA = "java"
    JAVASCRIPT = "javascript"
    RUST = "rust"
    GO = "go"


@dataclass
class SandboxConfig:
    """Sandbox execution configuration"""
    cpu_limit: str = "1.0"
    memory_limit: str = "512m"
    timeout: int = 30
    network_enabled: bool = False
    pids_limit: int = 50
    storage_limit: str = "100m"
    read_only: bool = True


@dataclass
class ExecutionResult:
    """Code execution result"""
    success: bool
    output: str
    error: Optional[str]
    exit_code: int
    execution_time_ms: float
    memory_usage_mb: float
    cpu_time_ms: float


class PodmanSandbox:
    """Military-grade code sandbox using Podman (RHEL 9.6 compatible)"""
    
    CLEARANCE_LIMITS = {
        'UNCLASSIFIED': SandboxConfig(cpu_limit="0.5", memory_limit="256m", timeout=10),
        'CONFIDENTIAL': SandboxConfig(cpu_limit="1.0", memory_limit="512m", timeout=30),
        'SECRET': SandboxConfig(cpu_limit="2.0", memory_limit="1g", timeout=60),
        'TOP SECRET': SandboxConfig(cpu_limit="4.0", memory_limit="2g", timeout=120),
        'TS/SCI': SandboxConfig(cpu_limit="8.0", memory_limit="4g", timeout=300),
        'TS/SCI/NOFORN': SandboxConfig(cpu_limit="16.0", memory_limit="8g", timeout=600),
    }
    
    def __init__(self, images_dir: str = "/opt/codex-swarm/command-post/containers"):
        self.images_dir = images_dir
        self.containers: Dict[str, Any] = {}
        self.lock = threading.RLock()
        self._verify_podman()
    
    def _verify_podman(self):
        """Verify Podman is installed and working"""
        try:
            result = subprocess.run(["podman", "version"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                logger.info("Podman verified and ready")
            else:
                logger.warning("Podman check returned non-zero")
        except FileNotFoundError:
            logger.error("Podman not found! Install podman for RHEL 9.6")
            raise RuntimeError("Podman is required but not installed")
        except Exception as e:
            logger.error(f"Podman verification failed: {e}")
            raise
    
    def _get_image_name(self, language: Language) -> str:
        """Get Podman image for language"""
        images = {
            Language.PYTHON: "ordl-python-sandbox:latest",
            Language.C: "ordl-c-sandbox:latest",
            Language.CPP: "ordl-c-sandbox:latest",
            Language.JAVA: "ordl-java-sandbox:latest",
        }
        return images.get(language, "ordl-python-sandbox:latest")
    
    def execute_python(self, code: str, clearance: str = "CONFIDENTIAL", inputs: Optional[Dict] = None) -> ExecutionResult:
        """Execute Python code in Podman sandbox"""
        config = self.CLEARANCE_LIMITS.get(clearance, self.CLEARANCE_LIMITS['CONFIDENTIAL'])
        code_hash = hashlib.sha256(code.encode()).hexdigest()
        container_name = f"ordl-sandbox-python-{code_hash[:12]}"
        start_time = time.time()
        
        try:
            with tempfile.NamedTemporaryFile(
            mode='w', suffix='.py', delete=False,
            dir='/opt/codex-swarm/command-post/sandbox_temp'
        ) as f:
                wrapped_code = self._wrap_python_code(code, inputs)
                f.write(wrapped_code)
                f.flush()
                temp_file = f.name
            
            # Make file readable by all (container runs as different user)
            os.chmod(temp_file, 0o644)
            
            cmd = [
                "podman", "run", "--rm",
                "--name", container_name,
                "--user", "root",
                #"--cpus", config.cpu_limit,  # Disabled: requires cgroup support
                "--memory", config.memory_limit,
                "--pids-limit", str(config.pids_limit),
                "--network", "none" if not config.network_enabled else "slirp4netns",
                "--security-opt", "no-new-privileges:true",
                "--cap-drop", "ALL",
                "--read-only",
                "-v", f"{temp_file}:/sandbox/script.py:Z",
                self._get_image_name(Language.PYTHON),
                "/sandbox/script.py"
            ]
            
            logger.info(f"Executing Python sandbox: {container_name}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=config.timeout)
            execution_time = (time.time() - start_time) * 1000
            
            return ExecutionResult(
                success=result.returncode == 0,
                output=result.stdout,
                error=result.stderr if result.stderr else None,
                exit_code=result.returncode,
                execution_time_ms=execution_time,
                memory_usage_mb=0.0,
                cpu_time_ms=0.0
            )
        except subprocess.TimeoutExpired:
            self._kill_container(container_name)
            return ExecutionResult(success=False, output="", error=f"Timeout after {config.timeout}s", exit_code=-1, execution_time_ms=config.timeout*1000, memory_usage_mb=0.0, cpu_time_ms=0.0)
        except Exception as e:
            return ExecutionResult(success=False, output="", error=str(e), exit_code=-1, execution_time_ms=(time.time()-start_time)*1000, memory_usage_mb=0.0, cpu_time_ms=0.0)
        finally:
            try:
                os.unlink(temp_file)
                self._cleanup_container(container_name)
            except:
                pass
    
    def _wrap_python_code(self, code: str, inputs: Optional[Dict]) -> str:
        """Wrap Python code with safety measures"""
        return f'''#!/usr/bin/env python3
import sys
import json
import resource
resource.setrlimit(resource.RLIMIT_CPU, (30, 30))
resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
__ordl_inputs__ = {json.dumps(inputs or {})}
{code}
'''
    
    def _kill_container(self, container_name: str):
        try:
            subprocess.run(["podman", "kill", container_name], capture_output=True, timeout=5)
        except:
            pass
    
    def _cleanup_container(self, container_name: str):
        try:
            subprocess.run(["podman", "rm", "-f", container_name], capture_output=True, timeout=5)
        except:
            pass

_sandbox = None
def get_sandbox() -> PodmanSandbox:
    global _sandbox
    if _sandbox is None:
        _sandbox = PodmanSandbox()
    return _sandbox
