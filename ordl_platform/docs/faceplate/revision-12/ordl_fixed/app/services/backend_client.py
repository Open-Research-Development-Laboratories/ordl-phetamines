"""
Backend HTTP Client for ORDL API Proxy

Provides resilient HTTP client with retry logic, circuit breaker pattern,
and proper error handling for communicating with the ORDL backend API.
"""
import os
import logging
import time
from typing import Optional, Dict, Any, Tuple, Union
from enum import Enum

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, rejecting requests
    HALF_OPEN = "half_open"  # Testing if backend recovered


class CircuitBreaker:
    """
    Circuit breaker pattern implementation to prevent cascading failures.
    
    - CLOSED: Normal operation, requests pass through
    - OPEN: Backend failing, requests fail fast
    - HALF_OPEN: Testing if backend recovered
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max_calls: int = 3
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.half_open_calls = 0
        self._lock_time: float = 0
    
    def can_execute(self) -> bool:
        """Check if a request can be executed."""
        now = time.time()
        
        if self.state == CircuitState.CLOSED:
            return True
        
        if self.state == CircuitState.OPEN:
            if now - (self.last_failure_time or 0) >= self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
                self.success_count = 0
                logger.info("Circuit breaker transitioning to HALF_OPEN")
                return True
            return False
        
        if self.state == CircuitState.HALF_OPEN:
            if self.half_open_calls < self.half_open_max_calls:
                self.half_open_calls += 1
                return True
            return False
        
        return True
    
    def record_success(self):
        """Record a successful request."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.half_open_max_calls:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                logger.info("Circuit breaker transitioning to CLOSED")
        else:
            self.failure_count = max(0, self.failure_count - 1)
    
    def record_failure(self):
        """Record a failed request."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            logger.warning("Circuit breaker transitioning to OPEN (half-open failure)")
        elif self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit breaker transitioning to OPEN ({self.failure_count} failures)")


class BackendClientError(Exception):
    """Base exception for backend client errors."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[Dict] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class BackendConnectionError(BackendClientError):
    """Error connecting to backend."""
    pass


class BackendTimeoutError(BackendClientError):
    """Backend request timed out."""
    pass


class BackendCircuitOpenError(BackendClientError):
    """Circuit breaker is open."""
    pass


class BackendClient:
    """
    HTTP client for ORDL backend API with resilience patterns.
    
    Features:
    - Automatic retries with exponential backoff
    - Circuit breaker pattern for fault tolerance
    - Connection pooling
    - Configurable timeouts
    - Proper error handling
    """
    
    DEFAULT_TIMEOUT = 30.0
    MAX_RETRIES = 3
    BACKOFF_FACTOR = 0.5
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = MAX_RETRIES,
        circuit_failure_threshold: int = 5,
        circuit_recovery_timeout: float = 30.0
    ):
        """
        Initialize the backend client.
        
        Args:
            base_url: Backend API base URL (defaults to BACKEND_URL env var)
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for failed requests
            circuit_failure_threshold: Failures before opening circuit
            circuit_recovery_timeout: Seconds before attempting recovery
        """
        self.base_url = (base_url or os.environ.get('BACKEND_URL', 'http://localhost:8080')).rstrip('/')
        self.timeout = timeout
        
        # Initialize circuit breaker
        self.circuit = CircuitBreaker(
            failure_threshold=circuit_failure_threshold,
            recovery_timeout=circuit_recovery_timeout
        )
        
        # Create session with retry strategy
        self.session = requests.Session()
        
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=BACKOFF_FACTOR,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST", "PUT", "DELETE", "PATCH"]
        )
        
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=20
        )
        
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        logger.info(f"BackendClient initialized with base_url: {self.base_url}")
    
    def _make_request(
        self,
        method: str,
        path: str,
        headers: Optional[Dict[str, str]] = None,
        json_data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        timeout: Optional[float] = None
    ) -> Tuple[int, Dict[str, Any]]:
        """
        Make an HTTP request to the backend.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE, PATCH)
            path: API path (will be appended to base_url)
            headers: Optional request headers
            json_data: Optional JSON request body
            params: Optional query parameters
            timeout: Optional override for request timeout
            
        Returns:
            Tuple of (status_code, response_data)
            
        Raises:
            BackendCircuitOpenError: If circuit breaker is open
            BackendConnectionError: If connection fails
            BackendTimeoutError: If request times out
            BackendClientError: For other errors
        """
        # Check circuit breaker
        if not self.circuit.can_execute():
            raise BackendCircuitOpenError("Circuit breaker is OPEN - backend unavailable")
        
        url = f"{self.base_url}{path}"
        request_timeout = timeout or self.timeout
        
        try:
            response = self.session.request(
                method=method.upper(),
                url=url,
                headers=headers,
                json=json_data,
                params=params,
                timeout=request_timeout
            )
            
            # Record success
            self.circuit.record_success()
            
            # Parse response
            try:
                response_data = response.json() if response.content else {}
            except ValueError:
                response_data = {"raw": response.text} if response.text else {}
            
            return response.status_code, response_data
            
        except requests.exceptions.Timeout as e:
            self.circuit.record_failure()
            logger.error(f"Request timeout: {method} {path}")
            raise BackendTimeoutError(f"Request timeout after {request_timeout}s", status_code=504)
            
        except requests.exceptions.ConnectionError as e:
            self.circuit.record_failure()
            logger.error(f"Connection error: {method} {path} - {e}")
            raise BackendConnectionError(f"Failed to connect to backend: {e}", status_code=503)
            
        except requests.exceptions.RequestException as e:
            self.circuit.record_failure()
            logger.error(f"Request error: {method} {path} - {e}")
            raise BackendClientError(f"Request failed: {e}", status_code=500)
    
    def get(
        self,
        path: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict] = None
    ) -> Tuple[int, Dict[str, Any]]:
        """Make a GET request."""
        return self._make_request("GET", path, headers=headers, params=params)
    
    def post(
        self,
        path: str,
        headers: Optional[Dict[str, str]] = None,
        json_data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Tuple[int, Dict[str, Any]]:
        """Make a POST request."""
        return self._make_request("POST", path, headers=headers, json_data=json_data, params=params)
    
    def put(
        self,
        path: str,
        headers: Optional[Dict[str, str]] = None,
        json_data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Tuple[int, Dict[str, Any]]:
        """Make a PUT request."""
        return self._make_request("PUT", path, headers=headers, json_data=json_data, params=params)
    
    def patch(
        self,
        path: str,
        headers: Optional[Dict[str, str]] = None,
        json_data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Tuple[int, Dict[str, Any]]:
        """Make a PATCH request."""
        return self._make_request("PATCH", path, headers=headers, json_data=json_data, params=params)
    
    def delete(
        self,
        path: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict] = None
    ) -> Tuple[int, Dict[str, Any]]:
        """Make a DELETE request."""
        return self._make_request("DELETE", path, headers=headers, params=params)
    
    def get_circuit_state(self) -> Dict[str, Any]:
        """Get current circuit breaker state."""
        return {
            "state": self.circuit.state.value,
            "failure_count": self.circuit.failure_count,
            "last_failure_time": self.circuit.last_failure_time,
            "success_count": getattr(self.circuit, 'success_count', 0)
        }
    
    def close(self):
        """Close the session and cleanup resources."""
        self.session.close()


# Singleton instance for application use
_backend_client: Optional[BackendClient] = None


def get_backend_client() -> BackendClient:
    """Get or create the singleton backend client instance."""
    global _backend_client
    if _backend_client is None:
        _backend_client = BackendClient()
    return _backend_client


def reset_backend_client():
    """Reset the singleton instance (useful for testing)."""
    global _backend_client
    if _backend_client:
        _backend_client.close()
    _backend_client = None
