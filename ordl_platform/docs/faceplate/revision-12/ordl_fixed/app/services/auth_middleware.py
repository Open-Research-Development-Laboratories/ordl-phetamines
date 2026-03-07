"""
Authentication Middleware for ORDL BFF API

Handles JWT extraction, validation, and user context injection.
"""
import os
import logging
from functools import wraps
from typing import Optional, Dict, Any, Callable

import jwt
from jwt.exceptions import PyJWTError, ExpiredSignatureError, InvalidTokenError
from flask import request, g, jsonify

from app.services.backend_client import get_backend_client, BackendClientError


logger = logging.getLogger(__name__)


class AuthError(Exception):
    """Authentication error with HTTP status code."""
    
    def __init__(self, message: str, status_code: int = 401, error_code: str = "AUTH_ERROR"):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": self.error_code,
            "message": self.message
        }


class JWTValidator:
    """
    JWT token validator with support for multiple signing algorithms.
    
    Validates:
    - Token signature
    - Expiration time
    - Required claims
    - Issuer (optional)
    - Audience (optional)
    """
    
    def __init__(
        self,
        secret_key: Optional[str] = None,
        algorithm: str = "HS256",
        issuer: Optional[str] = None,
        audience: Optional[str] = None,
        required_claims: Optional[list] = None
    ):
        """
        Initialize JWT validator.
        
        Args:
            secret_key: JWT signing secret (defaults to JWT_SECRET env var)
            algorithm: Signing algorithm (HS256, RS256, etc.)
            issuer: Expected token issuer
            audience: Expected token audience
            required_claims: List of required claims in token
        """
        self.secret_key = secret_key or os.environ.get('JWT_SECRET') or os.environ.get('SECRET_KEY')
        self.algorithm = algorithm
        self.issuer = issuer or os.environ.get('JWT_ISSUER')
        self.audience = audience or os.environ.get('JWT_AUDIENCE')
        self.required_claims = required_claims or ['sub', 'exp', 'iat']
        
        # Support RS256 for asymmetric keys
        if algorithm.startswith('RS'):
            public_key = os.environ.get('JWT_PUBLIC_KEY')
            if public_key:
                self.secret_key = public_key.replace('\\n', '\n')
    
    def validate(self, token: str) -> Dict[str, Any]:
        """
        Validate a JWT token.
        
        Args:
            token: The JWT token string
            
        Returns:
            Decoded token payload
            
        Raises:
            AuthError: If token is invalid or expired
        """
        if not self.secret_key:
            raise AuthError(
                "JWT validation not configured",
                status_code=500,
                error_code="AUTH_CONFIG_ERROR"
            )
        
        try:
            options = {}
            
            # Build verification kwargs
            verify_kwargs = {
                "key": self.secret_key,
                "algorithms": [self.algorithm],
                "options": options
            }
            
            if self.issuer:
                verify_kwargs["issuer"] = self.issuer
            if self.audience:
                verify_kwargs["audience"] = self.audience
            
            # Decode and validate
            payload = jwt.decode(token, **verify_kwargs)
            
            # Check required claims
            for claim in self.required_claims:
                if claim not in payload:
                    raise AuthError(
                        f"Missing required claim: {claim}",
                        error_code="INVALID_TOKEN"
                    )
            
            return payload
            
        except ExpiredSignatureError:
            raise AuthError("Token has expired", error_code="TOKEN_EXPIRED")
        except InvalidTokenError as e:
            raise AuthError(f"Invalid token: {str(e)}", error_code="INVALID_TOKEN")
        except PyJWTError as e:
            raise AuthError(f"Token validation failed: {str(e)}", error_code="TOKEN_VALIDATION_FAILED")


class AuthContext:
    """User authentication context extracted from JWT."""
    
    def __init__(self, token_payload: Dict[str, Any], raw_token: str):
        self.raw_token = raw_token
        self.payload = token_payload
        
        # Standard claims
        self.user_id = token_payload.get('sub') or token_payload.get('user_id')
        self.email = token_payload.get('email')
        self.name = token_payload.get('name')
        
        # ORDL-specific claims
        self.clearance_level = token_payload.get('clearance_level', 1)
        self.compartments = token_payload.get('compartments', [])
        self.is_admin = token_payload.get('is_admin', False) or 'admin' in token_payload.get('roles', [])
        self.org_memberships = token_payload.get('org_memberships', [])
        self.roles = token_payload.get('roles', [])
        
        # Token metadata
        self.issued_at = token_payload.get('iat')
        self.expires_at = token_payload.get('exp')
        self.issuer = token_payload.get('iss')
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'user_id': self.user_id,
            'email': self.email,
            'name': self.name,
            'clearance_level': self.clearance_level,
            'compartments': self.compartments,
            'is_admin': self.is_admin,
            'org_memberships': self.org_memberships,
            'roles': self.roles
        }
    
    def is_member_of(self, org_id: str) -> bool:
        """Check if user is member of an organization."""
        return org_id in self.org_memberships or self.is_admin
    
    def has_clearance(self, level: int) -> bool:
        """Check if user has required clearance level."""
        return self.clearance_level >= level or self.is_admin
    
    def has_role(self, role: str) -> bool:
        """Check if user has a specific role."""
        return role in self.roles or self.is_admin


# Global validator instance
_jwt_validator: Optional[JWTValidator] = None


def get_jwt_validator() -> JWTValidator:
    """Get or create the JWT validator singleton."""
    global _jwt_validator
    if _jwt_validator is None:
        # Check for RS256 public key
        algorithm = "RS256" if os.environ.get('JWT_PUBLIC_KEY') else "HS256"
        _jwt_validator = JWTValidator(algorithm=algorithm)
    return _jwt_validator


def extract_token_from_header() -> Optional[str]:
    """
    Extract JWT token from Authorization header.
    
    Supports:
    - Bearer token: "Authorization: Bearer <token>"
    - Direct token: "Authorization: <token>"
    
    Returns:
        Token string or None if not found/invalid format
    """
    auth_header = request.headers.get('Authorization', '')
    
    if not auth_header:
        return None
    
    # Handle Bearer token
    parts = auth_header.split()
    if len(parts) == 2 and parts[0].lower() == 'bearer':
        return parts[1]
    
    # Handle direct token
    if len(parts) == 1:
        return parts[0]
    
    return None


def extract_token_from_cookie() -> Optional[str]:
    """Extract JWT token from cookie."""
    return request.cookies.get('access_token')


def get_auth_token() -> Optional[str]:
    """
    Get authentication token from request.
    
    Checks in order:
    1. Authorization header (Bearer)
    2. Cookie (access_token)
    """
    # Try header first
    token = extract_token_from_header()
    if token:
        return token
    
    # Try cookie
    return extract_token_from_cookie()


def authenticate_request() -> AuthContext:
    """
    Authenticate the current request.
    
    Returns:
        AuthContext with user information
        
    Raises:
        AuthError: If authentication fails
    """
    token = get_auth_token()
    
    if not token:
        raise AuthError(
            "Authentication required",
            error_code="MISSING_TOKEN"
        )
    
    validator = get_jwt_validator()
    payload = validator.validate(token)
    
    return AuthContext(payload, token)


def require_auth(func: Callable) -> Callable:
    """
    Decorator to require authentication for a route.
    
    Injects auth context into Flask's g object as g.auth_context.
    
    Example:
        @bp.route('/protected')
        @require_auth
        def protected_route():
            user_id = g.auth_context.user_id
            return jsonify({"user": user_id})
    """
    @wraps(func)
    def decorated(*args, **kwargs):
        try:
            auth_context = authenticate_request()
            g.auth_context = auth_context
            g.user_id = auth_context.user_id
            g.is_admin = auth_context.is_admin
            g.clearance_level = auth_context.clearance_level
            g.compartments = auth_context.compartments
            g.org_memberships = auth_context.org_memberships
            
            return func(*args, **kwargs)
            
        except AuthError as e:
            logger.warning(f"Authentication failed: {e.message}")
            response = jsonify(e.to_dict())
            response.status_code = e.status_code
            return response
    
    return decorated


def optional_auth(func: Callable) -> Callable:
    """
    Decorator for optional authentication.
    
    Sets g.auth_context if token is present and valid, otherwise continues
    without authentication.
    """
    @wraps(func)
    def decorated(*args, **kwargs):
        try:
            auth_context = authenticate_request()
            g.auth_context = auth_context
            g.user_id = auth_context.user_id
            g.is_admin = auth_context.is_admin
            g.clearance_level = auth_context.clearance_level
            g.compartments = auth_context.compartments
            g.org_memberships = auth_context.org_memberships
        except AuthError:
            # Continue without auth context
            g.auth_context = None
            g.user_id = None
            g.is_admin = False
            g.clearance_level = 0
            g.compartments = []
            g.org_memberships = []
        
        return func(*args, **kwargs)
    
    return decorated


def check_org_access(org_id: str) -> bool:
    """
    Check if current user has access to an organization.
    
    Args:
        org_id: Organization ID to check
        
    Returns:
        True if user has access
    """
    auth_ctx = getattr(g, 'auth_context', None)
    if not auth_ctx:
        return False
    
    return auth_ctx.is_member_of(org_id)


def check_clearance(level: int) -> bool:
    """
    Check if current user has required clearance level.
    
    Args:
        level: Required clearance level
        
    Returns:
        True if user has clearance
    """
    auth_ctx = getattr(g, 'auth_context', None)
    if not auth_ctx:
        return False
    
    return auth_ctx.has_clearance(level)


def get_auth_headers() -> Dict[str, str]:
    """
    Get headers to forward authentication to backend.
    
    Returns:
        Dictionary of headers including Authorization
    """
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    # Forward authorization header
    auth_header = request.headers.get('Authorization')
    if auth_header:
        headers['Authorization'] = auth_header
    
    # Forward user context if available
    auth_ctx = getattr(g, 'auth_context', None)
    if auth_ctx:
        headers['X-User-ID'] = str(auth_ctx.user_id or '')
        headers['X-User-Clearance'] = str(auth_ctx.clearance_level)
        headers['X-User-Admin'] = str(auth_ctx.is_admin).lower()
    
    return headers
