#!/usr/bin/env python3
"""
================================================================================
ORDL COMMAND POST v6.0.0 - MCP INTEGRATION LAYER v2
================================================================================
Classification: TOP SECRET//SCI//NOFORN

MCP SERVER INTEGRATION FOR AI AGENTS - PROPER JSON-RPC IMPLEMENTATION
================================================================================
"""

import os
import json
import time
import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import threading
import hashlib

from .client import get_mcp_pool

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
    Registry for MCP server tools using proper JSON-RPC protocol
    """
    
    def __init__(self):
        self.tools: Dict[str, Dict] = {}
        self.cache: Dict[str, tuple] = {}
        self.cache_lock = threading.RLock()
        self.cache_ttl = timedelta(minutes=5)
        self.call_stats: Dict[str, Dict] = {}
        self.pool = get_mcp_pool()
        
        # Initialize all MCP tools
        self._init_all_tools()
        
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
    
    def _init_all_tools(self):
        """Initialize all MCP tool definitions"""
        # GitHub tools
        self._add_tool_def("github_search_repos", "github", "@modelcontextprotocol/server-github@latest",
                          "Search GitHub repositories", {"query": str, "limit": 10})
        self._add_tool_def("github_get_repo", "github", "@modelcontextprotocol/server-github@latest",
                          "Get repository information", {"owner": str, "repo": str})
        self._add_tool_def("github_search_code", "github", "@modelcontextprotocol/server-github@latest",
                          "Search code on GitHub", {"query": str, "limit": 10})
        
        # Context7 tools
        self._add_tool_def("context7_query", "context7", "@upstash/context7-mcp@latest",
                          "Query Context7 documentation", {"library": str, "query": str})
        self._add_tool_def("context7_resolve", "context7", "@upstash/context7-mcp@latest",
                          "Resolve library ID for Context7", {"library_name": str})
        
        # Playwright tools
        self._add_tool_def("playwright_navigate", "playwright", "@playwright/mcp@latest",
                          "Navigate to URL using Playwright", {"url": str})
        self._add_tool_def("playwright_screenshot", "playwright", "@playwright/mcp@latest",
                          "Take screenshot of webpage", {"url": str, "filename": str})
        self._add_tool_def("playwright_extract_text", "playwright", "@playwright/mcp@latest",
                          "Extract text content from webpage", {"url": str})
        
        # Filesystem tools
        self._add_tool_def("fs_read_file", "filesystem", "@modelcontextprotocol/server-filesystem",
                          "Read file from allowed directories", {"path": str})
        self._add_tool_def("fs_list_directory", "filesystem", "@modelcontextprotocol/server-filesystem",
                          "List directory contents", {"path": str})
        self._add_tool_def("fs_search_files", "filesystem", "@modelcontextprotocol/server-filesystem",
                          "Search files in directory", {"path": str, "pattern": str})
        
        # Fetch tools
        self._add_tool_def("fetch_url", "fetch", "mcp-server-fetch",
                          "Fetch and convert webpage to markdown", {"url": str, "max_length": 5000})
        
        # Sequential Thinking tools
        self._add_tool_def("think_sequential", "think", "@modelcontextprotocol/server-sequential-thinking",
                          "Use structured sequential thinking", {"problem": str, "steps": 5})
        self._add_tool_def("think_analyze", "think", "@modelcontextprotocol/server-sequential-thinking",
                          "Analyze data using sequential thinking", {"data": str, "context": str})
    
    def _add_tool_def(self, name: str, category: str, package: str, description: str, params: Dict):
        """Add a tool definition"""
        self.tools[name] = {
            "name": name,
            "category": category,
            "package": package,
            "description": description,
            "params": params
        }
    
    def execute_tool(self, tool_name: str, **kwargs) -> MCPResult:
        """Execute an MCP tool"""
        if tool_name not in self.tools:
            return MCPResult(
                success=False,
                result=None,
                error=f"Unknown MCP tool: {tool_name}"
            )
        
        tool_def = self.tools[tool_name]
        start_time = time.time()
        
        # Audit logging
        audit_logged = self._audit_log_start(tool_name, kwargs)
        
        try:
            # Check cache for read-only operations
            cache_key = None
            if tool_name in ["github_search_repos", "github_get_repo", "github_search_code", 
                            "context7_query", "context7_resolve", "fetch_url"]:
                cache_key = self._cache_key(tool_name, **kwargs)
                cached = self._get_cached(cache_key)
                if cached:
                    return MCPResult(success=True, result=cached, cached=True)
            
            # Execute via proper MCP client
            result = self._execute_via_client(tool_def, kwargs)
            execution_time = int((time.time() - start_time) * 1000)
            
            # Update stats
            self._update_stats(tool_name, result.get("error") is None)
            
            # Cache result
            if cache_key and result.get("error") is None:
                self._set_cached(cache_key, result)
            
            # Audit log completion
            if audit_logged:
                self._audit_log_complete(tool_name, execution_time, result.get("error") is None)
            
            if result.get("error"):
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
            logger.error(f"[MCP] Tool execution failed: {e}")
            
            if audit_logged:
                self._audit_log_error(tool_name, execution_time, str(e))
            
            return MCPResult(
                success=False,
                result=None,
                error=str(e),
                execution_time_ms=execution_time
            )
    
    def _execute_via_client(self, tool_def: Dict, kwargs: Dict) -> Dict:
        """Execute tool via MCP client"""
        package = tool_def["package"]
        tool_name = tool_def["name"]
        
        # Determine the correct MCP server command
        if package == "mcp-server-fetch":
            cmd = ["uvx", "mcp-server-fetch"]
        elif package.startswith("@modelcontextprotocol/server-filesystem"):
            # Filesystem server needs allowed directories
            cmd = ["npx", "-y", "@modelcontextprotocol/server-filesystem", 
                   "/home/winsock/Downloads/", "/development/", "/srv/", "/opt/codex-swarm/"]
        elif package.startswith("@playwright/mcp"):
            cmd = ["npx", "-y", "@playwright/mcp@latest", "--allow-unrestricted-file-access"]
        else:
            cmd = ["npx", "-y", package]
        
        # Get or create client
        client_name = tool_def["category"]
        client = self.pool.get_client(client_name, cmd)
        
        if not client:
            return {"error": f"Failed to connect to {client_name} MCP server"}
        
        # Map tool names to actual MCP tool names
        mcp_tool_name = self._map_tool_name(tool_name)
        
        # Execute the tool
        try:
            result = client.call_tool(mcp_tool_name, kwargs)
            
            # Format result
            if "content" in result:
                content = result["content"]
                if isinstance(content, list) and len(content) > 0:
                    text_items = [item.get("text", "") for item in content if item.get("type") == "text"]
                    return {"result": "\n".join(text_items)}
                return {"result": content}
            
            return result
            
        except Exception as e:
            logger.error(f"[MCP] Client call failed: {e}")
            return {"error": str(e)}
    
    def _map_tool_name(self, tool_name: str) -> str:
        """Map internal tool name to MCP server tool name"""
        # Most servers use the tool name directly
        mappings = {
            "github_search_repos": "search_repositories",
            "github_get_repo": "get_repository",
            "github_search_code": "search_code",
            "fs_read_file": "read_file",
            "fs_list_directory": "list_directory",
            "fs_search_files": "search_files",
        }
        return mappings.get(tool_name, tool_name)
    
    def _audit_log_start(self, tool_name: str, kwargs: Dict) -> bool:
        """Log tool execution start to audit chain"""
        try:
            from audit.tamper_evident import get_tamper_evident_audit, AuditEventType
            audit = get_tamper_evident_audit()
            
            audit_details = {k: v for k, v in kwargs.items() 
                           if k not in ['password', 'token', 'key', 'secret']}
            
            audit.create_entry(
                event_type=AuditEventType.MCP_TOOL_INVOKED,
                user_id=kwargs.get("_user_id", "system"),
                user_clearance=kwargs.get("_clearance", "SECRET"),
                resource_id=tool_name,
                action="mcp_execute",
                status="started",
                details=audit_details,
                classification="SECRET"
            )
            return True
        except Exception as e:
            logger.debug(f"[MCP AUDIT] Could not log: {e}")
            return False
    
    def _audit_log_complete(self, tool_name: str, execution_time: int, success: bool):
        """Log tool execution completion"""
        try:
            from audit.tamper_evident import get_tamper_evident_audit, AuditEventType
            audit = get_tamper_evident_audit()
            audit.create_entry(
                event_type=AuditEventType.MCP_DATA_RETRIEVED,
                user_id="system",
                user_clearance="SECRET",
                resource_id=tool_name,
                action="mcp_complete",
                status="success" if success else "error",
                details={"execution_time_ms": execution_time},
                classification="SECRET"
            )
        except:
            pass
    
    def _audit_log_error(self, tool_name: str, execution_time: int, error: str):
        """Log tool execution error"""
        try:
            from audit.tamper_evident import get_tamper_evident_audit, AuditEventType
            audit = get_tamper_evident_audit()
            audit.create_entry(
                event_type=AuditEventType.MCP_TOOL_INVOKED,
                user_id="system",
                user_clearance="SECRET",
                resource_id=tool_name,
                action="mcp_error",
                status="failed",
                details={"error": error, "execution_time_ms": execution_time},
                classification="SECRET"
            )
        except:
            pass
    
    def _update_stats(self, tool_name: str, success: bool):
        """Update call statistics"""
        if tool_name not in self.call_stats:
            self.call_stats[tool_name] = {"calls": 0, "errors": 0}
        self.call_stats[tool_name]["calls"] += 1
        if not success:
            self.call_stats[tool_name]["errors"] += 1
    
    def list_tools(self) -> List[Dict]:
        """List all available MCP tools"""
        tool_list = []
        for name, tool_def in self.tools.items():
            tool_list.append({
                "name": name,
                "description": tool_def["description"],
                "category": tool_def["category"],
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
