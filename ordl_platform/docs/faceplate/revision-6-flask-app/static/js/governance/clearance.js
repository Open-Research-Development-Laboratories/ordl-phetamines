/**
 * ORDL Governance - Clearance Page
 */

document.addEventListener('DOMContentLoaded', function() {
    // Edit Tiers button
    document.querySelector('[data-action="edit-tiers"]')?.addEventListener('click', function() {
        console.log('Edit clearance tiers');
        // TODO: Implement tier editing modal
    });

    // Add Compartment button
    document.querySelector('[data-action="add-compartment"]')?.addEventListener('click', function() {
        console.log('Add compartment');
        // TODO: Implement compartment creation modal
    });

    // View Tier buttons
    document.querySelectorAll('[data-action="view-tier"]').forEach(btn => {
        btn.addEventListener('click', function() {
            const tier = this.dataset.tier;
            console.log('View tier:', tier);
        });
    });

    // Edit Tier buttons
    document.querySelectorAll('[data-action="edit-tier"]').forEach(btn => {
        btn.addEventListener('click', function() {
            const tier = this.dataset.tier;
            console.log('Edit tier:', tier);
        });
    });

    // Edit Compartment buttons
    document.querySelectorAll('[data-action="edit-comp"]').forEach(btn => {
        btn.addEventListener('click', function() {
            const compId = this.dataset.comp;
            console.log('Edit compartment:', compId);
        });
    });

    // View Compartment buttons
    document.querySelectorAll('[data-action="view-comp"]').forEach(btn => {
        btn.addEventListener('click', function() {
            const compId = this.dataset.comp;
            console.log('View compartment:', compId);
        });
    });

    // Export Matrix button
    document.querySelector('[data-action="export-matrix"]')?.addEventListener('click', function() {
        console.log('Export NTK matrix');
        // TODO: Implement matrix export
    });

    // Edit Matrix button
    document.querySelector('[data-action="edit-matrix"]')?.addEventListener('click', function() {
        console.log('Edit NTK matrix');
        // TODO: Implement matrix editing
    });

    // Conflict resolve buttons
    document.querySelectorAll('.conflict-card .btn').forEach(btn => {
        btn.addEventListener('click', function() {
            console.log('Resolve conflict');
        });
    });
});
