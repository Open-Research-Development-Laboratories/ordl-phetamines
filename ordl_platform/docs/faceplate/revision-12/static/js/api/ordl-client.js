/**
 * ORDL API Core Client
 * Base HTTP client with interceptors, error handling, auth management, and retry logic
 * @module static/js/api/ordl-client
 */

/**
 * @typedef {Object} ApiConfig
 * @property {string} baseUrl - Base URL for API requests
 * @property {number} [timeout=30000] - Request timeout in milliseconds
 * @property {number} [maxRetries=3] - Maximum number of retry attempts
 * @property {number} [retryDelay=1000] - Initial retry delay in milliseconds
 * @property {number} [rateLimitRequests=100] - Rate limit requests per window
 * @property {number} [rateLimitWindow=60000] - Rate limit window in milliseconds
 */

/**
 * @typedef {Object} RequestOptions
 * @property {string} [method='GET'] - HTTP method
 * @property {Object} [headers] - Additional headers
 * @property {Object} [body] - Request body
 * @property {number} [timeout] - Request timeout override
 * @property {boolean} [skipAuth] - Skip authentication header
 * @property {boolean} [skipRetry] - Skip retry logic
 * @property {boolean} [skipRateLimit] - Skip rate limiting
 * @property {AbortSignal} [signal] - Abort signal for cancellation
 */

/**
 * @typedef {Object} ApiResponse
 * @property {boolean} success - Whether request was successful
 * @property {*} data - Response data
 * @property {number} status - HTTP status code
 * @property {Object} headers - Response headers
 * @property {string|null} error - Error message if failed
 */

/**
 * @typedef {Object} LoadingState
 * @property {boolean} loading - Whether request is in progress
 * @property {number} progress - Loading progress (0-100)
 * @property {string} [message] - Loading message
 */

/**
 * @callback LoadingStateCallback
 * @param {LoadingState} state - Current loading state
 * @returns {void}
 */

/**
 * @callback RequestInterceptor
 * @param {RequestOptions} options - Request options
 * @returns {RequestOptions|Promise<RequestOptions>} - Modified options
 */

/**
 * @callback ResponseInterceptor
 * @param {ApiResponse} response - API response
 * @returns {ApiResponse|Promise<ApiResponse>} - Modified response
 */

/**
 * @callback ErrorInterceptor
 * @param {Error} error - Error object
 * @param {RequestOptions} options - Original request options
 * @returns {Promise<*>} - Recovery value or rethrow
 */

/**
 * API Client class for ORDL platform
 */
class OrdlApiClient {
    /**
     * @param {ApiConfig} config - Client configuration
     */
    constructor(config = {}) {
        this.baseUrl = config.baseUrl || (window.ORDL_API_URL || '/v1');
        this.timeout = config.timeout || 30000;
        this.maxRetries = config.maxRetries || 3;
        this.retryDelay = config.retryDelay || 1000;
        this.rateLimitRequests = config.rateLimitRequests || 100;
        this.rateLimitWindow = config.rateLimitWindow || 60000;

        /** @type {RequestInterceptor[]} */
        this.requestInterceptors = [];
        
        /** @type {ResponseInterceptor[]} */
        this.responseInterceptors = [];
        
        /** @type {ErrorInterceptor[]} */
        this.errorInterceptors = [];

        // Rate limiting state
        this.requestQueue = [];
        this.requestsInWindow = 0;
        this.windowStart = Date.now();

        // Auth token storage
        this.authToken = null;
        this.tokenRefreshPromise = null;

        // Loading state callbacks
        /** @type {Set<LoadingStateCallback>} */
        this.loadingCallbacks = new Set();

        // WebSocket connections
        /** @type {Map<string, WebSocket>} */
        this.wsConnections = new Map();
        
        /** @type {Map<string, Set<Function>>} */
        this.wsListeners = new Map();

        // Initialize auth from storage
        this._initAuth();
    }

    /**
     * Initialize authentication from localStorage
     * @private
     */
    _initAuth() {
        const token = localStorage.getItem('ordl_auth_token');
        if (token) {
            this.authToken = token;
        }
        
        // Set up token refresh on page load if token exists
        if (this.authToken && !this._isTokenValid()) {
            this._refreshToken().catch(() => {
                this.clearAuth();
            });
        }
    }

    /**
     * Check if current token is still valid (not expired)
     * @private
     * @returns {boolean}
     */
    _isTokenValid() {
        try {
            const token = this.getAuthToken();
            if (!token) return false;
            
            const payload = JSON.parse(atob(token.split('.')[1]));
            const exp = payload.exp * 1000; // Convert to ms
            return Date.now() < exp - 60000; // 1 minute buffer
        } catch (e) {
            return false;
        }
    }

    /**
     * Set authentication token
     * @param {string|null} token - JWT token or null to clear
     * @param {Object} [userData] - Additional user data to store
     * @returns {void}
     */
    setAuthToken(token, userData = null) {
        this.authToken = token;
        if (token) {
            localStorage.setItem('ordl_auth_token', token);
            if (userData) {
                localStorage.setItem('ordl_user_data', JSON.stringify(userData));
            }
        } else {
            localStorage.removeItem('ordl_auth_token');
            localStorage.removeItem('ordl_user_data');
            localStorage.removeItem('ordl_refresh_token');
        }
    }

    /**
     * Get current authentication token
     * @returns {string|null}
     */
    getAuthToken() {
        if (!this.authToken) {
            this.authToken = localStorage.getItem('ordl_auth_token');
        }
        return this.authToken;
    }

    /**
     * Get stored user data
     * @returns {Object|null}
     */
    getUserData() {
        try {
            const data = localStorage.getItem('ordl_user_data');
            return data ? JSON.parse(data) : null;
        } catch (e) {
            return null;
        }
    }

    /**
     * Clear all authentication data
     * @returns {void}
     */
    clearAuth() {
        this.authToken = null;
        localStorage.removeItem('ordl_auth_token');
        localStorage.removeItem('ordl_user_data');
        localStorage.removeItem('ordl_refresh_token');
    }

    /**
     * Add request interceptor
     * @param {RequestInterceptor} interceptor
     * @returns {() => void} - Unregister function
     */
    addRequestInterceptor(interceptor) {
        this.requestInterceptors.push(interceptor);
        return () => {
            const idx = this.requestInterceptors.indexOf(interceptor);
            if (idx > -1) this.requestInterceptors.splice(idx, 1);
        };
    }

    /**
     * Add response interceptor
     * @param {ResponseInterceptor} interceptor
     * @returns {() => void} - Unregister function
     */
    addResponseInterceptor(interceptor) {
        this.responseInterceptors.push(interceptor);
        return () => {
            const idx = this.responseInterceptors.indexOf(interceptor);
            if (idx > -1) this.responseInterceptors.splice(idx, 1);
        };
    }

    /**
     * Add error interceptor
     * @param {ErrorInterceptor} interceptor
     * @returns {() => void} - Unregister function
     */
    addErrorInterceptor(interceptor) {
        this.errorInterceptors.push(interceptor);
        return () => {
            const idx = this.errorInterceptors.indexOf(interceptor);
            if (idx > -1) this.errorInterceptors.splice(idx, 1);
        };
    }

    /**
     * Subscribe to loading state changes
     * @param {LoadingStateCallback} callback
     * @returns {() => void} - Unsubscribe function
     */
    onLoadingState(callback) {
        this.loadingCallbacks.add(callback);
        return () => this.loadingCallbacks.delete(callback);
    }

    /**
     * Notify loading state callbacks
     * @param {LoadingState} state
     * @private
     */
    _notifyLoadingState(state) {
        this.loadingCallbacks.forEach(cb => {
            try { cb(state); } catch (e) { console.error('Loading callback error:', e); }
        });
    }

    /**
     * Apply request interceptors
     * @param {RequestOptions} options
     * @returns {Promise<RequestOptions>}
     * @private
     */
    async _applyRequestInterceptors(options) {
        let result = options;
        for (const interceptor of this.requestInterceptors) {
            result = await interceptor(result);
        }
        return result;
    }

    /**
     * Apply response interceptors
     * @param {ApiResponse} response
     * @returns {Promise<ApiResponse>}
     * @private
     */
    async _applyResponseInterceptors(response) {
        let result = response;
        for (const interceptor of this.responseInterceptors) {
            result = await interceptor(result);
        }
        return result;
    }

    /**
     * Apply error interceptors
     * @param {Error} error
     * @param {RequestOptions} options
     * @returns {Promise<*>}
     * @private
     */
    async _applyErrorInterceptors(error, options) {
        for (const interceptor of this.errorInterceptors) {
            try {
                return await interceptor(error, options);
            } catch (e) {
                error = e;
            }
        }
        throw error;
    }

    /**
     * Check and wait for rate limiting
     * @returns {Promise<void>}
     * @private
     */
    async _checkRateLimit() {
        const now = Date.now();
        
        // Reset window if expired
        if (now - this.windowStart >= this.rateLimitWindow) {
            this.requestsInWindow = 0;
            this.windowStart = now;
        }

        // Check if we're at the limit
        if (this.requestsInWindow >= this.rateLimitRequests) {
            const waitTime = this.rateLimitWindow - (now - this.windowStart);
            this._notifyLoadingState({ 
                loading: true, 
                progress: 10, 
                message: `Rate limited, waiting ${Math.round(waitTime/1000)}s...` 
            });
            await this._delay(waitTime);
            return this._checkRateLimit();
        }

        this.requestsInWindow++;
    }

    /**
     * Delay promise
     * @param {number} ms
     * @returns {Promise<void>}
     * @private
     */
    _delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    /**
     * Calculate exponential backoff delay
     * @param {number} attempt - Attempt number (0-based)
     * @returns {number}
     * @private
     */
    _getBackoffDelay(attempt) {
        // Exponential backoff with jitter
        const baseDelay = this.retryDelay * Math.pow(2, attempt);
        const jitter = Math.random() * 0.3 * baseDelay;
        return Math.min(baseDelay + jitter, 30000); // Max 30s
    }

    /**
     * Check if error is retryable
     * @param {Error} error
     * @param {number} status
     * @returns {boolean}
     * @private
     */
    _isRetryableError(error, status) {
        // Retry on network errors
        if (!status) return true;
        
        // Retry on specific status codes
        const retryableStatuses = [408, 429, 500, 502, 503, 504];
        return retryableStatuses.includes(status);
    }

    /**
     * Make HTTP request with fetch
     * @param {string} endpoint - API endpoint (relative to baseUrl)
     * @param {RequestOptions} [options={}]
     * @returns {Promise<ApiResponse>}
     */
    async request(endpoint, options = {}) {
        // Apply request interceptors
        const opts = await this._applyRequestInterceptors(options);

        // Check rate limiting
        if (!opts.skipRateLimit) {
            await this._checkRateLimit();
        }

        // Notify loading start
        this._notifyLoadingState({ loading: true, progress: 0, message: 'Starting request...' });

        const url = `${this.baseUrl}${endpoint.startsWith('/') ? endpoint : '/' + endpoint}`;
        
        // Build headers
        const headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
            ...opts.headers
        };

        // Add auth token
        if (!opts.skipAuth) {
            const token = this.getAuthToken();
            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }
        }

        // Prepare fetch options
        const fetchOptions = {
            method: opts.method || 'GET',
            headers,
            signal: opts.signal
        };

        // Add body for non-GET requests
        if (opts.body && opts.method !== 'GET') {
            fetchOptions.body = typeof opts.body === 'string' 
                ? opts.body 
                : JSON.stringify(opts.body);
        }

        // Execute request with timeout and retry logic
        let lastError;
        const maxAttempts = opts.skipRetry ? 1 : this.maxRetries + 1;

        for (let attempt = 0; attempt < maxAttempts; attempt++) {
            try {
                this._notifyLoadingState({ 
                    loading: true, 
                    progress: (attempt / maxAttempts) * 50,
                    message: attempt > 0 ? `Retry attempt ${attempt}...` : 'Sending request...'
                });

                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), opts.timeout || this.timeout);

                // Combine signals if external signal provided
                if (opts.signal) {
                    opts.signal.addEventListener('abort', () => controller.abort());
                }

                fetchOptions.signal = controller.signal;

                const response = await fetch(url, fetchOptions);
                clearTimeout(timeoutId);

                // Update loading progress
                this._notifyLoadingState({ loading: true, progress: 75, message: 'Processing response...' });

                // Parse response
                let data = null;
                const contentType = response.headers.get('content-type');
                if (contentType && contentType.includes('application/json')) {
                    data = await response.json();
                } else if (response.status !== 204) {
                    data = await response.text();
                }

                /** @type {ApiResponse} */
                const apiResponse = {
                    success: response.ok,
                    data,
                    status: response.status,
                    headers: Object.fromEntries(response.headers.entries()),
                    error: response.ok ? null : (data?.error || data?.message || response.statusText)
                };

                // Handle HTTP errors
                if (!response.ok) {
                    // Try to refresh token on 401
                    if (response.status === 401 && !opts.skipAuth) {
                        try {
                            await this._refreshToken();
                            // Retry with new token
                            continue;
                        } catch (refreshError) {
                            // Fall through to error handling
                        }
                    }

                    // Check if retryable
                    if (this._isRetryableError(new Error(apiResponse.error), response.status) && attempt < maxAttempts - 1) {
                        const delay = this._getBackoffDelay(attempt);
                        this._notifyLoadingState({ 
                            loading: true, 
                            progress: 25 + (attempt / maxAttempts) * 25,
                            message: `Waiting ${Math.round(delay/1000)}s before retry...`
                        });
                        await this._delay(delay);
                        continue;
                    }

                    throw new OrdlApiError(apiResponse.error, response.status, apiResponse);
                }

                // Apply response interceptors
                const finalResponse = await this._applyResponseInterceptors(apiResponse);
                
                this._notifyLoadingState({ loading: false, progress: 100, message: 'Complete' });
                return finalResponse;

            } catch (error) {
                lastError = error;

                // Handle abort/timeout
                if (error.name === 'AbortError') {
                    if (opts.signal?.aborted) {
                        throw new OrdlApiError('Request cancelled', 0, null);
                    }
                    throw new OrdlApiError('Request timeout', 408, null);
                }

                // Check if retryable
                const status = error instanceof OrdlApiError ? error.status : 0;
                if (this._isRetryableError(error, status) && attempt < maxAttempts - 1 && !opts.skipRetry) {
                    const delay = this._getBackoffDelay(attempt);
                    await this._delay(delay);
                    continue;
                }

                // Try error interceptors
                try {
                    return await this._applyErrorInterceptors(error, opts);
                } catch (interceptError) {
                    lastError = interceptError;
                    break;
                }
            }
        }

        this._notifyLoadingState({ loading: false, progress: 0, message: 'Error' });
        throw lastError;
    }

    /**
     * Refresh authentication token
     * @returns {Promise<string>}
     * @private
     */
    async _refreshToken() {
        if (this.tokenRefreshPromise) {
            return this.tokenRefreshPromise;
        }

        this.tokenRefreshPromise = (async () => {
            try {
                const response = await fetch(`${this.baseUrl}/auth/refresh`, {
                    method: 'POST',
                    credentials: 'include',
                    headers: { 'Content-Type': 'application/json' }
                });

                if (!response.ok) {
                    throw new Error('Token refresh failed');
                }

                const data = await response.json();
                this.setAuthToken(data.token, data.user);
                return data.token;
            } finally {
                this.tokenRefreshPromise = null;
            }
        })();

        return this.tokenRefreshPromise;
    }

    /**
     * Authenticate user with credentials
     * @param {string} username - Username or email
     * @param {string} password - Password
     * @returns {Promise<Object>} - Auth response with token and user data
     */
    async login(username, password) {
        const response = await this.request('/auth/login', {
            method: 'POST',
            body: { username, password },
            skipAuth: true
        });

        if (response.success && response.data.token) {
            this.setAuthToken(response.data.token, response.data.user);
        }

        return response.data;
    }

    /**
     * Logout user and clear auth
     * @returns {Promise<void>}
     */
    async logout() {
        try {
            await this.request('/auth/logout', { method: 'POST' });
        } finally {
            this.clearAuth();
        }
    }

    /**
     * GET request shorthand
     * @param {string} endpoint
     * @param {RequestOptions} [options]
     * @returns {Promise<ApiResponse>}
     */
    get(endpoint, options = {}) {
        return this.request(endpoint, { ...options, method: 'GET' });
    }

    /**
     * POST request shorthand
     * @param {string} endpoint
     * @param {Object} body
     * @param {RequestOptions} [options]
     * @returns {Promise<ApiResponse>}
     */
    post(endpoint, body, options = {}) {
        return this.request(endpoint, { ...options, method: 'POST', body });
    }

    /**
     * PUT request shorthand
     * @param {string} endpoint
     * @param {Object} body
     * @param {RequestOptions} [options]
     * @returns {Promise<ApiResponse>}
     */
    put(endpoint, body, options = {}) {
        return this.request(endpoint, { ...options, method: 'PUT', body });
    }

    /**
     * PATCH request shorthand
     * @param {string} endpoint
     * @param {Object} body
     * @param {RequestOptions} [options]
     * @returns {Promise<ApiResponse>}
     */
    patch(endpoint, body, options = {}) {
        return this.request(endpoint, { ...options, method: 'PATCH', body });
    }

    /**
     * DELETE request shorthand
     * @param {string} endpoint
     * @param {RequestOptions} [options]
     * @returns {Promise<ApiResponse>}
     */
    delete(endpoint, options = {}) {
        return this.request(endpoint, { ...options, method: 'DELETE' });
    }

    // =================================================================
    // WebSocket Methods
    // =================================================================

    /**
     * Connect to WebSocket endpoint
     * @param {string} endpoint - WebSocket endpoint
     * @param {Object} [options] - Connection options
     * @returns {WebSocket}
     */
    connectWebSocket(endpoint, options = {}) {
        const wsUrl = this._getWebSocketUrl(endpoint);
        
        if (this.wsConnections.has(wsUrl)) {
            return this.wsConnections.get(wsUrl);
        }

        const ws = new WebSocket(wsUrl);
        
        ws.onopen = () => {
            console.log(`WebSocket connected: ${endpoint}`);
            if (options.onOpen) options.onOpen();
        };

        ws.onclose = () => {
            console.log(`WebSocket disconnected: ${endpoint}`);
            this.wsConnections.delete(wsUrl);
            if (options.onClose) options.onClose();
            
            // Auto-reconnect if enabled
            if (options.autoReconnect !== false) {
                setTimeout(() => {
                    this.connectWebSocket(endpoint, options);
                }, options.reconnectDelay || 3000);
            }
        };

        ws.onerror = (error) => {
            console.error(`WebSocket error: ${endpoint}`, error);
            if (options.onError) options.onError(error);
        };

        ws.onmessage = (event) => {
            let data;
            try {
                data = JSON.parse(event.data);
            } catch (e) {
                data = event.data;
            }

            // Notify listeners for this endpoint
            const listeners = this.wsListeners.get(wsUrl) || new Set();
            listeners.forEach(cb => {
                try { cb(data); } catch (e) { console.error('WebSocket listener error:', e); }
            });

            if (options.onMessage) options.onMessage(data);
        };

        this.wsConnections.set(wsUrl, ws);
        return ws;
    }

    /**
     * Subscribe to WebSocket messages
     * @param {string} endpoint - WebSocket endpoint
     * @param {Function} callback - Message handler
     * @returns {() => void} - Unsubscribe function
     */
    subscribeWebSocket(endpoint, callback) {
        const wsUrl = this._getWebSocketUrl(endpoint);
        
        if (!this.wsListeners.has(wsUrl)) {
            this.wsListeners.set(wsUrl, new Set());
        }
        
        const listeners = this.wsListeners.get(wsUrl);
        listeners.add(callback);

        // Ensure connection exists
        if (!this.wsConnections.has(wsUrl)) {
            this.connectWebSocket(endpoint);
        }

        return () => {
            listeners.delete(callback);
            if (listeners.size === 0) {
                this.disconnectWebSocket(endpoint);
            }
        };
    }

    /**
     * Send message via WebSocket
     * @param {string} endpoint - WebSocket endpoint
     * @param {*} data - Message data
     */
    sendWebSocket(endpoint, data) {
        const wsUrl = this._getWebSocketUrl(endpoint);
        const ws = this.wsConnections.get(wsUrl);
        
        if (ws && ws.readyState === WebSocket.OPEN) {
            const message = typeof data === 'string' ? data : JSON.stringify(data);
            ws.send(message);
        } else {
            console.warn(`WebSocket not connected: ${endpoint}`);
        }
    }

    /**
     * Disconnect WebSocket
     * @param {string} endpoint - WebSocket endpoint
     */
    disconnectWebSocket(endpoint) {
        const wsUrl = this._getWebSocketUrl(endpoint);
        const ws = this.wsConnections.get(wsUrl);
        
        if (ws) {
            ws.close();
            this.wsConnections.delete(wsUrl);
            this.wsListeners.delete(wsUrl);
        }
    }

    /**
     * Get WebSocket URL from endpoint
     * @param {string} endpoint
     * @returns {string}
     * @private
     */
    _getWebSocketUrl(endpoint) {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const basePath = this.baseUrl.replace(/^https?:/, '').replace(/^http?:/, '');
        return `${protocol}//${window.location.host}${basePath}${endpoint}`;
    }
}

/**
 * Custom API Error class
 */
class OrdlApiError extends Error {
    /**
     * @param {string} message
     * @param {number} status
     * @param {ApiResponse|null} response
     */
    constructor(message, status, response) {
        super(message);
        this.name = 'OrdlApiError';
        this.status = status;
        this.response = response;
    }

    /**
     * Check if error is client error (4xx)
     * @returns {boolean}
     */
    isClientError() {
        return this.status >= 400 && this.status < 500;
    }

    /**
     * Check if error is server error (5xx)
     * @returns {boolean}
     */
    isServerError() {
        return this.status >= 500 && this.status < 600;
    }

    /**
     * Check if error is network error
     * @returns {boolean}
     */
    isNetworkError() {
        return this.status === 0;
    }

    /**
     * Check if error is authentication error
     * @returns {boolean}
     */
    isAuthError() {
        return this.status === 401 || this.status === 403;
    }

    /**
     * Get user-friendly error message
     * @returns {string}
     */
    getUserMessage() {
        if (this.isNetworkError()) {
            return 'Network connection failed. Please check your internet connection.';
        }
        if (this.status === 401) {
            return 'Authentication failed. Please log in again.';
        }
        if (this.status === 403) {
            return 'You do not have permission to perform this action.';
        }
        if (this.status === 404) {
            return 'The requested resource was not found.';
        }
        if (this.status === 429) {
            return 'Too many requests. Please try again later.';
        }
        if (this.isServerError()) {
            return 'Server error occurred. Please try again later.';
        }
        return this.message || 'An unexpected error occurred.';
    }
}

// Create singleton instance
const ordlClient = new OrdlApiClient();

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { OrdlApiClient, OrdlApiError, ordlClient };
}
