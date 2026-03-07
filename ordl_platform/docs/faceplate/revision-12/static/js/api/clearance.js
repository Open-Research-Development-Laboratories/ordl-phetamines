/**
 * ORDL Clearance API Module
 * Clearance tiers and compartment management for security access control
 * @module static/js/api/clearance
 */

/**
 * @typedef {Object} ClearanceTier
 * @property {string} id - Tier unique identifier
 * @property {string} name - Tier name (e.g., "Level 1", "Level 2")
 * @property {number} level - Numeric level (0-5)
 * @property {string} [description] - Tier description
 * @property {string[]} [permissions] - Associated permissions
 * @property {Object} [restrictions] - Tier restrictions
 * @property {string} color - Display color for UI
 * @property {boolean} active - Whether tier is active
 */

/**
 * @typedef {Object} Compartment
 * @property {string} id - Compartment ID
 * @property {string} code - Compartment code
 * @property {string} name - Compartment name
 * @property {string} [description] - Compartment description
 * @property {string[]} [parentIds] - Parent compartment IDs
 * @property {string} [classification] - Classification level
 * @property {boolean} active - Whether compartment is active
 * @property {string} createdAt - Creation timestamp
 */

/**
 * @typedef {Object} ClearanceMatrix
 * @property {Object} tierCompartmentMap - Mapping of tiers to compartments
 * @property {Object} userTierMap - Mapping of users to tiers
 * @property {Object} rules - Access rules
 * @property {string} version - Matrix version
 * @property {string} updatedAt - Last update timestamp
 */

/**
 * @typedef {Object} PolicyDecisionRequest
 * @property {string} action - Action to evaluate (read, write, delete, admin)
 * @property {string} resource - Resource identifier
 * @property {string} userId - User ID
 * @property {Object} [context] - Additional context
 */

/**
 * @typedef {Object} PolicyDecisionResponse
 * @property {string} decision - Decision result (allow, deny)
 * @property {string[]} reasonCodes - Reason codes
 * @property {string} requestHash - Request hash
 * @property {string} policyToken - Policy token for audit
 * @property {string} [expiresAt] - Token expiration
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
 * @callback ClearanceEventCallback
 * @param {Object} event - Real-time event data
 * @returns {void}
 */

/**
 * Clearance API module
 */
class ClearanceApi {
    /**
     * @param {import('./ordl-client.js').OrdlApiClient} [client] - API client instance
     */
    constructor(client) {
        this.client = client || (typeof ordlClient !== 'undefined' ? ordlClient : null);
        if (!this.client) {
            throw new Error('OrdlApiClient instance required. Ensure ordl-client.js is loaded first.');
        }
    }

    // =================================================================
    // Clearance Tier Operations
    // =================================================================

    /**
     * Get all clearance tiers
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<ClearanceTier[]>}
     */
    async getTiers(onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.get('/clearance/tiers');
            return response.data.tiers || response.data || [];
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Get single clearance tier
     * @param {string} tierId - Tier ID
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<ClearanceTier>}
     */
    async getTier(tierId, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.get(`/clearance/tiers/${tierId}`);
            return this._formatTier(response.data);
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Update clearance tiers (bulk)
     * @param {ClearanceTier[]} tiers - Array of tier definitions
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<{tiers: ClearanceTier[], updatedAt: string}>}
     */
    async updateTiers(tiers, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.put('/clearance/tiers', { tiers });
            return {
                tiers: (response.data.tiers || []).map(t => this._formatTier(t)),
                updatedAt: response.data.updated_at || response.data.updatedAt
            };
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Create new clearance tier
     * @param {Partial<ClearanceTier>} data - Tier data
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<ClearanceTier>}
     */
    async createTier(data, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.post('/clearance/tiers', data);
            return this._formatTier(response.data);
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Delete clearance tier
     * @param {string} tierId - Tier ID
     * @param {Object} [options] - Delete options
     * @param {string} [options.migrateTo] - Tier ID to migrate users to
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<void>}
     */
    async deleteTier(tierId, options = {}, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            await this.client.delete(`/clearance/tiers/${tierId}`, { body: options });
        } finally {
            if (unsub) unsub();
        }
    }

    // =================================================================
    // Compartment Operations
    // =================================================================

    /**
     * Get all compartments
     * @param {PaginationParams & {active?: boolean, parentId?: string}} [params]
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<PaginatedResponse<Compartment>>}
     */
    async getCompartments(params = {}, onLoading) {
        const { page = 1, limit = 20, active, parentId } = params;
        
        const query = new URLSearchParams({ page: String(page), limit: String(limit) });
        if (active !== undefined) query.append('active', String(active));
        if (parentId) query.append('parent_id', parentId);

        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.get(`/clearance/compartments?${query}`);
            return this._formatPaginatedResponse(response.data, page, item => this._formatCompartment(item));
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Get single compartment
     * @param {string} compId - Compartment ID
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<Compartment>}
     */
    async getCompartment(compId, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.get(`/clearance/compartments/${compId}`);
            return this._formatCompartment(response.data);
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Create new compartment
     * @param {Object} data - Compartment data
     * @param {string} data.code - Compartment code
     * @param {string} data.name - Compartment name
     * @param {string} [data.description] - Compartment description
     * @param {string[]} [data.parentIds] - Parent compartment IDs
     * @param {string} [data.classification] - Classification level
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<Compartment>}
     */
    async createCompartment(data, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.post('/clearance/compartments', data);
            return this._formatCompartment(response.data);
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Update compartment
     * @param {string} compId - Compartment ID
     * @param {Partial<Compartment>} data - Update data
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<Compartment>}
     */
    async updateCompartment(compId, data, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.put(`/clearance/compartments/${compId}`, data);
            return this._formatCompartment(response.data);
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Delete compartment
     * @param {string} compId - Compartment ID
     * @param {Object} [options] - Delete options
     * @param {string} [options.migrateTo] - Compartment ID to migrate to
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<void>}
     */
    async deleteCompartment(compId, options = {}, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            await this.client.delete(`/clearance/compartments/${compId}`, { body: options });
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Get compartment hierarchy/tree
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<Object>} - Tree structure
     */
    async getCompartmentTree(onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.get('/clearance/compartments/tree');
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    // =================================================================
    // Clearance Matrix Operations
    // =================================================================

    /**
     * Get clearance matrix
     * @param {Object} [params] - Query params
     * @param {string} [params.orgId] - Organization ID
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<ClearanceMatrix>}
     */
    async getMatrix(params = {}, onLoading) {
        const query = new URLSearchParams();
        if (params.orgId) query.append('org_id', params.orgId);

        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.get(`/clearance/matrix?${query}`);
            return this._formatMatrix(response.data);
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Update clearance matrix
     * @param {ClearanceMatrix} matrix - Matrix configuration
     * @param {Object} [options] - Update options
     * @param {boolean} [options.validateOnly=false] - Validate without applying
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<ClearanceMatrix>}
     */
    async updateMatrix(matrix, options = {}, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.put('/clearance/matrix', {
                matrix,
                validate_only: options.validateOnly
            });
            return this._formatMatrix(response.data);
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Export clearance matrix
     * @param {Object} [options] - Export options
     * @param {string} [options.format='json'] - Export format (json, csv, yaml)
     * @param {boolean} [options.includeHistory=false] - Include history
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<{data: string, format: string, exportedAt: string}>}
     */
    async exportMatrix(options = {}, onLoading) {
        const { format = 'json', includeHistory = false } = options;
        const query = new URLSearchParams({ format });
        if (includeHistory) query.append('include_history', 'true');

        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.get(`/clearance/matrix/export?${query}`);
            return {
                data: response.data.data || response.data,
                format: response.data.format || format,
                exportedAt: response.data.exported_at || new Date().toISOString()
            };
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Import clearance matrix
     * @param {string|Object} data - Matrix data to import
     * @param {Object} [options] - Import options
     * @param {boolean} [options.dryRun=false] - Validate without applying
     * @param {boolean} [options.overwrite=false] - Overwrite existing
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<{imported: number, errors: string[], warnings: string[]}>}
     */
    async importMatrix(data, options = {}, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.post('/clearance/matrix/import', {
                data,
                dry_run: options.dryRun,
                overwrite: options.overwrite
            });
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Get matrix version history
     * @param {PaginationParams} [params]
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<PaginatedResponse>}
     */
    async getMatrixHistory(params = {}, onLoading) {
        const { page = 1, limit = 20 } = params;
        const query = new URLSearchParams({ page: String(page), limit: String(limit) });

        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.get(`/clearance/matrix/history?${query}`);
            return this._formatPaginatedResponse(response.data, page);
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Restore matrix to previous version
     * @param {string} versionId - Version ID to restore
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<ClearanceMatrix>}
     */
    async restoreMatrixVersion(versionId, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.post(`/clearance/matrix/restore/${versionId}`);
            return this._formatMatrix(response.data);
        } finally {
            if (unsub) unsub();
        }
    }

    // =================================================================
    // Policy Decision Operations
    // =================================================================

    /**
     * Evaluate policy decision
     * @param {PolicyDecisionRequest} request - Decision request
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<PolicyDecisionResponse>}
     */
    async evaluatePolicy(request, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.post('/policy/decide', request);
            return {
                decision: response.data.decision,
                reasonCodes: response.data.reason_codes || response.data.reasonCodes || [],
                requestHash: response.data.request_hash || response.data.requestHash,
                policyToken: response.data.policy_token || response.data.policyToken,
                expiresAt: response.data.expires_at || response.data.expiresAt
            };
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Batch evaluate policy decisions
     * @param {PolicyDecisionRequest[]} requests - Array of decision requests
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<PolicyDecisionResponse[]>}
     */
    async batchEvaluatePolicy(requests, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.post('/policy/decide/batch', { requests });
            return (response.data.results || response.data || []).map(r => ({
                decision: r.decision,
                reasonCodes: r.reason_codes || r.reasonCodes || [],
                requestHash: r.request_hash || r.requestHash,
                policyToken: r.policy_token || r.policyToken,
                expiresAt: r.expires_at || r.expiresAt
            }));
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Check user access to resource
     * @param {string} userId - User ID
     * @param {string} resource - Resource identifier
     * @param {string} action - Action to check (read, write, delete, admin)
     * @param {Object} [context] - Additional context
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<{allowed: boolean, reason?: string, tier?: string, compartments?: string[]}>}
     */
    async checkAccess(userId, resource, action, context = {}, onLoading) {
        const result = await this.evaluatePolicy({
            userId,
            resource,
            action,
            context
        }, onLoading);

        return {
            allowed: result.decision === 'allow',
            reason: result.reasonCodes.join(', '),
            policyToken: result.policyToken
        };
    }

    /**
     * Get user's effective clearance
     * @param {string} userId - User ID
     * @param {Object} [context] - Context (orgId, projectId, etc.)
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<{tier: string, compartments: string[], grantedAt: string}>}
     */
    async getUserClearance(userId, context = {}, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const query = new URLSearchParams({ user_id: userId });
            if (context.orgId) query.append('org_id', context.orgId);
            if (context.projectId) query.append('project_id', context.projectId);

            const response = await this.client.get(`/clearance/user?${query}`);
            return {
                tier: response.data.tier,
                compartments: response.data.compartments || [],
                grantedAt: response.data.granted_at || response.data.grantedAt
            };
        } finally {
            if (unsub) unsub();
        }
    }

    // =================================================================
    // User Clearance Management
    // =================================================================

    /**
     * Grant clearance to user
     * @param {string} userId - User ID
     * @param {Object} data - Grant data
     * @param {string} data.tier - Clearance tier
     * @param {string[]} [data.compartments] - Compartments
     * @param {string} [data.expiresAt] - Expiration date
     * @param {string} [data.reason] - Grant reason
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<Object>}
     */
    async grantClearance(userId, data, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.post(`/clearance/users/${userId}/grant`, data);
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Revoke user clearance
     * @param {string} userId - User ID
     * @param {Object} [options] - Revoke options
     * @param {string} [options.reason] - Revoke reason
     * @param {boolean} [options.immediate=true] - Immediate effect
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<void>}
     */
    async revokeClearance(userId, options = {}, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            await this.client.post(`/clearance/users/${userId}/revoke`, options);
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Get user's clearance history
     * @param {string} userId - User ID
     * @param {PaginationParams} [params]
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<PaginatedResponse>}
     */
    async getUserClearanceHistory(userId, params = {}, onLoading) {
        const { page = 1, limit = 20 } = params;
        const query = new URLSearchParams({ page: String(page), limit: String(limit) });

        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.get(`/clearance/users/${userId}/history?${query}`);
            return this._formatPaginatedResponse(response.data, page);
        } finally {
            if (unsub) unsub();
        }
    }

    // =================================================================
    // Real-time Updates
    // =================================================================

    /**
     * Subscribe to clearance matrix updates
     * @param {ClearanceEventCallback} callback - Event handler
     * @returns {() => void} - Unsubscribe function
     */
    subscribeToMatrixUpdates(callback) {
        return this.client.subscribeWebSocket('/ws/clearance/matrix', callback);
    }

    /**
     * Subscribe to tier updates
     * @param {ClearanceEventCallback} callback - Event handler
     * @returns {() => void} - Unsubscribe function
     */
    subscribeToTierUpdates(callback) {
        return this.client.subscribeWebSocket('/ws/clearance/tiers', callback);
    }

    /**
     * Subscribe to compartment updates
     * @param {ClearanceEventCallback} callback - Event handler
     * @returns {() => void} - Unsubscribe function
     */
    subscribeToCompartmentUpdates(callback) {
        return this.client.subscribeWebSocket('/ws/clearance/compartments', callback);
    }

    // =================================================================
    // Helper Methods
    // =================================================================

    /**
     * Format API response to standard paginated format
     * @param {*} data - API response data
     * @param {number} page - Current page
     * @param {Function} [formatter] - Item formatter
     * @returns {PaginatedResponse}
     * @private
     */
    _formatPaginatedResponse(data, page, formatter = null) {
        if (Array.isArray(data)) {
            return {
                items: formatter ? data.map(formatter) : data,
                total: data.length,
                page: page,
                pages: 1,
                hasNext: false,
                hasPrev: page > 1
            };
        }
        
        const items = data.items || data.data || [];
        return {
            items: formatter ? items.map(formatter) : items,
            total: data.total || 0,
            page: data.page || page,
            pages: data.pages || Math.ceil((data.total || 0) / 20),
            hasNext: data.has_next || data.hasNext || false,
            hasPrev: data.has_prev || data.hasPrev || page > 1
        };
    }

    /**
     * Format tier data
     * @param {*} data - API tier data
     * @returns {ClearanceTier}
     * @private
     */
    _formatTier(data) {
        return {
            id: data.id,
            name: data.name,
            level: data.level,
            description: data.description,
            permissions: data.permissions || [],
            restrictions: data.restrictions,
            color: data.color || '#6B7280',
            active: data.active !== false,
            ...data
        };
    }

    /**
     * Format compartment data
     * @param {*} data - API compartment data
     * @returns {Compartment}
     * @private
     */
    _formatCompartment(data) {
        return {
            id: data.id,
            code: data.code,
            name: data.name,
            description: data.description,
            parentIds: data.parent_ids || data.parentIds || [],
            classification: data.classification,
            active: data.active !== false,
            createdAt: data.created_at || data.createdAt,
            ...data
        };
    }

    /**
     * Format matrix data
     * @param {*} data - API matrix data
     * @returns {ClearanceMatrix}
     * @private
     */
    _formatMatrix(data) {
        return {
            tierCompartmentMap: data.tier_compartment_map || data.tierCompartmentMap || {},
            userTierMap: data.user_tier_map || data.userTierMap || {},
            rules: data.rules || {},
            version: data.version,
            updatedAt: data.updated_at || data.updatedAt,
            ...data
        };
    }
}

// Create singleton instance
const clearanceApi = typeof ordlClient !== 'undefined' ? new ClearanceApi(ordlClient) : null;

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { ClearanceApi, clearanceApi };
}
