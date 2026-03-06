#!/usr/bin/env python3
"""
ORDL LLM Error Handler
Military-grade error handling and response validation
"""

import json
import logging
import traceback
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger('llm.error_handler')


class LLMErrorType(Enum):
    """Types of LLM errors"""
    CONNECTION_ERROR = "connection_error"
    TIMEOUT = "timeout"
    INVALID_RESPONSE = "invalid_response"
    JSON_PARSE_ERROR = "json_parse_error"
    TOOL_EXECUTION_ERROR = "tool_execution_error"
    RATE_LIMIT = "rate_limit"
    MODEL_UNAVAILABLE = "model_unavailable"
    UNKNOWN = "unknown"


@dataclass
class LLMError:
    """Structured LLM error"""
    error_type: LLMErrorType
    message: str
    details: Optional[Dict] = None
    recoverable: bool = False
    retry_after: Optional[int] = None


class ResponseValidator:
    """
    Validates and sanitizes LLM responses
    """
    
    @staticmethod
    def validate_json_response(data: Any) -> Dict[str, Any]:
        """
        Validate and sanitize a response that should be JSON
        
        Args:
            data: The data to validate
            
        Returns:
            Validated dictionary
        """
        if isinstance(data, dict):
            return data
        
        if isinstance(data, str):
            try:
                return json.loads(data)
            except json.JSONDecodeError as e:
                logger.error(f"JSON parse error: {e}")
                # Return error structure
                return {
                    "success": False,
                    "error": f"Invalid JSON: {str(e)[:100]}",
                    "raw_response": data[:500] if len(data) > 500 else data
                }
        
        return {
            "success": False,
            "error": f"Unexpected response type: {type(data).__name__}",
            "raw_response": str(data)[:500]
        }
    
    @staticmethod
    def sanitize_string(content: str) -> str:
        """
        Sanitize string content for safe display
        
        Args:
            content: Raw content string
            
        Returns:
            Sanitized string
        """
        if not content:
            return ""
        
        # Remove null bytes
        content = content.replace('\x00', '')
        
        # Remove control characters except newlines and tabs
        sanitized = ''.join(
            char for char in content
            if char == '\n' or char == '\t' or (ord(char) >= 32 and ord(char) < 127)
        )
        
        return sanitized
    
    @staticmethod
    def validate_tool_call(tool_call: Dict) -> Optional[LLMError]:
        """
        Validate a tool call structure
        
        Args:
            tool_call: The tool call to validate
            
        Returns:
            LLMError if invalid, None if valid
        """
        if not isinstance(tool_call, dict):
            return LLMError(
                error_type=LLMErrorType.INVALID_RESPONSE,
                message="Tool call must be a dictionary",
                details={"received_type": type(tool_call).__name__}
            )
        
        # Check required fields
        if "function" not in tool_call:
            return LLMError(
                error_type=LLMErrorType.INVALID_RESPONSE,
                message="Tool call missing 'function' field",
                details={"tool_call": tool_call}
            )
        
        function = tool_call.get("function", {})
        if not isinstance(function, dict):
            return LLMError(
                error_type=LLMErrorType.INVALID_RESPONSE,
                message="Tool call 'function' must be a dictionary",
                details={"function_type": type(function).__name__}
            )
        
        if "name" not in function:
            return LLMError(
                error_type=LLMErrorType.INVALID_RESPONSE,
                message="Tool call function missing 'name' field"
            )
        
        return None


class ErrorRecovery:
    """
    Error recovery strategies
    """
    
    MAX_RETRIES = 3
    RETRY_DELAY_BASE = 1.0
    
    @staticmethod
    def should_retry(error: LLMError, attempt: int) -> bool:
        """Determine if error is recoverable and should be retried"""
        if attempt >= ErrorRecovery.MAX_RETRIES:
            return False
        
        recoverable_types = [
            LLMErrorType.CONNECTION_ERROR,
            LLMErrorType.TIMEOUT,
            LLMErrorType.RATE_LIMIT,
            LLMErrorType.MODEL_UNAVAILABLE
        ]
        
        return error.error_type in recoverable_types or error.recoverable
    
    @staticmethod
    def get_retry_delay(attempt: int) -> float:
        """Calculate exponential backoff delay"""
        import random
        delay = ErrorRecovery.RETRY_DELAY_BASE * (2 ** attempt)
        # Add jitter
        delay *= (0.5 + random.random())
        return delay
    
    @staticmethod
    def create_fallback_response(error: LLMError, original_prompt: str) -> str:
        """
        Create a graceful fallback response when LLM fails
        
        Args:
            error: The error that occurred
            original_prompt: The original user prompt
            
        Returns:
            Fallback response text
        """
        if error.error_type == LLMErrorType.MODEL_UNAVAILABLE:
            return (
                "[SYSTEM MESSAGE] The AI model is currently unavailable. "
                "Your message has been logged and will be processed when service is restored. "
                f"Error: {error.message}"
            )
        
        elif error.error_type == LLMErrorType.TIMEOUT:
            return (
                "[SYSTEM MESSAGE] The request timed out. "
                "The system may be experiencing high load. Please try again."
            )
        
        elif error.error_type == LLMErrorType.CONNECTION_ERROR:
            return (
                "[SYSTEM MESSAGE] Connection to AI service failed. "
                "Please check network connectivity and try again."
            )
        
        elif error.error_type == LLMErrorType.JSON_PARSE_ERROR:
            return (
                "[SYSTEM MESSAGE] The AI response could not be parsed correctly. "
                "This may be a temporary issue. Please try rephrasing your request."
            )
        
        else:
            return (
                "[SYSTEM MESSAGE] An unexpected error occurred while processing your request. "
                f"Error type: {error.error_type.value}. "
                "Please try again or contact support if the issue persists."
            )


class ResponseFormatter:
    """
    Formats responses consistently for the API
    """
    
    @staticmethod
    def format_success_response(
        content: str,
        model: str,
        tool_results: Optional[list] = None,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Format a successful response
        
        Args:
            content: Response content
            model: Model name
            tool_results: Tool execution results
            metadata: Additional metadata
            
        Returns:
            Formatted response dictionary
        """
        response = {
            "success": True,
            "response": ResponseValidator.sanitize_string(content),
            "model": model,
            "timestamp": __import__('datetime').datetime.utcnow().isoformat(),
            "tool_calls_executed": len(tool_results) if tool_results else 0
        }
        
        if tool_results:
            response["tool_results"] = tool_results
        
        if metadata:
            response["metadata"] = metadata
        
        return response
    
    @staticmethod
    def format_error_response(
        error: str,
        error_type: str = "unknown",
        details: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Format an error response
        
        Args:
            error: Error message
            error_type: Type of error
            details: Additional error details
            
        Returns:
            Formatted error response dictionary
        """
        response = {
            "success": False,
            "response": f"[ERROR] {error}",
            "error": error,
            "error_type": error_type,
            "timestamp": __import__('datetime').datetime.utcnow().isoformat()
        }
        
        if details:
            response["details"] = details
        
        return response


def safe_json_dumps(obj: Any, default: str = "{}") -> str:
    """
    Safely serialize to JSON with error handling
    
    Args:
        obj: Object to serialize
        default: Default string if serialization fails
        
    Returns:
        JSON string
    """
    try:
        return json.dumps(obj, ensure_ascii=False, default=str)
    except (TypeError, ValueError) as e:
        logger.error(f"JSON serialization error: {e}")
        return json.dumps({
            "success": False,
            "error": f"Serialization error: {str(e)}"
        })


def log_exception(context: str, exception: Exception):
    """
    Log an exception with full context
    
    Args:
        context: Context where error occurred
        exception: The exception
    """
    logger.error(f"[{context}] Exception: {exception}")
    logger.error(traceback.format_exc())


__all__ = [
    'LLMErrorType',
    'LLMError', 
    'ResponseValidator',
    'ErrorRecovery',
    'ResponseFormatter',
    'safe_json_dumps',
    'log_exception'
]
