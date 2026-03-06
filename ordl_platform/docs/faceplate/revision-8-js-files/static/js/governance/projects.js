/**
 * ORDL Governance - Projects Page
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize governance API
    const api = window.governanceApi || (typeof governanceApi !== 'undefined' ? governanceApi : null);
    const ui = window.ORDL?.ui;

    // Create Project button
    document.querySelector('[data-action="create-project"]')?.addEventListener('click', function() {
        openProjectModal();
    });

    // Edit Defaults button
    document.querySelector('[data-action="edit-defaults"]')?.addEventListener('click', async function() {
        const btn = this;
        const hideSpinner = ui?.showSpinner?.(btn, 'Loading...');
        
        try {
            const defaults = await api.getProjectDefaultClearance();
            openDefaultsModal(defaults);
        } catch (error) {
            ui?.handleError?.(error, 'Failed to load default clearance');
        } finally {
            hideSpinner?.();
        }
    });

    // View Project buttons
    document.querySelectorAll('[data-action="view-project"]').forEach(btn => {
        btn.addEventListener('click', async function() {
            const projectId = this.dataset.project;
            const hideSpinner = ui?.showSpinner?.(this, 'Loading...');
            
            try {
                const project = await api.getProject(projectId);
                openProjectViewModal(project);
            } catch (error) {
                ui?.handleError?.(error, 'Failed to load project');
            } finally {
                hideSpinner?.();
            }
        });
    });

    // Edit Project buttons
    document.querySelectorAll('[data-action="edit-project"]').forEach(btn => {
        btn.addEventListener('click', async function() {
            const projectId = this.dataset.project;
            const hideSpinner = ui?.showSpinner?.(this, 'Loading...');
            
            try {
                const project = await api.getProject(projectId);
                openProjectModal(project);
            } catch (error) {
                ui?.handleError?.(error, 'Failed to load project');
            } finally {
                hideSpinner?.();
            }
        });
    });

    // Manage Seats buttons
    document.querySelectorAll('[data-action="manage-seats"]').forEach(btn => {
        btn.addEventListener('click', function() {
            const projectId = this.dataset.project;
            window.location.href = `/app/seats?project=${encodeURIComponent(projectId)}`;
        });
    });

    // Search filter
    const searchInput = document.getElementById('projectSearch');
    if (searchInput) {
        searchInput.addEventListener('input', debounce(async function() {
            const query = this.value.trim();
            
            try {
                const result = await api.getProjects({ search: query, page: 1 });
                updateProjectsList(result.items || []);
            } catch (error) {
                // Silent fail for search - just filter client-side
                filterProjectsClientSide(query.toLowerCase());
            }
        }, 300));
    }

    // Status filter
    const statusFilter = document.getElementById('statusFilter');
    if (statusFilter) {
        statusFilter.addEventListener('change', async function() {
            const status = this.value;
            const hideSpinner = ui?.showGlobalLoading?.('Filtering...');
            
            try {
                const result = await api.getProjects({ status, page: 1 });
                updateProjectsList(result.items || []);
            } catch (error) {
                // Fallback to client-side filtering
                document.querySelectorAll('.project-row').forEach(row => {
                    if (!status) {
                        row.style.display = '';
                    } else {
                        const rowStatus = row.querySelector('.status-badge')?.textContent?.toLowerCase();
                        row.style.display = rowStatus === status ? '' : 'none';
                    }
                });
            } finally {
                hideSpinner?.();
            }
        });
    }

    // Helper functions
    function filterProjectsClientSide(query) {
        document.querySelectorAll('.project-row').forEach(row => {
            const name = row.querySelector('h4')?.textContent?.toLowerCase() || '';
            row.style.display = name.includes(query) ? '' : 'none';
        });
    }

    function updateProjectsList(projects) {
        const container = document.querySelector('.projects-list');
        if (!container) return;
        
        // FIXME: backend gap - implement full project list rendering
        ui?.showToast?.('Project list updated from API', 'info');
        console.log('Projects to render:', projects);
    }

    function openProjectModal(project = null) {
        const isEdit = !!project;
        const modalHtml = `
            <div id="project-modal" class="modal" style="display: block; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.7); z-index: 1000;">
                <div style="background: #1a1a1a; max-width: 600px; margin: 50px auto; padding: 24px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1); color: #faf8f5; max-height: 80vh; overflow-y: auto;">
                    <h3>${isEdit ? 'Edit' : 'Create'} Project</h3>
                    <form id="project-form">
                        <div style="margin-bottom: 16px;">
                            <label style="display: block; margin-bottom: 4px; color: #d4cfc7;">Project Name *</label>
                            <input type="text" name="name" value="${escapeHtml(project?.name || '')}" required style="width: 100%; padding: 8px; background: #0d0d0d; border: 1px solid rgba(255,255,255,0.1); color: #faf8f5; border-radius: 4px;">
                        </div>
                        <div style="margin-bottom: 16px;">
                            <label style="display: block; margin-bottom: 4px; color: #d4cfc7;">Owner</label>
                            <input type="text" name="owner" value="${escapeHtml(project?.owner || '')}" style="width: 100%; padding: 8px; background: #0d0d0d; border: 1px solid rgba(255,255,255,0.1); color: #faf8f5; border-radius: 4px;">
                        </div>
                        <div style="margin-bottom: 16px;">
                            <label style="display: block; margin-bottom: 4px; color: #d4cfc7;">Team</label>
                            <input type="text" name="team" value="${escapeHtml(project?.team || '')}" style="width: 100%; padding: 8px; background: #0d0d0d; border: 1px solid rgba(255,255,255,0.1); color: #faf8f5; border-radius: 4px;">
                        </div>
                        <div style="margin-bottom: 16px;">
                            <label style="display: block; margin-bottom: 4px; color: #d4cfc7;">Status</label>
                            <select name="status" style="width: 100%; padding: 8px; background: #0d0d0d; border: 1px solid rgba(255,255,255,0.1); color: #faf8f5; border-radius: 4px;">
                                <option value="planning">Planning</option>
                                <option value="active">Active</option>
                                <option value="archived">Archived</option>
                            </select>
                        </div>
                        <div style="margin-bottom: 16px;">
                            <label style="display: block; margin-bottom: 4px; color: #d4cfc7;">Default Clearance</label>
                            <select name="clearance" style="width: 100%; padding: 8px; background: #0d0d0d; border: 1px solid rgba(255,255,255,0.1); color: #faf8f5; border-radius: 4px;">
                                <option value="L1">L1 - Restricted</option>
                                <option value="L2">L2 - Standard</option>
                                <option value="L3">L3 - Confidential</option>
                                <option value="L4">L4 - Secret</option>
                                <option value="L5">L5 - Top Secret</option>
                            </select>
                        </div>
                        <div style="margin-bottom: 16px;">
                            <label style="display: block; margin-bottom: 4px; color: #d4cfc7;">Compartments (comma-separated)</label>
                            <input type="text" name="compartments" value="${escapeHtml((project?.compartments || []).join(', '))}" placeholder="e.g. R&D, AI-Core" style="width: 100%; padding: 8px; background: #0d0d0d; border: 1px solid rgba(255,255,255,0.1); color: #faf8f5; border-radius: 4px;">
                        </div>
                        <div style="display: flex; gap: 10px; justify-content: flex-end; margin-top: 20px;">
                            ${isEdit ? `<button type="button" class="delete-btn" style="padding: 8px 16px; background: #dc2626; border: none; color: white; border-radius: 4px; cursor: pointer; margin-right: auto;">Delete</button>
                            ` : ''}
                            <button type="button" class="cancel-btn" style="padding: 8px 16px; background: transparent; border: 1px solid rgba(255,255,255,0.2); color: #d4cfc7; border-radius: 4px; cursor: pointer;">Cancel</button>
                            <button type="submit" style="padding: 8px 16px; background: #f59e0b; border: none; color: #0d0d0d; border-radius: 4px; cursor: pointer; font-weight: 500;">${isEdit ? 'Update' : 'Create'} Project</button>
                        </div>
                    </form>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        const modal = document.getElementById('project-modal');
        const form = document.getElementById('project-form');
        
        if (project?.status) form.querySelector('[name="status"]').value = project.status;
        if (project?.clearance) form.querySelector('[name="clearance"]').value = project.clearance;
        
        modal.querySelector('.cancel-btn')?.addEventListener('click', () => {
            modal.remove();
        });
        
        modal.querySelector('.delete-btn')?.addEventListener('click', async () => {
            const confirmed = await ui?.confirmDialog?.(
                `Are you sure you want to delete project "${project.name}"? This action cannot be undone.`,
                { title: 'Delete Project', confirmText: 'Delete', confirmClass: 'danger' }
            );
            
            if (!confirmed) return;
            
            const hideSpinner = ui?.showSpinner?.(modal.querySelector('.delete-btn'), 'Deleting...');
            
            try {
                await api.deleteProject(project.id);
                ui?.showToast?.('Project deleted successfully', 'success');
                modal.remove();
                ui?.refreshData?.();
            } catch (error) {
                ui?.handleError?.(error, 'Failed to delete project');
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
                const compartments = formData.get('compartments').split(',').map(s => s.trim()).filter(Boolean);
                
                const data = {
                    name: formData.get('name'),
                    owner: formData.get('owner'),
                    team: formData.get('team'),
                    status: formData.get('status'),
                    clearance: formData.get('clearance'),
                    compartments: compartments
                };
                
                if (isEdit) {
                    await api.updateProject(project.id, data);
                    ui?.showToast?.('Project updated successfully', 'success');
                } else {
                    await api.createProject(data);
                    ui?.showToast?.('Project created successfully', 'success');
                }
                
                modal.remove();
                ui?.refreshData?.();
            } catch (error) {
                ui?.handleError?.(error, isEdit ? 'Failed to update project' : 'Failed to create project');
            } finally {
                hideSpinner?.();
            }
        });
    }

    function openProjectViewModal(project) {
        const modalHtml = `
            <div id="project-view-modal" class="modal" style="display: block; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.7); z-index: 1000;">
                <div style="background: #1a1a1a; max-width: 600px; margin: 50px auto; padding: 24px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1); color: #faf8f5;">
                    <h3>${escapeHtml(project.name)}</h3>
                    <div style="margin-bottom: 16px;">
                        <div style="color: #a8a39c; font-size: 12px; text-transform: uppercase; margin-bottom: 4px;">Status</div>
                        <div><span class="status-badge status-${project.status}" style="padding: 4px 12px; border-radius: 4px; font-size: 12px; text-transform: capitalize; background: ${getStatusColor(project.status)};">${project.status}</span></div>
                    </div>
                    <div style="margin-bottom: 16px;">
                        <div style="color: #a8a39c; font-size: 12px; text-transform: uppercase; margin-bottom: 4px;">Owner</div>
                        <div>${escapeHtml(project.owner || 'Not assigned')}</div>
                    </div>
                    <div style="margin-bottom: 16px;">
                        <div style="color: #a8a39c; font-size: 12px; text-transform: uppercase; margin-bottom: 4px;">Team</div>
                        <div>${escapeHtml(project.team || 'Not assigned')}</div>
                    </div>
                    <div style="margin-bottom: 16px;">
                        <div style="color: #a8a39c; font-size: 12px; text-transform: uppercase; margin-bottom: 4px;">Clearance</div>
                        <div>${project.clearance || 'L1'}</div>
                    </div>
                    <div style="margin-bottom: 16px;">
                        <div style="color: #a8a39c; font-size: 12px; text-transform: uppercase; margin-bottom: 4px;">Compartments</div>
                        <div>${(project.compartments || []).map(c => `<span style="display: inline-block; padding: 2px 8px; background: rgba(245,158,11,0.2); color: #f59e0b; border-radius: 4px; margin-right: 4px; font-size: 12px;">${escapeHtml(c)}</span>`).join('') || 'None'}</div>
                    </div>
                    <div style="display: flex; gap: 10px; justify-content: flex-end; margin-top: 20px;">
                        <button type="button" class="close-btn" style="padding: 8px 16px; background: transparent; border: 1px solid rgba(255,255,255,0.2); color: #d4cfc7; border-radius: 4px; cursor: pointer;">Close</button>
                        <a href="/app/seats?project=${encodeURIComponent(project.id)}" style="padding: 8px 16px; background: #f59e0b; border: none; color: #0d0d0d; border-radius: 4px; cursor: pointer; font-weight: 500; text-decoration: none;">Manage Seats</a>
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        const modal = document.getElementById('project-view-modal');
        modal.querySelector('.close-btn').addEventListener('click', () => {
            modal.remove();
        });
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.remove();
        });
    }

    function openDefaultsModal(defaults) {
        const modalHtml = `
            <div id="defaults-modal" class="modal" style="display: block; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.7); z-index: 1000;">
                <div style="background: #1a1a1a; max-width: 500px; margin: 50px auto; padding: 24px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1); color: #faf8f5;">
                    <h3>Edit Default Clearance</h3>
                    <form id="defaults-form">
                        <div style="margin-bottom: 16px;">
                            <label style="display: block; margin-bottom: 4px; color: #d4cfc7;">Default Clearance Level</label>
                            <select name="clearance" style="width: 100%; padding: 8px; background: #0d0d0d; border: 1px solid rgba(255,255,255,0.1); color: #faf8f5; border-radius: 4px;">
                                <option value="L1">L1 - Restricted</option>
                                <option value="L2">L2 - Standard</option>
                                <option value="L3">L3 - Confidential</option>
                                <option value="L4">L4 - Secret</option>
                                <option value="L5">L5 - Top Secret</option>
                            </select>
                        </div>
                        <div style="display: flex; gap: 10px; justify-content: flex-end; margin-top: 20px;">
                            <button type="button" class="cancel-btn" style="padding: 8px 16px; background: transparent; border: 1px solid rgba(255,255,255,0.2); color: #d4cfc7; border-radius: 4px; cursor: pointer;">Cancel</button>
                            <button type="submit" style="padding: 8px 16px; background: #f59e0b; border: none; color: #0d0d0d; border-radius: 4px; cursor: pointer; font-weight: 500;">Save Changes</button>
                        </div>
                    </form>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        const modal = document.getElementById('defaults-modal');
        const form = document.getElementById('defaults-form');
        
        if (defaults?.clearance) {
            form.querySelector('[name="clearance"]').value = defaults.clearance;
        }
        
        modal.querySelector('.cancel-btn').addEventListener('click', () => {
            modal.remove();
        });
        
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.remove();
        });
        
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const submitBtn = form.querySelector('button[type="submit"]');
            const hideSpinner = ui?.showSpinner?.(submitBtn, 'Saving...');
            
            try {
                const formData = new FormData(form);
                await api.updateProjectDefaultClearance({
                    clearance: formData.get('clearance')
                });
                ui?.showToast?.('Default clearance updated successfully', 'success');
                modal.remove();
            } catch (error) {
                ui?.handleError?.(error, 'Failed to update defaults');
            } finally {
                hideSpinner?.();
            }
        });
    }

    function getStatusColor(status) {
        const colors = {
            active: 'rgba(34,197,94,0.2)',
            planning: 'rgba(59,130,246,0.2)',
            archived: 'rgba(168,163,156,0.2)'
        };
        return colors[status] || colors.planning;
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
