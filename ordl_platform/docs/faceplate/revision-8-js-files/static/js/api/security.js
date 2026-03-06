/**
 * ORDL Security API Module
 * Audit, extensions, and providers management
 * @module static/js/api/security
 */

/**
 * @typedef {Object} Provider
 * @property {string} id - Provider ID
 * @property {string} name - Provider name
 * @property {string} type - Provider type (openai, anthropic, azure, aws, google, cohere)
 * @property {number} priority - Failover priority
 * @property {string} status - Health status
 * @property {string} auth - Auth status
 * @property {number} latency - Current latency (ms)
 * @property {number} rps - Requests per second
 * @property {string} region - Region
 * @property {string} lastCheck - Last health check
 */

/**
 * @typedef {Object} Extension
 * @property {string} id - Extension ID
 * @property {string} name - Extension name
 * @property {string} type - Type (plugin, skill, mcp)
 * @property {string} version - Version
 * @property {string} author - Author
 * @property {string} signature - Signature status
 * @property {string} status - Extension status
 * @property {string} updated - Last updated
 */

/**
 * @typedef {Object} AuditEvent
 * @property {string} timestamp - Event timestamp
 * @property {string} severity - Severity level
 * @property {string} category - Event category
 * @property {string} actor - Actor ID
 * @property {string} action - Action performed
 * @property {string} resource - Resource ID
 * @property {string} details - Event details
 */

/**
 * @typedef {Object} ExportJob
 * @property {string} id - Job ID
 * @property {string} start - Start date
 * @property {string} end - End date
 * @property {string} filters - Applied filters
 * @property {number} events - Event count
 * @property {string} size - Size string
 * @property {string} status - Job status
 * @property {string} created - Creation timestamp
 */

/**
 * @typedef {Object} EvidencePackage
 * @property {string} id - Package ID
 * @property {string} name - Package name
 * @property {string} case - Case ID
 * @property {number} events - Event count
 * @property {string} size - Size string
 * @property {string} created - Creation date
 * @property {string} expires - Expiration date
 * @property {string} custodian - Custodian
 */

/**
 * @typedef {Object} HealthProbe
 * @property {string} id - Probe ID
 * @property {string} providerId - Provider ID
 * @property {string} type - Probe type
 * @property {string} endpoint - Probe endpoint
 * @property {number} interval - Check interval
 * @property {number} timeout - Timeout
 * @property {boolean} enabled - Is enabled
 */

/**
 * @typedef {Object} PaginationParams
 * @property {number} [page=1] - Page number
 * @property {number} [limit=20] - Items per page
 * @property {string} [sortBy] - Sort field
 * @property {string} [sortOrder='asc'] - Sort order
 */

/**
 * @typedef {Object} PaginatedResponse
 * @property {Array} items - Items
 * @property {number} total - Total count
 * @property {number} page - Current page
 * @property {number} pages - Total pages
 * @property {boolean} hasNext - Has next page
 * @property {boolean} hasPrev - Has previous page
 */

/**
 * @callback LoadingStateCallback
 * @param {import('./client.js').LoadingState} state - Loading state
 * @returns {void}
 */

/**
 * Security API module
 */
class SecurityApi {
    constructor(client) {
        this.client = client || (typeof apiClient !== 'undefined' ? apiClient : null);
        if (!this.client) {
            throw new Error('ApiClient instance required. Ensure client.js is loaded first.');
        }
    }

    // =========================================================================
    // PROVIDERS
    // =========================================================================

    async getProviders(params = {}, onLoading) {
        const { page = 1, limit = 20, status, type } = params;
        const query = new URLSearchParams({ page: String(page), limit: String(limit) });
        if (status) query.append('status', status);
        if (type) query.append('type', type);

        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.get(`/v1/providers?${query}`);
            return {
                items: response.data.items || [],
                total: response.data.total || 0,
                page: response.data.page || page,
                pages: response.data.pages || 1,
                hasNext: response.data.has_next || false,
                hasPrev: response.data.has_prev || false
            };
        } finally {
            if (unsub) unsub();
        }
    }

    async getProvider(id, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.get(`/v1/providers/${id}`);
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    async createProvider(data, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.post('/v1/providers', data);
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    async updateProvider(id, data, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.patch(`/v1/providers/${id}`, data);
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    async deleteProvider(id, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            await this.client.delete(`/v1/providers/${id}`);
        } finally {
            if (unsub) unsub();
        }
    }

    async testProvider(id, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.post(`/v1/providers/${id}/test`);
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    async getProviderLogs(id, params = {}, onLoading) {
        const { tail = 100 } = params;
        const query = new URLSearchParams({ tail: String(tail) });

        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.get(`/v1/providers/${id}/logs?${query}`);
            return response.data || [];
        } finally {
            if (unsub) unsub();
        }
    }

    async forceFailover(fromProviderId, toProviderId, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.post('/v1/providers/failover', {
                from: fromProviderId,
                to: toProviderId
            });
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    async getFailoverPriority(onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.get('/v1/providers/priority');
            return response.data || [];
        } finally {
            if (unsub) unsub();
        }
    }

    async updateFailoverPriority(providerIds, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.patch('/v1/providers/priority', { order: providerIds });
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    async getHealthProbes(providerId, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.get(`/v1/providers/${providerId}/probes`);
            return response.data || [];
        } finally {
            if (unsub) unsub();
        }
    }

    async createHealthProbe(providerId, data, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.post(`/v1/providers/${providerId}/probes`, data);
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    async updateHealthProbe(providerId, probeId, data, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.patch(`/v1/providers/${providerId}/probes/${probeId}`, data);
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    async deleteHealthProbe(providerId, probeId, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            await this.client.delete(`/v1/providers/${providerId}/probes/${probeId}`);
        } finally {
            if (unsub) unsub();
        }
    }

    // =========================================================================
    // EXTENSIONS
    // =========================================================================

    async getExtensions(params = {}, onLoading) {
        const { page = 1, limit = 20, type, status, signature } = params;
        const query = new URLSearchParams({ page: String(page), limit: String(limit) });
        if (type) query.append('type', type);
        if (status) query.append('status', status);
        if (signature) query.append('signature', signature);

        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.get(`/v1/extensions?${query}`);
            return {
                items: response.data.items || [],
                total: response.data.total || 0,
                page: response.data.page || page,
                pages: response.data.pages || 1,
                hasNext: response.data.has_next || false,
                hasPrev: response.data.has_prev || false
            };
        } finally {
            if (unsub) unsub();
        }
    }

    async getExtension(id, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.get(`/v1/extensions/${id}`);
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    async registerExtension(data, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.post('/v1/extensions', data);
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    async updateExtension(id, data, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.patch(`/v1/extensions/${id}`, data);
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    async deleteExtension(id, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            await this.client.delete(`/v1/extensions/${id}`);
        } finally {
            if (unsub) unsub();
        }
    }

    async verifyExtension(id, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.post(`/v1/extensions/${id}/verify`);
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    async verifyAllExtensions(onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.post('/v1/extensions/verify-all');
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    async revokeExtension(id, reason, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.post(`/v1/extensions/${id}/revoke`, { reason });
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    async emergencyRevokeAll(reason, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.post('/v1/extensions/emergency-revoke', { reason });
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    async getSignatureLog(extensionId, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.get(`/v1/extensions/${extensionId}/signature-log`);
            return response.data || [];
        } finally {
            if (unsub) unsub();
        }
    }

    async getExtensionTypes(onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.get('/v1/extensions/types');
            return response.data || [];
        } finally {
            if (unsub) unsub();
        }
    }

    // =========================================================================
    // AUDIT (Additional methods beyond audit.js)
    // =========================================================================

    async getAuditEvents(params = {}, onLoading) {
        const { page = 1, limit = 50, severity, category, startDate, endDate } = params;
        const query = new URLSearchParams({ page: String(page), limit: String(limit) });
        if (severity) query.append('severity', severity);
        if (category) query.append('category', category);
        if (startDate) query.append('start_date', startDate);
        if (endDate) query.append('end_date', endDate);

        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.get(`/v1/audit/events?${query}`);
            return {
                items: response.data.items || [],
                total: response.data.total || 0,
                page: response.data.page || page,
                pages: response.data.pages || 1,
                hasNext: response.data.has_next || false,
                hasPrev: response.data.has_prev || false
            };
        } finally {
            if (unsub) unsub();
        }
    }

    async createExportJob(data, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.post('/v1/audit/exports', data);
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    async getExportJobs(params = {}, onLoading) {
        const { page = 1, limit = 20, status } = params;
        const query = new URLSearchParams({ page: String(page), limit: String(limit) });
        if (status) query.append('status', status);

        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.get(`/v1/audit/exports?${query}`);
            return {
                items: response.data.items || [],
                total: response.data.total || 0,
                page: response.data.page || page,
                pages: response.data.pages || 1,
                hasNext: response.data.has_next || false,
                hasPrev: response.data.has_prev || false
            };
        } finally {
            if (unsub) unsub();
        }
    }

    async downloadExportJob(id, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.get(`/v1/audit/exports/${id}/download`, {
                headers: { 'Accept': 'application/zip' }
            });
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    async verifyExportJob(id, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.get(`/v1/audit/exports/${id}/verify`);
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    async deleteExportJob(id, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            await this.client.delete(`/v1/audit/exports/${id}`);
        } finally {
            if (unsub) unsub();
        }
    }

    async createEvidencePackage(data, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.post('/v1/audit/evidence', data);
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    async getEvidencePackages(params = {}, onLoading) {
        const { page = 1, limit = 20 } = params;
        const query = new URLSearchParams({ page: String(page), limit: String(limit) });

        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.get(`/v1/audit/evidence?${query}`);
            return {
                items: response.data.items || [],
                total: response.data.total || 0,
                page: response.data.page || page,
                pages: response.data.pages || 1,
                hasNext: response.data.has_next || false,
                hasPrev: response.data.has_prev || false
            };
        } finally {
            if (unsub) unsub();
        }
    }

    async downloadEvidencePackage(id, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.get(`/v1/audit/evidence/${id}/download`, {
                headers: { 'Accept': 'application/zip' }
            });
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    async getEvidenceChain(id, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.get(`/v1/audit/evidence/${id}/chain`);
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    async packageEvidence(eventIds, name, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.post('/v1/audit/evidence/package', {
                event_ids: eventIds,
                name
            });
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    async getAuditCategories(onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.get('/v1/audit/categories');
            return response.data || [];
        } finally {
            if (unsub) unsub();
        }
    }

    async getAuditSeverities(onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.get('/v1/audit/severities');
            return response.data || [];
        } finally {
            if (unsub) unsub();
        }
    }
}

// Create singleton instance
const securityApi = typeof apiClient !== 'undefined' ? new SecurityApi(apiClient) : null;

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { SecurityApi, securityApi };
}
