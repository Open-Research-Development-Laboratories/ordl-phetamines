/**
 * ORDL Security - Providers Page
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize security API
    const api = window.securityApi || (typeof securityApi !== 'undefined' ? securityApi : null);
    const ui = window.ORDL?.ui;

    // Add Provider button
    document.querySelector('[data-action="add-provider"]')?.addEventListener('click', function() {
        openProviderModal();
    });

    // Save Priority button
    document.querySelector('[data-action="save-priority"]')?.addEventListener('click', async function() {
        const btn = this;
        const hideSpinner = ui?.showSpinner?.(btn, 'Saving...');
        
        try {
            // Get the current order from the DOM
            const providerIds = Array.from(document.querySelectorAll('.chain-item')).map(item => item.dataset.provider);
            await api.updateFailoverPriority(providerIds);
            ui?.showToast?.('Failover priority saved successfully', 'success');
        } catch (error) {
            ui?.handleError?.(error, 'Failed to save priority');
        } finally {
            hideSpinner?.();
        }
    });

    // Edit Probes button
    document.querySelector('[data-action="edit-probes"]')?.addEventListener('click', async function() {
        // FIXME: backend gap - select which provider to edit probes for
        ui?.showToast?.('Select a provider to edit probes', 'info');
    });

    // Test Provider buttons
    document.querySelectorAll('[data-action="test-provider"]').forEach(btn => {
        btn.addEventListener('click', async function() {
            const providerId = this.dataset.provider;
            const hideSpinner = ui?.showSpinner?.(this, 'Testing...');
            
            try {
                const result = await api.testProvider(providerId);
                if (result.healthy) {
                    ui?.showToast?.('Provider is healthy', 'success');
                } else {
                    ui?.showToast?.('Provider health check failed', 'error');
                }
            } catch (error) {
                ui?.handleError?.(error, 'Failed to test provider');
            } finally {
                hideSpinner?.();
            }
        });
    });

    // Configure Provider buttons
    document.querySelectorAll('[data-action="config-provider"]').forEach(btn => {
        btn.addEventListener('click', async function() {
            const providerId = this.dataset.provider;
            const hideSpinner = ui?.showSpinner?.(this, 'Loading...');
            
            try {
                const provider = await api.getProvider(providerId);
                openProviderModal(provider);
            } catch (error) {
                ui?.handleError?.(error, 'Failed to load provider configuration');
            } finally {
                hideSpinner?.();
            }
        });
    });

    // View Logs buttons
    document.querySelectorAll('[data-action="logs-provider"]').forEach(btn => {
        btn.addEventListener('click', async function() {
            const providerId = this.dataset.provider;
            const hideSpinner = ui?.showSpinner?.(this, 'Loading...');
            
            try {
                const logs = await api.getProviderLogs(providerId);
                openLogsModal(logs, providerId);
            } catch (error) {
                ui?.handleError?.(error, 'Failed to load provider logs');
            } finally {
                hideSpinner?.();
            }
        });
    });

    // Force Failover buttons
    document.querySelectorAll('[data-action="failover-provider"]').forEach(btn => {
        btn.addEventListener('click', async function() {
            const providerId = this.dataset.provider;
            
            const confirmed = await ui?.confirmDialog?.(
                `Force failover from ${providerId}? This will redirect traffic to the next provider in the priority chain.`,
                { title: 'Force Failover', confirmText: 'Failover', confirmClass: 'danger' }
            );
            
            if (!confirmed) return;
            
            const hideSpinner = ui?.showSpinner?.(this, 'Failing over...');
            
            try {
                await api.forceFailover(providerId, null); // null = next in chain
                ui?.showToast?.('Failover initiated successfully', 'success');
                ui?.refreshData?.();
            } catch (error) {
                ui?.handleError?.(error, 'Failed to initiate failover');
            } finally {
                hideSpinner?.();
            }
        });
    });

    // Delete Provider buttons (if present)
    document.querySelectorAll('[data-action="delete-provider"]').forEach(btn => {
        btn.addEventListener('click', async function() {
            const providerId = this.dataset.provider;
            
            const confirmed = await ui?.confirmDialog?.(
                `Delete provider ${providerId}? This cannot be undone.`,
                { title: 'Delete Provider', confirmText: 'Delete', confirmClass: 'danger' }
            );
            
            if (!confirmed) return;
            
            const hideSpinner = ui?.showSpinner?.(this, 'Deleting...');
            
            try {
                await api.deleteProvider(providerId);
                ui?.showToast?.('Provider deleted successfully', 'success');
                ui?.refreshData?.();
            } catch (error) {
                ui?.handleError?.(error, 'Failed to delete provider');
            } finally {
                hideSpinner?.();
            }
        });
    });

    // Priority chain drag and drop
    const chainItems = document.querySelectorAll('.chain-item');
    let draggedItem = null;

    chainItems.forEach(item => {
        item.draggable = true;
        item.addEventListener('dragstart', handleDragStart);
        item.addEventListener('dragover', handleDragOver);
        item.addEventListener('drop', handleDrop);
        item.addEventListener('dragend', handleDragEnd);
    });

    function handleDragStart(e) {
        draggedItem = this;
        this.style.opacity = '0.5';
        e.dataTransfer.effectAllowed = 'move';
    }

    function handleDragOver(e) {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        
        const afterElement = getDragAfterElement(document.querySelector('.priority-chain'), e.clientY);
        if (afterElement == null) {
            document.querySelector('.priority-chain').appendChild(draggedItem);
        } else {
            document.querySelector('.priority-chain').insertBefore(draggedItem, afterElement);
        }
    }

    function handleDrop(e) {
        e.preventDefault();
        ui?.showToast?.('Priority order updated. Click Save Priority to persist changes.', 'info');
    }

    function handleDragEnd() {
        this.style.opacity = '1';
        draggedItem = null;
    }

    function getDragAfterElement(container, y) {
        const draggableElements = [...container.querySelectorAll('.chain-item:not([style*="opacity: 0.5"])')];
        
        return draggableElements.reduce((closest, child) => {
            const box = child.getBoundingClientRect();
            const offset = y - box.top - box.height / 2;
            
            if (offset < 0 && offset > closest.offset) {
                return { offset: offset, element: child };
            } else {
                return closest;
            }
        }, { offset: Number.NEGATIVE_INFINITY }).element;
    }

    function openProviderModal(provider = null) {
        const isEdit = !!provider;
        const modalHtml = `
            <div id="provider-modal" class="modal" style="display: block; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.7); z-index: 1000;">
                <div style="background: #1a1a1a; max-width: 500px; margin: 50px auto; padding: 24px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1); color: #faf8f5;">
                    <h3>${isEdit ? 'Configure' : 'Add'} Provider</h3>
                    <form id="provider-form">
                        <div style="margin-bottom: 16px;">
                            <label style="display: block; margin-bottom: 4px; color: #d4cfc7;">Provider Name *</label>
                            <input type="text" name="name" value="${escapeHtml(provider?.name || '')}" required style="width: 100%; padding: 8px; background: #0d0d0d; border: 1px solid rgba(255,255,255,0.1); color: #faf8f5; border-radius: 4px;">
                        </div>
                        <div style="margin-bottom: 16px;">
                            <label style="display: block; margin-bottom: 4px; color: #d4cfc7;">Type</label>
                            <select name="type" style="width: 100%; padding: 8px; background: #0d0d0d; border: 1px solid rgba(255,255,255,0.1); color: #faf8f5; border-radius: 4px;">
                                <option value="openai">OpenAI</option>
                                <option value="anthropic">Anthropic</option>
                                <option value="azure">Azure OpenAI</option>
                                <option value="aws">AWS Bedrock</option>
                                <option value="google">Google Vertex</option>
                                <option value="cohere">Cohere</option>
                            </select>
                        </div>
                        <div style="margin-bottom: 16px;">
                            <label style="display: block; margin-bottom: 4px; color: #d4cfc7;">Region</label>
                            <input type="text" name="region" value="${escapeHtml(provider?.region || '')}" placeholder="e.g. us-east-1" style="width: 100%; padding: 8px; background: #0d0d0d; border: 1px solid rgba(255,255,255,0.1); color: #faf8f5; border-radius: 4px;">
                        </div>
                        <div style="margin-bottom: 16px;">
                            <label style="display: block; margin-bottom: 4px; color: #d4cfc7;">API Key</label>
                            <input type="password" name="apiKey" placeholder="${isEdit ? 'Leave blank to keep current' : 'Enter API key'}" style="width: 100%; padding: 8px; background: #0d0d0d; border: 1px solid rgba(255,255,255,0.1); color: #faf8f5; border-radius: 4px;">
                        </div>
                        <div style="margin-bottom: 16px;">
                            <label style="display: block; margin-bottom: 4px; color: #d4cfc7;">Priority</label>
                            <input type="number" name="priority" value="${provider?.priority || 1}" min="1" style="width: 100%; padding: 8px; background: #0d0d0d; border: 1px solid rgba(255,255,255,0.1); color: #faf8f5; border-radius: 4px;">
                        </div>
                        <div style="display: flex; gap: 10px; justify-content: flex-end; margin-top: 20px;">
                            ${isEdit ? `<button type="button" class="delete-btn" style="padding: 8px 16px; background: #dc2626; border: none; color: white; border-radius: 4px; cursor: pointer; margin-right: auto;">Delete</button>
                            ` : ''}
                            <button type="button" class="cancel-btn" style="padding: 8px 16px; background: transparent; border: 1px solid rgba(255,255,255,0.2); color: #d4cfc7; border-radius: 4px; cursor: pointer;">Cancel</button>
                            <button type="submit" style="padding: 8px 16px; background: #f59e0b; border: none; color: #0d0d0d; border-radius: 4px; cursor: pointer; font-weight: 500;">${isEdit ? 'Save Changes' : 'Add Provider'}</button>
                        </div>
                    </form>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        const modal = document.getElementById('provider-modal');
        const form = document.getElementById('provider-form');
        
        if (provider?.type) form.querySelector('[name="type"]').value = provider.type;
        
        modal.querySelector('.cancel-btn')?.addEventListener('click', () => {
            modal.remove();
        });
        
        modal.querySelector('.delete-btn')?.addEventListener('click', async () => {
            const confirmed = await ui?.confirmDialog?.(
                `Delete provider "${provider.name}"?`,
                { title: 'Delete Provider', confirmText: 'Delete', confirmClass: 'danger' }
            );
            
            if (!confirmed) return;
            
            const hideSpinner = ui?.showSpinner?.(modal.querySelector('.delete-btn'), 'Deleting...');
            
            try {
                await api.deleteProvider(provider.id);
                ui?.showToast?.('Provider deleted successfully', 'success');
                modal.remove();
                ui?.refreshData?.();
            } catch (error) {
                ui?.handleError?.(error, 'Failed to delete provider');
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
            const hideSpinner = ui?.showSpinner?.(submitBtn, isEdit ? 'Saving...' : 'Adding...');
            
            try {
                const formData = new FormData(form);
                const data = {
                    name: formData.get('name'),
                    type: formData.get('type'),
                    region: formData.get('region'),
                    priority: parseInt(formData.get('priority'))
                };
                
                const apiKey = formData.get('apiKey');
                if (apiKey) data.apiKey = apiKey;
                
                if (isEdit) {
                    await api.updateProvider(provider.id, data);
                    ui?.showToast?.('Provider updated successfully', 'success');
                } else {
                    await api.createProvider(data);
                    ui?.showToast?.('Provider added successfully', 'success');
                }
                
                modal.remove();
                ui?.refreshData?.();
            } catch (error) {
                ui?.handleError?.(error, isEdit ? 'Failed to update provider' : 'Failed to add provider');
            } finally {
                hideSpinner?.();
            }
        });
    }

    function openLogsModal(logs, providerId) {
        const modalHtml = `
            <div id="logs-modal" class="modal" style="display: block; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.7); z-index: 1000;">
                <div style="background: #1a1a1a; max-width: 800px; margin: 50px auto; padding: 24px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1); color: #faf8f5; max-height: 80vh; display: flex; flex-direction: column;">
                    <h3>Provider Logs - ${providerId}</h3>
                    <div style="flex: 1; overflow-y: auto; margin-top: 16px; background: #0d0d0d; padding: 16px; border-radius: 4px; font-family: 'JetBrains Mono', monospace; font-size: 12px; line-height: 1.6;">
                        ${(logs || []).length === 0 ? '<div style="color: #a8a39c;">No logs available</div>' : 
                            logs.map(log => `<div style="color: #d4cfc7; border-bottom: 1px solid rgba(255,255,255,0.05); padding: 4px 0;">${escapeHtml(log)}</div>`).join('')
                        }
                    </div>
                    <div style="display: flex; gap: 10px; justify-content: flex-end; margin-top: 20px;">
                        <button type="button" class="close-btn" style="padding: 8px 16px; background: transparent; border: 1px solid rgba(255,255,255,0.2); color: #d4cfc7; border-radius: 4px; cursor: pointer;">Close</button>
                        <button type="button" class="refresh-btn" style="padding: 8px 16px; background: #f59e0b; border: none; color: #0d0d0d; border-radius: 4px; cursor: pointer; font-weight: 500;">Refresh</button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        const modal = document.getElementById('logs-modal');
        
        modal.querySelector('.close-btn').addEventListener('click', () => {
            modal.remove();
        });
        
        modal.querySelector('.refresh-btn').addEventListener('click', async () => {
            const btn = modal.querySelector('.refresh-btn');
            const hideSpinner = ui?.showSpinner?.(btn, 'Loading...');
            
            try {
                const newLogs = await api.getProviderLogs(providerId);
                const logsContainer = modal.querySelector('div[style*="overflow-y: auto"]');
                logsContainer.innerHTML = (newLogs || []).length === 0 ? 
                    '<div style="color: #a8a39c;">No logs available</div>' : 
                    newLogs.map(log => `<div style="color: #d4cfc7; border-bottom: 1px solid rgba(255,255,255,0.05); padding: 4px 0;">${escapeHtml(log)}</div>`).join('');
            } catch (error) {
                ui?.handleError?.(error, 'Failed to refresh logs');
            } finally {
                hideSpinner?.();
            }
        });
        
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.remove();
        });
    }

    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
});
