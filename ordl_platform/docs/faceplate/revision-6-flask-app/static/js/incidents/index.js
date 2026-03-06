/**
 * templates/incidents/index.js - Incident Management JavaScript
 */

document.addEventListener('DOMContentLoaded', function() {
    initIncidentCards();
    initWorkflows();
    initBannerActions();
    startIncidentPolling();
});

// Incident card interactions
function initIncidentCards() {
    const cards = document.querySelectorAll('.incident-card');
    
    cards.forEach(card => {
        card.addEventListener('click', function() {
            const incidentId = this.querySelector('.incident-id').textContent;
            openIncidentDetail(incidentId);
        });
        
        // Make cards draggable
        card.draggable = true;
        card.addEventListener('dragstart', handleDragStart);
    });
    
    // Setup drop zones
    const columns = document.querySelectorAll('.incident-column');
    columns.forEach(column => {
        column.addEventListener('dragover', handleDragOver);
        column.addEventListener('drop', handleDrop);
    });
}

function handleDragStart(e) {
    e.dataTransfer.setData('text/plain', e.target.querySelector('.incident-id').textContent);
}

function handleDragOver(e) {
    e.preventDefault();
}

async function handleDrop(e) {
    e.preventDefault();
    const incidentId = e.dataTransfer.getData('text/plain');
    const newStatus = e.currentTarget.querySelector('.column-header span').textContent;
    
    await updateIncidentStatus(incidentId, newStatus);
}

async function updateIncidentStatus(incidentId, status) {
    await fetch(`/api/incidents/${incidentId}/status`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status })
    });
    
    // Refresh display
    location.reload();
}

function openIncidentDetail(incidentId) {
    window.location.href = `/app/incidents/${incidentId}`;
}

// Workflow buttons
function initWorkflows() {
    const workflowBtns = document.querySelectorAll('.workflow-btn');
    
    workflowBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const workflowName = this.closest('.workflow-item').querySelector('.workflow-name').textContent;
            runWorkflow(workflowName);
        });
    });
}

async function runWorkflow(workflowName) {
    if (!confirm(`Run "${workflowName}" workflow?`)) return;
    
    const response = await fetch('/api/incidents/workflows/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ workflow: workflowName })
    });
    
    const result = await response.json();
    alert(`Workflow started: ${result.execution_id}`);
}

// Banner actions
function initBannerActions() {
    const bannerBtns = document.querySelectorAll('.banner-btn');
    
    bannerBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const action = this.textContent.trim();
            if (action === 'Acknowledge') {
                acknowledgeIncident('INC-2024-0089');
            } else if (action === 'View Details') {
                openIncidentDetail('INC-2024-0089');
            }
        });
    });
}

async function acknowledgeIncident(incidentId) {
    await fetch(`/api/incidents/${incidentId}/acknowledge`, { method: 'POST' });
    document.querySelector('.active-incident-banner').style.display = 'none';
}

// Incident polling
function startIncidentPolling() {
    setInterval(() => {
        fetchNewIncidents();
    }, 30000);
}

async function fetchNewIncidents() {
    const response = await fetch('/api/incidents?status=active');
    const incidents = await response.json();
    
    // Update incident board if needed
}

// Create new incident
async function createIncident(data) {
    const response = await fetch('/api/incidents', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    
    return response.json();
}

// Add timeline entry
async function addTimelineEntry(incidentId, entry) {
    await fetch(`/api/incidents/${incidentId}/timeline`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(entry)
    });
}

// API
const IncidentManagement = {
    getAll: (filters = {}) => {
        const params = new URLSearchParams(filters);
        return fetch(`/api/incidents?${params}`).then(r => r.json());
    },
    
    get: (id) => fetch(`/api/incidents/${id}`).then(r => r.json()),
    
    create: (data) => fetch('/api/incidents', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    }).then(r => r.json()),
    
    updateStatus: (id, status) => fetch(`/api/incidents/${id}/status`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status })
    }).then(r => r.json()),
    
    acknowledge: (id) => fetch(`/api/incidents/${id}/acknowledge`, { method: 'POST' }),
    
    getTimeline: (id) => fetch(`/api/incidents/${id}/timeline`).then(r => r.json()),
    
    addTimelineEntry: (id, entry) => fetch(`/api/incidents/${id}/timeline`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(entry)
    }),
    
    getPostmortems: () => fetch('/api/incidents/postmortems').then(r => r.json()),
    
    runWorkflow: (name) => fetch('/api/incidents/workflows/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ workflow: name })
    }).then(r => r.json())
};

window.IncidentManagement = IncidentManagement;
