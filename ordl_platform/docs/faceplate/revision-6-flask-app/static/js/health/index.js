/**
 * templates/health/index.js - Health Dashboard JavaScript
 */

document.addEventListener('DOMContentLoaded', function() {
    initGatewaySelection();
    initNodeGrid();
    startHealthPolling();
});

// Gateway selection
function initGatewaySelection() {
    const gateways = document.querySelectorAll('.gateway-item');
    
    gateways.forEach(gateway => {
        gateway.addEventListener('click', function() {
            gateways.forEach(g => g.classList.remove('selected'));
            this.classList.add('selected');
        });
    });
}

// Node grid interactions
function initNodeGrid() {
    const nodes = document.querySelectorAll('.node-cell');
    
    nodes.forEach(node => {
        node.addEventListener('click', function() {
            const nodeName = this.querySelector('.node-name').textContent;
            showNodeDetails(nodeName);
        });
    });
}

function showNodeDetails(nodeName) {
    // Show node details in modal or side panel
    console.log('Showing details for', nodeName);
}

// Health polling
function startHealthPolling() {
    setInterval(() => {
        fetchHealthStatus();
    }, 10000);
}

async function fetchHealthStatus() {
    try {
        const response = await fetch('/api/health/status');
        const data = await response.json();
        
        updateGatewayMetrics(data.gateways);
        updateNodeGrid(data.nodes);
        updateSLOs(data.slos);
    } catch (error) {
        console.error('Failed to fetch health status:', error);
    }
}

function updateGatewayMetrics(gateways) {
    // Update gateway status display
}

function updateNodeGrid(nodes) {
    // Update node status in grid
}

function updateSLOs(slos) {
    // Update SLO progress bars
}

// Run diagnostics
async function runDiagnostics() {
    const response = await fetch('/api/health/diagnostics', {
        method: 'POST'
    });
    
    const results = await response.json();
    displayDiagnostics(results);
}

function displayDiagnostics(results) {
    const logContainer = document.querySelector('.diagnostics-panel');
    // Append diagnostic results to log
}

// Export health report
async function exportReport() {
    const response = await fetch('/api/health/report');
    const blob = await response.blob();
    
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'health-report.json';
    a.click();
    window.URL.revokeObjectURL(url);
}

// Acknowledge alerts
async function acknowledgeAll() {
    if (!confirm('Acknowledge all active alerts?')) return;
    
    await fetch('/api/health/alerts/acknowledge', { method: 'POST' });
    // Refresh display
}

// API
const HealthDashboard = {
    getStatus: () => fetch('/api/health/status').then(r => r.json()),
    
    getGateway: (gatewayId) => fetch(`/api/health/gateways/${gatewayId}`).then(r => r.json()),
    
    getNode: (nodeId) => fetch(`/api/health/nodes/${nodeId}`).then(r => r.json()),
    
    runDiagnostics: () => fetch('/api/health/diagnostics', { method: 'POST' }).then(r => r.json()),
    
    getSLOs: () => fetch('/api/health/slos').then(r => r.json()),
    
    getReconnectStats: () => fetch('/api/health/reconnect').then(r => r.json()),
    
    acknowledgeAlerts: () => fetch('/api/health/alerts/acknowledge', { method: 'POST' })
};

window.HealthDashboard = HealthDashboard;
