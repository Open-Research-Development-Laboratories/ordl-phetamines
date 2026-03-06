/**
 * ORDL Governance - Teams Page
 */

document.addEventListener('DOMContentLoaded', function() {
    // Create Team button
    document.querySelector('[data-action="create-team"]')?.addEventListener('click', function() {
        console.log('Create team');
        // TODO: Implement team creation modal
    });

    // Edit Scope button
    document.querySelector('[data-action="edit-scope"]')?.addEventListener('click', function() {
        console.log('Edit scope matrix');
        // TODO: Implement scope editing
    });

    // View Team buttons
    document.querySelectorAll('[data-action="view-team"]').forEach(btn => {
        btn.addEventListener('click', function() {
            const teamId = this.dataset.team;
            console.log('View team:', teamId);
            window.location.href = `/app/teams/${teamId}`;
        });
    });

    // Escalation tree selector
    const treeSelect = document.getElementById('escalationTreeSelect');
    if (treeSelect) {
        treeSelect.addEventListener('change', function() {
            console.log('Switch escalation tree:', this.value);
            // TODO: Load different escalation tree
        });
    }

    // Search filter
    const searchInput = document.getElementById('teamSearch');
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            const query = this.value.toLowerCase();
            document.querySelectorAll('.team-card').forEach(card => {
                const name = card.querySelector('h4').textContent.toLowerCase();
                card.style.display = name.includes(query) ? '' : 'none';
            });
        });
    }

    // Scope filter
    const scopeFilter = document.getElementById('scopeFilter');
    if (scopeFilter) {
        scopeFilter.addEventListener('change', function() {
            const scope = this.value;
            document.querySelectorAll('.team-card').forEach(card => {
                if (!scope) {
                    card.style.display = '';
                } else {
                    const cardScope = card.querySelector('.scope-badge').textContent.toLowerCase();
                    card.style.display = cardScope === scope ? '' : 'none';
                }
            });
        });
    }
});
