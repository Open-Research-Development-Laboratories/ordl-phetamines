/**
 * ORDL Governance - Projects Page
 */

document.addEventListener('DOMContentLoaded', function() {
    // Create Project button
    document.querySelector('[data-action="create-project"]')?.addEventListener('click', function() {
        console.log('Create project');
        // TODO: Implement project creation modal
    });

    // Edit Defaults button
    document.querySelector('[data-action="edit-defaults"]')?.addEventListener('click', function() {
        console.log('Edit default clearance');
        // TODO: Implement defaults editing
    });

    // View Project buttons
    document.querySelectorAll('[data-action="view-project"]').forEach(btn => {
        btn.addEventListener('click', function() {
            const projectId = this.dataset.project;
            console.log('View project:', projectId);
            window.location.href = `/app/projects/${projectId}`;
        });
    });

    // Edit Project buttons
    document.querySelectorAll('[data-action="edit-project"]').forEach(btn => {
        btn.addEventListener('click', function() {
            const projectId = this.dataset.project;
            console.log('Edit project:', projectId);
        });
    });

    // Manage Seats buttons
    document.querySelectorAll('[data-action="manage-seats"]').forEach(btn => {
        btn.addEventListener('click', function() {
            const projectId = this.dataset.project;
            console.log('Manage seats for project:', projectId);
            window.location.href = `/app/seats?project=${projectId}`;
        });
    });

    // Search filter
    const searchInput = document.getElementById('projectSearch');
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            const query = this.value.toLowerCase();
            document.querySelectorAll('.project-row').forEach(row => {
                const name = row.querySelector('h4').textContent.toLowerCase();
                row.style.display = name.includes(query) ? '' : 'none';
            });
        });
    }

    // Status filter
    const statusFilter = document.getElementById('statusFilter');
    if (statusFilter) {
        statusFilter.addEventListener('change', function() {
            const status = this.value;
            document.querySelectorAll('.project-row').forEach(row => {
                if (!status) {
                    row.style.display = '';
                } else {
                    const rowStatus = row.querySelector('.status-badge').textContent.toLowerCase();
                    row.style.display = rowStatus === status ? '' : 'none';
                }
            });
        });
    }
});
