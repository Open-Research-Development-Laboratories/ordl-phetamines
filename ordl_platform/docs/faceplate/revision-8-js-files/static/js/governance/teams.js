/**
 * ORDL Governance - Teams Page
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize governance API
    const api = window.governanceApi || (typeof governanceApi !== 'undefined' ? governanceApi : null);
    const ui = window.ORDL?.ui;

    // Create Team button
    document.querySelector('[data-action="create-team"]')?.addEventListener('click', function() {
        openTeamModal();
    });

    // Edit Scope button
    document.querySelector('[data-action="edit-scope"]')?.addEventListener('click', async function() {
        const btn = this;
        const hideSpinner = ui?.showSpinner?.(btn, 'Loading...');
        
        try {
            const matrix = await api.getTeamScopeMatrix();
            openScopeMatrixModal(matrix);
        } catch (error) {
            ui?.handleError?.(error, 'Failed to load scope matrix');
        } finally {
            hideSpinner?.();
        }
    });

    // View Team buttons
    document.querySelectorAll('[data-action="view-team"]').forEach(btn => {
        btn.addEventListener('click', async function() {
            const teamId = this.dataset.team;
            const hideSpinner = ui?.showSpinner?.(this, 'Loading...');
            
            try {
                const team = await api.getTeam(teamId);
                openTeamViewModal(team);
            } catch (error) {
                ui?.handleError?.(error, 'Failed to load team');
            } finally {
                hideSpinner?.();
            }
        });
    });

    // Edit Team buttons (add if not present)
    document.querySelectorAll('[data-action="edit-team"]').forEach(btn => {
        btn.addEventListener('click', async function() {
            const teamId = this.dataset.team;
            const hideSpinner = ui?.showSpinner?.(this, 'Loading...');
            
            try {
                const team = await api.getTeam(teamId);
                openTeamModal(team);
            } catch (error) {
                ui?.handleError?.(error, 'Failed to load team');
            } finally {
                hideSpinner?.();
            }
        });
    });

    // Escalation tree selector
    const treeSelect = document.getElementById('escalationTreeSelect');
    if (treeSelect) {
        treeSelect.addEventListener('change', async function() {
            const treeId = this.value;
            if (!treeId) return;
            
            const hideSpinner = ui?.showGlobalLoading?.('Loading...');
            
            try {
                const tree = await api.getEscalationTree(treeId);
                updateEscalationTreeDisplay(tree);
            } catch (error) {
                ui?.handleError?.(error, 'Failed to load escalation tree');
            } finally {
                hideSpinner?.();
            }
        });
    }

    // Search filter
    const searchInput = document.getElementById('teamSearch');
    if (searchInput) {
        searchInput.addEventListener('input', debounce(async function() {
            const query = this.value.trim();
            
            try {
                const result = await api.getTeams({ search: query, page: 1 });
                updateTeamsList(result.items || []);
            } catch (error) {
                // Silent fail for search - filter client-side
                filterTeamsClientSide(query.toLowerCase());
            }
        }, 300));
    }

    // Scope filter
    const scopeFilter = document.getElementById('scopeFilter');
    if (scopeFilter) {
        scopeFilter.addEventListener('change', async function() {
            const scope = this.value;
            const hideSpinner = ui?.showGlobalLoading?.('Filtering...');
            
            try {
                const result = await api.getTeams({ scope, page: 1 });
                updateTeamsList(result.items || []);
            } catch (error) {
                filterTeamsClientSideByScope(scope);
            } finally {
                hideSpinner?.();
            }
        });
    }

    // Helper functions
    function filterTeamsClientSide(query) {
        document.querySelectorAll('.team-card').forEach(card => {
            const name = card.querySelector('h4')?.textContent?.toLowerCase() || '';
            card.style.display = name.includes(query) ? '' : 'none';
        });
    }

    function filterTeamsClientSideByScope(scope) {
        document.querySelectorAll('.team-card').forEach(card => {
            if (!scope) {
                card.style.display = '';
            } else {
                const cardScope = card.querySelector('.scope-badge')?.textContent?.toLowerCase() || '';
                card.style.display = cardScope === scope ? '' : 'none';
            }
        });
    }

    function updateTeamsList(teams) {
        // FIXME: backend gap - implement full teams list rendering
        ui?.showToast?.('Team list updated from API', 'info');
        console.log('Teams to render:', teams);
    }

    function updateEscalationTreeDisplay(tree) {
        const container = document.getElementById('escalationTreeContainer');
        if (!container) return;
        
        container.innerHTML = `
            <div style="padding: 20px; background: rgba(0,0,0,0.2); border-radius: 8px;">
                <h4>${escapeHtml(tree.name || 'Escalation Tree')}</h4>
                <pre style="color: #d4cfc7; font-size: 12px; overflow-x: auto;">${escapeHtml(JSON.stringify(tree, null, 2))}</pre>
            </div>
        `;
    }

    function openTeamModal(team = null) {
        const isEdit = !!team;
        const modalHtml = `
            <div id="team-modal" class="modal" style="display: block; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.7); z-index: 1000;">
                <div style="background: #1a1a1a; max-width: 500px; margin: 50px auto; padding: 24px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1); color: #faf8f5;">
                    <h3>${isEdit ? 'Edit' : 'Create'} Team</h3>
                    <form id="team-form">
                        <div style="margin-bottom: 16px;">
                            <label style="display: block; margin-bottom: 4px; color: #d4cfc7;">Team Name *</label>
                            <input type="text" name="name" value="${escapeHtml(team?.name || '')}" required style="width: 100%; padding: 8px; background: #0d0d0d; border: 1px solid rgba(255,255,255,0.1); color: #faf8f5; border-radius: 4px;">
                        </div>
                        <div style="margin-bottom: 16px;">
                            <label style="display: block; margin-bottom: 4px; color: #d4cfc7;">Operating Scope</label>
                            <select name="scope" style="width: 100%; padding: 8px; background: #0d0d0d; border: 1px solid rgba(255,255,255,0.1); color: #faf8f5; border-radius: 4px;">
                                <option value="Global">Global</option>
                                <option value="Regional">Regional</option>
                                <option value="Project">Project</option>
                            </select>
                        </div>
                        <div style="margin-bottom: 16px;">
                            <label style="display: block; margin-bottom: 4px; color: #d4cfc7;">Team Lead</label>
                            <input type="text" name="lead" value="${escapeHtml(team?.lead || '')}" style="width: 100%; padding: 8px; background: #0d0d0d; border: 1px solid rgba(255,255,255,0.1); color: #faf8f5; border-radius: 4px;">
                        </div>
                        <div style="margin-bottom: 16px;">
                            <label style="display: block; margin-bottom: 4px; color: #d4cfc7;">Clearance Level</label>
                            <select name="clearance" style="width: 100%; padding: 8px; background: #0d0d0d; border: 1px solid rgba(255,255,255,0.1); color: #faf8f5; border-radius: 4px;">
                                <option value="L1">L1 - Restricted</option>
                                <option value="L2">L2 - Standard</option>
                                <option value="L3">L3 - Confidential</option>
                                <option value="L4">L4 - Secret</option>
                                <option value="L5">L5 - Top Secret</option>
                            </select>
                        </div>
                        <div style="display: flex; gap: 10px; justify-content: flex-end; margin-top: 20px;">
                            ${isEdit ? `<button type="button" class="delete-btn" style="padding: 8px 16px; background: #dc2626; border: none; color: white; border-radius: 4px; cursor: pointer; margin-right: auto;">Delete</button>
                            ` : ''}
                            <button type="button" class="cancel-btn" style="padding: 8px 16px; background: transparent; border: 1px solid rgba(255,255,255,0.2); color: #d4cfc7; border-radius: 4px; cursor: pointer;">Cancel</button>
                            <button type="submit" style="padding: 8px 16px; background: #f59e0b; border: none; color: #0d0d0d; border-radius: 4px; cursor: pointer; font-weight: 500;">${isEdit ? 'Update' : 'Create'} Team</button>
                        </div>
                    </form>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        const modal = document.getElementById('team-modal');
        const form = document.getElementById('team-form');
        
        if (team?.scope) form.querySelector('[name="scope"]').value = team.scope;
        if (team?.clearance) form.querySelector('[name="clearance"]').value = team.clearance;
        
        modal.querySelector('.cancel-btn')?.addEventListener('click', () => {
            modal.remove();
        });
        
        modal.querySelector('.delete-btn')?.addEventListener('click', async () => {
            const confirmed = await ui?.confirmDialog?.(
                `Delete team "${team.name}"?`,
                { title: 'Delete Team', confirmText: 'Delete', confirmClass: 'danger' }
            );
            
            if (!confirmed) return;
            
            const hideSpinner = ui?.showSpinner?.(modal.querySelector('.delete-btn'), 'Deleting...');
            
            try {
                await api.deleteTeam(team.id);
                ui?.showToast?.('Team deleted successfully', 'success');
                modal.remove();
                ui?.refreshData?.();
            } catch (error) {
                ui?.handleError?.(error, 'Failed to delete team');
            } finally {
                hideSpinner?.();
            }
        });
        
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.remove();
        });
        
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const submitBtn = form.querySelector('button[type="submit"]');
            const hideSpinner = ui?.showSpinner?.(submitBtn, isEdit ? 'Updating...' : 'Creating...');
            
            try {
                const formData = new FormData(form);
                const data = {
                    name: formData.get('name'),
                    scope: formData.get('scope'),
                    lead: formData.get('lead'),
                    clearance: formData.get('clearance')
                };
                
                if (isEdit) {
                    await api.updateTeam(team.id, data);
                    ui?.showToast?.('Team updated successfully', 'success');
                } else {
                    await api.createTeam(data);
                    ui?.showToast?.('Team created successfully', 'success');
                }
                
                modal.remove();
                ui?.refreshData?.();
            } catch (error) {
                ui?.handleError?.(error, isEdit ? 'Failed to update team' : 'Failed to create team');
            } finally {
                hideSpinner?.();
            }
        });
    }

    function openTeamViewModal(team) {
        const modalHtml = `
            <div id="team-view-modal" class="modal" style="display: block; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.7); z-index: 1000;">
                <div style="background: #1a1a1a; max-width: 500px; margin: 50px auto; padding: 24px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1); color: #faf8f5;">
                    <h3>${escapeHtml(team.name)}</h3>
                    <div style="margin-bottom: 16px;">
                        <div style="color: #a8a39c; font-size: 12px; text-transform: uppercase; margin-bottom: 4px;">Scope</div>
                        <div><span class="scope-badge" style="display: inline-block; padding: 4px 12px; border-radius: 4px; font-size: 12px; background: rgba(245,158,11,0.2); color: #f59e0b;">${escapeHtml(team.scope || 'Unknown')}</span></div>
                    </div>
                    <div style="margin-bottom: 16px;">
                        <div style="color: #a8a39c; font-size: 12px; text-transform: uppercase; margin-bottom: 4px;">Lead</div>
                        <div>${escapeHtml(team.lead || 'Not assigned')}</div>
                    </div>
                    <div style="margin-bottom: 16px;">
                        <div style="color: #a8a39c; font-size: 12px; text-transform: uppercase; margin-bottom: 4px;">Clearance</div>
                        <div>${escapeHtml(team.clearance || 'L1')}</div>
                    </div>
                    <div style="margin-bottom: 16px;">
                        <div style="color: #a8a39c; font-size: 12px; text-transform: uppercase; margin-bottom: 4px;">Members</div>
                        <div>${team.members || 0}</div>
                    </div>
                    <div style="margin-bottom: 16px;">
                        <div style="color: #a8a39c; font-size: 12px; text-transform: uppercase; margin-bottom: 4px;">Projects</div>
                        <div>${team.projects || 0}</div>
                    </div>
                    <div style="display: flex; gap: 10px; justify-content: flex-end; margin-top: 20px;">
                        <button type="button" class="close-btn" style="padding: 8px 16px; background: transparent; border: 1px solid rgba(255,255,255,0.2); color: #d4cfc7; border-radius: 4px; cursor: pointer;">Close</button>
                        <button type="button" class="edit-btn" style="padding: 8px 16px; background: #f59e0b; border: none; color: #0d0d0d; border-radius: 4px; cursor: pointer; font-weight: 500;">Edit Team</button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        const modal = document.getElementById('team-view-modal');
        
        modal.querySelector('.close-btn').addEventListener('click', () => {
            modal.remove();
        });
        
        modal.querySelector('.edit-btn').addEventListener('click', () => {
            modal.remove();
            openTeamModal(team);
        });
        
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.remove();
        });
    }

    function openScopeMatrixModal(matrix) {
        ui?.showToast?.('Scope matrix editor - FIXME: backend gap PUT /v1/teams/scope-matrix', 'warning');
        console.log('Scope matrix editor:', matrix);
    }

    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function debounce(fn, ms) {
        let timeout;
        return function(...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => fn.apply(this, args), ms);
        };
    }
});
