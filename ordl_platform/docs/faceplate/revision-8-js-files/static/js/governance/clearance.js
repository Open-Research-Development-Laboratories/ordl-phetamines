/**
 * ORDL Governance - Clearance Page
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize governance API
    const api = window.governanceApi || (typeof governanceApi !== 'undefined' ? governanceApi : null);
    const ui = window.ORDL?.ui;

    // Edit Tiers button
    document.querySelector('[data-action="edit-tiers"]')?.addEventListener('click', async function() {
        const btn = this;
        const hideSpinner = ui?.showSpinner?.(btn, 'Loading...');
        
        try {
            const tiers = await api.getClearanceTiers();
            ui?.showToast?.('Clearance tiers loaded', 'info');
            openTierEditorModal(tiers);
        } catch (error) {
            ui?.handleError?.(error, 'Failed to load clearance tiers');
        } finally {
            hideSpinner?.();
        }
    });

    // Add Compartment button
    document.querySelector('[data-action="add-compartment"]')?.addEventListener('click', function() {
        openCompartmentModal();
    });

    // View Tier buttons
    document.querySelectorAll('[data-action="view-tier"]').forEach(btn => {
        btn.addEventListener('click', async function() {
            const tier = this.dataset.tier;
            const hideSpinner = ui?.showSpinner?.(this, 'Loading...');
            
            try {
                const tiers = await api.getClearanceTiers();
                const tierData = tiers.find(t => t.level === tier);
                if (tierData) {
                    openTierViewModal(tierData);
                }
            } catch (error) {
                ui?.handleError?.(error, 'Failed to load tier details');
            } finally {
                hideSpinner?.();
            }
        });
    });

    // Edit Tier buttons
    document.querySelectorAll('[data-action="edit-tier"]').forEach(btn => {
        btn.addEventListener('click', async function() {
            const tier = this.dataset.tier;
            const hideSpinner = ui?.showSpinner?.(this, 'Loading...');
            
            try {
                const tiers = await api.getClearanceTiers();
                const tierData = tiers.find(t => t.level === tier);
                if (tierData) {
                    openTierEditModal(tierData);
                }
            } catch (error) {
                ui?.handleError?.(error, 'Failed to load tier for editing');
            } finally {
                hideSpinner?.();
            }
        });
    });

    // Edit Compartment buttons
    document.querySelectorAll('[data-action="edit-comp"]').forEach(btn => {
        btn.addEventListener('click', async function() {
            const compId = this.dataset.comp;
            const hideSpinner = ui?.showSpinner?.(this, 'Loading...');
            
            try {
                const compartment = await api.getCompartment(compId);
                openCompartmentModal(compartment);
            } catch (error) {
                ui?.handleError?.(error, 'Failed to load compartment');
            } finally {
                hideSpinner?.();
            }
        });
    });

    // View Compartment buttons
    document.querySelectorAll('[data-action="view-comp"]').forEach(btn => {
        btn.addEventListener('click', async function() {
            const compId = this.dataset.comp;
            const hideSpinner = ui?.showSpinner?.(this, 'Loading...');
            
            try {
                const compartment = await api.getCompartment(compId);
                openCompartmentViewModal(compartment);
            } catch (error) {
                ui?.handleError?.(error, 'Failed to load compartment');
            } finally {
                hideSpinner?.();
            }
        });
    });

    // Export Matrix button
    document.querySelector('[data-action="export-matrix"]')?.addEventListener('click', async function() {
        const btn = this;
        const hideSpinner = ui?.showSpinner?.(btn, 'Exporting...');
        
        try {
            const data = await api.exportNTKMatrix('json');
            downloadJson(data, 'ntk-matrix.json');
            ui?.showToast?.('NTK matrix exported successfully', 'success');
        } catch (error) {
            ui?.handleError?.(error, 'Failed to export matrix');
        } finally {
            hideSpinner?.();
        }
    });

    // Edit Matrix button
    document.querySelector('[data-action="edit-matrix"]')?.addEventListener('click', async function() {
        const btn = this;
        const hideSpinner = ui?.showSpinner?.(btn, 'Loading...');
        
        try {
            const matrix = await api.getNTKMatrix();
            openMatrixEditorModal(matrix);
        } catch (error) {
            ui?.handleError?.(error, 'Failed to load matrix');
        } finally {
            hideSpinner?.();
        }
    });

    // Conflict resolve buttons
    document.querySelectorAll('.conflict-card .btn').forEach(btn => {
        btn.addEventListener('click', async function() {
            const conflictId = this.closest('.conflict-card')?.dataset?.conflictId;
            if (!conflictId) return;
            
            const confirmed = await ui?.confirmDialog?.(
                'Are you sure you want to resolve this conflict?',
                { title: 'Resolve Conflict', confirmText: 'Resolve' }
            );
            
            if (!confirmed) return;
            
            const hideSpinner = ui?.showSpinner?.(this, 'Resolving...');
            
            try {
                await api.resolveConflict(conflictId, 'manual');
                ui?.showToast?.('Conflict resolved successfully', 'success');
                ui?.refreshData?.();
            } catch (error) {
                ui?.handleError?.(error, 'Failed to resolve conflict');
            } finally {
                hideSpinner?.();
            }
        });
    });

    // Helper functions
    function openTierEditorModal(tiers) {
        ui?.showToast?.('Tier editor modal - FIXME: backend gap /v1/clearance/tiers/bulk-update', 'warning');
        console.log('Opening tier editor with tiers:', tiers);
    }

    function openTierViewModal(tier) {
        ui?.showToast?.(`Viewing tier ${tier.level} - FIXME: backend gap /v1/clearance/tiers/${tier.level}/details`, 'warning');
        console.log('Viewing tier:', tier);
    }

    function openTierEditModal(tier) {
        ui?.showToast?.(`Editing tier ${tier.level} - FIXME: backend gap /v1/clearance/tiers/${tier.level}`, 'warning');
        console.log('Editing tier:', tier);
    }

    function openCompartmentModal(compartment = null) {
        if (compartment) {
            ui?.showToast?.(`Editing compartment ${compartment.id} - FIXME: backend gap PUT /v1/clearance/compartments/${compartment.id}`, 'warning');
        } else {
            ui?.showToast?.('Creating new compartment - FIXME: backend gap POST /v1/clearance/compartments', 'warning');
        }
        console.log('Compartment modal:', compartment);
    }

    function openCompartmentViewModal(compartment) {
        ui?.showToast?.(`Viewing compartment ${compartment.id}`, 'info');
        console.log('Viewing compartment:', compartment);
    }

    function openMatrixEditorModal(matrix) {
        ui?.showToast?.('Opening matrix editor - FIXME: backend gap PUT /v1/clearance/ntk-matrix', 'warning');
        console.log('Opening matrix editor:', matrix);
    }

    function downloadJson(data, filename) {
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }
});
