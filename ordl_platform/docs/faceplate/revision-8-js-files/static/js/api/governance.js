/**
 * ORDL Governance API Module
 * Organizations, teams, projects, seats, clearance, and policy management
 * @module static/js/api/governance
 */

/**
 * @typedef {Object} Organization
 * @property {string} id - Organization ID
 * @property {string} name - Organization name
 * @property {string} shortName - Short name/code
 * @property {string} tier - Organization tier
 * @property {string} primaryRegion - Primary region
 * @property {string} legalName - Legal entity name
 * @property {string} taxId - Tax ID
 * @property {string} industry - Industry sector
 * @property {string} employeeCount - Employee count
 * @property {string} dataResidency - Data residency regions
 * @property {string} createdAt - Creation timestamp
 */

/**
 * @typedef {Object} BoardMember
 * @property {string} id - Member ID
 * @property {string} name - Member name
 * @property {string} role - Board role
 * @property {string} clearance - Clearance level
 * @property {string} appointed - Appointment date
 * @property {string} expires - Term expiration
 * @property {string} status - Member status
 */

/**
 * @typedef {Object} Region
 * @property {string} code - Region code
 * @property {string} name - Region name
 * @property {string} residency - Data residency
 * @property {string} compliance - Compliance framework
 * @property {string} encryption - Encryption standard
 * @property {string} crossBorder - Cross-border policy
 * @property {string} status - Region status
 */

/**
 * @typedef {Object} Team
 * @property {string} id - Team ID
 * @property {string} name - Team name
 * @property {string} scope - Operating scope
 * @property {number} members - Member count
 * @property {string} lead - Team lead
 * @property {string} clearance - Required clearance
 * @property {number} projects - Project count
 */

/**
 * @typedef {Object} Project
 * @property {string} id - Project ID
 * @property {string} name - Project name
 * @property {string} status - Project status
 * @property {string} owner - Project owner
 * @property {string} team - Owning team
 * @property {number} seats - Seat count
 * @property {string[]} compartments - Compartment assignments
 * @property {string} clearance - Default clearance
 * @property {string} created - Creation date
 */

/**
 * @typedef {Object} Seat
 * @property {string} id - Seat ID
 * @property {string} project - Project name
 * @property {string} [occupant] - Occupant name
 * @property {string} [role] - Role
 * @property {string} [rank] - Rank level
 * @property {string} [position] - Position title
 * @property {string} [group] - Group assignment
 * @property {string} [clearance] - Clearance level
 * @property {string} state - Seat state
 */

/**
 * @typedef {Object} ClearanceTier
 * @property {string} level - Tier level (L0-L5)
 * @property {string} name - Tier name
 * @property {string} description - Description
 * @property {number} count - User count
 * @property {string} color - Display color
 */

/**
 * @typedef {Object} Compartment
 * @property {string} id - Compartment ID
 * @property {string} name - Compartment name
 * @property {string} description - Description
 * @property {string} minClearance - Minimum clearance
 * @property {number} seats - Seat count
 * @property {string} status - Status
 */

/**
 * @typedef {Object} PolicyRule
 * @property {string} id - Rule ID
 * @property {string} name - Rule name
 * @property {string} category - Rule category
 * @property {string} effect - Allow/Deny
 * @property {Object} conditions - Rule conditions
 * @property {number} priority - Priority order
 * @property {boolean} enabled - Is enabled
 */

/**
 * @typedef {Object} PolicySimulationResult
 * @property {string} decision - GRANTED/DENIED/HELD
 * @property {string[]} matchedRules - Rules that matched
 * @property {string[]} failedRules - Rules that failed
 * @property {Object} context - Simulation context
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
 * Governance API module
 */
class GovernanceApi {
    constructor(client) {
        this.client = client || (typeof apiClient !== 'undefined' ? apiClient : null);
        if (!this.client) {
            throw new Error('ApiClient instance required. Ensure client.js is loaded first.');
        }
    }

    // =========================================================================
    // ORGANIZATIONS
    // =========================================================================

    async getOrganization(onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.get('/v1/orgs/current');
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    async updateOrganization(data, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.patch('/v1/orgs/current', data);
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    async getBoardMembers(onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.get('/v1/orgs/board');
            return response.data || [];
        } finally {
            if (unsub) unsub();
        }
    }

    async addBoardMember(data, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.post('/v1/orgs/board', data);
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    async updateBoardMember(id, data, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.patch(`/v1/orgs/board/${id}`, data);
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    async removeBoardMember(id, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            await this.client.delete(`/v1/orgs/board/${id}`);
        } finally {
            if (unsub) unsub();
        }
    }

    async getBoardMemberHistory(id, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.get(`/v1/orgs/board/${id}/history`);
            return response.data || [];
        } finally {
            if (unsub) unsub();
        }
    }

    async getRegions(onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.get('/v1/orgs/regions');
            return response.data || [];
        } finally {
            if (unsub) unsub();
        }
    }

    async addRegion(data, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.post('/v1/orgs/regions', data);
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    async updateRegion(code, data, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.patch(`/v1/orgs/regions/${code}`, data);
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    async getPolicyDefaults(onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.get('/v1/orgs/policy-defaults');
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    async updatePolicyDefaults(data, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.patch('/v1/orgs/policy-defaults', data);
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    // =========================================================================
    // TEAMS
    // =========================================================================

    async getTeams(params = {}, onLoading) {
        const { page = 1, limit = 20, scope, search } = params;
        const query = new URLSearchParams({ page: String(page), limit: String(limit) });
        if (scope) query.append('scope', scope);
        if (search) query.append('search', search);

        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.get(`/v1/teams?${query}`);
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

    async getTeam(id, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.get(`/v1/teams/${id}`);
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    async createTeam(data, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.post('/v1/teams', data);
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    async updateTeam(id, data, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.patch(`/v1/teams/${id}`, data);
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    async deleteTeam(id, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            await this.client.delete(`/v1/teams/${id}`);
        } finally {
            if (unsub) unsub();
        }
    }

    async getTeamScopeMatrix(onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.get('/v1/teams/scope-matrix');
            return response.data || [];
        } finally {
            if (unsub) unsub();
        }
    }

    async updateTeamScope(teamId, scope, data, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.patch(`/v1/teams/${teamId}/scope/${scope}`, data);
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    async getEscalationTrees(onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.get('/v1/teams/escalation-trees');
            return response.data || [];
        } finally {
            if (unsub) unsub();
        }
    }

    async getEscalationTree(id, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.get(`/v1/teams/escalation-trees/${id}`);
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    // =========================================================================
    // PROJECTS
    // =========================================================================

    async getProjects(params = {}, onLoading) {
        const { page = 1, limit = 20, status, search } = params;
        const query = new URLSearchParams({ page: String(page), limit: String(limit) });
        if (status) query.append('status', status);
        if (search) query.append('search', search);

        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.get(`/v1/projects?${query}`);
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

    async getProject(id, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.get(`/v1/projects/${id}`);
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    async createProject(data, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.post('/v1/projects', data);
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    async updateProject(id, data, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.patch(`/v1/projects/${id}`, data);
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    async deleteProject(id, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            await this.client.delete(`/v1/projects/${id}`);
        } finally {
            if (unsub) unsub();
        }
    }

    async getProjectSeats(id, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.get(`/v1/projects/${id}/seats`);
            return response.data || [];
        } finally {
            if (unsub) unsub();
        }
    }

    async getProjectDefaultClearance(onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.get('/v1/projects/defaults/clearance');
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    async updateProjectDefaultClearance(data, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.patch('/v1/projects/defaults/clearance', data);
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    // =========================================================================
    // SEATS
    // =========================================================================

    async getSeats(params = {}, onLoading) {
        const { page = 1, limit = 20, state, projectId } = params;
        const query = new URLSearchParams({ page: String(page), limit: String(limit) });
        if (state) query.append('state', state);
        if (projectId) query.append('project_id', projectId);

        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.get(`/v1/seats?${query}`);
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

    async getSeat(id, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.get(`/v1/seats/${id}`);
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    async createSeat(data, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.post('/v1/seats', data);
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    async updateSeat(id, data, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.patch(`/v1/seats/${id}`, data);
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    async deleteSeat(id, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            await this.client.delete(`/v1/seats/${id}`);
        } finally {
            if (unsub) unsub();
        }
    }

    async assignSeat(id, occupantId, data = {}, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.post(`/v1/seats/${id}/assign`, { occupant_id: occupantId, ...data });
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    async vacateSeat(id, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.post(`/v1/seats/${id}/vacate`);
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    async bulkAssignSeats(seatIds, occupantId, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.post('/v1/seats/bulk-assign', { seat_ids: seatIds, occupant_id: occupantId });
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    async getSeatHistory(id, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.get(`/v1/seats/${id}/history`);
            return response.data || [];
        } finally {
            if (unsub) unsub();
        }
    }

    async getPositionGroupMatrix(onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.get('/v1/seats/matrix');
            return response.data || [];
        } finally {
            if (unsub) unsub();
        }
    }

    async updatePositionGroupMatrix(data, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.patch('/v1/seats/matrix', data);
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    // =========================================================================
    // CLEARANCE
    // =========================================================================

    async getClearanceTiers(onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.get('/v1/clearance/tiers');
            return response.data || [];
        } finally {
            if (unsub) unsub();
        }
    }

    async updateClearanceTier(level, data, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.patch(`/v1/clearance/tiers/${level}`, data);
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    async getCompartments(onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.get('/v1/clearance/compartments');
            return response.data || [];
        } finally {
            if (unsub) unsub();
        }
    }

    async getCompartment(id, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.get(`/v1/clearance/compartments/${id}`);
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    async createCompartment(data, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.post('/v1/clearance/compartments', data);
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    async updateCompartment(id, data, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.patch(`/v1/clearance/compartments/${id}`, data);
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    async deleteCompartment(id, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            await this.client.delete(`/v1/clearance/compartments/${id}`);
        } finally {
            if (unsub) unsub();
        }
    }

    async getNTKMatrix(onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.get('/v1/clearance/ntk-matrix');
            return response.data || [];
        } finally {
            if (unsub) unsub();
        }
    }

    async updateNTKMatrix(data, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.patch('/v1/clearance/ntk-matrix', data);
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    async exportNTKMatrix(format = 'json', onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.get(`/v1/clearance/ntk-matrix/export?format=${format}`);
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    async getClearanceConflicts(onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.get('/v1/clearance/conflicts');
            return response.data || [];
        } finally {
            if (unsub) unsub();
        }
    }

    async resolveConflict(id, resolution, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.post(`/v1/clearance/conflicts/${id}/resolve`, { resolution });
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    // =========================================================================
    // POLICY
    // =========================================================================

    async getPolicyRules(params = {}, onLoading) {
        const { page = 1, limit = 20, category, enabled } = params;
        const query = new URLSearchParams({ page: String(page), limit: String(limit) });
        if (category) query.append('category', category);
        if (enabled !== undefined) query.append('enabled', String(enabled));

        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.get(`/v1/policy/rules?${query}`);
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

    async getPolicyRule(id, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.get(`/v1/policy/rules/${id}`);
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    async createPolicyRule(data, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.post('/v1/policy/rules', data);
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    async updatePolicyRule(id, data, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.patch(`/v1/policy/rules/${id}`, data);
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    async deletePolicyRule(id, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            await this.client.delete(`/v1/policy/rules/${id}`);
        } finally {
            if (unsub) unsub();
        }
    }

    async simulatePolicy(subject, action, resource, context, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.post('/v1/policy/simulate', {
                subject, action, resource, context
            });
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    async getPolicyCategories(onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.get('/v1/policy/categories');
            return response.data || [];
        } finally {
            if (unsub) unsub();
        }
    }

    async getPolicyTokens(params = {}, onLoading) {
        const { page = 1, limit = 20, status } = params;
        const query = new URLSearchParams({ page: String(page), limit: String(limit) });
        if (status) query.append('status', status);

        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.get(`/v1/policy/tokens?${query}`);
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

    async getHoldDenyReasons(category, onLoading) {
        const query = category ? `?category=${encodeURIComponent(category)}` : '';
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        try {
            const response = await this.client.get(`/v1/policy/reasons${query}`);
            return response.data || [];
        } finally {
            if (unsub) unsub();
        }
    }
}

// Create singleton instance
const governanceApi = typeof apiClient !== 'undefined' ? new GovernanceApi(apiClient) : null;

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { GovernanceApi, governanceApi };
}
