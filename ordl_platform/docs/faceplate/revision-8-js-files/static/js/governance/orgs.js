/**
 * ORDL Governance - Organizations Page
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize governance API
    const api = window.governanceApi || (typeof governanceApi !== 'undefined' ? governanceApi : null);
    const ui = window.ORDL?.ui;

    // Edit Profile button
    document.querySelector('[data-action="edit-profile"]')?.addEventListener('click', async function() {
        const btn = this;
        const hideSpinner = ui?.showSpinner?.(btn, 'Loading...');
        
        try {
            const org = await api.getOrganization();
            openProfileModal(org);
        } catch (error) {
            ui?.handleError?.(error, 'Failed to load organization profile');
        } finally {
            hideSpinner?.();
        }
    });

    // Add Board Member button
    document.querySelector('[data-action="add-board-member"]')?.addEventListener('click', function() {
        openBoardMemberModal();
    });

    // Edit Defaults button
    document.querySelector('[data-action="edit-defaults"]')?.addEventListener('click', async function() {
        const btn = this;
        const hideSpinner = ui?.showSpinner?.(btn, 'Loading...');
        
        try {
            const defaults = await api.getPolicyDefaults();
            openDefaultsModal(defaults);
        } catch (error) {
            ui?.handleError?.(error, 'Failed to load policy defaults');
        } finally {
            hideSpinner?.();
        }
    });

    // Add Region button
    document.querySelector('[data-action="add-region"]')?.addEventListener('click', function() {
        openRegionModal();
    });

    // Board member action buttons
    document.querySelectorAll('[data-action="view-board-history"]').forEach(btn => {
        btn.addEventListener('click', async function() {
            const memberId = this.closest('tr')?.dataset?.memberId;
            if (!memberId) return;
            
            const hideSpinner = ui?.showSpinner?.(this, 'Loading...');
            
            try {
                const history = await api.getBoardMemberHistory(memberId);
                openHistoryModal(history, memberId);
            } catch (error) {
                ui?.handleError?.(error, 'Failed to load member history');
            } finally {
                hideSpinner?.();
            }
        });
    });

    // Helper functions
    function openProfileModal(org) {
        const modalHtml = `
            <div id="profile-modal" class="modal" style="display: block; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.7); z-index: 1000;">
                <div style="background: #1a1a1a; max-width: 600px; margin: 50px auto; padding: 24px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1); color: #faf8f5;">
                    <h3>Edit Organization Profile</h3>
                    <form id="profile-form">
                        <div style="margin-bottom: 16px;">
                            <label style="display: block; margin-bottom: 4px; color: #d4cfc7;">Organization Name</label>
                            <input type="text" name="name" value="${escapeHtml(org?.name || '')}" style="width: 100%; padding: 8px; background: #0d0d0d; border: 1px solid rgba(255,255,255,0.1); color: #faf8f5; border-radius: 4px;">
                        </div>
                        <div style="margin-bottom: 16px;">
                            <label style="display: block; margin-bottom: 4px; color: #d4cfc7;">Legal Name</label>
                            <input type="text" name="legalName" value="${escapeHtml(org?.legalName || '')}" style="width: 100%; padding: 8px; background: #0d0d0d; border: 1px solid rgba(255,255,255,0.1); color: #faf8f5; border-radius: 4px;">
                        </div>
                        <div style="margin-bottom: 16px;">
                            <label style="display: block; margin-bottom: 4px; color: #d4cfc7;">Industry</label>
                            <input type="text" name="industry" value="${escapeHtml(org?.industry || '')}" style="width: 100%; padding: 8px; background: #0d0d0d; border: 1px solid rgba(255,255,255,0.1); color: #faf8f5; border-radius: 4px;">
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
        
        const modal = document.getElementById('profile-modal');
        const form = document.getElementById('profile-form');
        
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
                await api.updateOrganization({
                    name: formData.get('name'),
                    legalName: formData.get('legalName'),
                    industry: formData.get('industry')
                });
                ui?.showToast?.('Organization profile updated successfully', 'success');
                modal.remove();
                ui?.refreshData?.();
            } catch (error) {
                ui?.handleError?.(error, 'Failed to update profile');
            } finally {
                hideSpinner?.();
            }
        });
    }

    function openBoardMemberModal(member = null) {
        const isEdit = !!member;
        const modalHtml = `
            <div id="board-member-modal" class="modal" style="display: block; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.7); z-index: 1000;">
                <div style="background: #1a1a1a; max-width: 500px; margin: 50px auto; padding: 24px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1); color: #faf8f5;">
                    <h3>${isEdit ? 'Edit' : 'Add'} Board Member</h3>
                    <form id="board-member-form">
                        <div style="margin-bottom: 16px;">
                            <label style="display: block; margin-bottom: 4px; color: #d4cfc7;">Name</label>
                            <input type="text" name="name" value="${escapeHtml(member?.name || '')}" required style="width: 100%; padding: 8px; background: #0d0d0d; border: 1px solid rgba(255,255,255,0.1); color: #faf8f5; border-radius: 4px;">
                        </div>
                        <div style="margin-bottom: 16px;">
                            <label style="display: block; margin-bottom: 4px; color: #d4cfc7;">Role</label>
                            <select name="role" style="width: 100%; padding: 8px; background: #0d0d0d; border: 1px solid rgba(255,255,255,0.1); color: #faf8f5; border-radius: 4px;">
                                <option value="Chair">Chair</option>
                                <option value="Secretary">Secretary</option>
                                <option value="Risk Officer">Risk Officer</option>
                                <option value="Member">Member</option>
                            </select>
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
                            <button type="button" class="cancel-btn" style="padding: 8px 16px; background: transparent; border: 1px solid rgba(255,255,255,0.2); color: #d4cfc7; border-radius: 4px; cursor: pointer;">Cancel</button>
                            <button type="submit" style="padding: 8px 16px; background: #f59e0b; border: none; color: #0d0d0d; border-radius: 4px; cursor: pointer; font-weight: 500;">${isEdit ? 'Update' : 'Add'} Member</button>
                        </div>
                    </form>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        const modal = document.getElementById('board-member-modal');
        const form = document.getElementById('board-member-form');
        
        if (member?.role) form.querySelector('[name="role"]').value = member.role;
        if (member?.clearance) form.querySelector('[name="clearance"]').value = member.clearance;
        
        modal.querySelector('.cancel-btn').addEventListener('click', () => {
            modal.remove();
        });
        
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.remove();
        });
        
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const submitBtn = form.querySelector('button[type="submit"]');
            const hideSpinner = ui?.showSpinner?.(submitBtn, isEdit ? 'Updating...' : 'Adding...');
            
            try {
                const formData = new FormData(form);
                const data = {
                    name: formData.get('name'),
                    role: formData.get('role'),
                    clearance: formData.get('clearance')
                };
                
                if (isEdit) {
                    await api.updateBoardMember(member.id, data);
                    ui?.showToast?.('Board member updated successfully', 'success');
                } else {
                    await api.addBoardMember(data);
                    ui?.showToast?.('Board member added successfully', 'success');
                }
                
                modal.remove();
                ui?.refreshData?.();
            } catch (error) {
                ui?.handleError?.(error, isEdit ? 'Failed to update member' : 'Failed to add member');
            } finally {
                hideSpinner?.();
            }
        });
    }

    function openDefaultsModal(defaults) {
        ui?.showToast?.('Policy defaults editor - FIXME: backend gap PUT /v1/orgs/policy-defaults', 'warning');
        console.log('Opening defaults modal:', defaults);
    }

    function openRegionModal(region = null) {
        const isEdit = !!region;
        const modalHtml = `
            <div id="region-modal" class="modal" style="display: block; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.7); z-index: 1000;">
                <div style="background: #1a1a1a; max-width: 500px; margin: 50px auto; padding: 24px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1); color: #faf8f5;">
                    <h3>${isEdit ? 'Edit' : 'Add'} Region</h3>
                    <form id="region-form">
                        <div style="margin-bottom: 16px;">
                            <label style="display: block; margin-bottom: 4px; color: #d4cfc7;">Region Code</label>
                            <input type="text" name="code" value="${escapeHtml(region?.code || '')}" ${isEdit ? 'readonly' : ''} required style="width: 100%; padding: 8px; background: ${isEdit ? '#0d0d0d' : '#0d0d0d'}; border: 1px solid rgba(255,255,255,0.1); color: ${isEdit ? '#a8a39c' : '#faf8f5'}; border-radius: 4px;">
                        </div>
                        <div style="margin-bottom: 16px;">
                            <label style="display: block; margin-bottom: 4px; color: #d4cfc7;">Region Name</label>
                            <input type="text" name="name" value="${escapeHtml(region?.name || '')}" required style="width: 100%; padding: 8px; background: #0d0d0d; border: 1px solid rgba(255,255,255,0.1); color: #faf8f5; border-radius: 4px;">
                        </div>
                        <div style="margin-bottom: 16px;">
                            <label style="display: block; margin-bottom: 4px; color: #d4cfc7;">Compliance Framework</label>
                            <select name="compliance" style="width: 100%; padding: 8px; background: #0d0d0d; border: 1px solid rgba(255,255,255,0.1); color: #faf8f5; border-radius: 4px;">
                                <option value="SOC2">SOC2</option>
                                <option value="GDPR">GDPR</option>
                                <option value="HIPAA">HIPAA</option>
                                <option value="PCI">PCI DSS</option>
                                <option value="PDPA">PDPA</option>
                            </select>
                        </div>
                        <div style="display: flex; gap: 10px; justify-content: flex-end; margin-top: 20px;">
                            <button type="button" class="cancel-btn" style="padding: 8px 16px; background: transparent; border: 1px solid rgba(255,255,255,0.2); color: #d4cfc7; border-radius: 4px; cursor: pointer;">Cancel</button>
                            <button type="submit" style="padding: 8px 16px; background: #f59e0b; border: none; color: #0d0d0d; border-radius: 4px; cursor: pointer; font-weight: 500;">${isEdit ? 'Update' : 'Add'} Region</button>
                        </div>
                    </form>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        const modal = document.getElementById('region-modal');
        const form = document.getElementById('region-form');
        
        if (region?.compliance) form.querySelector('[name="compliance"]').value = region.compliance;
        
        modal.querySelector('.cancel-btn').addEventListener('click', () => {
            modal.remove();
        });
        
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.remove();
        });
        
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const submitBtn = form.querySelector('button[type="submit"]');
            const hideSpinner = ui?.showSpinner?.(submitBtn, isEdit ? 'Updating...' : 'Adding...');
            
            try {
                const formData = new FormData(form);
                const data = {
                    code: formData.get('code'),
                    name: formData.get('name'),
                    compliance: formData.get('compliance')
                };
                
                if (isEdit) {
                    await api.updateRegion(region.code, data);
                    ui?.showToast?.('Region updated successfully', 'success');
                } else {
                    await api.addRegion(data);
                    ui?.showToast?.('Region added successfully', 'success');
                }
                
                modal.remove();
                ui?.refreshData?.();
            } catch (error) {
                ui?.handleError?.(error, isEdit ? 'Failed to update region' : 'Failed to add region');
            } finally {
                hideSpinner?.();
            }
        });
    }

    function openHistoryModal(history, memberId) {
        ui?.showToast?.(`Viewing history for member ${memberId}`, 'info');
        console.log('Member history:', history);
    }

    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
});
