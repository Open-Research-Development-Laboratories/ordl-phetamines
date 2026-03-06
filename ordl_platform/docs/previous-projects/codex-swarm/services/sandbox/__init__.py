"""
ORDL Command Post - Code Sandbox Service
========================================

A military-grade, Docker-based secure code execution environment supporting
multiple programming languages with comprehensive security isolation.

Usage:
    from services.sandbox import SandboxOrchestrator, Language, ClearanceLevel
    
    with SandboxOrchestrator() as sandbox:
        result = sandbox.execute(
            source_code='print("Hello World")',
            language=Language.PYTHON,
            clearance_level=ClearanceLevel.UNCLASSIFIED
        )
        print(result.stdout)

Supported Languages:
    - Python 3.11
    - C23 (GCC 13)
    - Java 21 (OpenJDK)
    - JavaScript/Node.js 20
    - Rust 1.75
    - Go 1.21

Clearance Levels:
    - UNCLASSIFIED: Network isolated, restricted execution
    - CONFIDENTIAL: Limited network access
    - SECRET: Standard network access
    - TOP_SECRET: Extended network access
    - TS_SCI: Full network capabilities
    - TS_SCI_NOFORN: Reserved for restricted operations

Classification: TOP SECRET//NOFORN//SCI
"""

from .sandbox import (
    # Main orchestrator
    SandboxOrchestrator,
    
    # Enums
    Language,
    ClearanceLevel,
    
    # Data classes
    ResourceLimits,
    SecurityOptions,
    SandboxConfig,
    ExecutionResult,
    
    # Exceptions
    SandboxError,
    SandboxTimeoutError,
    SandboxSecurityError,
    SandboxResourceError,
    
    # Convenience functions
    get_sandbox,
    execute_code,
)

__version__ = "1.0.0"
__author__ = "ORDL Engineering Team"
__classification__ = "TOP SECRET//NOFORN//SCI"

__all__ = [
    'SandboxOrchestrator',
    'Language',
    'ClearanceLevel',
    'ResourceLimits',
    'SecurityOptions',
    'SandboxConfig',
    'ExecutionResult',
    'SandboxError',
    'SandboxTimeoutError',
    'SandboxSecurityError',
    'SandboxResourceError',
    'get_sandbox',
    'execute_code',
]
