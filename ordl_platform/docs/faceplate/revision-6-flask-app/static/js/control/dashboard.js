/**
 * Dashboard JavaScript
 * Handles dashboard interactions, metric updates, and real-time data
 */

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function() {
    initDashboard();
});

function initDashboard() {
    // Time selector functionality
    initTimeSelector();
    
    // Start metric updates
    startMetricUpdates();
    
    // Initialize topology interactions
    initTopologyInteractions();
}

// Time selector
function initTimeSelector() {
    const buttons = document.querySelectorAll('.time-selector .btn');
    buttons.forEach(btn => {
        btn.addEventListener('click', function() {
            buttons.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            refreshDashboard(this.textContent);
        });
    });
}

// Refresh dashboard data based on time range
function refreshDashboard(timeRange) {
    console.log('Refreshing dashboard for:', timeRange);
    // Simulate data refresh
    updateMetrics();
}

// Start periodic metric updates
function startMetricUpdates() {
    setInterval(updateMetrics, 30000); // Update every 30 seconds
}

// Update metrics with simulated data
function updateMetrics() {
    const metrics = {
        fleetHealth: document.getElementById('fleetHealth'),
        activeDeployments: document.getElementById('activeDeployments'),
        policyHolds: document.getElementById('policyHolds'),
        agentActivity: document.getElementById('agentActivity')
    };

    // Simulate slight variations
    if (metrics.agentActivity) {
        const base = 23400;
        const variation = Math.floor(Math.random() * 1000);
        metrics.agentActivity.textContent = ((base + variation) / 1000).toFixed(1) + 'k';
    }
}

// Topology interactions
function initTopologyInteractions() {
    const nodes = document.querySelectorAll('.topology-node');
    nodes.forEach(node => {
        node.addEventListener('click', function() {
            const nodeId = this.textContent;
            console.log('Node clicked:', nodeId);
            showNodeDetails(nodeId);
        });
    });
}

function showNodeDetails(nodeId) {
    // Could open a modal or navigate to node details
    console.log('Show details for node:', nodeId);
}

// Widget actions
function zoomTopology() {
    console.log('Zoom topology');
    window.location.href = '/app/topology';
}

function refreshTopology() {
    console.log('Refresh topology');
    // Trigger topology refresh
}

function viewAllIncidents() {
    console.log('View all incidents');
    // Could navigate to incidents page
}

function viewAllApprovals() {
    console.log('View all approvals');
    // Could navigate to approvals page
}

function openApproval(id) {
    console.log('Open approval:', id);
    // Show approval details modal
}

// Quick actions
function emergencyStop() {
    if (confirm('Are you sure you want to trigger an EMERGENCY STOP? This will halt all operations immediately.')) {
        console.log('Emergency stop triggered');
        dispatchCommand('emergency_stop');
    }
}

function freezeDeployments() {
    if (confirm('Freeze all deployments? New deployments will be queued until unfrozen.')) {
        console.log('Deployments frozen');
        dispatchCommand('freeze_deployments');
    }
}

function escalateIncident() {
    console.log('Escalate incident');
    // Open incident escalation modal
}

function triggerReview() {
    console.log('Trigger review');
    // Open review trigger modal
}

// Dispatch command helper
function dispatchCommand(command) {
    fetch('/api/command/dispatch', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            command: command,
            targets: ['all'],
            options: {}
        })
    })
    .then(response => response.json())
    .then(data => {
        console.log('Command dispatched:', data);
    })
    .catch(error => {
        console.error('Error dispatching command:', error);
    });
}
