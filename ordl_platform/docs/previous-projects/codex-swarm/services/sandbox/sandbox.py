#!/usr/bin/env python3
"""
ORDL Command Post - Docker-based Code Sandbox System
=====================================================

A comprehensive, security-hardened code execution environment supporting
multiple programming languages with full container isolation.

Supported Languages:
    - Python 3.11
    - C23 (GCC 13)
    - Java 21 (OpenJDK)
    - JavaScript/Node.js 20
    - Rust 1.75
    - Go 1.21

Security Features:
    - Non-root container execution
    - Seccomp syscall filtering
    - Resource limits (CPU, memory, PIDs, timeouts)
    - Network isolation per clearance level
    - Read-only filesystems (except /tmp)
    - No new privileges
    - Capability dropping

Clearance Levels:
    - UNCLASSIFIED: Network isolated, restricted execution
    - CONFIDENTIAL: Limited network access (DNS, HTTP/HTTPS only)
    - SECRET: Standard network access
    - TOP_SECRET: Extended network access
    - TS_SCI: Full network capabilities
    - TS_SCI_NOFORN: Reserved for future use

Author: ORDL Engineering Team
Version: 1.0.0
Classification: TOP SECRET//NOFORN//SCI
"""

import os
import sys
import json
import time
import uuid
import logging
import tempfile
import shutil
from enum import Enum
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Union, Callable, Any
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

# Docker SDK
import docker
from docker.errors import (
    DockerException,
    ContainerError,
    ImageNotFound,
    APIError,
    NotFound
)

# System monitoring
import psutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('ordl.sandbox')


class ClearanceLevel(Enum):
    """Security clearance levels for sandbox execution."""
    UNCLASSIFIED = "unclassified"
    CONFIDENTIAL = "confidential"
    SECRET = "secret"
    TOP_SECRET = "top_secret"
    TS_SCI = "ts_sci"
    TS_SCI_NOFORN = "ts_sci_noforn"


class Language(Enum):
    """Supported programming languages."""
    PYTHON = "python"
    C23 = "c23"
    JAVA = "java"
    JAVASCRIPT = "javascript"
    RUST = "rust"
    GO = "go"


class SandboxError(Exception):
    """Base exception for sandbox errors."""
    pass


class SandboxTimeoutError(SandboxError):
    """Raised when code execution exceeds timeout."""
    pass


class SandboxSecurityError(SandboxError):
    """Raised when a security violation is detected."""
    pass


class SandboxResourceError(SandboxError):
    """Raised when resource limits are exceeded."""
    pass


@dataclass
class ResourceLimits:
    """Resource limits for sandbox execution."""
    cpu_quota: int = 100000  # CPU quota in microseconds (1 CPU = 100000)
    cpu_period: int = 100000  # CPU period in microseconds
    mem_limit: str = "512m"  # Memory limit (e.g., "512m", "1g")
    mem_swap_limit: str = "512m"  # Swap limit (should equal mem_limit to prevent swap usage)
    pids_limit: int = 64  # Maximum number of PIDs
    timeout: int = 30  # Execution timeout in seconds (default: 30, max: 300)
    max_file_size: int = 10 * 1024 * 1024  # Maximum output file size (10MB)
    max_output_size: int = 1024 * 1024  # Maximum stdout/stderr size (1MB)
    
    def to_docker_resources(self) -> Dict[str, Any]:
        """Convert to Docker resources format."""
        return {
            'cpu_quota': self.cpu_quota,
            'cpu_period': self.cpu_period,
            'mem_limit': self.mem_limit,
            'memswap_limit': self.mem_swap_limit,
            'pids_limit': self.pids_limit,
        }


@dataclass
class SecurityOptions:
    """Security options for sandbox execution."""
    # Container capabilities to drop (ALL drops all capabilities)
    cap_drop: List[str] = field(default_factory=lambda: ['ALL'])
    
    # Container capabilities to add back (minimal required set)
    cap_add: List[str] = field(default_factory=lambda: ['KILL', 'NET_BIND_SERVICE'])
    
    # Prevent privilege escalation
    no_new_privileges: bool = True
    
    # Read-only root filesystem
    read_only: bool = True
    
    # Seccomp profile path
    seccomp_profile: Optional[str] = None
    
    # AppArmor profile
    apparmor_profile: str = "docker-default"
    
    # Security opt list for Docker
    security_opt: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.security_opt:
            self.security_opt = [
                f"no-new-privileges:{str(self.no_new_privileges).lower()}",
                f"apparmor:{self.apparmor_profile}",
            ]
            if self.seccomp_profile and os.path.exists(self.seccomp_profile):
                self.security_opt.append(f"seccomp={self.seccomp_profile}")


@dataclass
class SandboxConfig:
    """Complete sandbox configuration."""
    language: Language
    clearance_level: ClearanceLevel = ClearanceLevel.UNCLASSIFIED
    resource_limits: ResourceLimits = field(default_factory=ResourceLimits)
    security_options: SecurityOptions = field(default_factory=SecurityOptions)
    network_isolated: bool = True
    allow_file_uploads: bool = True
    env_vars: Dict[str, str] = field(default_factory=dict)
    
    # Docker image configuration
    image_tag: Optional[str] = None
    image_registry: str = "ordl-sandbox"


@dataclass
class ExecutionResult:
    """Result of sandbox code execution."""
    success: bool
    exit_code: int
    stdout: str
    stderr: str
    execution_time: float  # seconds
    memory_usage: int  # bytes
    cpu_usage: float  # percentage
    container_id: Optional[str] = None
    error_message: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    request_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert result to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


class SandboxOrchestrator:
    """
    Main orchestrator for Docker-based code sandbox execution.
    
    Manages container lifecycle, resource limits, security options,
    and execution of code in isolated environments.
    """
    
    # Language to Docker image mapping
    DEFAULT_IMAGES = {
        Language.PYTHON: "ordl-sandbox-python:3.11",
        Language.C23: "ordl-sandbox-c23:gcc-13",
        Language.JAVA: "ordl-sandbox-java:21",
        Language.JAVASCRIPT: "ordl-sandbox-javascript:20",
        Language.RUST: "ordl-sandbox-rust:1.75",
        Language.GO: "ordl-sandbox-go:1.21",
    }
    
    # File extensions for each language
    FILE_EXTENSIONS = {
        Language.PYTHON: ".py",
        Language.C23: ".c",
        Language.JAVA: ".java",
        Language.JAVASCRIPT: ".js",
        Language.RUST: ".rs",
        Language.GO: ".go",
    }
    
    # Default class names for languages that need them
    DEFAULT_CLASS_NAMES = {
        Language.JAVA: "Main",
    }
    
    # Network configuration per clearance level
    NETWORK_CONFIG = {
        ClearanceLevel.UNCLASSIFIED: {
            'network_mode': 'none',
            'dns': [],
            'extra_hosts': {},
        },
        ClearanceLevel.CONFIDENTIAL: {
            'network_mode': 'bridge',
            'dns': ['8.8.8.8', '8.8.4.4'],
            'extra_hosts': {},
        },
        ClearanceLevel.SECRET: {
            'network_mode': 'bridge',
            'dns': ['8.8.8.8', '8.8.4.4'],
            'extra_hosts': {},
        },
        ClearanceLevel.TOP_SECRET: {
            'network_mode': 'bridge',
            'dns': ['8.8.8.8', '8.8.4.4'],
            'extra_hosts': {},
        },
        ClearanceLevel.TS_SCI: {
            'network_mode': 'bridge',
            'dns': ['8.8.8.8', '8.8.4.4'],
            'extra_hosts': {},
        },
        ClearanceLevel.TS_SCI_NOFORN: {
            'network_mode': 'none',
            'dns': [],
            'extra_hosts': {},
        },
    }
    
    def __init__(self, 
                 docker_url: Optional[str] = None,
                 seccomp_profile_path: Optional[str] = None,
                 cleanup_on_exit: bool = True):
        """
        Initialize the sandbox orchestrator.
        
        Args:
            docker_url: Docker daemon URL (default: env DOCKER_HOST or unix socket)
            seccomp_profile_path: Path to custom seccomp profile
            cleanup_on_exit: Whether to cleanup containers on exit
        """
        self.docker_url = docker_url or os.environ.get('DOCKER_HOST', 'unix://var/run/docker.sock')
        self.seccomp_profile_path = seccomp_profile_path or self._find_seccomp_profile()
        self.cleanup_on_exit = cleanup_on_exit
        self._client: Optional[docker.DockerClient] = None
        self._active_containers: set = set()
        self._executor = ThreadPoolExecutor(max_workers=10)
        
        # Initialize Docker client
        self._connect()
        
        # Register cleanup handler
        if cleanup_on_exit:
            import atexit
            atexit.register(self.cleanup_all)
    
    def _connect(self) -> None:
        """Establish connection to Docker daemon."""
        try:
            self._client = docker.DockerClient(base_url=self.docker_url)
            version_info = self._client.version()
            logger.info(f"Connected to Docker daemon - API: {version_info['ApiVersion']}, "
                       f"Version: {version_info['Version']}")
        except DockerException as e:
            logger.error(f"Failed to connect to Docker daemon: {e}")
            raise SandboxError(f"Docker connection failed: {e}")
    
    def _find_seccomp_profile(self) -> Optional[str]:
        """Find the seccomp profile in standard locations."""
        possible_paths = [
            os.path.join(os.path.dirname(__file__), 'seccomp-profile.json'),
            '/etc/ordl/sandbox/seccomp-profile.json',
            '/opt/codex-swarm/services/sandbox/seccomp-profile.json',
        ]
        for path in possible_paths:
            if os.path.exists(path):
                logger.info(f"Using seccomp profile: {path}")
                return path
        logger.warning("No seccomp profile found, using Docker default")
        return None
    
    def _get_image_name(self, config: SandboxConfig) -> str:
        """Get Docker image name for the configured language."""
        if config.image_tag:
            return f"{config.image_registry}/{config.image_tag}"
        return self.DEFAULT_IMAGES.get(config.language, f"ordl-sandbox-{config.language.value}:latest")
    
    def _ensure_image(self, image_name: str) -> bool:
        """Ensure the Docker image exists, pull if needed."""
        try:
            self._client.images.get(image_name)
            return True
        except ImageNotFound:
            logger.info(f"Image {image_name} not found locally, attempting to pull...")
            try:
                self._client.images.pull(image_name)
                return True
            except Exception as e:
                logger.error(f"Failed to pull image {image_name}: {e}")
                return False
    
    def _create_temp_directory(self, request_id: str) -> str:
        """Create a temporary directory for the sandbox execution."""
        base_dir = tempfile.gettempdir()
        sandbox_dir = os.path.join(base_dir, f"ordl-sandbox-{request_id}")
        os.makedirs(sandbox_dir, mode=0o755, exist_ok=True)
        return sandbox_dir
    
    def _cleanup_temp_directory(self, path: str) -> None:
        """Clean up a temporary directory."""
        try:
            if os.path.exists(path):
                shutil.rmtree(path)
                logger.debug(f"Cleaned up temp directory: {path}")
        except Exception as e:
            logger.warning(f"Failed to cleanup temp directory {path}: {e}")
    
    def _truncate_output(self, data: str, max_size: int = 1024 * 1024) -> str:
        """Truncate output to prevent memory issues."""
        if len(data) > max_size:
            truncation_msg = f"\n... [OUTPUT TRUNCATED - exceeded {max_size} bytes] ..."
            return data[:max_size - len(truncation_msg)] + truncation_msg
        return data
    
    def _build_container_config(self, 
                                config: SandboxConfig,
                                temp_dir: str,
                                command: List[str]) -> Dict[str, Any]:
        """Build Docker container configuration."""
        image_name = self._get_image_name(config)
        network_config = self.NETWORK_CONFIG.get(config.clearance_level, self.NETWORK_CONFIG[ClearanceLevel.UNCLASSIFIED])
        
        # Base configuration
        container_config = {
            'image': image_name,
            'command': command,
            'detach': True,
            'stdout': True,
            'stderr': True,
            'tty': False,
            'stdin_open': False,
            'network_mode': network_config['network_mode'] if config.network_isolated else 'bridge',
            'working_dir': '/tmp',
            'environment': {
                'ORDL_SANDBOX': '1',
                'ORDL_CLEARANCE': config.clearance_level.value,
                'ORDL_REQUEST_ID': config.resource_limits.timeout,
                **config.env_vars
            },
            'volumes': {
                temp_dir: {
                    'bind': '/tmp',
                    'mode': 'rw'
                }
            },
            # Security options
            'cap_drop': config.security_options.cap_drop,
            'security_opt': config.security_options.security_opt,
            'read_only': config.security_options.read_only,
        }
        
        # Add capabilities if specified
        if config.security_options.cap_add:
            container_config['cap_add'] = config.security_options.cap_add
        
        # Add resource limits
        resources = config.resource_limits.to_docker_resources()
        container_config.update(resources)
        
        # Add DNS configuration for non-isolated networks
        if network_config['dns'] and not config.network_isolated:
            container_config['dns'] = network_config['dns']
        
        return container_config
    
    def _execute_python(self, 
                       source_code: str, 
                       config: SandboxConfig,
                       temp_dir: str,
                       request_id: str) -> ExecutionResult:
        """Execute Python code in sandbox."""
        # Write source to file
        source_file = os.path.join(temp_dir, f"script_{request_id}.py")
        with open(source_file, 'w') as f:
            f.write(source_code)
        
        # Build command
        command = ['python', f'/tmp/script_{request_id}.py']
        
        return self._run_container(config, temp_dir, command, source_file)
    
    def _execute_c23(self, 
                     source_code: str, 
                     config: SandboxConfig,
                     temp_dir: str,
                     request_id: str,
                     compiler_flags: Optional[str] = None) -> ExecutionResult:
        """Execute C23 code in sandbox."""
        # Write source to file
        source_file = os.path.join(temp_dir, f"program_{request_id}.c")
        with open(source_file, 'w') as f:
            f.write(source_code)
        
        # Build command using the compile_and_run script
        flags = compiler_flags or "-std=c23 -O2 -Wall -Wextra"
        command = [
            '/usr/local/bin/compile_and_run.sh',
            f'/tmp/program_{request_id}.c',
            f'program_{request_id}',
            flags,
            str(config.resource_limits.timeout)
        ]
        
        return self._run_container(config, temp_dir, command, source_file)
    
    def _execute_java(self, 
                     source_code: str, 
                     config: SandboxConfig,
                     temp_dir: str,
                     request_id: str,
                     class_name: str = "Main") -> ExecutionResult:
        """Execute Java code in sandbox."""
        # Write source to file
        source_file = os.path.join(temp_dir, f"{class_name}.java")
        with open(source_file, 'w') as f:
            f.write(source_code)
        
        # Build command using the compile_and_run script
        command = [
            '/usr/local/bin/compile_and_run.sh',
            f'/tmp/{class_name}.java',
            class_name,
            str(config.resource_limits.timeout)
        ]
        
        return self._run_container(config, temp_dir, command, source_file)
    
    def _execute_javascript(self, 
                           source_code: str, 
                           config: SandboxConfig,
                           temp_dir: str,
                           request_id: str) -> ExecutionResult:
        """Execute JavaScript code in sandbox."""
        # Write source to file
        source_file = os.path.join(temp_dir, f"script_{request_id}.js")
        with open(source_file, 'w') as f:
            f.write(source_code)
        
        # Build command
        command = [
            '/usr/local/bin/run_node.sh',
            f'/tmp/script_{request_id}.js',
            str(config.resource_limits.timeout)
        ]
        
        return self._run_container(config, temp_dir, command, source_file)
    
    def _execute_rust(self, 
                     source_code: str, 
                     config: SandboxConfig,
                     temp_dir: str,
                     request_id: str,
                     build_mode: str = "release") -> ExecutionResult:
        """Execute Rust code in sandbox."""
        # Write source to file
        source_file = os.path.join(temp_dir, f"main_{request_id}.rs")
        with open(source_file, 'w') as f:
            f.write(source_code)
        
        # Build command using the compile_and_run script
        command = [
            '/usr/local/bin/compile_and_run.sh',
            f'/tmp/main_{request_id}.rs',
            str(config.resource_limits.timeout),
            build_mode
        ]
        
        return self._run_container(config, temp_dir, command, source_file)
    
    def _execute_go(self, 
                   source_code: str, 
                   config: SandboxConfig,
                   temp_dir: str,
                   request_id: str) -> ExecutionResult:
        """Execute Go code in sandbox."""
        # Write source to file
        source_file = os.path.join(temp_dir, f"main_{request_id}.go")
        with open(source_file, 'w') as f:
            f.write(source_code)
        
        # Build command using the compile_and_run script
        command = [
            '/usr/local/bin/compile_and_run.sh',
            f'/tmp/main_{request_id}.go',
            f'program_{request_id}',
            str(config.resource_limits.timeout)
        ]
        
        return self._run_container(config, temp_dir, command, source_file)
    
    def _run_container(self,
                      config: SandboxConfig,
                      temp_dir: str,
                      command: List[str],
                      source_file: str) -> ExecutionResult:
        """Run a Docker container with the given configuration."""
        container = None
        container_id = None
        start_time = time.time()
        
        try:
            # Ensure image exists
            image_name = self._get_image_name(config)
            if not self._ensure_image(image_name):
                raise SandboxError(f"Required image not available: {image_name}")
            
            # Build container configuration
            container_config = self._build_container_config(config, temp_dir, command)
            
            # Create and start container
            logger.info(f"Creating container with image: {image_name}")
            container = self._client.containers.create(**container_config)
            container_id = container.id[:12]
            self._active_containers.add(container_id)
            
            logger.info(f"Starting container {container_id}")
            container.start()
            
            # Wait for container with timeout
            timeout = config.resource_limits.timeout
            logger.info(f"Waiting for container {container_id} (timeout: {timeout}s)")
            
            try:
                result = container.wait(timeout=timeout)
                exit_code = result.get('StatusCode', -1)
                error_msg = result.get('Error', None)
            except FutureTimeoutError:
                logger.warning(f"Container {container_id} timed out after {timeout}s")
                self._kill_container(container)
                raise SandboxTimeoutError(f"Execution timed out after {timeout} seconds")
            
            # Get logs
            stdout_data = container.logs(stdout=True, stderr=False).decode('utf-8', errors='replace')
            stderr_data = container.logs(stdout=False, stderr=True).decode('utf-8', errors='replace')
            
            # Truncate if necessary
            stdout_data = self._truncate_output(stdout_data, config.resource_limits.max_output_size)
            stderr_data = self._truncate_output(stderr_data, config.resource_limits.max_output_size)
            
            # Get container stats
            memory_usage = 0
            cpu_usage = 0.0
            try:
                stats = container.stats(stream=False)
                memory_stats = stats.get('memory_stats', {})
                memory_usage = memory_stats.get('usage', 0)
                
                cpu_stats = stats.get('cpu_stats', {})
                cpu_usage_data = cpu_stats.get('cpu_usage', {})
                total_usage = cpu_usage_data.get('total_usage', 0)
                system_cpu_usage = cpu_stats.get('system_cpu_usage', 1)
                if system_cpu_usage > 0:
                    cpu_usage = (total_usage / system_cpu_usage) * 100
            except Exception as e:
                logger.warning(f"Failed to get container stats: {e}")
            
            execution_time = time.time() - start_time
            
            success = exit_code == 0 and error_msg is None
            
            return ExecutionResult(
                success=success,
                exit_code=exit_code,
                stdout=stdout_data,
                stderr=stderr_data,
                execution_time=execution_time,
                memory_usage=memory_usage,
                cpu_usage=cpu_usage,
                container_id=container_id,
                error_message=error_msg
            )
            
        except SandboxTimeoutError:
            raise
        except ContainerError as e:
            execution_time = time.time() - start_time
            return ExecutionResult(
                success=False,
                exit_code=e.exit_status,
                stdout='',
                stderr=str(e),
                execution_time=execution_time,
                memory_usage=0,
                cpu_usage=0.0,
                container_id=container_id,
                error_message=str(e)
            )
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Container execution error: {e}")
            return ExecutionResult(
                success=False,
                exit_code=-1,
                stdout='',
                stderr=str(e),
                execution_time=execution_time,
                memory_usage=0,
                cpu_usage=0.0,
                container_id=container_id,
                error_message=str(e)
            )
        finally:
            # Cleanup container
            if container:
                self._remove_container(container)
                if container_id:
                    self._active_containers.discard(container_id)
    
    def _kill_container(self, container) -> None:
        """Force kill a container."""
        try:
            container.kill(signal='SIGKILL')
            logger.info(f"Killed container {container.id[:12]}")
        except Exception as e:
            logger.warning(f"Failed to kill container: {e}")
    
    def _remove_container(self, container) -> None:
        """Remove a container and its volumes."""
        try:
            container.remove(force=True, v=True)
            logger.debug(f"Removed container {container.id[:12]}")
        except NotFound:
            pass  # Already removed
        except Exception as e:
            logger.warning(f"Failed to remove container: {e}")
    
    def execute(self,
                source_code: str,
                language: Union[str, Language],
                clearance_level: Union[str, ClearanceLevel] = ClearanceLevel.UNCLASSIFIED,
                timeout: Optional[int] = None,
                memory_limit: Optional[str] = None,
                network_isolated: bool = True,
                file_uploads: Optional[Dict[str, bytes]] = None,
                **kwargs) -> ExecutionResult:
        """
        Execute source code in a sandboxed Docker container.
        
        Args:
            source_code: The source code to execute
            language: Programming language (python, c23, java, javascript, rust, go)
            clearance_level: Security clearance level
            timeout: Execution timeout in seconds (default: 30, max: 300)
            memory_limit: Memory limit (e.g., "512m", "1g")
            network_isolated: Whether to disable network access
            file_uploads: Dictionary of filename -> bytes for additional files
            **kwargs: Language-specific options
                
        Returns:
            ExecutionResult with execution details
            
        Raises:
            SandboxError: For configuration errors
            SandboxTimeoutError: If execution times out
        """
        # Parse language
        if isinstance(language, str):
            try:
                language = Language(language.lower())
            except ValueError:
                raise SandboxError(f"Unsupported language: {language}")
        
        # Parse clearance level
        if isinstance(clearance_level, str):
            try:
                clearance_level = ClearanceLevel(clearance_level.lower())
            except ValueError:
                clearance_level = ClearanceLevel.UNCLASSIFIED
        
        # Generate request ID
        request_id = str(uuid.uuid4())[:8]
        
        # Build configuration
        resource_limits = ResourceLimits()
        if timeout is not None:
            resource_limits.timeout = min(max(1, timeout), 300)  # Clamp between 1-300
        if memory_limit:
            resource_limits.mem_limit = memory_limit
            resource_limits.mem_swap_limit = memory_limit
        
        security_options = SecurityOptions()
        if self.seccomp_profile_path:
            security_options.seccomp_profile = self.seccomp_profile_path
            security_options.__post_init__()  # Rebuild security_opt list
        
        config = SandboxConfig(
            language=language,
            clearance_level=clearance_level,
            resource_limits=resource_limits,
            security_options=security_options,
            network_isolated=network_isolated,
        )
        
        # Create temp directory
        temp_dir = self._create_temp_directory(request_id)
        
        try:
            # Write file uploads if provided
            if file_uploads:
                for filename, content in file_uploads.items():
                    # Security: Validate filename (prevent directory traversal)
                    safe_filename = os.path.basename(filename)
                    if safe_filename != filename:
                        raise SandboxSecurityError(f"Invalid filename: {filename}")
                    
                    filepath = os.path.join(temp_dir, safe_filename)
                    with open(filepath, 'wb') as f:
                        f.write(content)
                    logger.debug(f"Wrote uploaded file: {safe_filename}")
            
            # Dispatch to language-specific handler
            handlers: Dict[Language, Callable] = {
                Language.PYTHON: self._execute_python,
                Language.C23: lambda *args: self._execute_c23(*args, compiler_flags=kwargs.get('compiler_flags')),
                Language.JAVA: lambda *args: self._execute_java(*args, class_name=kwargs.get('class_name', 'Main')),
                Language.JAVASCRIPT: self._execute_javascript,
                Language.RUST: lambda *args: self._execute_rust(*args, build_mode=kwargs.get('build_mode', 'release')),
                Language.GO: self._execute_go,
            }
            
            handler = handlers.get(language)
            if not handler:
                raise SandboxError(f"No handler for language: {language}")
            
            logger.info(f"Executing {language.value} code (request: {request_id}, "
                       f"clearance: {clearance_level.value}, timeout: {resource_limits.timeout}s)")
            
            return handler(source_code, config, temp_dir, request_id)
            
        except SandboxTimeoutError as e:
            return ExecutionResult(
                success=False,
                exit_code=-1,
                stdout='',
                stderr=f"Timeout: {e}",
                execution_time=resource_limits.timeout,
                memory_usage=0,
                cpu_usage=0.0,
                error_message=str(e),
                request_id=request_id
            )
        except Exception as e:
            logger.exception("Sandbox execution failed")
            return ExecutionResult(
                success=False,
                exit_code=-1,
                stdout='',
                stderr=str(e),
                execution_time=0.0,
                memory_usage=0,
                cpu_usage=0.0,
                error_message=str(e),
                request_id=request_id
            )
        finally:
            # Cleanup temp directory
            self._cleanup_temp_directory(temp_dir)
    
    def get_container_stats(self) -> Dict[str, Any]:
        """Get statistics about active containers."""
        return {
            'active_containers': len(self._active_containers),
            'container_ids': list(self._active_containers),
            'docker_info': self._client.info() if self._client else None,
        }
    
    def cleanup_all(self) -> None:
        """Clean up all active containers and resources."""
        logger.info(f"Cleaning up {len(self._active_containers)} active containers")
        
        for container_id in list(self._active_containers):
            try:
                container = self._client.containers.get(container_id)
                self._kill_container(container)
                self._remove_container(container)
            except NotFound:
                pass
            except Exception as e:
                logger.warning(f"Failed to cleanup container {container_id}: {e}")
            finally:
                self._active_containers.discard(container_id)
        
        # Clean up any temp directories
        temp_base = tempfile.gettempdir()
        for item in os.listdir(temp_base):
            if item.startswith('ordl-sandbox-'):
                try:
                    full_path = os.path.join(temp_base, item)
                    if os.path.isdir(full_path):
                        shutil.rmtree(full_path)
                        logger.debug(f"Cleaned up temp directory: {full_path}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup temp directory {item}: {e}")
    
    def health_check(self) -> Dict[str, Any]:
        """Perform a health check on the sandbox system."""
        health = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'docker_connected': False,
            'images_available': {},
            'errors': []
        }
        
        try:
            # Check Docker connection
            if self._client:
                version = self._client.version()
                health['docker_connected'] = True
                health['docker_version'] = version.get('Version', 'unknown')
                health['api_version'] = version.get('ApiVersion', 'unknown')
            else:
                health['status'] = 'unhealthy'
                health['errors'].append('Docker client not initialized')
                return health
            
            # Check available images
            for lang, image_name in self.DEFAULT_IMAGES.items():
                try:
                    self._client.images.get(image_name)
                    health['images_available'][lang.value] = True
                except ImageNotFound:
                    health['images_available'][lang.value] = False
                    health['errors'].append(f"Image not found: {image_name}")
            
            # Overall status
            if not all(health['images_available'].values()):
                health['status'] = 'degraded'
            
        except Exception as e:
            health['status'] = 'unhealthy'
            health['errors'].append(str(e))
        
        return health
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self.cleanup_on_exit:
            self.cleanup_all()
        return False


# Singleton instance for global access
_default_orchestrator: Optional[SandboxOrchestrator] = None


def get_sandbox() -> SandboxOrchestrator:
    """Get the default sandbox orchestrator instance."""
    global _default_orchestrator
    if _default_orchestrator is None:
        _default_orchestrator = SandboxOrchestrator()
    return _default_orchestrator


def execute_code(source_code: str,
                 language: str,
                 timeout: int = 30,
                 **kwargs) -> ExecutionResult:
    """
    Convenience function for quick code execution.
    
    Args:
        source_code: Source code to execute
        language: Programming language
        timeout: Timeout in seconds
        **kwargs: Additional options
        
    Returns:
        ExecutionResult
    """
    sandbox = get_sandbox()
    return sandbox.execute(
        source_code=source_code,
        language=language,
        timeout=timeout,
        **kwargs
    )


# Example usage and testing
if __name__ == '__main__':
    # Configure logging for testing
    logging.basicConfig(level=logging.DEBUG)
    
    print("ORDL Command Post - Code Sandbox System")
    print("=" * 50)
    
    with SandboxOrchestrator() as sandbox:
        # Health check
        health = sandbox.health_check()
        print(f"\nHealth Check: {health['status']}")
        print(f"Docker Version: {health.get('docker_version', 'N/A')}")
        print(f"Images Available: {health['images_available']}")
        
        if health['status'] == 'unhealthy':
            print("Sandbox system is unhealthy, exiting tests")
            sys.exit(1)
        
        # Test Python execution
        print("\n--- Testing Python Execution ---")
        python_code = '''
import sys
print("Hello from Python sandbox!")
print(f"Python version: {sys.version}")
print(f"Platform: {sys.platform}")

# Test basic computation
data = [i**2 for i in range(10)]
print(f"Squares: {data}")
print(f"Sum: {sum(data)}")
'''
        result = sandbox.execute(python_code, Language.PYTHON, timeout=10)
        print(f"Success: {result.success}")
        print(f"Exit Code: {result.exit_code}")
        print(f"Execution Time: {result.execution_time:.2f}s")
        print(f"Memory Usage: {result.memory_usage} bytes")
        print(f"Output:\n{result.stdout}")
        if result.stderr:
            print(f"Stderr: {result.stderr}")
        
        # Test timeout handling
        print("\n--- Testing Timeout Handling ---")
        infinite_loop = '''
import time
print("Starting infinite loop...")
while True:
    time.sleep(1)
'''
        result = sandbox.execute(infinite_loop, Language.PYTHON, timeout=3)
        print(f"Success: {result.success}")
        print(f"Exit Code: {result.exit_code}")
        print(f"Error: {result.error_message}")
        
        # Test C23 execution
        print("\n--- Testing C23 Execution ---")
        c_code = '''
#include <stdio.h>
#include <stdlib.h>

int main() {
    printf("Hello from C23 sandbox!\\n");
    
    // Test basic computation
    int sum = 0;
    for (int i = 0; i < 10; i++) {
        sum += i * i;
    }
    printf("Sum of squares: %d\\n", sum);
    
    return 0;
}
'''
        result = sandbox.execute(c_code, Language.C23, timeout=30)
        print(f"Success: {result.success}")
        print(f"Exit Code: {result.exit_code}")
        print(f"Execution Time: {result.execution_time:.2f}s")
        print(f"Output:\n{result.stdout}")
        if result.stderr:
            print(f"Stderr: {result.stderr}")
    
    print("\n" + "=" * 50)
    print("Sandbox tests completed")
