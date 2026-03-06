/**
 * templates/nodes/discovery.js - Node Discovery JavaScript
 */

document.addEventListener('DOMContentLoaded', function() {
    initNetworkSelection();
    initCandidateSelection();
    initScanActions();
});

// Network selection
function initNetworkSelection() {
    const networkOptions = document.querySelectorAll('.network-option');
    
    networkOptions.forEach(option => {
        option.addEventListener('click', function() {
            this.classList.toggle('selected');
        });
    });
}

// Candidate selection
function initCandidateSelection() {
    const candidates = document.querySelectorAll('.candidate-item');
    
    candidates.forEach(candidate => {
        candidate.addEventListener('click', function() {
            candidates.forEach(c => c.classList.remove('selected'));
            this.classList.add('selected');
            
            const ip = this.querySelector('.candidate-ip').textContent;
            updateFitAnalysis(ip);
        });
    });
}

// Update fit analysis display
function updateFitAnalysis(ip) {
    const header = document.querySelector('.fit-panel .panel-header span:last-child');
    if (header) header.textContent = ip;
}

// Scan actions
function initScanActions() {
    const scanBtn = document.getElementById('startScanBtn');
    if (scanBtn) {
        scanBtn.addEventListener('click', startDiscoveryScan);
    }
}

async function startDiscoveryScan() {
    const selectedNetworks = [];
    document.querySelectorAll('.network-option.selected').forEach(opt => {
        selectedNetworks.push({
            name: opt.querySelector('.network-name').textContent,
            range: opt.querySelector('.network-range').textContent
        });
    });
    
    const options = {
        deepInspection: document.querySelector('input[value="deep"]')?.checked ?? true,
        benchmark: document.querySelector('input[value="benchmark"]')?.checked ?? true,
        connectivity: document.querySelector('input[value="connectivity"]')?.checked ?? false
    };
    
    console.log('Starting discovery scan:', { networks: selectedNetworks, options });
    
    // Show scan progress
    showScanProgress();
    
    try {
        const response = await fetch('/api/nodes/discovery/scan', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ networks: selectedNetworks, options })
        });
        
        const data = await response.json();
        console.log('Scan started:', data);
        
        // Poll for results
        pollScanResults(data.scan_id);
    } catch (error) {
        console.error('Scan failed:', error);
    }
}

function showScanProgress() {
    // Show progress UI
}

async function pollScanResults(scanId) {
    const poll = async () => {
        const response = await fetch(`/api/nodes/discovery/scan/${scanId}`);
        const data = await response.json();
        
        if (data.status === 'completed') {
            updateCandidatesList(data.candidates);
        } else if (data.status === 'running') {
            setTimeout(poll, 2000);
        }
    };
    
    poll();
}

function updateCandidatesList(candidates) {
    const list = document.getElementById('candidatesList');
    // Update candidates list
}

// Approve candidates
function approveCandidates(candidateIds, roles) {
    return fetch('/api/nodes/discovery/approve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ candidates: candidateIds, roles })
    }).then(r => r.json());
}

// Calculate fit score
function calculateFitScore(hostSpecs) {
    const weights = {
        cpu: 0.2,
        memory: 0.2,
        gpu: 0.3,
        network: 0.15,
        storage: 0.1,
        latency: 0.05
    };
    
    // Fit score calculation logic
    return {
        overall: 94,
        breakdown: {
            cpu: 96,
            memory: 98,
            gpu: 95,
            network: 88,
            storage: 92,
            latency: 90
        }
    };
}

// API
const NodeDiscovery = {
    scan: (config) => fetch('/api/nodes/discovery/scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
    }).then(r => r.json()),
    
    getScanStatus: (scanId) => fetch(`/api/nodes/discovery/scan/${scanId}`).then(r => r.json()),
    
    getCandidates: () => fetch('/api/nodes/discovery/candidates').then(r => r.json()),
    
    approve: (candidateIds, roles) => fetch('/api/nodes/discovery/approve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ candidates: candidateIds, roles })
    }).then(r => r.json()),
    
    getNetworks: () => fetch('/api/nodes/networks').then(r => r.json())
};

window.NodeDiscovery = NodeDiscovery;
