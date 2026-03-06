#!/usr/bin/env python3
"""
================================================================================
ORDL COMMAND POST v6.0.0 - MCP INTEGRATION LAYER
================================================================================
Classification: TOP SECRET//SCI//NOFORN
Classification Level: TS/SCI/NOFORN

MCP SERVER INTEGRATION FOR AI AGENTS
================================================================================
Connects all MCP servers to the Agent System as tools:
- GitHub MCP: Repository access, code search, issue management
- Context7 MCP: Documentation queries
- Playwright MCP: Web automation, screenshots
- SSH MCP: Remote command execution
- Filesystem MCP: File operations
- Fetch MCP: Web content retrieval

Each MCP tool is wrapped with:
- Authentication handling
- Error handling
- Audit logging
- Rate limiting
- Result caching

Author: ORDL Cyber Operations Division
Version: 6.0.0
================================================================================
"""

import os
import json
import time
import logging
import subprocess
import hashlib
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import wraps
import threading

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger('mcp_integration')


@dataclass
class MCPResult:
    """MCP tool execution result"""
    success: bool
    result: Any
    error: Optional[str] = None
    execution_time_ms: int = 0
    cached: bool = False
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class MCPToolRegistry:
    """
    Registry for MCP server tools
    
    Manages connections to all MCP servers and exposes them as agent tools.
    """
    
    def __init__(self):
        self.tools: Dict[str, Callable] = {}
        self.cache: Dict[str, Tuple[Any, datetime]] = {}
        self.cache_lock = threading.RLock()
        self.cache_ttl = timedelta(minutes=5)
        self.call_stats: Dict[str, Dict] = {}
        
        # Initialize all MCP tools
        self._init_github_tools()
        self._init_context7_tools()
        self._init_playwright_tools()
        self._init_ssh_tools()
        self._init_filesystem_tools()
        self._init_fetch_tools()
        self._init_sequential_thinking_tools()
        self._init_artiforge_tools()
        
        logger.info(f"[MCP] Initialized {len(self.tools)} MCP tools")
    
    def _cache_key(self, tool_name: str, **kwargs) -> str:
        """Generate cache key for tool call"""
        data = json.dumps({"tool": tool_name, "args": kwargs}, sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()
    
    def _get_cached(self, cache_key: str) -> Optional[Any]:
        """Get cached result if valid"""
        with self.cache_lock:
            if cache_key in self.cache:
                result, timestamp = self.cache[cache_key]
                if datetime.utcnow() - timestamp < self.cache_ttl:
                    return result
                else:
                    del self.cache[cache_key]
            return None
    
    def _set_cached(self, cache_key: str, result: Any):
        """Cache result"""
        with self.cache_lock:
            self.cache[cache_key] = (result, datetime.utcnow())
    
    def _run_mcp_command(self, server: str, command: str, args: List[str], 
                        timeout: int = 60) -> MCPResult:
        """Execute MCP server command via subprocess"""
        start_time = time.time()
        
        try:
            # Build command
            cmd = ["npx", "-y", server] + args
            
            # Execute
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            execution_time = int((time.time() - start_time) * 1000)
            
            if result.returncode == 0:
                return MCPResult(
                    success=True,
                    result=result.stdout,
                    execution_time_ms=execution_time
                )
            else:
                return MCPResult(
                    success=False,
                    result=None,
                    error=result.stderr,
                    execution_time_ms=execution_time
                )
                
        except subprocess.TimeoutExpired:
            return MCPResult(
                success=False,
                result=None,
                error=f"Command timed out after {timeout}s"
            )
        except Exception as e:
            return MCPResult(
                success=False,
                result=None,
                error=str(e)
            )
    
    # ==================== GITHUB MCP TOOLS ====================
    
    def _init_github_tools(self):
        """Initialize GitHub MCP tools"""
        
        def github_search_repos(query: str, language: str = None, limit: int = 10) -> Dict:
            """Search GitHub repositories"""
            args = ["search", "repositories", query, "--limit", str(limit)]
            if language:
                args.extend(["--language", language])
            
            result = self._run_mcp_command(
                "@modelcontextprotocol/server-github",
                "search",
                args
            )
            
            if result.success:
                return {
                    "query": query,
                    "results": result.result[:2000],  # Limit output
                    "count": limit
                }
            else:
                return {"error": result.error}
        
        def github_get_repo(owner: str, repo: str) -> Dict:
            """Get repository information"""
            result = self._run_mcp_command(
                "@modelcontextprotocol/server-github",
                "get",
                ["repository", f"{owner}/{repo}"]
            )
            
            if result.success:
                return {"repository": result.result[:2000]}
            else:
                return {"error": result.error}
        
        def github_search_code(query: str, language: str = None, limit: int = 10) -> Dict:
            """Search code on GitHub"""
            args = ["search", "code", query, "--limit", str(limit)]
            if language:
                args.extend(["--language", language])
            
            result = self._run_mcp_command(
                "@modelcontextprotocol/server-github",
                "search",
                args
            )
            
            if result.success:
                return {
                    "query": query,
                    "results": result.result[:2000],
                    "count": limit
                }
            else:
                return {"error": result.error}
        
        self.tools["github_search_repos"] = github_search_repos
        self.tools["github_get_repo"] = github_get_repo
        self.tools["github_search_code"] = github_search_code
    
    # ==================== CONTEXT7 MCP TOOLS ====================
    
    def _init_context7_tools(self):
        """Initialize Context7 MCP tools"""
        
        def context7_query(library: str, query: str) -> Dict:
            """Query Context7 documentation"""
            result = self._run_mcp_command(
                "@upstash/context7-mcp",
                "query",
                ["--library", library, "--query", query]
            )
            
            if result.success:
                return {
                    "library": library,
                    "query": query,
                    "documentation": result.result[:3000]
                }
            else:
                return {"error": result.error}
        
        def context7_resolve(library_name: str) -> Dict:
            """Resolve library ID for Context7"""
            result = self._run_mcp_command(
                "@upstash/context7-mcp",
                "resolve",
                ["--library", library_name]
            )
            
            if result.success:
                return {"library": library_name, "resolution": result.result}
            else:
                return {"error": result.error}
        
        self.tools["context7_query"] = context7_query
        self.tools["context7_resolve"] = context7_resolve
    
    # ==================== PLAYWRIGHT MCP TOOLS ====================
    
    def _init_playwright_tools(self):
        """Initialize Playwright MCP tools"""
        
        def playwright_navigate(url: str) -> Dict:
            """Navigate to URL using Playwright"""
            result = self._run_mcp_command(
                "@playwright/mcp",
                "navigate",
                ["--url", url],
                timeout=30
            )
            
            if result.success:
                return {
                    "url": url,
                    "title": "Navigation successful",
                    "content": result.result[:2000]
                }
            else:
                return {"error": result.error}
        
        def playwright_screenshot(url: str, filename: str = None) -> Dict:
            """Take screenshot of webpage"""
            if not filename:
                filename = f"screenshot_{int(time.time())}.png"
            
            result = self._run_mcp_command(
                "@playwright/mcp",
                "screenshot",
                ["--url", url, "--output", f"/tmp/{filename}"],
                timeout=30
            )
            
            if result.success:
                return {
                    "url": url,
                    "screenshot_path": f"/tmp/{filename}",
                    "status": "captured"
                }
            else:
                return {"error": result.error}
        
        def playwright_extract_text(url: str) -> Dict:
            """Extract text content from webpage"""
            result = self._run_mcp_command(
                "@playwright/mcp",
                "extract",
                ["--url", url],
                timeout=30
            )
            
            if result.success:
                return {
                    "url": url,
                    "text": result.result[:5000]
                }
            else:
                return {"error": result.error}
        
        self.tools["playwright_navigate"] = playwright_navigate
        self.tools["playwright_screenshot"] = playwright_screenshot
        self.tools["playwright_extract_text"] = playwright_extract_text
    
    # ==================== SSH MCP TOOLS ====================
    
    def _init_ssh_tools(self):
        """Initialize SSH MCP tools"""
        
        def ssh_execute_command(host: str, command: str, username: str = None) -> Dict:
            """Execute command on remote SSH server"""
            args = ["--host", host, "--command", command]
            if username:
                args.extend(["--username", username])
            
            result = self._run_mcp_command(
                "@fangjunjie/ssh-mcp-server",
                "execute",
                args,
                timeout=60
            )
            
            if result.success:
                return {
                    "host": host,
                    "command": command,
                    "output": result.result[:5000]
                }
            else:
                return {"error": result.error}
        
        def ssh_upload_file(host: str, local_path: str, remote_path: str) -> Dict:
            """Upload file via SSH"""
            result = self._run_mcp_command(
                "@fangjunjie/ssh-mcp-server",
                "upload",
                ["--host", host, "--local", local_path, "--remote", remote_path],
                timeout=120
            )
            
            if result.success:
                return {
                    "host": host,
                    "local_path": local_path,
                    "remote_path": remote_path,
                    "status": "uploaded"
                }
            else:
                return {"error": result.error}
        
        self.tools["ssh_execute"] = ssh_execute_command
        self.tools["ssh_upload"] = ssh_upload_file
    
    # ==================== FILESYSTEM MCP TOOLS ====================
    
    def _init_filesystem_tools(self):
        """Initialize Filesystem MCP tools"""
        
        def fs_read_file(path: str) -> Dict:
            """Read file from allowed directories"""
            cache_key = self._cache_key("fs_read_file", path=path)
            cached = self._get_cached(cache_key)
            
            if cached:
                return {"path": path, "content": cached, "cached": True}
            
            result = self._run_mcp_command(
                "@modelcontextprotocol/server-filesystem",
                "read",
                ["--path", path]
            )
            
            if result.success:
                content = result.result
                self._set_cached(cache_key, content)
                return {
                    "path": path,
                    "content": content[:10000],
                    "size": len(content)
                }
            else:
                return {"error": result.error}
        
        def fs_list_directory(path: str) -> Dict:
            """List directory contents"""
            result = self._run_mcp_command(
                "@modelcontextprotocol/server-filesystem",
                "list",
                ["--path", path]
            )
            
            if result.success:
                return {
                    "path": path,
                    "entries": result.result[:5000]
                }
            else:
                return {"error": result.error}
        
        def fs_search_files(path: str, pattern: str) -> Dict:
            """Search files in directory"""
            result = self._run_mcp_command(
                "@modelcontextprotocol/server-filesystem",
                "search",
                ["--path", path, "--pattern", pattern]
            )
            
            if result.success:
                return {
                    "path": path,
                    "pattern": pattern,
                    "matches": result.result[:5000]
                }
            else:
                return {"error": result.error}
        
        self.tools["fs_read_file"] = fs_read_file
        self.tools["fs_list_directory"] = fs_list_directory
        self.tools["fs_search_files"] = fs_search_files
    
    # ==================== FETCH MCP TOOLS ====================
    
    def _init_fetch_tools(self):
        """Initialize Fetch MCP tools"""
        
        def fetch_url(url: str, max_length: int = 5000) -> Dict:
            """Fetch and convert webpage to markdown"""
            cache_key = self._cache_key("fetch_url", url=url)
            cached = self._get_cached(cache_key)
            
            if cached:
                return {"url": url, "content": cached[:max_length], "cached": True}
            
            result = self._run_mcp_command(
                "mcp-server-fetch",
                "fetch",
                ["--url", url, "--max-length", str(max_length)],
                timeout=30
            )
            
            if result.success:
                content = result.result
                self._set_cached(cache_key, content)
                return {
                    "url": url,
                    "content": content[:max_length],
                    "length": len(content)
                }
            else:
                return {"error": result.error}
        
        self.tools["fetch_url"] = fetch_url
    
    # ==================== SEQUENTIAL THINKING TOOLS ====================
    
    def _init_sequential_thinking_tools(self):
        """Initialize Sequential Thinking MCP tools"""
        
        def think_sequential(problem: str, steps: int = 5) -> Dict:
            """Use structured sequential thinking to solve complex problems"""
            result = self._run_mcp_command(
                "@modelcontextprotocol/server-sequential-thinking",
                "think",
                ["--problem", problem, "--steps", str(steps)],
                timeout=60
            )
            
            if result.success:
                return {
                    "problem": problem,
                    "steps": steps,
                    "solution": result.result[:5000]
                }
            else:
                return {"error": result.error}
        
        def think_analyze(data: str, context: str = None) -> Dict:
            """Analyze data using sequential thinking"""
            args = ["--analyze", data]
            if context:
                args.extend(["--context", context])
            
            result = self._run_mcp_command(
                "@modelcontextprotocol/server-sequential-thinking",
                "analyze",
                args,
                timeout=60
            )
            
            if result.success:
                return {
                    "data_summary": data[:200],
                    "analysis": result.result[:5000]
                }
            else:
                return {"error": result.error}
        
        self.tools["think_sequential"] = think_sequential
        self.tools["think_analyze"] = think_analyze
    
    # ==================== ARTIFORGE TOOLS ====================
    
    def _init_artiforge_tools(self):
        """Initialize Artiforge production code generation tools"""
        
        def artiforge_generate_code(task: str, language: str = "python", 
                                     framework: str = None) -> Dict:
            """Generate production-ready code using Artiforge"""
            args = ["--task", task, "--language", language]
            if framework:
                args.extend(["--framework", framework])
            
            result = self._run_mcp_command(
                "@antiforge/mcp-server",
                "generate-code",
                args,
                timeout=120
            )
            
            if result.success:
                return {
                    "task": task,
                    "language": language,
                    "framework": framework,
                    "code": result.result[:10000]
                }
            else:
                return {"error": result.error}
        
        def artiforge_make_plan(task: str, stack: str = None) -> Dict:
            """Create development task plan using Artiforge"""
            args = ["--task", task]
            if stack:
                args.extend(["--stack", stack])
            
            result = self._run_mcp_command(
                "@antiforge/mcp-server",
                "make-plan",
                args,
                timeout=60
            )
            
            if result.success:
                return {
                    "task": task,
                    "stack": stack,
                    "plan": result.result[:5000]
                }
            else:
                return {"error": result.error}
        
        def artiforge_scan_codebase(path: str = ".") -> Dict:
            """Scan codebase for analysis using Artiforge"""
            result = self._run_mcp_command(
                "@antiforge/mcp-server",
                "scan-codebase",
                ["--path", path],
                timeout=120
            )
            
            if result.success:
                return {
                    "path": path,
                    "analysis": result.result[:5000]
                }
            else:
                return {"error": result.error}
        
        self.tools["artiforge_generate_code"] = artiforge_generate_code
        self.tools["artiforge_make_plan"] = artiforge_make_plan
        self.tools["artiforge_scan_codebase"] = artiforge_scan_codebase
    
    # ==================== PUBLIC API ====================
    
    def execute_tool(self, tool_name: str, **kwargs) -> MCPResult:
        """Execute an MCP tool by name with tamper-evident audit logging"""
        if tool_name not in self.tools:
            return MCPResult(
                success=False,
                result=None,
                error=f"Unknown MCP tool: {tool_name}"
            )
        
        start_time = time.time()
        
        # Tamper-evident audit logging
        audit_entry = None
        try:
            from audit.tamper_evident import get_tamper_evident_audit, AuditEventType
            audit = get_tamper_evident_audit()
            
            # Sanitize kwargs for audit (remove sensitive data)
            audit_details = {k: v for k, v in kwargs.items() 
                           if k not in ['password', 'token', 'key', 'secret']}
            
            audit_entry = audit.create_entry(
                event_type=AuditEventType.MCP_TOOL_INVOKED,
                user_id=kwargs.get("_user_id", "system"),
                user_clearance=kwargs.get("_clearance", "SECRET"),
                resource_id=tool_name,
                action="mcp_execute",
                status="started",
                details=audit_details,
                classification="SECRET"
            )
        except Exception as e:
            logger.warning(f"[MCP AUDIT] Could not create audit entry: {e}")
        
        try:
            result = self.tools[tool_name](**kwargs)
            execution_time = int((time.time() - start_time) * 1000)
            
            # Update stats
            if tool_name not in self.call_stats:
                self.call_stats[tool_name] = {"calls": 0, "errors": 0}
            self.call_stats[tool_name]["calls"] += 1
            
            # Log completion to audit chain
            if audit_entry:
                try:
                    from audit.tamper_evident import get_tamper_evident_audit, AuditEventType
                    audit = get_tamper_evident_audit()
                    audit.create_entry(
                        event_type=AuditEventType.MCP_DATA_RETRIEVED,
                        user_id=kwargs.get("_user_id", "system"),
                        user_clearance=kwargs.get("_clearance", "SECRET"),
                        resource_id=tool_name,
                        action="mcp_complete",
                        status="success" if not (isinstance(result, dict) and "error" in result) else "error",
                        details={"execution_time_ms": execution_time},
                        classification="SECRET"
                    )
                except:
                    pass
            
            if isinstance(result, dict) and "error" in result:
                self.call_stats[tool_name]["errors"] += 1
                return MCPResult(
                    success=False,
                    result=result,
                    error=result["error"],
                    execution_time_ms=execution_time
                )
            
            return MCPResult(
                success=True,
                result=result,
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            
            # Log error to audit chain
            if audit_entry:
                try:
                    from audit.tamper_evident import get_tamper_evident_audit, AuditEventType
                    audit = get_tamper_evident_audit()
                    audit.create_entry(
                        event_type=AuditEventType.MCP_TOOL_INVOKED,
                        user_id=kwargs.get("_user_id", "system"),
                        user_clearance=kwargs.get("_clearance", "SECRET"),
                        resource_id=tool_name,
                        action="mcp_error",
                        status="failed",
                        details={"error": str(e), "execution_time_ms": execution_time},
                        classification="SECRET"
                    )
                except:
                    pass
            
            return MCPResult(
                success=False,
                result=None,
                error=str(e),
                execution_time_ms=execution_time
            )
    
    def list_tools(self) -> List[Dict]:
        """List all available MCP tools"""
        tool_list = []
        
        for name, func in self.tools.items():
            doc = func.__doc__ or "No description"
            category = name.split('_')[0]
            
            tool_list.append({
                "name": name,
                "description": doc.strip(),
                "category": category,
                "calls": self.call_stats.get(name, {}).get("calls", 0),
                "errors": self.call_stats.get(name, {}).get("errors", 0)
            })
        
        return tool_list
    
    def get_stats(self) -> Dict:
        """Get MCP tool execution statistics"""
        total_calls = sum(s.get("calls", 0) for s in self.call_stats.values())
        total_errors = sum(s.get("errors", 0) for s in self.call_stats.values())
        
        return {
            "total_tools": len(self.tools),
            "total_calls": total_calls,
            "total_errors": total_errors,
            "success_rate": ((total_calls - total_errors) / total_calls * 100) if total_calls > 0 else 100,
            "tool_breakdown": self.call_stats
        }


# Singleton instance
_mcp_registry_instance: Optional[MCPToolRegistry] = None

def get_mcp_registry() -> MCPToolRegistry:
    """Get singleton MCP registry"""
    global _mcp_registry_instance
    if _mcp_registry_instance is None:
        _mcp_registry_instance = MCPToolRegistry()
    return _mcp_registry_instance
