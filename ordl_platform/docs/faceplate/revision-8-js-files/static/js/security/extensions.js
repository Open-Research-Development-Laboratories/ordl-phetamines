/**
 * ORDL Security - Extensions Page
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize security API
    const api = window.securityApi || (typeof securityApi !== 'undefined' ? securityApi : null);
    const ui = window.ORDL?.ui;

    // Register Extension button
    document.querySelector('[data-action="register-extension"]')?.addEventListener('click', function() {
        openExtensionModal();
    });

    // Verify All button
    document.querySelector('[data-action="verify-all"]')?.addEventListener('click', async function() {
        const confirmed = await ui?.confirmDialog?.(
            'Verify all extensions? This may take a moment.',
            { title: 'Verify All Extensions', confirmText: 'Verify All' }
        );
        
        if (!confirmed) return;
        
        const btn = this;
        const hideSpinner = ui?.showSpinner?.(btn, 'Verifying...');
        
        try {
            const result = await api.verifyAllExtensions();
            ui?.showToast?.(`Verified ${result.verified || 0} extensions`, 'success');
            ui?.refreshData?.();
        } catch (error) {
            ui?.handleError?.(error, 'Failed to verify extensions');
        } finally {
            hideSpinner?.();
        }
    });

    // Emergency Revoke button
    document.querySelector('[data-action="emergency-revoke"]')?.addEventListener('click', async function() {
        const confirmed = await ui?.confirmDialog?.(
            'EMERGENCY: Revoke ALL extensions? This will disable all plugins, skills, and MCP integrations immediately. This action cannot be undone.',
            { title: 'EMERGENCY REVOKE', confirmText: 'REVOKE ALL', confirmClass: 'danger' }
        );
        
        if (!confirmed) return;
        
        const reason = prompt('Enter reason for emergency revocation (required for audit trail):');
        if (!reason) {
            ui?.showToast?.('Emergency revoke cancelled - reason required', 'warning');
            return;
        }
        
        const btn = this;
        const hideSpinner = ui?.showSpinner?.(btn, 'Revoking...');
        
        try {
            await api.emergencyRevokeAll(reason);
            ui?.showToast?.('Emergency revoke completed', 'success');
            ui?.refreshData?.();
        } catch (error) {
            ui?.handleError?.(error, 'Emergency revoke failed');
        } finally {
            hideSpinner?.();
        }
    });

    // View Sig Log button
    document.querySelector('[data-action="view-sig-log"]')?.addEventListener('click', async function() {
        ui?.showToast?.('Signature log viewer - FIXME: backend gap /v1/extensions/signature-log', 'warning');
    });

    // Tab switching
    document.querySelectorAll('.tab-btn').forEach(tab => {
        tab.addEventListener('click', async function() {
            document.querySelectorAll('.tab-btn').forEach(t => t.classList.remove('active'));
            this.classList.add('active');
            
            const tabType = this.dataset.tab;
            filterExtensions(tabType);
            
            // If switching tabs, try to fetch filtered data from API
            if (tabType !== 'all') {
                try {
                    const result = await api.getExtensions({ type: tabType === 'all' ? undefined : tabType });
                    updateExtensionsList(result.items || []);
                } catch (error) {
                    // Silent fail - client-side filtering already applied
                }
            }
        });
    });

    function filterExtensions(type) {
        document.querySelectorAll('.extension-card').forEach(card => {
            if (type === 'all') {
                card.style.display = '';
            } else {
                const cardType = card.dataset.type;
                card.style.display = cardType === type ? '' : 'none';
            }
        });
    }

    function updateExtensionsList(extensions) {
        // FIXME: backend gap - implement full extensions list rendering
        ui?.showToast?.('Extensions list updated from API', 'info');
        console.log('Extensions to render:', extensions);
    }

    // View Extension buttons
    document.querySelectorAll('[data-action="view-ext"]').forEach(btn => {
        btn.addEventListener('click', async function() {
            const extId = this.dataset.ext;
            const hideSpinner = ui?.showSpinner?.(this, 'Loading...');
            
            try {
                const extension = await api.getExtension(extId);
                openExtensionViewModal(extension);
            } catch (error) {
                ui?.handleError?.(error, 'Failed to load extension');
            } finally {
                hideSpinner?.();
            }
        });
    });

    // Verify Extension buttons
    document.querySelectorAll('[data-action="verify-ext"]').forEach(btn => {
        btn.addEventListener('click', async function() {
            const extId = this.dataset.ext;
            const hideSpinner = ui?.showSpinner?.(this, 'Verifying...');
            
            try {
                const result = await api.verifyExtension(extId);
                if (result.verified) {
                    ui?.showToast?.('Extension verified successfully', 'success');
                } else {
                    ui?.showToast?.('Extension verification failed', 'error');
                }
                ui?.refreshData?.();
            } catch (error) {
                ui?.handleError?.(error, 'Failed to verify extension');
            } finally {
                hideSpinner?.();
            }
        });
    });

    // Revoke Extension buttons
    document.querySelectorAll('[data-action="revoke-ext"]').forEach(btn => {
        btn.addEventListener('click', async function() {
            const extId = this.dataset.ext;
            
            const confirmed = await ui?.confirmDialog?.(
                `Revoke extension ${extId}? This will immediately disable the extension.`,
                { title: 'Revoke Extension', confirmText: 'Revoke', confirmClass: 'danger' }
            );
            
            if (!confirmed) return;
            
            const reason = prompt('Enter reason for revocation:');
            
            const hideSpinner = ui?.showSpinner?.(this, 'Revoking...');
            
            try {
                await api.revokeExtension(extId, reason);
                ui?.showToast?.('Extension revoked successfully', 'success');
                ui?.refreshData?.();
            } catch (error) {
                ui?.handleError?.(error, 'Failed to revoke extension');
            } finally {
                hideSpinner?.();
            }
        });
    });

    // Edit Extension buttons (if present)
    document.querySelectorAll('[data-action="edit-ext"]').forEach(btn => {
        btn.addEventListener('click', async function() {
            const extId = this.dataset.ext;
            const hideSpinner = ui?.showSpinner?.(this, 'Loading...');
            
            try {
                const extension = await api.getExtension(extId);
                openExtensionModal(extension);
            } catch (error) {
                ui?.handleError?.(error, 'Failed to load extension');
            } finally {
                hideSpinner?.();
            }
        });
    });

    // Delete Extension buttons (if present)
    document.querySelectorAll('[data-action="delete-ext"]').forEach(btn => {
        btn.addEventListener('click', async function() {
            const extId = this.dataset.ext;
            
            const confirmed = await ui?.confirmDialog?.(
                `Permanently delete extension ${extId}? This cannot be undone.`,
                { title: 'Delete Extension', confirmText: 'Delete', confirmClass: 'danger' }
            );
            
            if (!confirmed) return;
            
            const hideSpinner = ui?.showSpinner?.(this, 'Deleting...');
            
            try {
                await api.deleteExtension(extId);
                ui?.showToast?.('Extension deleted successfully', 'success');
                ui?.refreshData?.();
            } catch (error) {
                ui?.handleError?.(error, 'Failed to delete extension');
            } finally {
                hideSpinner?.();
            }
        });
    });

    function openExtensionModal(extension = null) {
        const isEdit = !!extension;
        const modalHtml = `
            <div id="extension-modal" class="modal" style="display: block; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.7); z-index: 1000;">
                <div style="background: #1a1a1a; max-width: 500px; margin: 50px auto; padding: 24px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1); color: #faf8f5;">
                    <h3>${isEdit ? 'Edit' : 'Register'} Extension</h3>
                    <form id="extension-form">
                        <div style="margin-bottom: 16px;">
                            <label style="display: block; margin-bottom: 4px; color: #d4cfc7;">Name *</label>
                            <input type="text" name="name" value="${escapeHtml(extension?.name || '')}" required style="width: 100%; padding: 8px; background: #0d0d0d; border: 1px solid rgba(255,255,255,0.1); color: #faf8f5; border-radius: 4px;">
                        </div>
                        <div style="margin-bottom: 16px;">
                            <label style="display: block; margin-bottom: 4px; color: #d4cfc7;">Type</label>
                            <select name="type" style="width: 100%; padding: 8px; background: #0d0d0d; border: 1px solid rgba(255,255,255,0.1); color: #faf8f5; border-radius: 4px;">
                                <option value="plugin">Plugin</option>
                                <option value="skill">Skill</option>
                                <option value="mcp">MCP</option>
                            </select>
                        </div>
                        <div style="margin-bottom: 16px;">
                            <label style="display: block; margin-bottom: 4px; color: #d4cfc7;">Version</label>
                            <input type="text" name="version" value="${escapeHtml(extension?.version || '1.0.0')}" placeholder="1.0.0" style="width: 100%; padding: 8px; background: #0d0d0d; border: 1px solid rgba(255,255,255,0.1); color: #faf8f5; border-radius: 4px;">
                        </div>
                        <div style="margin-bottom: 16px;">
                            <label style="display: block; margin-bottom: 4px; color: #d4cfc7;">Author</label>
                            <input type="text" name="author" value="${escapeHtml(extension?.author || '')}" style="width: 100%; padding: 8px; background: #0d0d0d; border: 1px solid rgba(255,255,255,0.1); color: #faf8f5; border-radius: 4px;">
                        </div>
                        <div style="display: flex; gap: 10px; justify-content: flex-end; margin-top: 20px;">
                            ${isEdit ? `<button type="button" class="delete-btn" style="padding: 8px 16px; background: #dc2626; border: none; color: white; border-radius: 4px; cursor: pointer; margin-right: auto;">Delete</button>
                            ` : ''}
                            <button type="button" class="cancel-btn" style="padding: 8px 16px; background: transparent; border: 1px solid rgba(255,255,255,0.2); color: #d4cfc7; border-radius: 4px; cursor: pointer;">Cancel</button>
                            <button type="submit" style="padding: 8px 16px; background: #f59e0b; border: none; color: #0d0d0d; border-radius: 4px; cursor: pointer; font-weight: 500;">${isEdit ? 'Update' : 'Register'}</button>
                        </div>
                    </form>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        const modal = document.getElementById('extension-modal');
        const form = document.getElementById('extension-form');
        
        if (extension?.type) form.querySelector('[name="type"]').value = extension.type;
        
        modal.querySelector('.cancel-btn')?.addEventListener('click', () => {
            modal.remove();
        });
        
        modal.querySelector('.delete-btn')?.addEventListener('click', async () => {
            const confirmed = await ui?.confirmDialog?.(
                `Delete extension "${extension.name}"?`,
                { title: 'Delete Extension', confirmText: 'Delete', confirmClass: 'danger' }
            );
            
            if (!confirmed) return;
            
            const hideSpinner = ui?.showSpinner?.(modal.querySelector('.delete-btn'), 'Deleting...');
            
            try {
                await api.deleteExtension(extension.id);
                ui?.showToast?.('Extension deleted successfully', 'success');
                modal.remove();
                ui?.refreshData?.();
            } catch (error) {
                ui?.handleError?.(error, 'Failed to delete extension');
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
            const hideSpinner = ui?.showSpinner?.(submitBtn, isEdit ? 'Updating...' : 'Registering...');
            
            try {
                const formData = new FormData(form);
                const data = {
                    name: formData.get('name'),
                    type: formData.get('type'),
                    version: formData.get('version'),
                    author: formData.get('author')
                };
                
                if (isEdit) {
                    await api.updateExtension(extension.id, data);
                    ui?.showToast?.('Extension updated successfully', 'success');
                } else {
                    await api.registerExtension(data);
                    ui?.showToast?.('Extension registered successfully', 'success');
                }
                
                modal.remove();
                ui?.refreshData?.();
            } catch (error) {
                ui?.handleError?.(error, isEdit ? 'Failed to update extension' : 'Failed to register extension');
            } finally {
                hideSpinner?.();
            }
        });
    }

    function openExtensionViewModal(extension) {
        const modalHtml = `
            <div id="extension-view-modal" class="modal" style="display: block; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.7); z-index: 1000;">
                <div style="background: #1a1a1a; max-width: 500px; margin: 50px auto; padding: 24px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1); color: #faf8f5;">
                    <h3>${escapeHtml(extension.name)}</h3>
                    <div style="margin-bottom: 16px;">
                        <div style="color: #a8a39c; font-size: 12px; text-transform: uppercase; margin-bottom: 4px;">ID</div>
                        <div>${escapeHtml(extension.id)}</div>
                    </div>
                    <div style="margin-bottom: 16px;">
                        <div style="color: #a8a39c; font-size: 12px; text-transform: uppercase; margin-bottom: 4px;">Type</div>
                        <div><span style="display: inline-block; padding: 4px 12px; border-radius: 4px; font-size: 12px; text-transform: uppercase; background: rgba(245,158,11,0.2); color: #f59e0b;">${escapeHtml(extension.type)}</span></div>
                    </div>
                    <div style="margin-bottom: 16px;">
                        <div style="color: #a8a39c; font-size: 12px; text-transform: uppercase; margin-bottom: 4px;">Version</div>
                        <div>${escapeHtml(extension.version)}</div>
                    </div>
                    <div style="margin-bottom: 16px;">
                        <div style="color: #a8a39c; font-size: 12px; text-transform: uppercase; margin-bottom: 4px;">Author</div>
                        <div>${escapeHtml(extension.author || 'Unknown')}</div>
                    </div>
                    <div style="margin-bottom: 16px;">
                        <div style="color: #a8a39c; font-size: 12px; text-transform: uppercase; margin-bottom: 4px;">Signature Status</div>
                        <div><span class="signature-${extension.signature}" style="display: inline-block; padding: 4px 12px; border-radius: 4px; font-size: 12px; text-transform: capitalize; background: ${getSignatureColor(extension.signature)};">${escapeHtml(extension.signature)}</span></div>
                    </div>
                    <div style="margin-bottom: 16px;">
                        <div style="color: #a8a39c; font-size: 12px; text-transform: uppercase; margin-bottom: 4px;">Status</div>
                        <div><span class="status-${extension.status}" style="display: inline-block; padding: 4px 12px; border-radius: 4px; font-size: 12px; text-transform: capitalize; background: ${getStatusColor(extension.status)};">${escapeHtml(extension.status)}</span></div>
                    </div>
                    <div style="display: flex; gap: 10px; justify-content: flex-end; margin-top: 20px;">
                        <button type="button" class="close-btn" style="padding: 8px 16px; background: transparent; border: 1px solid rgba(255,255,255,0.2); color: #d4cfc7; border-radius: 4px; cursor: pointer;">Close</button>
                        <button type="button" class="edit-btn" style="padding: 8px 16px; background: #f59e0b; border: none; color: #0d0d0d; border-radius: 4px; cursor: pointer; font-weight: 500;">Edit</button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        const modal = document.getElementById('extension-view-modal');
        
        modal.querySelector('.close-btn').addEventListener('click', () => {
            modal.remove();
        });
        
        modal.querySelector('.edit-btn').addEventListener('click', () => {
            modal.remove();
            openExtensionModal(extension);
        });
        
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.remove();
        });
    }

    function getSignatureColor(signature) {
        const colors = {
            verified: 'rgba(34,197,94,0.2)',
            pending: 'rgba(245,158,11,0.2)',
            failed: 'rgba(239,68,68,0.2)'
        };
        return colors[signature] || colors.pending;
    }

    function getStatusColor(status) {
        const colors = {
            active: 'rgba(34,197,94,0.2)',
            review: 'rgba(245,158,11,0.2)',
            revoked: 'rgba(239,68,68,0.2)'
        };
        return colors[status] || colors.review;
    }

    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
});
