/**
 * ORDL Projects API Module
 * Project management operations for teams
 * @module static/js/api/projects
 */

/**
 * @typedef {Object} Project
 * @property {string} id - Project unique identifier
 * @property {string} teamId - Parent team ID
 * @property {string} code - Project code/short name
 * @property {string} name - Project name
 * @property {string} [description] - Project description
 * @property {string} ingressMode - Ingress mode (standard, restricted, open)
 * @property {string} visibilityMode - Visibility mode (private, team, org, public)
 * @property {Object} [defaults] - Project default settings
 * @property {string} createdAt - Creation timestamp
 * @property {string} updatedAt - Last update timestamp
 */

/**
 * @typedef {Object} ProjectDefaults
 * @property {string} [defaultClearance] - Default clearance tier
 * @property {boolean} [autoArchive] - Auto-archive inactive projects
 * @property {number} [archiveAfterDays] - Days before auto-archive
 * @property {boolean} [requireApproval] - Require approval for changes
 * @property {string[]} [allowedCompartments] - Default allowed compartments
 */

/**
 * @typedef {Object} ProjectStats
 * @property {number} totalSeats - Total seats in project
 * @property {number} occupiedSeats - Occupied seats
 * @property {number} vacantSeats - Vacant seats
 * @property {number} pendingInvites - Pending invitations
 * @property {string} lastActivity - Last activity timestamp
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
 * @callback ProjectEventCallback
 * @param {Object} event - Real-time event data
 * @returns {void}
 */

/**
 * Projects API module
 */
class ProjectsApi {
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
     * Get paginated list of projects
     * @param {PaginationParams & {teamId?: string, orgId?: string, status?: string}} [params]
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<PaginatedResponse<Project>>}
     */
    async getProjects(params = {}, onLoading) {
        const { page = 1, limit = 20, sortBy, sortOrder, teamId, orgId, status } = params;
        
        const query = new URLSearchParams({ page: String(page), limit: String(limit) });
        if (sortBy) query.append('sort_by', sortBy);
        if (sortOrder) query.append('sort_order', sortOrder);
        if (teamId) query.append('team_id', teamId);
        if (orgId) query.append('org_id', orgId);
        if (status) query.append('status', status);

        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.get(`/projects?${query}`);
            return this._formatPaginatedResponse(response.data, page);
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Get single project by ID
     * @param {string} id - Project ID
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<Project>}
     */
    async getProject(id, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.get(`/projects/${id}`);
            return this._formatProject(response.data);
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Create new project
     * @param {Object} data - Project data
     * @param {string} data.teamId - Parent team ID
     * @param {string} data.code - Project code
     * @param {string} data.name - Project name
     * @param {string} [data.description] - Project description
     * @param {string} [data.ingressMode='standard'] - Ingress mode
     * @param {string} [data.visibilityMode='private'] - Visibility mode
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<Project>}
     */
    async createProject(data, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.post('/projects', data);
            return this._formatProject(response.data);
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Update project
     * @param {string} id - Project ID
     * @param {Partial<Project>} data - Update data
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<Project>}
     */
    async updateProject(id, data, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.put(`/projects/${id}`, data);
            return this._formatProject(response.data);
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Delete project
     * @param {string} id - Project ID
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<void>}
     */
    async deleteProject(id, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            await this.client.delete(`/projects/${id}`);
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Get project default settings
     * @param {string} id - Project ID
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<ProjectDefaults>}
     */
    async getProjectDefaults(id, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.get(`/projects/${id}/defaults`);
            return response.data.defaults || response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Update project default settings
     * @param {string} id - Project ID
     * @param {ProjectDefaults} defaults - Default settings
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<ProjectDefaults>}
     */
    async updateProjectDefaults(id, defaults, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.put(`/projects/${id}/defaults`, { defaults });
            return response.data.defaults || response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Get project statistics
     * @param {string} id - Project ID
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<ProjectStats>}
     */
    async getProjectStats(id, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.get(`/projects/${id}/stats`);
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Get project activity log
     * @param {string} id - Project ID
     * @param {PaginationParams} [params]
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<PaginatedResponse>}
     */
    async getProjectActivity(id, params = {}, onLoading) {
        const { page = 1, limit = 20 } = params;
        const query = new URLSearchParams({ page: String(page), limit: String(limit) });

        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.get(`/projects/${id}/activity?${query}`);
            return this._formatPaginatedResponse(response.data, page);
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Transfer project to different team
     * @param {string} id - Project ID
     * @param {string} newTeamId - New team ID
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<Project>}
     */
    async transferProject(id, newTeamId, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.post(`/projects/${id}/transfer`, {
                new_team_id: newTeamId
            });
            return this._formatProject(response.data);
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Archive project (soft delete)
     * @param {string} id - Project ID
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<void>}
     */
    async archiveProject(id, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            await this.client.post(`/projects/${id}/archive`);
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Restore archived project
     * @param {string} id - Project ID
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<Project>}
     */
    async restoreProject(id, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.post(`/projects/${id}/restore`);
            return this._formatProject(response.data);
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Clone project with settings and optionally seats
     * @param {string} id - Project ID to clone
     * @param {Object} options - Clone options
     * @param {string} options.newCode - Code for cloned project
     * @param {string} options.newName - Name for cloned project
     * @param {boolean} [options.includeSeats=false] - Include seats
     * @param {boolean} [options.includeSettings=true] - Include settings
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<Project>}
     */
    async cloneProject(id, options, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.post(`/projects/${id}/clone`, options);
            return this._formatProject(response.data);
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Search projects
     * @param {string} query - Search query
     * @param {PaginationParams & {teamId?: string, orgId?: string}} [params]
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<PaginatedResponse<Project>>}
     */
    async searchProjects(query, params = {}, onLoading) {
        const { page = 1, limit = 20, teamId, orgId } = params;
        const searchParams = new URLSearchParams({ 
            q: query, 
            page: String(page), 
            limit: String(limit) 
        });
        if (teamId) searchParams.append('team_id', teamId);
        if (orgId) searchParams.append('org_id', orgId);

        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.get(`/projects/search?${searchParams}`);
            return this._formatPaginatedResponse(response.data, page);
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Validate project code availability
     * @param {string} code - Project code to validate
     * @param {string} [teamId] - Team ID for scope
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<{available: boolean, suggestions?: string[]}>}
     */
    async validateCode(code, teamId, onLoading) {
        const query = new URLSearchParams({ code });
        if (teamId) query.append('team_id', teamId);

        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.get(`/projects/validate-code?${query}`);
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Update project ingress mode
     * @param {string} id - Project ID
     * @param {string} mode - New ingress mode (standard, restricted, open)
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<Project>}
     */
    async updateIngressMode(id, mode, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.patch(`/projects/${id}/ingress`, {
                ingress_mode: mode
            });
            return this._formatProject(response.data);
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Update project visibility mode
     * @param {string} id - Project ID
     * @param {string} mode - New visibility mode (private, team, org, public)
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<Project>}
     */
    async updateVisibilityMode(id, mode, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.patch(`/projects/${id}/visibility`, {
                visibility_mode: mode
            });
            return this._formatProject(response.data);
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Get project members (via seats)
     * @param {string} id - Project ID
     * @param {PaginationParams} [params]
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<PaginatedResponse>}
     */
    async getProjectMembers(id, params = {}, onLoading) {
        const { page = 1, limit = 20 } = params;
        const query = new URLSearchParams({ page: String(page), limit: String(limit) });

        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.get(`/projects/${id}/members?${query}`);
            return this._formatPaginatedResponse(response.data, page);
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Bulk update projects
     * @param {string[]} projectIds - Project IDs to update
     * @param {Partial<Project>} updates - Updates to apply
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<{updated: number, failed: number, results: Object[]}>}
     */
    async bulkUpdate(projectIds, updates, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.post('/projects/bulk', {
                project_ids: projectIds,
                updates
            });
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Subscribe to project real-time updates
     * @param {string} projectId - Project ID to subscribe to
     * @param {ProjectEventCallback} callback - Event handler
     * @returns {() => void} - Unsubscribe function
     */
    subscribeToUpdates(projectId, callback) {
        return this.client.subscribeWebSocket(`/ws/projects/${projectId}`, callback);
    }

    /**
     * Subscribe to all project updates for a team
     * @param {string} teamId - Team ID
     * @param {ProjectEventCallback} callback - Event handler
     * @returns {() => void} - Unsubscribe function
     */
    subscribeToTeamUpdates(teamId, callback) {
        return this.client.subscribeWebSocket(`/ws/teams/${teamId}/projects`, callback);
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
     * Format project data to standard format
     * @param {*} data - API project data
     * @returns {Project}
     * @private
     */
    _formatProject(data) {
        return {
            id: data.id,
            teamId: data.team_id || data.teamId,
            code: data.code,
            name: data.name,
            description: data.description,
            ingressMode: data.ingress_mode || data.ingressMode || 'standard',
            visibilityMode: data.visibility_mode || data.visibilityMode || 'private',
            defaults: data.defaults,
            createdAt: data.created_at || data.createdAt,
            updatedAt: data.updated_at || data.updatedAt,
            ...data
        };
    }
}

// Create singleton instance
const projectsApi = typeof ordlClient !== 'undefined' ? new ProjectsApi(ordlClient) : null;

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { ProjectsApi, projectsApi };
}
