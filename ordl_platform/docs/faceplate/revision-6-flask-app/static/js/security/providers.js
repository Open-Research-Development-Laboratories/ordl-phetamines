/**
 * ORDL Security - Providers Page
 */

document.addEventListener('DOMContentLoaded', function() {
    // Add Provider button
    document.querySelector('[data-action="add-provider"]')?.addEventListener('click', function() {
        console.log('Add provider');
        // TODO: Implement provider creation modal
    });

    // Save Priority button
    document.querySelector('[data-action="save-priority"]')?.addEventListener('click', function() {
        console.log('Save failover priority');
        // TODO: Implement priority save
    });

    // Edit Probes button
    document.querySelector('[data-action="edit-probes"]')?.addEventListener('click', function() {
        console.log('Edit health probes');
        // TODO: Implement probe editing
    });

    // Test Provider buttons
    document.querySelectorAll('[data-action="test-provider"]').forEach(btn => {
        btn.addEventListener('click', function() {
            const providerId = this.dataset.provider;
            console.log('Test provider:', providerId);
        });
    });

    // Configure Provider buttons
    document.querySelectorAll('[data-action="config-provider"]').forEach(btn => {
        btn.addEventListener('click', function() {
            const providerId = this.dataset.provider;
            console.log('Configure provider:', providerId);
        });
    });

    // View Logs buttons
    document.querySelectorAll('[data-action="logs-provider"]').forEach(btn => {
        btn.addEventListener('click', function() {
            const providerId = this.dataset.provider;
            console.log('View logs for provider:', providerId);
        });
    });

    // Force Failover buttons
    document.querySelectorAll('[data-action="failover-provider"]').forEach(btn => {
        btn.addEventListener('click', function() {
            const providerId = this.dataset.provider;
            if (confirm(`Force failover for ${providerId}?`)) {
                console.log('Force failover:', providerId);
            }
        });
    });

    // Priority chain drag and drop (simplified)
    const chainItems = document.querySelectorAll('.chain-item');
    chainItems.forEach(item => {
        item.draggable = true;
        item.addEventListener('dragstart', handleDragStart);
        item.addEventListener('dragover', handleDragOver);
        item.addEventListener('drop', handleDrop);
    });

    let draggedItem = null;

    function handleDragStart(e) {
        draggedItem = this;
        e.dataTransfer.effectAllowed = 'move';
    }

    function handleDragOver(e) {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
    }

    function handleDrop(e) {
        e.preventDefault();
        if (draggedItem !== this) {
            // Simple swap logic - in production, use proper reordering
            console.log('Reordered providers');
        }
    }
});
