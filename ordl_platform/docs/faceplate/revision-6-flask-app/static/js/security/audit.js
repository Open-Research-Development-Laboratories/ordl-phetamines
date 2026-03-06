/**
 * ORDL Security - Audit Page
 */

document.addEventListener('DOMContentLoaded', function() {
    // Create Evidence button
    document.querySelector('[data-action="create-evidence"]')?.addEventListener('click', function() {
        console.log('Create evidence package');
        // TODO: Implement evidence creation modal
    });

    // New Export button
    document.querySelector('[data-action="new-export"]')?.addEventListener('click', function() {
        console.log('New export job');
        // TODO: Implement export creation modal
    });

    // Package Evidence button
    document.querySelector('[data-action="package-evidence"]')?.addEventListener('click', function() {
        console.log('Package evidence');
    });

    // Pause Stream button
    let streamPaused = false;
    document.querySelector('[data-action="pause-stream"]')?.addEventListener('click', function() {
        streamPaused = !streamPaused;
        this.textContent = streamPaused ? 'Resume' : 'Pause';
        console.log('Stream:', streamPaused ? 'paused' : 'resumed');
    });

    // Jump to Now button
    document.querySelector('[data-action="jump-now"]')?.addEventListener('click', function() {
        const stream = document.getElementById('auditStream');
        if (stream) {
            stream.scrollTop = stream.scrollHeight;
        }
    });

    // Load More button
    document.querySelector('[data-action="load-more"]')?.addEventListener('click', function() {
        console.log('Load more events');
        // TODO: Implement pagination
    });

    // Export Filtered button
    document.querySelector('[data-action="export-filtered"]')?.addEventListener('click', function() {
        console.log('Export filtered results');
    });

    // Download job buttons
    document.querySelectorAll('[data-action="download"]').forEach(btn => {
        btn.addEventListener('click', function() {
            const jobId = this.dataset.job;
            console.log('Download export:', jobId);
        });
    });

    // Verify job buttons
    document.querySelectorAll('[data-action="verify"]').forEach(btn => {
        btn.addEventListener('click', function() {
            const jobId = this.dataset.job;
            console.log('Verify export:', jobId);
        });
    });

    // Delete job buttons
    document.querySelectorAll('[data-action="delete-job"]').forEach(btn => {
        btn.addEventListener('click', function() {
            const jobId = this.dataset.job;
            if (confirm(`Delete export job ${jobId}?`)) {
                console.log('Delete export:', jobId);
            }
        });
    });

    // Download package buttons
    document.querySelectorAll('[data-action="download-pkg"]').forEach(btn => {
        btn.addEventListener('click', function() {
            const pkgId = this.dataset.pkg;
            console.log('Download package:', pkgId);
        });
    });

    // View chain buttons
    document.querySelectorAll('[data-action="chain-pkg"]').forEach(btn => {
        btn.addEventListener('click', function() {
            const pkgId = this.dataset.pkg;
            console.log('View chain for package:', pkgId);
        });
    });

    // Filters
    const severityFilter = document.getElementById('severityFilter');
    const categoryFilter = document.getElementById('categoryFilter');
    
    if (severityFilter) {
        severityFilter.addEventListener('change', filterEvents);
    }
    
    if (categoryFilter) {
        categoryFilter.addEventListener('change', filterEvents);
    }

    function filterEvents() {
        const severity = severityFilter?.value;
        const category = categoryFilter?.value;
        
        document.querySelectorAll('.audit-event').forEach(event => {
            let show = true;
            if (severity && !event.classList.contains(severity)) show = false;
            // Category filtering would need data attributes
            event.style.display = show ? '' : 'none';
        });
    }

    // Simulate live stream updates
    setInterval(() => {
        if (!streamPaused) {
            // In production, this would fetch new events
            // console.log('Checking for new events...');
        }
    }, 5000);
});
