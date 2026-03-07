/**
 * ORDL Teams API Module
 * Team management operations for organizations
 * @module static/js/api/teams
 */

/**
 * @typedef {Object} Team
 * @property {string} id - Team unique identifier
 * @property {string} orgId - Organization ID
 * @property {string} name - Team name
 * @property {string} [description] - Team description
 * @property {string} [code] - Team code/short name
 * @property {Object} [scopeMatrix] - Team scope matrix defining permissions
 * @property {string} createdAt - Creation timestamp
 * @property {string} updatedAt - Last update timestamp
 * @property {Object} [metadata] - Additional metadata
 */

/**
 * @typedef {Object} TeamMember
 * @property {string} id - Member ID
 * @property {string} userId - User ID
 * @property {string} teamId - Team ID
 * @property {string} role - Member role (lead, member, guest)
 * @property {string} [clearanceTier] - Clearance tier (L0-L5)
 * @property {string[]} [compartments] - Assigned compartments
 * @property {string} joinedAt - Join timestamp
 */

/**
 * @typedef {Object} ScopeMatrix
 * @property {boolean} [read] - Read permission
 * @property {boolean} [write] - Write permission
 * @property {boolean} [admin] - Admin permission
 * @property {boolean} [delete] - Delete permission
 * @property {Object} [custom] - Custom scope definitions
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
 * @callback TeamEventCallback
 * @param {Object} event - Real-time event data
 * @returns {void}
 */

/**
 * Teams API module
 */
class TeamsApi {
    /**
     * @param {import('./ordl-client.js').OrdlApiClient} [client] - API client instance
     */
    constructor(client) {
        this.client = client || (typeof ordlClient !== 'undefined' ? ordlClient : null);
        if (!this.client) {
            throw new Error('OrdlApiClient instance required. Ensure ordl-client.js is loaded first.');
        }
        
        // WebSocket subscription for real-time updates
        this._wsUnsubscribe = null;
    }

    /**
     * Get paginated list of teams
     * @param {PaginationParams & {orgId?: string, status?: string}} [params]
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<PaginatedResponse<Team>>}
     */
    async getTeams(params = {}, onLoading) {
        const { page = 1, limit = 20, sortBy, sortOrder, orgId, status } = params;
        
        const query = new URLSearchParams({ page: String(page), limit: String(limit) });
        if (sortBy) query.append('sort_by', sortBy);
        if (sortOrder) query.append('sort_order', sortOrder);
        if (orgId) query.append('org_id', orgId);
        if (status) query.append('status', status);

        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.get(`/teams?${query}`);
            return this._formatPaginatedResponse(response.data, page);
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Get single team by ID
     * @param {string} id - Team ID
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<Team>}
     */
    async getTeam(id, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.get(`/teams/${id}`);
            return this._formatTeam(response.data);
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Create new team
     * @param {Object} data - Team data
     * @param {string} data.orgId - Organization ID
     * @param {string} data.name - Team name
     * @param {string} [data.description] - Team description
     * @param {string} [data.code] - Team code
     * @param {Object} [data.metadata] - Additional metadata
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<Team>}
     */
    async createTeam(data, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.post('/teams', data);
            return this._formatTeam(response.data);
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Update team
     * @param {string} id - Team ID
     * @param {Partial<Team>} data - Update data
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<Team>}
     */
    async updateTeam(id, data, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.put(`/teams/${id}`, data);
            return this._formatTeam(response.data);
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Delete team
     * @param {string} id - Team ID
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<void>}
     */
    async deleteTeam(id, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            await this.client.delete(`/teams/${id}`);
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Get team scope matrix
     * @param {string} id - Team ID
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<ScopeMatrix>}
     */
    async getTeamScope(id, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.get(`/teams/${id}/scope`);
            return response.data.scope_matrix || response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Update team scope matrix
     * @param {string} id - Team ID
     * @param {ScopeMatrix} scopeMatrix - Scope matrix configuration
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<ScopeMatrix>}
     */
    async updateTeamScope(id, scopeMatrix, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.put(`/teams/${id}/scope`, {
                scope_matrix: scopeMatrix
            });
            return response.data.scope_matrix || response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Get team members
     * @param {string} teamId - Team ID
     * @param {PaginationParams} [params]
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<PaginatedResponse<TeamMember>>}
     */
    async getTeamMembers(teamId, params = {}, onLoading) {
        const { page = 1, limit = 20 } = params;
        const query = new URLSearchParams({ page: String(page), limit: String(limit) });

        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.get(`/teams/${teamId}/members?${query}`);
            return this._formatPaginatedResponse(response.data, page);
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Add member to team
     * @param {string} teamId - Team ID
     * @param {Object} data - Member data
     * @param {string} data.userId - User ID
     * @param {string} [data.role='member'] - Member role
     * @param {string} [data.clearanceTier] - Clearance tier
     * @param {string[]} [data.compartments] - Assigned compartments
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<TeamMember>}
     */
    async addTeamMember(teamId, data, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.post(`/teams/${teamId}/members`, data);
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Remove member from team
     * @param {string} teamId - Team ID
     * @param {string} userId - User ID
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<void>}
     */
    async removeTeamMember(teamId, userId, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            await this.client.delete(`/teams/${teamId}/members/${userId}`);
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Update team member role
     * @param {string} teamId - Team ID
     * @param {string} userId - User ID
     * @param {Object} data - Update data
     * @param {string} [data.role] - New role
     * @param {string} [data.clearanceTier] - New clearance tier
     * @param {string[]} [data.compartments] - New compartments
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<TeamMember>}
     */
    async updateTeamMember(teamId, userId, data, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.patch(`/teams/${teamId}/members/${userId}`, data);
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Transfer team ownership
     * @param {string} teamId - Team ID
     * @param {string} newOwnerId - New owner user ID
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<Object>}
     */
    async transferOwnership(teamId, newOwnerId, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.post(`/teams/${teamId}/transfer`, {
                new_owner_id: newOwnerId
            });
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Get team statistics
     * @param {string} teamId - Team ID
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<Object>}
     */
    async getTeamStats(teamId, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.get(`/teams/${teamId}/stats`);
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Clone team with members and settings
     * @param {string} teamId - Team ID to clone
     * @param {Object} options - Clone options
     * @param {string} options.newName - Name for cloned team
     * @param {boolean} [options.includeMembers=false] - Include members
     * @param {boolean} [options.includeProjects=false] - Include projects
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<Team>}
     */
    async cloneTeam(teamId, options, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.post(`/teams/${teamId}/clone`, options);
            return this._formatTeam(response.data);
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Archive team (soft delete)
     * @param {string} teamId - Team ID
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<void>}
     */
    async archiveTeam(teamId, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            await this.client.post(`/teams/${teamId}/archive`);
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Restore archived team
     * @param {string} teamId - Team ID
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<Team>}
     */
    async restoreTeam(teamId, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.post(`/teams/${teamId}/restore`);
            return this._formatTeam(response.data);
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Search teams
     * @param {string} query - Search query
     * @param {PaginationParams & {orgId?: string}} [params]
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<PaginatedResponse<Team>>}
     */
    async searchTeams(query, params = {}, onLoading) {
        const { page = 1, limit = 20, orgId } = params;
        const searchParams = new URLSearchParams({ 
            q: query, 
            page: String(page), 
            limit: String(limit) 
        });
        if (orgId) searchParams.append('org_id', orgId);

        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.get(`/teams/search?${searchParams}`);
            return this._formatPaginatedResponse(response.data, page);
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Subscribe to team real-time updates
     * @param {string} teamId - Team ID to subscribe to
     * @param {TeamEventCallback} callback - Event handler
     * @returns {() => void} - Unsubscribe function
     */
    subscribeToUpdates(teamId, callback) {
        return this.client.subscribeWebSocket(`/ws/teams/${teamId}`, callback);
    }

    /**
     * Subscribe to all team updates for an organization
     * @param {string} orgId - Organization ID
     * @param {TeamEventCallback} callback - Event handler
     * @returns {() => void} - Unsubscribe function
     */
    subscribeToOrgUpdates(orgId, callback) {
        return this.client.subscribeWebSocket(`/ws/orgs/${orgId}/teams`, callback);
    }

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
                items: data,
                total: data.length,
                page: page,
                pages: 1,
                hasNext: false,
                hasPrev: page > 1
            };
        }
        
        return {
            items: data.items || data.data || [],
            total: data.total || 0,
            page: data.page || page,
            pages: data.pages || Math.ceil((data.total || 0) / 20),
            hasNext: data.has_next || data.hasNext || false,
            hasPrev: data.has_prev || data.hasPrev || page > 1
        };
    }

    /**
     * Format team data to standard format
     * @param {*} data - API team data
     * @returns {Team}
     * @private
     */
    _formatTeam(data) {
        return {
            id: data.id,
            orgId: data.org_id || data.orgId,
            name: data.name,
            description: data.description,
            code: data.code,
            scopeMatrix: data.scope_matrix || data.scopeMatrix,
            createdAt: data.created_at || data.createdAt,
            updatedAt: data.updated_at || data.updatedAt,
            metadata: data.metadata,
            ...data
        };
    }
}

// Create singleton instance
const teamsApi = typeof ordlClient !== 'undefined' ? new TeamsApi(ordlClient) : null;

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { TeamsApi, teamsApi };
}
