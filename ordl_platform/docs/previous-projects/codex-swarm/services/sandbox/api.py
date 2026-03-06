#!/usr/bin/env python3
"""
ORDL Command Post - Sandbox API Integration
===========================================

Flask/HTTP API endpoints for the code sandbox service.

This module provides REST API endpoints for remote code execution,
designed to integrate with the ORDL Command Post main application.

Classification: TOP SECRET//NOFORN//SCI
"""

import json
import logging
from functools import wraps
from typing import Dict, Any, Optional
from dataclasses import asdict

try:
    from flask import Blueprint, request, jsonify, current_app
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False

from .sandbox import (
    SandboxOrchestrator,
    Language,
    ClearanceLevel,
    ResourceLimits,
    SandboxError,
    SandboxTimeoutError,
)

logger = logging.getLogger('ordl.sandbox.api')

# Create blueprint (only if Flask is available)
if FLASK_AVAILABLE:
    sandbox_bp = Blueprint('sandbox', __name__, url_prefix='/api/sandbox')
else:
    sandbox_bp = None


class SandboxAPI:
    """
    API handler for sandbox operations.
    
    Can be used directly or mounted as Flask blueprint.
    """
    
    def __init__(self, orchestrator: Optional[SandboxOrchestrator] = None):
        """
        Initialize the sandbox API.
        
        Args:
            orchestrator: Sandbox orchestrator instance (creates default if None)
        """
        self.orchestrator = orchestrator or SandboxOrchestrator()
    
    def execute_code(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute code in sandbox.
        
        Request format:
        {
            "source_code": "print('Hello')",
            "language": "python",
            "timeout": 30,
            "memory_limit": "512m",
            "clearance_level": "unclassified",
            "network_isolated": true,
            "file_uploads": {...}  # base64 encoded files
        }
        
        Args:
            data: Request data dictionary
            
        Returns:
            Response dictionary with execution results
        """
        try:
            # Validate required fields
            if 'source_code' not in data:
                return {
                    'success': False,
                    'error': 'Missing required field: source_code'
                }, 400
            
            if 'language' not in data:
                return {
                    'success': False,
                    'error': 'Missing required field: language'
                }, 400
            
            # Extract parameters
            source_code = data['source_code']
            language = data['language']
            timeout = data.get('timeout', 30)
            memory_limit = data.get('memory_limit')
            clearance_level = data.get('clearance_level', 'unclassified')
            network_isolated = data.get('network_isolated', True)
            
            # Validate timeout (1-300 seconds)
            timeout = max(1, min(300, int(timeout)))
            
            # Execute code
            result = self.orchestrator.execute(
                source_code=source_code,
                language=language,
                clearance_level=clearance_level,
                timeout=timeout,
                memory_limit=memory_limit,
                network_isolated=network_isolated
            )
            
            # Return result as dictionary
            return {
                'success': True,
                'result': result.to_dict()
            }, 200
            
        except SandboxTimeoutError as e:
            logger.warning(f"Code execution timed out: {e}")
            return {
                'success': False,
                'error': 'Execution timed out',
                'message': str(e)
            }, 408
            
        except SandboxError as e:
            logger.error(f"Sandbox error: {e}")
            return {
                'success': False,
                'error': 'Sandbox error',
                'message': str(e)
            }, 400
            
        except Exception as e:
            logger.exception("Unexpected error during code execution")
            return {
                'success': False,
                'error': 'Internal server error',
                'message': str(e)
            }, 500
    
    def get_health(self) -> Dict[str, Any]:
        """Get sandbox health status."""
        try:
            health = self.orchestrator.health_check()
            return {
                'success': True,
                'health': health
            }, 200
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }, 500
    
    def get_stats(self) -> Dict[str, Any]:
        """Get sandbox statistics."""
        try:
            stats = self.orchestrator.get_container_stats()
            return {
                'success': True,
                'stats': stats
            }, 200
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {
                'success': False,
                'error': str(e)
            }, 500
    
    def get_languages(self) -> Dict[str, Any]:
        """Get supported languages."""
        languages = [
            {
                'id': lang.value,
                'name': lang.value.capitalize(),
                'docker_image': self.orchestrator.DEFAULT_IMAGES.get(lang, 'unknown')
            }
            for lang in Language
        ]
        
        return {
            'success': True,
            'languages': languages
        }, 200
    
    def get_clearance_levels(self) -> Dict[str, Any]:
        """Get available clearance levels."""
        levels = [
            {
                'id': level.value,
                'name': level.value.upper().replace('_', '/'),
                'network_access': level not in [
                    ClearanceLevel.UNCLASSIFIED,
                    ClearanceLevel.TS_SCI_NOFORN
                ]
            }
            for level in ClearanceLevel
        ]
        
        return {
            'success': True,
            'clearance_levels': levels
        }, 200


# Flask blueprint routes (if Flask is available)
if FLASK_AVAILABLE and sandbox_bp is not None:
    
    def get_api() -> SandboxAPI:
        """Get or create sandbox API instance."""
        if not hasattr(current_app, '_sandbox_api'):
            current_app._sandbox_api = SandboxAPI()
        return current_app._sandbox_api
    
    @sandbox_bp.route('/execute', methods=['POST'])
    def execute():
        """Execute code endpoint."""
        data = request.get_json() or {}
        result, status_code = get_api().execute_code(data)
        return jsonify(result), status_code
    
    @sandbox_bp.route('/health', methods=['GET'])
    def health():
        """Health check endpoint."""
        result, status_code = get_api().get_health()
        return jsonify(result), status_code
    
    @sandbox_bp.route('/stats', methods=['GET'])
    def stats():
        """Statistics endpoint."""
        result, status_code = get_api().get_stats()
        return jsonify(result), status_code
    
    @sandbox_bp.route('/languages', methods=['GET'])
    def languages():
        """Supported languages endpoint."""
        result, status_code = get_api().get_languages()
        return jsonify(result), status_code
    
    @sandbox_bp.route('/clearance-levels', methods=['GET'])
    def clearance_levels():
        """Clearance levels endpoint."""
        result, status_code = get_api().get_clearance_levels()
        return jsonify(result), status_code


def register_blueprint(app, url_prefix: str = '/api/sandbox'):
    """
    Register sandbox blueprint with Flask app.
    
    Args:
        app: Flask application instance
        url_prefix: URL prefix for sandbox endpoints
    """
    if not FLASK_AVAILABLE:
        raise ImportError("Flask is required for blueprint registration")
    
    if sandbox_bp is None:
        raise RuntimeError("Sandbox blueprint not available")
    
    app.register_blueprint(sandbox_bp, url_prefix=url_prefix)
    logger.info(f"Registered sandbox blueprint at {url_prefix}")


# Example usage
if __name__ == '__main__':
    # Standalone API server example
    if not FLASK_AVAILABLE:
        print("Flask is required to run the API server")
        print("Install with: pip install flask")
        exit(1)
    
    from flask import Flask
    
    app = Flask(__name__)
    register_blueprint(app)
    
    @app.route('/')
    def index():
        return jsonify({
            'service': 'ORDL Code Sandbox API',
            'version': '1.0.0',
            'classification': 'TOP SECRET//NOFORN//SCI',
            'endpoints': [
                '/api/sandbox/execute',
                '/api/sandbox/health',
                '/api/sandbox/stats',
                '/api/sandbox/languages',
                '/api/sandbox/clearance-levels'
            ]
        })
    
    print("Starting ORDL Code Sandbox API Server...")
    print("Endpoints:")
    print("  POST /api/sandbox/execute")
    print("  GET  /api/sandbox/health")
    print("  GET  /api/sandbox/stats")
    print("  GET  /api/sandbox/languages")
    print("  GET  /api/sandbox/clearance-levels")
    
    app.run(host='0.0.0.0', port=18080, debug=False)
