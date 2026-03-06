/**
 * ORDL Governance - Policy Engine Page
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize APIs
    const api = window.governanceApi || (typeof governanceApi !== 'undefined' ? governanceApi : null);
    const ui = window.ORDL?.ui;

    // Run Simulation button
    document.querySelector('[data-action="run-simulation"]')?.addEventListener('click', runSimulation);

    async function runSimulation() {
        const subject = document.getElementById('simSubject')?.value;
        const action = document.getElementById('simAction')?.value;
        const resource = document.getElementById('simResource')?.value;
        const context = document.getElementById('simContext')?.value;

        if (!subject || !action || !resource) {
            ui?.showToast?.('Please fill in all required fields', 'warning');
            return;
        }

        const btn = document.querySelector('[data-action="run-simulation"]');
        const hideSpinner = ui?.showSpinner?.(btn, 'Running...');

        try {
            const result = await api.simulatePolicy(subject, action, resource, context);
            displaySimulationResult(result);
            ui?.showToast?.('Simulation completed', 'success');
        } catch (error) {
            ui?.handleError?.(error, 'Simulation failed');
            displaySimulationError(error);
        } finally {
            hideSpinner?.();
        }
    }

    function displaySimulationResult(result) {
        const resultDiv = document.getElementById('simResult');
        const rulesDiv = document.getElementById('simRules');
        const statusSpan = document.querySelector('.sim-status');

        const decision = result?.decision || 'DENIED';
        const isGranted = decision === 'GRANTED';
        const color = isGranted ? '#22c55e' : (decision === 'HELD' ? '#f59e0b' : '#ef4444');
        const icon = isGranted ? '✓' : (decision === 'HELD' ? '⏸' : '✕');

        if (resultDiv) {
            resultDiv.innerHTML = `
                <div class="simulation-result ${decision.toLowerCase()}" style="padding: 20px; border-radius: 8px; background: rgba(0,0,0,0.3); margin-bottom: 16px;">
                    <div class="result-icon" style="font-size: 48px; text-align: center; color: ${color}; margin-bottom: 12px;">
                        ${icon}
                    </div>
                    <div class="result-text" style="text-align: center;">
                        <h3 style="margin: 0 0 8px; color: ${color}; font-size: 24px;">${decision}</h3>
                        <p style="margin: 0; color: #d4cfc7;">${isGranted ? 'All policy rules passed' : (decision === 'HELD' ? 'Request requires manual review' : 'Policy rules failed')}</p>
                    </div>
                </div>
            `;
        }

        if (rulesDiv) {
            rulesDiv.style.display = 'block';
            const matchedRules = result?.matchedRules || [];
            const failedRules = result?.failedRules || [];
            
            let rulesHtml = '<h4>Matched Rules</h4>';
            if (matchedRules.length > 0) {
                rulesHtml += '<ul>' + matchedRules.map(r => `<li style="color: #22c55e;">${escapeHtml(r)}</li>`).join('') + '</ul>';
            } else {
                rulesHtml += '<p style="color: #a8a39c;">No rules matched</p>';
            }
            
            if (failedRules.length > 0) {
                rulesHtml += '<h4>Failed Rules</h4><ul>' + failedRules.map(r => `<li style="color: #ef4444;">${escapeHtml(r)}</li>`).join('') + '</ul>';
            }
            
            rulesDiv.innerHTML = rulesHtml;
        }

        if (statusSpan) {
            statusSpan.textContent = 'Complete';
            statusSpan.className = 'sim-status success';
            statusSpan.style.color = color;
        }
    }

    function displaySimulationError(error) {
        const resultDiv = document.getElementById('simResult');
        if (resultDiv) {
            resultDiv.innerHTML = `
                <div style="padding: 20px; border-radius: 8px; background: rgba(239,68,68,0.1); border: 1px solid rgba(239,68,68,0.3);">
                    <h3 style="margin: 0 0 8px; color: #ef4444;">Simulation Error</h3>
                    <p style="margin: 0; color: #d4cfc7;">${escapeHtml(error.message || 'Unknown error')}</p>
                </div>
            `;
        }
    }

    // Reason type filter
    const reasonFilter = document.getElementById('reasonTypeFilter');
    if (reasonFilter) {
        reasonFilter.addEventListener('change', async function() {
            const type = this.value;
            const hideSpinner = ui?.showGlobalLoading?.('Filtering...');
            
            try {
                const reasons = await api.getHoldDenyReasons(type);
                filterReasonsDisplay(reasons, type);
            } catch (error) {
                ui?.handleError?.(error, 'Failed to filter reasons');
            } finally {
                hideSpinner?.();
            }
        });
    }

    function filterReasonsDisplay(reasons, type) {
        document.querySelectorAll('.reason-item').forEach(item => {
            if (!type || item.dataset.category === type) {
                item.style.display = '';
            } else {
                item.style.display = 'none';
            }
        });
    }

    // Category headers toggle
    document.querySelectorAll('.category-header').forEach(header => {
        header.addEventListener('click', function() {
            const items = this.nextElementSibling;
            if (items) {
                const isHidden = items.style.display === 'none';
                items.style.display = isHidden ? 'block' : 'none';
                this.style.opacity = isHidden ? '1' : '0.7';
            }
        });
    });

    // Policy rule management buttons (if present)
    document.querySelectorAll('[data-action="create-rule"]').forEach(btn => {
        btn.addEventListener('click', () => openRuleModal());
    });

    document.querySelectorAll('[data-action="edit-rule"]').forEach(btn => {
        btn.addEventListener('click', async function() {
            const ruleId = this.dataset.ruleId;
            const hideSpinner = ui?.showSpinner?.(this, 'Loading...');
            
            try {
                const rule = await api.getPolicyRule(ruleId);
                openRuleModal(rule);
            } catch (error) {
                ui?.handleError?.(error, 'Failed to load rule');
            } finally {
                hideSpinner?.();
            }
        });
    });

    document.querySelectorAll('[data-action="delete-rule"]').forEach(btn => {
        btn.addEventListener('click', async function() {
            const ruleId = this.dataset.ruleId;
            
            const confirmed = await ui?.confirmDialog?.(
                'Are you sure you want to delete this policy rule? This action cannot be undone.',
                { title: 'Delete Policy Rule', confirmText: 'Delete', confirmClass: 'danger' }
            );
            
            if (!confirmed) return;
            
            const hideSpinner = ui?.showSpinner?.(this, 'Deleting...');
            
            try {
                await api.deletePolicyRule(ruleId);
                ui?.showToast?.('Policy rule deleted successfully', 'success');
                ui?.refreshData?.();
            } catch (error) {
                ui?.handleError?.(error, 'Failed to delete rule');
            } finally {
                hideSpinner?.();
            }
        });
    });

    function openRuleModal(rule = null) {
        const isEdit = !!rule;
        const modalHtml = `
            <div id="rule-modal" class="modal" style="display: block; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.7); z-index: 1000;">
                <div style="background: #1a1a1a; max-width: 600px; margin: 50px auto; padding: 24px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1); color: #faf8f5; max-height: 80vh; overflow-y: auto;">
                    <h3>${isEdit ? 'Edit' : 'Create'} Policy Rule</h3>
                    <form id="rule-form">
                        <div style="margin-bottom: 16px;">
                            <label style="display: block; margin-bottom: 4px; color: #d4cfc7;">Rule Name</label>
                            <input type="text" name="name" value="${escapeHtml(rule?.name || '')}" required style="width: 100%; padding: 8px; background: #0d0d0d; border: 1px solid rgba(255,255,255,0.1); color: #faf8f5; border-radius: 4px;">
                        </div>
                        <div style="margin-bottom: 16px;">
                            <label style="display: block; margin-bottom: 4px; color: #d4cfc7;">Category</label>
                            <select name="category" style="width: 100%; padding: 8px; background: #0d0d0d; border: 1px solid rgba(255,255,255,0.1); color: #faf8f5; border-radius: 4px;">
                                <option value="access">Access Control</option>
                                <option value="data">Data Protection</option>
                                <option value="auth">Authentication</option>
                                <option value="audit">Audit</option>
                                <option value="system">System</option>
                            </select>
                        </div>
                        <div style="margin-bottom: 16px;">
                            <label style="display: block; margin-bottom: 4px; color: #d4cfc7;">Effect</label>
                            <select name="effect" style="width: 100%; padding: 8px; background: #0d0d0d; border: 1px solid rgba(255,255,255,0.1); color: #faf8f5; border-radius: 4px;">
                                <option value="allow">Allow</option>
                                <option value="deny">Deny</option>
                                <option value="hold">Hold</option>
                            </select>
                        </div>
                        <div style="margin-bottom: 16px;">
                            <label style="display: block; margin-bottom: 4px; color: #d4cfc7;">Priority</label>
                            <input type="number" name="priority" value="${rule?.priority || 100}" min="1" max="1000" style="width: 100%; padding: 8px; background: #0d0d0d; border: 1px solid rgba(255,255,255,0.1); color: #faf8f5; border-radius: 4px;">
                        </div>
                        <div style="margin-bottom: 16px;">
                            <label style="display: flex; align-items: center; gap: 8px; color: #d4cfc7; cursor: pointer;">
                                <input type="checkbox" name="enabled" ${rule?.enabled !== false ? 'checked' : ''}>
                                <span>Enabled</span>
                            </label>
                        </div>
                        <div style="display: flex; gap: 10px; justify-content: flex-end; margin-top: 20px;">
                            <button type="button" class="cancel-btn" style="padding: 8px 16px; background: transparent; border: 1px solid rgba(255,255,255,0.2); color: #d4cfc7; border-radius: 4px; cursor: pointer;">Cancel</button>
                            <button type="submit" style="padding: 8px 16px; background: #f59e0b; border: none; color: #0d0d0d; border-radius: 4px; cursor: pointer; font-weight: 500;">${isEdit ? 'Update' : 'Create'} Rule</button>
                        </div>
                    </form>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        const modal = document.getElementById('rule-modal');
        const form = document.getElementById('rule-form');
        
        if (rule?.category) form.querySelector('[name="category"]').value = rule.category;
        if (rule?.effect) form.querySelector('[name="effect"]').value = rule.effect;
        
        modal.querySelector('.cancel-btn').addEventListener('click', () => {
            modal.remove();
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
                    category: formData.get('category'),
                    effect: formData.get('effect'),
                    priority: parseInt(formData.get('priority')),
                    enabled: formData.has('enabled')
                };
                
                if (isEdit) {
                    await api.updatePolicyRule(rule.id, data);
                    ui?.showToast?.('Policy rule updated successfully', 'success');
                } else {
                    await api.createPolicyRule(data);
                    ui?.showToast?.('Policy rule created successfully', 'success');
                }
                
                modal.remove();
                ui?.refreshData?.();
            } catch (error) {
                ui?.handleError?.(error, isEdit ? 'Failed to update rule' : 'Failed to create rule');
            } finally {
                hideSpinner?.();
            }
        });
    }

    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
});
