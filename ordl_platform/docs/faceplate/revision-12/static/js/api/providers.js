/**
 * ORDL Providers API Module
 * AI service provider management for authentication, inference, and integrations
 * @module static/js/api/providers
 */

/**
 * @typedef {Object} Provider
 * @property {string} id - Provider unique identifier
 * @property {string} name - Provider name
 * @property {string} [alias] - Provider alias/short name
 * @property {string} providerType - Provider type (openai, anthropic, custom, oauth, saml)
 * @property {number} priority - Failover priority (lower = higher priority)
 * @property {string} status - Provider status (healthy, degraded, unhealthy, unknown)
 * @property {string} authStatus - Authentication status (valid, invalid, unknown)
 * @property {number} [latencyMs] - Last measured latency
 * @property {number} rps - Requests per second limit
 * @property {string} [region] - Provider region
 * @property {string} [lastCheck] - Last health check timestamp
 * @property {ProviderConfig} config - Provider configuration
 * @property {string} createdAt - Creation timestamp
 * @property {string} updatedAt - Last update timestamp
 */

/**
 * @typedef {Object} ProviderConfig
 * @property {string} [apiKeyRef] - API key reference (vault path)
 * @property {string} [baseUrl] - Base API URL
 * @property {number} [timeout] - Request timeout (seconds)
 * @property {string} [retryPolicy] - Retry policy name
 * @property {Object} [custom] - Custom configuration
 */

/**
 * @typedef {Object} ProviderTestResult
 * @property {string} providerId - Provider ID
 * @property {string} testType - Test type (connectivity, auth, inference)
 * @property {string} status - Test status (passed, failed)
 * @property {number} latencyMs - Test latency
 * @property {string} timestamp - Test timestamp
 * @property {Object} details - Test details
 */

/**
 * @typedef {Object} ProbeConfig
 * @property {number} interval - Probe interval (seconds)
 * @property {number} timeout - Probe timeout (seconds)
 * @property {number} retries - Number of retries
 * @property {string[]} testTypes - Types of tests to run
 */

/**
 * @typedef {Object} PaginationParams
 * @property {number} [page=1] - Page number
 * @property {number} [limit=20] - Items per page
 * @property {string} [sortBy] - Sort field
 * @property {string} [sortOrder='asc'] - Sort order (asc, desc)
 */

/**
 * @typedef {Object} PaginatedResponse
 * @property {Array} items - Items in current page
 * @property {number} total - Total number of items
 * @property {number} page - Current page
 * @property {number} pages - Total pages
 * @property {boolean} hasNext - Has next page
 * @property {boolean} hasPrev - Has previous page
 */

/**
 * @callback LoadingStateCallback
 * @param {import('./ordl-client.js').LoadingState} state - Loading state
 * @returns {void}
 */

/**
 * @callback ProviderEventCallback
 * @param {Object} event - Real-time event data
 * @returns {void}
 */

/**
 * Providers API module
 */
class ProvidersApi {
    /**
     * @param {import('./ordl-client.js').OrdlApiClient} [client] - API client instance
     */
    constructor(client) {
        this.client = client || (typeof ordlClient !== 'undefined' ? ordlClient : null);
        if (!this.client) {
            throw new Error('OrdlApiClient instance required. Ensure ordl-client.js is loaded first.');
        }
    }

    /**
     * Get paginated list of providers
     * @param {PaginationParams & {type?: string, status?: string, region?: string}} [params]
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<PaginatedResponse<Provider>>}
     */
    async getProviders(params = {}, onLoading) {
        const { page = 1, limit = 20, sortBy, sortOrder, type, status, region } = params;
        
        const query = new URLSearchParams({ page: String(page), limit: String(limit) });
        if (sortBy) query.append('sort_by', sortBy);
        if (sortOrder) query.append('sort_order', sortOrder);
        if (type) query.append('type', type);
        if (status) query.append('status', status);
        if (region) query.append('region', region);

        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.get(`/providers?${query}`);
            return this._formatPaginatedResponse(response.data, page);
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Get single provider by ID or alias
     * @param {string} providerId - Provider ID or alias
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<Provider>}
     */
    async getProvider(providerId, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.get(`/providers/${providerId}`);
            return this._formatProvider(response.data);
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Create new provider
     * @param {Object} data - Provider data
     * @param {string} data.name - Provider name
     * @param {string} [data.alias] - Provider alias
     * @param {string} data.providerType - Provider type
     * @param {number} [data.priority=1] - Priority level
     * @param {ProviderConfig} [data.config] - Provider configuration
     * @param {number} [data.rps=100] - Requests per second limit
     * @param {string} [data.region] - Provider region
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<Provider>}
     */
    async createProvider(data, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.post('/providers', data);
            return this._formatProvider(response.data);
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Update provider
     * @param {string} providerId - Provider ID or alias
     * @param {Partial<Provider>} data - Update data
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<Provider>}
     */
    async updateProvider(providerId, data, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.put(`/providers/${providerId}`, data);
            return this._formatProvider(response.data);
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Delete provider
     * @param {string} providerId - Provider ID or alias
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<void>}
     */
    async deleteProvider(providerId, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            await this.client.delete(`/providers/${providerId}`);
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Update provider configuration
     * @param {string} providerId - Provider ID or alias
     * @param {Object} config - Configuration updates
     * @param {string} [config.apiKeyRef] - API key reference
     * @param {string} [config.baseUrl] - Base URL
     * @param {number} [config.timeout] - Timeout
     * @param {string} [config.retryPolicy] - Retry policy
     * @param {number} [config.priority] - Priority
     * @param {number} [config.rps] - RPS limit
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<Object>}
     */
    async updateConfig(providerId, config, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.put(`/providers/${providerId}/config`, config);
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Test provider connectivity and authentication
     * @param {string} providerId - Provider ID or alias
     * @param {Object} [options] - Test options
     * @param {string} [options.testType='connectivity'] - Test type
     * @param {number} [options.timeout=30] - Test timeout
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<ProviderTestResult>}
     */
    async testProvider(providerId, options = {}, onLoading) {
        const { testType = 'connectivity', timeout = 30 } = options;

        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.post(`/providers/${providerId}/test`, {
                test_type: testType,
                timeout
            });
            return this._formatTestResult(response.data);
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Test multiple providers
     * @param {string[]} providerIds - Provider IDs to test
     * @param {Object} [options] - Test options
     * @param {string} [options.testType='connectivity'] - Test type
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<ProviderTestResult[]>}
     */
    async testProviders(providerIds, options = {}, onLoading) {
        const { testType = 'connectivity' } = options;

        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.post('/providers/test/batch', {
                provider_ids: providerIds,
                test_type: testType
            });
            return (response.data.results || []).map(r => this._formatTestResult(r));
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Update provider priorities (batch)
     * @param {Object[]} priorityUpdates - Array of {id, priority} objects
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<{results: Object[], total: number, successCount: number}>}
     */
    async updatePriorities(priorityUpdates, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.put('/providers/priority', {
                providers: priorityUpdates
            });
            return {
                results: response.data.results || [],
                total: response.data.total,
                successCount: response.data.success_count || response.data.successCount
            };
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Update probe configuration
     * @param {ProbeConfig} probeConfig - Probe configuration
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<{probeConfig: ProbeConfig, updatedAt: string}>}
     */
    async updateProbes(probeConfig, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.put('/providers/probes', {
                probe_config: probeConfig
            });
            return {
                probeConfig: response.data.probe_config || response.data.probeConfig,
                updatedAt: response.data.updated_at || response.data.updatedAt
            };
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Get probe configuration
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<ProbeConfig>}
     */
    async getProbeConfig(onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.get('/providers/probes');
            return response.data.probe_config || response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Get provider health status
     * @param {string} providerId - Provider ID or alias
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<{status: string, latencyMs: number, lastCheck: string, details: Object}>}
     */
    async getHealth(providerId, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.get(`/providers/${providerId}/health`);
            return {
                status: response.data.status,
                latencyMs: response.data.latency_ms || response.data.latencyMs,
                lastCheck: response.data.last_check || response.data.lastCheck,
                details: response.data.details || {}
            };
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Get health status for all providers
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<Object[]>}
     */
    async getAllHealth(onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.get('/providers/health');
            return response.data.providers || response.data || [];
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Enable provider
     * @param {string} providerId - Provider ID or alias
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<Provider>}
     */
    async enableProvider(providerId, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.post(`/providers/${providerId}/enable`);
            return this._formatProvider(response.data);
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Disable provider
     * @param {string} providerId - Provider ID or alias
     * @param {Object} [options] - Disable options
     * @param {string} [options.reason] - Disable reason
     * @param {boolean} [options.drainConnections=false] - Drain connections first
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<Provider>}
     */
    async disableProvider(providerId, options = {}, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.post(`/providers/${providerId}/disable`, options);
            return this._formatProvider(response.data);
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Clone provider configuration
     * @param {string} providerId - Provider ID to clone
     * @param {Object} options - Clone options
     * @param {string} options.newName - Name for cloned provider
     * @param {string} [options.newAlias] - Alias for cloned provider
     * @param {boolean} [options.includeCredentials=false] - Include credentials
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<Provider>}
     */
    async cloneProvider(providerId, options, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.post(`/providers/${providerId}/clone`, options);
            return this._formatProvider(response.data);
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Get provider usage statistics
     * @param {string} providerId - Provider ID or alias
     * @param {Object} [params] - Query params
     * @param {string} [params.from] - Start date
     * @param {string} [params.to] - End date
     * @param {string} [params.granularity='day'] - Granularity (hour, day, week)
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<Object>}
     */
    async getUsageStats(providerId, params = {}, onLoading) {
        const { from, to, granularity = 'day' } = params;
        const query = new URLSearchParams({ granularity });
        if (from) query.append('from', from);
        if (to) query.append('to', to);

        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.get(`/providers/${providerId}/usage?${query}`);
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Get provider logs
     * @param {string} providerId - Provider ID or alias
     * @param {PaginationParams} [params]
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<PaginatedResponse>}
     */
    async getProviderLogs(providerId, params = {}, onLoading) {
        const { page = 1, limit = 20 } = params;
        const query = new URLSearchParams({ page: String(page), limit: String(limit) });

        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.get(`/providers/${providerId}/logs?${query}`);
            return this._formatPaginatedResponse(response.data, page);
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Rotate provider credentials
     * @param {string} providerId - Provider ID or alias
     * @param {Object} [options] - Rotation options
     * @param {boolean} [options.gracePeriod=true] - Allow grace period
     * @param {number} [options.gracePeriodMinutes=5] - Grace period duration
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<{rotated: boolean, previousKeyValidUntil: string}>}
     */
    async rotateCredentials(providerId, options = {}, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.post(`/providers/${providerId}/rotate`, options);
            return {
                rotated: response.data.rotated,
                previousKeyValidUntil: response.data.previous_key_valid_until || 
                                       response.data.previousKeyValidUntil
            };
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Get available provider types
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<Array>}
     */
    async getProviderTypes(onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.get('/providers/types');
            return response.data.types || response.data || [];
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Get provider type schema
     * @param {string} type - Provider type
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<Object>}
     */
    async getTypeSchema(type, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.get(`/providers/types/${type}/schema`);
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Validate provider configuration
     * @param {string} type - Provider type
     * @param {Object} config - Configuration to validate
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<{valid: boolean, errors?: string[]}>}
     */
    async validateConfig(type, config, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.post('/providers/validate', {
                type,
                config
            });
            return {
                valid: response.data.valid,
                errors: response.data.errors
            };
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Export provider configurations
     * @param {Object} [options] - Export options
     * @param {string[]} [options.providerIds] - Specific providers to export
     * @param {string} [options.format='json'] - Export format
     * @param {boolean} [options.includeCredentials=false] - Include credentials
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<{data: string, format: string}>}
     */
    async exportProviders(options = {}, onLoading) {
        const { providerIds, format = 'json', includeCredentials = false } = options;

        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.post('/providers/export', {
                provider_ids: providerIds,
                format,
                include_credentials: includeCredentials
            });
            return {
                data: response.data.data,
                format: response.data.format
            };
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Import provider configurations
     * @param {string|Object} data - Import data
     * @param {Object} [options] - Import options
     * @param {boolean} [options.dryRun=false] - Validate without importing
     * @param {boolean} [options.skipExisting=false] - Skip existing providers
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<{imported: number, skipped: number, errors: string[]}>}
     */
    async importProviders(data, options = {}, onLoading) {
        const { dryRun = false, skipExisting = false } = options;

        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.post('/providers/import', {
                data,
                dry_run: dryRun,
                skip_existing: skipExisting
            });
            return {
                imported: response.data.imported,
                skipped: response.data.skipped,
                errors: response.data.errors || []
            };
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Get provider failover chain
     * @param {Object} [params] - Query params
     * @param {string} [params.type] - Filter by type
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<Provider[]>}
     */
    async getFailoverChain(params = {}, onLoading) {
        const { type } = params;
        const query = new URLSearchParams();
        if (type) query.append('type', type);

        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.get(`/providers/failover?${query}`);
            return (response.data.providers || response.data || [])
                .map(p => this._formatProvider(p));
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Trigger manual failover
     * @param {string} fromProviderId - Current primary provider
     * @param {string} [toProviderId] - Target provider (optional, uses next in chain)
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<{success: boolean, newPrimary: string}>}
     */
    async triggerFailover(fromProviderId, toProviderId = null, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const body = { from_provider_id: fromProviderId };
            if (toProviderId) body.to_provider_id = toProviderId;

            const response = await this.client.post('/providers/failover', body);
            return {
                success: response.data.success,
                newPrimary: response.data.new_primary || response.data.newPrimary
            };
        } finally {
            if (unsub) unsub();
        }
    }

    // =================================================================
    // Real-time Updates
    // =================================================================

    /**
     * Subscribe to provider updates
     * @param {ProviderEventCallback} callback - Event handler
     * @returns {() => void} - Unsubscribe function
     */
    subscribeToUpdates(callback) {
        return this.client.subscribeWebSocket('/ws/providers', callback);
    }

    /**
     * Subscribe to specific provider updates
     * @param {string} providerId - Provider ID
     * @param {ProviderEventCallback} callback - Event handler
     * @returns {() => void} - Unsubscribe function
     */
    subscribeToProviderUpdates(providerId, callback) {
        return this.client.subscribeWebSocket(`/ws/providers/${providerId}`, callback);
    }

    /**
     * Subscribe to health check updates
     * @param {ProviderEventCallback} callback - Event handler
     * @returns {() => void} - Unsubscribe function
     */
    subscribeToHealthUpdates(callback) {
        return this.client.subscribeWebSocket('/ws/providers/health', callback);
    }

    // =================================================================
    // Helper Methods
    // =================================================================

    /**
     * Format API response to standard paginated format
     * @param {*} data - API response data
     * @param {number} page - Current page
     * @returns {PaginatedResponse}
     * @private
     */
    _formatPaginatedResponse(data, page) {
        if (Array.isArray(data)) {
            return {
                items: data.map(p => this._formatProvider(p)),
                total: data.length,
                page: page,
                pages: 1,
                hasNext: false,
                hasPrev: page > 1
            };
        }
        
        const items = data.items || data.data || [];
        return {
            items: items.map(p => this._formatProvider(p)),
            total: data.total || 0,
            page: data.page || page,
            pages: data.pages || Math.ceil((data.total || 0) / 20),
            hasNext: data.has_next || data.hasNext || false,
            hasPrev: data.has_prev || data.hasPrev || page > 1
        };
    }

    /**
     * Format provider data
     * @param {*} data - API provider data
     * @returns {Provider}
     * @private
     */
    _formatProvider(data) {
        return {
            id: data.id,
            name: data.name,
            alias: data.alias,
            providerType: data.provider_type || data.providerType,
            priority: data.priority || 1,
            status: data.status || 'unknown',
            authStatus: data.auth_status || data.authStatus || 'unknown',
            latencyMs: data.latency_ms || data.latencyMs,
            rps: data.rps || 100,
            region: data.region,
            lastCheck: data.last_check || data.lastCheck,
            config: this._formatConfig(data.config || {}),
            createdAt: data.created_at || data.createdAt,
            updatedAt: data.updated_at || data.updatedAt,
            ...data
        };
    }

    /**
     * Format provider config
     * @param {*} config - API config data
     * @returns {ProviderConfig}
     * @private
     */
    _formatConfig(config) {
        return {
            apiKeyRef: config.api_key_ref || config.apiKeyRef,
            baseUrl: config.base_url || config.baseUrl,
            timeout: config.timeout,
            retryPolicy: config.retry_policy || config.retryPolicy,
            custom: config.custom || {}
        };
    }

    /**
     * Format test result data
     * @param {*} data - API test result data
     * @returns {ProviderTestResult}
     * @private
     */
    _formatTestResult(data) {
        return {
            providerId: data.provider_id || data.providerId,
            testType: data.test_type || data.testType,
            status: data.status,
            latencyMs: data.latency_ms || data.latencyMs,
            timestamp: data.timestamp,
            details: data.details || {}
        };
    }
}

// Create singleton instance
const providersApi = typeof ordlClient !== 'undefined' ? new ProvidersApi(ordlClient) : null;

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { ProvidersApi, providersApi };
}
