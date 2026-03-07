/**
 * ORDL Seats API Module
 * Seat management operations for projects
 * @module static/js/api/seats
 */

/**
 * @typedef {Object} Seat
 * @property {string} id - Seat unique identifier
 * @property {string} projectId - Parent project ID
 * @property {string} [userId] - Assigned user ID (null if vacant)
 * @property {string} role - Seat role (e.g., developer, reviewer, admin)
 * @property {string} [rank] - Seat rank/level (e.g., L1, L2, L3, L4, L5)
 * @property {string} [position] - Position title
 * @property {string} [groupName] - Group/team name within project
 * @property {string} [clearanceTier] - Required clearance tier (L0-L5)
 * @property {string[]} [compartments] - Required compartments
 * @property {string} status - Seat status (open, occupied, pending, suspended)
 * @property {string} [assignedAt] - Assignment timestamp
 * @property {string} createdAt - Creation timestamp
 * @property {string} updatedAt - Last update timestamp
 */

/**
 * @typedef {Object} SeatMatrix
 * @property {Object} tiers - Clearance tier requirements by role
 * @property {Object} compartments - Compartment access by role
 * @property {Object} limits - Seat limits by type
 * @property {Object} rules - Assignment rules
 */

/**
 * @typedef {Object} BulkSeatOperation
 * @property {string} operation - Operation type (assign, vacate, update, create, delete)
 * @property {string[]} [seatIds] - Target seat IDs
 * @property {Object} [data] - Operation data
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
 * @callback SeatEventCallback
 * @param {Object} event - Real-time event data
 * @returns {void}
 */

/**
 * Seats API module
 */
class SeatsApi {
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
     * Get paginated list of seats
     * @param {PaginationParams & {projectId?: string, status?: string, userId?: string}} [params]
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<PaginatedResponse<Seat>>}
     */
    async getSeats(params = {}, onLoading) {
        const { page = 1, limit = 20, sortBy, sortOrder, projectId, status, userId } = params;
        
        const query = new URLSearchParams({ page: String(page), limit: String(limit) });
        if (sortBy) query.append('sort_by', sortBy);
        if (sortOrder) query.append('sort_order', sortOrder);
        if (projectId) query.append('project_id', projectId);
        if (status) query.append('status', status);
        if (userId) query.append('user_id', userId);

        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.get(`/seats?${query}`);
            return this._formatPaginatedResponse(response.data, page);
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Get single seat by ID
     * @param {string} id - Seat ID
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<Seat>}
     */
    async getSeat(id, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.get(`/seats/${id}`);
            return this._formatSeat(response.data);
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Create new seat
     * @param {Object} data - Seat data
     * @param {string} data.projectId - Parent project ID
     * @param {string} data.role - Seat role
     * @param {string} [data.rank] - Seat rank
     * @param {string} [data.position] - Position title
     * @param {string} [data.groupName] - Group name
     * @param {string} [data.clearanceTier] - Required clearance tier
     * @param {string[]} [data.compartments] - Required compartments
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<Seat>}
     */
    async createSeat(data, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.post('/seats', data);
            return this._formatSeat(response.data);
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Update seat
     * @param {string} id - Seat ID
     * @param {Partial<Seat>} data - Update data
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<Seat>}
     */
    async updateSeat(id, data, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.put(`/seats/${id}`, data);
            return this._formatSeat(response.data);
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Delete seat
     * @param {string} id - Seat ID
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<void>}
     */
    async deleteSeat(id, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            await this.client.delete(`/seats/${id}`);
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Assign user to seat
     * @param {string} id - Seat ID
     * @param {Object} data - Assignment data
     * @param {string} data.userId - User ID to assign
     * @param {string} [data.startDate] - Assignment start date
     * @param {string} [data.notes] - Assignment notes
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<Seat>}
     */
    async assignSeat(id, data, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.post(`/seats/${id}/assign`, data);
            return this._formatSeat(response.data);
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Vacate (unassign) seat
     * @param {string} id - Seat ID
     * @param {Object} [options] - Vacate options
     * @param {string} [options.reason] - Reason for vacating
     * @param {boolean} [options.handover=false] - Enable handover mode
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<Seat>}
     */
    async vacateSeat(id, options = {}, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.post(`/seats/${id}/vacate`, options);
            return this._formatSeat(response.data);
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Get seat matrix for project
     * @param {string} projectId - Project ID
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<SeatMatrix>}
     */
    async getSeatMatrix(projectId, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.get(`/seats/matrix?project_id=${projectId}`);
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Update seat matrix
     * @param {string} projectId - Project ID
     * @param {SeatMatrix} matrix - Seat matrix configuration
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<SeatMatrix>}
     */
    async updateSeatMatrix(projectId, matrix, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.put('/seats/matrix', {
                project_id: projectId,
                matrix
            });
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Perform bulk seat operations
     * @param {BulkSeatOperation[]} operations - Array of operations
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<{success: number, failed: number, results: Object[]}>}
     */
    async bulkOperations(operations, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.post('/seats/bulk', { operations });
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Bulk create seats
     * @param {string} projectId - Project ID
     * @param {Object[]} seats - Array of seat definitions
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<{created: number, seats: Seat[]}>}
     */
    async bulkCreate(projectId, seats, onLoading) {
        return this.bulkOperations(
            seats.map(seat => ({
                operation: 'create',
                data: { ...seat, project_id: projectId }
            })),
            onLoading
        );
    }

    /**
     * Bulk assign users to seats
     * @param {Object[]} assignments - Array of {seatId, userId} objects
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<{assigned: number, failed: number}>}
     */
    async bulkAssign(assignments, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.post('/seats/bulk/assign', { assignments });
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Bulk vacate seats
     * @param {string[]} seatIds - Seat IDs to vacate
     * @param {Object} [options] - Vacate options
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<{vacated: number, failed: number}>}
     */
    async bulkVacate(seatIds, options = {}, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.post('/seats/bulk/vacate', {
                seat_ids: seatIds,
                ...options
            });
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Get seat statistics for project
     * @param {string} projectId - Project ID
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<Object>}
     */
    async getProjectStats(projectId, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.get(`/seats/stats?project_id=${projectId}`);
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Transfer seat to different project
     * @param {string} seatId - Seat ID
     * @param {string} newProjectId - New project ID
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<Seat>}
     */
    async transferSeat(seatId, newProjectId, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.post(`/seats/${seatId}/transfer`, {
                new_project_id: newProjectId
            });
            return this._formatSeat(response.data);
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Swap seat assignments between two seats
     * @param {string} seatId1 - First seat ID
     * @param {string} seatId2 - Second seat ID
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<{seat1: Seat, seat2: Seat}>}
     */
    async swapAssignments(seatId1, seatId2, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.post('/seats/swap', {
                seat_id_1: seatId1,
                seat_id_2: seatId2
            });
            return {
                seat1: this._formatSeat(response.data.seat1),
                seat2: this._formatSeat(response.data.seat2)
            };
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Get seat history/audit log
     * @param {string} seatId - Seat ID
     * @param {PaginationParams} [params]
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<PaginatedResponse>}
     */
    async getSeatHistory(seatId, params = {}, onLoading) {
        const { page = 1, limit = 20 } = params;
        const query = new URLSearchParams({ page: String(page), limit: String(limit) });

        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.get(`/seats/${seatId}/history?${query}`);
            return this._formatPaginatedResponse(response.data, page);
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Get available users for seat assignment
     * @param {string} projectId - Project ID
     * @param {Object} [filters] - Filter options
     * @param {string} [filters.clearanceTier] - Minimum clearance tier
     * @param {string[]} [filters.compartments] - Required compartments
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<Array>}
     */
    async getAvailableUsers(projectId, filters = {}, onLoading) {
        const query = new URLSearchParams({ project_id: projectId });
        if (filters.clearanceTier) query.append('clearance_tier', filters.clearanceTier);
        if (filters.compartments) query.append('compartments', filters.compartments.join(','));

        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.get(`/seats/available-users?${query}`);
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Validate seat assignment eligibility
     * @param {string} seatId - Seat ID
     * @param {string} userId - User ID
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<{eligible: boolean, reasons?: string[]}>}
     */
    async validateAssignment(seatId, userId, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.get(`/seats/${seatId}/validate-assignment`, {
                params: { user_id: userId }
            });
            return response.data;
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Suspend seat (temporarily disable)
     * @param {string} seatId - Seat ID
     * @param {Object} [options] - Suspend options
     * @param {string} [options.reason] - Suspension reason
     * @param {string} [options.until] - Suspension end date
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<Seat>}
     */
    async suspendSeat(seatId, options = {}, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.post(`/seats/${seatId}/suspend`, options);
            return this._formatSeat(response.data);
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Reactivate suspended seat
     * @param {string} seatId - Seat ID
     * @param {LoadingStateCallback} [onLoading]
     * @returns {Promise<Seat>}
     */
    async reactivateSeat(seatId, onLoading) {
        const unsub = onLoading ? this.client.onLoadingState(onLoading) : null;
        
        try {
            const response = await this.client.post(`/seats/${seatId}/reactivate`);
            return this._formatSeat(response.data);
        } finally {
            if (unsub) unsub();
        }
    }

    /**
     * Subscribe to seat real-time updates
     * @param {string} seatId - Seat ID to subscribe to
     * @param {SeatEventCallback} callback - Event handler
     * @returns {() => void} - Unsubscribe function
     */
    subscribeToUpdates(seatId, callback) {
        return this.client.subscribeWebSocket(`/ws/seats/${seatId}`, callback);
    }

    /**
     * Subscribe to all seat updates for a project
     * @param {string} projectId - Project ID
     * @param {SeatEventCallback} callback - Event handler
     * @returns {() => void} - Unsubscribe function
     */
    subscribeToProjectUpdates(projectId, callback) {
        return this.client.subscribeWebSocket(`/ws/projects/${projectId}/seats`, callback);
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
     * Format seat data to standard format
     * @param {*} data - API seat data
     * @returns {Seat}
     * @private
     */
    _formatSeat(data) {
        return {
            id: data.id,
            projectId: data.project_id || data.projectId,
            userId: data.user_id || data.userId,
            role: data.role,
            rank: data.rank,
            position: data.position,
            groupName: data.group_name || data.groupName,
            clearanceTier: data.clearance_tier || data.clearanceTier,
            compartments: data.compartments || [],
            status: data.status || 'open',
            assignedAt: data.assigned_at || data.assignedAt,
            createdAt: data.created_at || data.createdAt,
            updatedAt: data.updated_at || data.updatedAt,
            ...data
        };
    }
}

// Create singleton instance
const seatsApi = typeof ordlClient !== 'undefined' ? new SeatsApi(ordlClient) : null;

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { SeatsApi, seatsApi };
}
