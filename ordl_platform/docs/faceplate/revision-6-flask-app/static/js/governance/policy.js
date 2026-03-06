/**
 * ORDL Governance - Policy Engine Page
 */

document.addEventListener('DOMContentLoaded', function() {
    // Run Simulation button
    document.querySelector('[data-action="run-simulation"]')?.addEventListener('click', runSimulation);

    function runSimulation() {
        const subject = document.getElementById('simSubject')?.value;
        const action = document.getElementById('simAction')?.value;
        const resource = document.getElementById('simResource')?.value;
        const context = document.getElementById('simContext')?.value;

        console.log('Running simulation:', { subject, action, resource, context });

        // Simulate result
        const resultDiv = document.getElementById('simResult');
        const rulesDiv = document.getElementById('simRules');
        const statusSpan = document.querySelector('.sim-status');

        if (resultDiv) {
            resultDiv.innerHTML = `
                <div class="simulation-result granted">
                    <div class="result-icon">
                        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#22c55e" stroke-width="2">
                            <polyline points="20 6 9 17 4 12"></polyline>
                        </svg>
                    </div>
                    <div class="result-text">
                        <h3>GRANTED</h3>
                        <p>All policy rules passed</p>
                    </div>
                </div>
            `;
        }

        if (rulesDiv) {
            rulesDiv.style.display = 'block';
        }

        if (statusSpan) {
            statusSpan.textContent = 'Complete';
            statusSpan.className = 'sim-status success';
        }
    }

    // Reason type filter
    const reasonFilter = document.getElementById('reasonTypeFilter');
    if (reasonFilter) {
        reasonFilter.addEventListener('change', function() {
            const type = this.value;
            console.log('Filter reasons by type:', type);
            // TODO: Implement reason filtering
        });
    }

    // Category headers toggle
    document.querySelectorAll('.category-header').forEach(header => {
        header.addEventListener('click', function() {
            const items = this.nextElementSibling;
            if (items) {
                items.style.display = items.style.display === 'none' ? 'block' : 'none';
            }
        });
    });
});
