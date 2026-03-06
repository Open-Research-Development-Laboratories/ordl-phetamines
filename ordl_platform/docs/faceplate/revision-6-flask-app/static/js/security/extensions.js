/**
 * ORDL Security - Extensions Page
 */

document.addEventListener('DOMContentLoaded', function() {
    // Register Extension button
    document.querySelector('[data-action="register-extension"]')?.addEventListener('click', function() {
        console.log('Register extension');
        // TODO: Implement extension registration modal
    });

    // Verify All button
    document.querySelector('[data-action="verify-all"]')?.addEventListener('click', function() {
        console.log('Verify all extensions');
        // TODO: Implement batch verification
    });

    // Emergency Revoke button
    document.querySelector('[data-action="emergency-revoke"]')?.addEventListener('click', function() {
        if (confirm('EMERGENCY: Revoke all extensions? This cannot be undone.')) {
            console.log('Emergency revoke initiated');
        }
    });

    // View Sig Log button
    document.querySelector('[data-action="view-sig-log"]')?.addEventListener('click', function() {
        console.log('View signature log');
    });

    // Tab switching
    document.querySelectorAll('.tab-btn').forEach(tab => {
        tab.addEventListener('click', function() {
            document.querySelectorAll('.tab-btn').forEach(t => t.classList.remove('active'));
            this.classList.add('active');
            
            const tabType = this.dataset.tab;
            filterExtensions(tabType);
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

    // View Extension buttons
    document.querySelectorAll('[data-action="view-ext"]').forEach(btn => {
        btn.addEventListener('click', function() {
            const extId = this.dataset.ext;
            console.log('View extension:', extId);
        });
    });

    // Verify Extension buttons
    document.querySelectorAll('[data-action="verify-ext"]').forEach(btn => {
        btn.addEventListener('click', function() {
            const extId = this.dataset.ext;
            console.log('Verify extension:', extId);
        });
    });

    // Revoke Extension buttons
    document.querySelectorAll('[data-action="revoke-ext"]').forEach(btn => {
        btn.addEventListener('click', function() {
            const extId = this.dataset.ext;
            if (confirm(`Revoke extension ${extId}?`)) {
                console.log('Revoke extension:', extId);
            }
        });
    });
});
