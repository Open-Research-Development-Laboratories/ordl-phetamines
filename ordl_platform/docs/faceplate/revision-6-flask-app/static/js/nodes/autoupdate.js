/**
 * templates/nodes/autoupdate.js - Node Auto-Update JavaScript
 */

document.addEventListener('DOMContentLoaded', function() {
    initUpdateActions();
    initRingManagement();
    startUpdatePolling();
});

// Update actions
function initUpdateActions() {
    const triggerBtn = document.querySelector('.header-btn.primary');
    const stopBtn = document.querySelector('.header-btn:nth-child(2)');
    
    if (triggerBtn) {
        triggerBtn.addEventListener('click', triggerUpdate);
    }
    
    if (stopBtn) {
        stopBtn.addEventListener('click', emergencyStop);
    }
}

async function triggerUpdate() {
    const version = prompt('Enter version to deploy:');
    if (!version) return;
    
    try {
        const response = await fetch('/api/nodes/autoupdate/trigger', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ version })
        });
        
        const data = await response.json();
        alert(`Update triggered: ${data.update_id}`);
    } catch (error) {
        alert('Failed to trigger update: ' + error.message);
    }
}

async function emergencyStop() {
    if (!confirm('EMERGENCY STOP: Halt all in-progress updates?')) return;
    
    try {
        await fetch('/api/nodes/autoupdate/emergency-stop', { method: 'POST' });
        alert('Emergency stop activated');
    } catch (error) {
        alert('Failed to stop updates: ' + error.message);
    }
}

// Ring management
function initRingManagement() {
    // Ring promotion logic would go here
}

async function promoteToNextRing(ring) {
    const response = await fetch(`/api/nodes/autoupdate/rings/${ring}/promote`, {
        method: 'POST'
    });
    return response.json();
}

// Update polling
function startUpdatePolling() {
    setInterval(() => {
        updateNodeStatus();
    }, 5000);
}

async function updateNodeStatus() {
    try {
        const response = await fetch('/api/nodes/autoupdate/status');
        const data = await response.json();
        
        // Update UI with latest status
        updateRingDisplay(data.rings);
        updateStageDisplay(data.current_stage);
    } catch (error) {
        console.error('Failed to fetch update status:', error);
    }
}

function updateRingDisplay(rings) {
    // Update ring status in UI
}

function updateStageDisplay(stage) {
    const stages = document.querySelectorAll('.update-stage');
    stages.forEach((s, i) => {
        s.classList.remove('active', 'completed');
        if (i < stage.index) {
            s.classList.add('completed');
        } else if (i === stage.index) {
            s.classList.add('active');
        }
    });
}

// Rollback functionality
async function initiateRollback(version) {
    if (!confirm(`Rollback to ${version}?`)) return;
    
    const response = await fetch('/api/nodes/autoupdate/rollback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ version })
    });
    
    return response.json();
}

// Maintenance windows
async function createMaintenanceWindow(config) {
    const response = await fetch('/api/nodes/autoupdate/windows', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
    });
    return response.json();
}

// API
const NodeAutoUpdate = {
    getStatus: () => fetch('/api/nodes/autoupdate/status').then(r => r.json()),
    
    trigger: (version) => fetch('/api/nodes/autoupdate/trigger', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ version })
    }).then(r => r.json()),
    
    emergencyStop: () => fetch('/api/nodes/autoupdate/emergency-stop', { method: 'POST' }),
    
    promote: (ring) => fetch(`/api/nodes/autoupdate/rings/${ring}/promote`, { method: 'POST' })
        .then(r => r.json()),
    
    rollback: (version) => fetch('/api/nodes/autoupdate/rollback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ version })
    }).then(r => r.json()),
    
    getRings: () => fetch('/api/nodes/autoupdate/rings').then(r => r.json()),
    
    getRegressionChecks: () => fetch('/api/nodes/autoupdate/checks').then(r => r.json()),
    
    getSnapshots: () => fetch('/api/nodes/autoupdate/snapshots').then(r => r.json())
};

window.NodeAutoUpdate = NodeAutoUpdate;
