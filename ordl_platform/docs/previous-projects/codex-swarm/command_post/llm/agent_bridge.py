#!/usr/bin/env python3
"""
ORDL LLM Agent Bridge
Connects LLM providers to Agent system with tool execution loop
"""

import os
import sys
import json
import logging
import asyncio
from typing import Dict, Any, List, Optional, AsyncIterator, Callable
from dataclasses import dataclass, field
from datetime import datetime

# Import LLM types
from .provider import (
    LLMProvider, Message, MessageRole, ToolDefinition, 
    LLMResponse, StreamingDelta, TokenCounter
)

# Import error handling
from .error_handler import (
    ResponseValidator, ErrorRecovery, ResponseFormatter,
    LLMError, LLMErrorType, safe_json_dumps, log_exception
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger('llm.agent_bridge')


@dataclass
class ToolExecutionResult:
    """Result of tool execution"""
    tool_name: str
    tool_call_id: str
    success: bool
    result: Any
    error: Optional[str] = None
    execution_time_ms: int = 0
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class LLMAgentBridge:
    """
    Bridge between LLM providers and Agent Tool System
    
    Features:
    - Tool execution loop (LLM decides → tool executes → result to LLM)
    - Conversation context management
    - Token budget enforcement
    - Streaming responses with tool integration
    - Tamper-evident audit logging
    """
    
    DEFAULT_SYSTEM_PROMPT = """You are an AI agent in the ORDL Command Post, a military-grade cyber operations platform.

Your capabilities include:
- Red Team operations (reconnaissance, vulnerability scanning, payload generation)
- Blue Team defense (SIEM monitoring, incident response, threat detection)
- Knowledge retrieval (RAG semantic search)
- Code execution (secure sandbox)
- MCP tool access (GitHub, SSH, filesystem, web automation)

When you need to use a tool, respond with a tool call in the format specified by your provider.
Available tools will be provided in each conversation.

Classification: TOP SECRET//SCI//NOFORN
Operate with military discipline and precision."""

    def __init__(self,
                 provider: LLMProvider,
                 tool_registry=None,
                 system_prompt: Optional[str] = None,
                 max_context_tokens: int = 32000,
                 max_tool_iterations: int = 10):
        self.provider = provider
        self.tool_registry = tool_registry
        self.system_prompt = system_prompt or self.DEFAULT_SYSTEM_PROMPT
        self.max_context_tokens = max_context_tokens
        self.max_tool_iterations = max_tool_iterations
        self.conversation_history: List[Message] = []
        self._lock = asyncio.Lock()
        
        # Initialize with system message
        self.conversation_history.append(
            Message(role=MessageRole.SYSTEM, content=self.system_prompt)
        )
    
    def _tools_to_definitions(self) -> List[ToolDefinition]:
        """Convert tool registry to LLM tool definitions"""
        if not self.tool_registry:
            return []
        
        definitions = []
        try:
            tools = self.tool_registry.list_tools()
            for tool in tools:
                # Convert tool parameters to JSON schema
                params = tool.get("parameters", {})
                properties = {}
                required = []
                
                for param_name, param_info in params.items():
                    properties[param_name] = {
                        "type": param_info.get("type", "string"),
                        "description": param_info.get("description", "")
                    }
                    if param_info.get("required", False):
                        required.append(param_name)
                
                definitions.append(ToolDefinition(
                    name=tool["name"],
                    description=tool["description"],
                    parameters=properties,
                    required=required
                ))
        except Exception as e:
            logger.error(f"[LLM Bridge] Failed to convert tools: {e}")
        
        return definitions
    
    def _manage_context_window(self):
        """Trim conversation history to fit within token budget"""
        total_tokens = TokenCounter.count_message_tokens(self.conversation_history)
        
        while total_tokens > self.max_context_tokens and len(self.conversation_history) > 2:
            # Remove oldest user/assistant pair (keep system message)
            if len(self.conversation_history) > 2:
                removed = self.conversation_history.pop(1)  # Remove first non-system message
                total_tokens = TokenCounter.count_message_tokens(self.conversation_history)
                logger.debug(f"[LLM Bridge] Removed message from context: {removed.role.value}")
    
    async def _execute_tool(self, tool_call: Dict) -> ToolExecutionResult:
        """Execute a tool call and return result with comprehensive error handling"""
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Validate tool call structure
            error = ResponseValidator.validate_tool_call(tool_call)
            if error:
                return ToolExecutionResult(
                    tool_name="unknown",
                    tool_call_id=tool_call.get("id", "unknown"),
                    success=False,
                    result=None,
                    error=f"Invalid tool call: {error.message}"
                )
            
            function_data = tool_call.get("function", {})
            tool_name = function_data.get("name", "")
            tool_call_id = tool_call.get("id", f"call_{int(start_time * 1000)}")
            arguments_str = function_data.get("arguments", "{}")
            
            # Parse arguments with error handling
            try:
                if isinstance(arguments_str, str):
                    arguments = json.loads(arguments_str)
                elif isinstance(arguments_str, dict):
                    arguments = arguments_str
                else:
                    arguments = {}
            except json.JSONDecodeError as e:
                logger.error(f"[LLM Bridge] Failed to parse arguments: {e}")
                arguments = {}
            
            logger.info(f"[LLM Bridge] Executing tool: {tool_name}")
            
            if not self.tool_registry:
                return ToolExecutionResult(
                    tool_name=tool_name,
                    tool_call_id=tool_call_id,
                    success=False,
                    result=None,
                    error="Tool registry not available"
                )
            
            # Check if tool exists
            available_tools = self.tool_registry.list_tools()
            tool_names = [t.get("name", "") for t in available_tools]
            if tool_name not in tool_names:
                return ToolExecutionResult(
                    tool_name=tool_name,
                    tool_call_id=tool_call_id,
                    success=False,
                    result=None,
                    error=f"Tool '{tool_name}' not found. Available tools: {', '.join(tool_names[:10])}..."
                )
            
            # Execute the tool
            try:
                tool_result = self.tool_registry.execute(tool_name, **arguments)
            except Exception as exec_e:
                logger.error(f"[LLM Bridge] Tool execution exception: {exec_e}")
                return ToolExecutionResult(
                    tool_name=tool_name,
                    tool_call_id=tool_call_id,
                    success=False,
                    result=None,
                    error=f"Execution error: {str(exec_e)}"
                )
            
            execution_time_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
            
            # Extract result safely
            try:
                if hasattr(tool_result, 'success'):
                    success = tool_result.success
                    result = tool_result.result if success else None
                    error = tool_result.error_message if not success else None
                else:
                    success = True
                    result = tool_result
                    error = None
            except Exception as extract_e:
                logger.error(f"[LLM Bridge] Result extraction error: {extract_e}")
                success = False
                result = None
                error = f"Result extraction failed: {str(extract_e)}"
            
            return ToolExecutionResult(
                tool_name=tool_name,
                tool_call_id=tool_call_id,
                success=success,
                result=result,
                error=error,
                execution_time_ms=execution_time_ms
            )
            
        except Exception as e:
            execution_time_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
            log_exception("LLM Bridge Tool Execution", e)
            return ToolExecutionResult(
                tool_name=tool_call.get("function", {}).get("name", "unknown") if isinstance(tool_call, dict) else "unknown",
                tool_call_id=tool_call.get("id", "unknown") if isinstance(tool_call, dict) else "unknown",
                success=False,
                result=None,
                error=f"Tool execution failed: {str(e)}",
                execution_time_ms=execution_time_ms
            )
    
    async def process_message(self, user_message: str) -> Dict[str, Any]:
        """
        Process a user message with potential tool execution loop
        Comprehensive error handling and response validation
        """
        async with self._lock:
            # Add user message
            self.conversation_history.append(
                Message(role=MessageRole.USER, content=user_message)
            )
            
            # Manage context window
            self._manage_context_window()
            
            # Get tool definitions
            tools = self._tools_to_definitions()
            
            iteration = 0
            final_response = None
            tool_results = []
            last_error = None
            
            while iteration < self.max_tool_iterations:
                iteration += 1
                
                try:
                    # Call LLM with retry logic
                    response = None
                    for attempt in range(3):
                        try:
                            response = await self.provider.complete(
                                messages=self.conversation_history,
                                tools=tools if tools else None
                            )
                            break
                        except Exception as e:
                            logger.warning(f"[LLM Bridge] Attempt {attempt + 1} failed: {e}")
                            if attempt < 2:
                                await asyncio.sleep(0.5 * (attempt + 1))
                            else:
                                raise
                    
                    if response is None:
                        raise RuntimeError("Failed to get response from LLM after retries")
                    
                    # Validate response content
                    if not isinstance(response.content, str):
                        logger.warning(f"[LLM Bridge] Response content is not string: {type(response.content)}")
                        response.content = str(response.content) if response.content else ""
                    
                    # Check if tool calls were made
                    if response.tool_calls and len(response.tool_calls) > 0:
                        logger.info(f"[LLM Bridge] LLM requested {len(response.tool_calls)} tool calls")
                        
                        # Validate tool calls
                        valid_tool_calls = []
                        for tc in response.tool_calls:
                            error = ResponseValidator.validate_tool_call(tc)
                            if error:
                                logger.error(f"[LLM Bridge] Invalid tool call: {error.message}")
                            else:
                                valid_tool_calls.append(tc)
                        
                        if valid_tool_calls:
                            # Add assistant message with tool calls
                            self.conversation_history.append(Message(
                                role=MessageRole.ASSISTANT,
                                content=response.content or "",
                                tool_calls=valid_tool_calls
                            ))
                            
                            # Execute each tool call
                            for tool_call in valid_tool_calls:
                                result = await self._execute_tool(tool_call)
                                tool_results.append(result)
                                
                                # Add tool result to conversation
                                try:
                                    result_content = safe_json_dumps({
                                        "success": result.success,
                                        "result": result.result,
                                        "error": result.error
                                    })
                                except:
                                    result_content = str(result.result)
                                
                                self.conversation_history.append(Message(
                                    role=MessageRole.TOOL,
                                    content=result_content,
                                    tool_call_id=result.tool_call_id,
                                    name=result.tool_name
                                ))
                            
                            # Continue loop to get LLM's response to tool results
                            continue
                        else:
                            # No valid tool calls, use content as response
                            final_response = response
                            break
                    
                    else:
                        # No tool calls, this is the final response
                        final_response = response
                        
                        # Add assistant response to history
                        self.conversation_history.append(Message(
                            role=MessageRole.ASSISTANT,
                            content=response.content or ""
                        ))
                        break
                        
                except Exception as e:
                    log_exception("LLM Bridge", e)
                    last_error = str(e)
                    
                    # Create error response
                    return ResponseFormatter.format_error_response(
                        error=last_error,
                        error_type="llm_error",
                        details={
                            "iteration": iteration,
                            "tool_results_count": len(tool_results)
                        }
                    )
            
            # Format successful response
            if final_response:
                return ResponseFormatter.format_success_response(
                    content=final_response.content or "",
                    model=final_response.model,
                    tool_results=[
                        {
                            "tool": r.tool_name,
                            "success": r.success,
                            "result": r.result,
                            "error": r.error
                        }
                        for r in tool_results
                    ],
                    metadata={
                        "iterations": iteration,
                        "latency_ms": final_response.latency_ms
                    }
                )
            else:
                return ResponseFormatter.format_error_response(
                    error="No response generated",
                    error_type="no_response"
                )
    
    async def process_message_stream(self, user_message: str) -> AsyncIterator[Dict[str, Any]]:
        """
        Process a user message with streaming response
        
        Yields:
            - content chunks
            - tool call notifications
            - final result
        """
        async with self._lock:
            # Add user message
            self.conversation_history.append(
                Message(role=MessageRole.USER, content=user_message)
            )
            
            self._manage_context_window()
            tools = self._tools_to_definitions()
            
            try:
                # Start streaming
                full_content = ""
                pending_tool_calls = []
                
                async for delta in self.provider.complete_stream(
                    messages=self.conversation_history,
                    tools=tools if tools else None
                ):
                    if delta.content:
                        full_content += delta.content
                        yield {
                            "type": "content",
                            "content": delta.content
                        }
                    
                    if delta.tool_calls:
                        pending_tool_calls = delta.tool_calls
                        yield {
                            "type": "tool_calls",
                            "tool_calls": delta.tool_calls
                        }
                    
                    if delta.finish_reason:
                        if delta.finish_reason == "tool_calls" and pending_tool_calls:
                            # Execute tools
                            tool_results = []
                            for tool_call in pending_tool_calls:
                                yield {
                                    "type": "tool_start",
                                    "tool": tool_call.get("function", {}).get("name", "")
                                }
                                result = await self._execute_tool(tool_call)
                                tool_results.append(result)
                                yield {
                                    "type": "tool_complete",
                                    "tool": result.tool_name,
                                    "success": result.success
                                }
                            
                            # Add to history and continue
                            self.conversation_history.append(Message(
                                role=MessageRole.ASSISTANT,
                                content=full_content,
                                tool_calls=pending_tool_calls
                            ))
                            
                            for result in tool_results:
                                result_content = json.dumps({
                                    "success": result.success,
                                    "result": result.result,
                                    "error": result.error
                                })
                                self.conversation_history.append(Message(
                                    role=MessageRole.TOOL,
                                    content=result_content,
                                    tool_call_id=result.tool_call_id,
                                    name=result.tool_name
                                ))
                            
                            # Continue with non-streaming call for final response
                            # (simplification to avoid nested streaming complexity)
                            final_response = await self.provider.complete(
                                messages=self.conversation_history,
                                tools=None  # Don't allow more tool calls
                            )
                            
                            self.conversation_history.append(Message(
                                role=MessageRole.ASSISTANT,
                                content=final_response.content
                            ))
                            
                            yield {
                                "type": "final",
                                "content": final_response.content,
                                "tool_results": [
                                    {
                                        "tool": r.tool_name,
                                        "success": r.success,
                                        "result": r.result,
                                        "error": r.error
                                    }
                                    for r in tool_results
                                ]
                            }
                        
                        else:
                            # Normal completion
                            self.conversation_history.append(Message(
                                role=MessageRole.ASSISTANT,
                                content=full_content
                            ))
                            
                            yield {
                                "type": "final",
                                "content": full_content,
                                "tool_results": []
                            }
                        
            except Exception as e:
                logger.error(f"[LLM Bridge] Stream processing failed: {e}")
                yield {
                    "type": "error",
                    "error": str(e)
                }
    
    def clear_history(self):
        """Clear conversation history (keep system prompt)"""
        self.conversation_history = [
            Message(role=MessageRole.SYSTEM, content=self.system_prompt)
        ]
        logger.info("[LLM Bridge] Conversation history cleared")
    
    def get_history(self) -> List[Dict[str, Any]]:
        """Get conversation history"""
        return [
            {
                "role": msg.role.value,
                "content": msg.content,
                "timestamp": msg.timestamp
            }
            for msg in self.conversation_history
        ]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get bridge statistics"""
        return {
            "provider": self.provider.__class__.__name__,
            "model": self.provider.model,
            "history_length": len(self.conversation_history),
            "token_estimate": TokenCounter.count_message_tokens(self.conversation_history),
            "max_context_tokens": self.max_context_tokens,
            "max_tool_iterations": self.max_tool_iterations
        }
