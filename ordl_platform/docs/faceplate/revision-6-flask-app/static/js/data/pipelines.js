/**
 * templates/data/pipelines.js - Data Pipelines JavaScript
 */

document.addEventListener('DOMContentLoaded', function() {
    initJobActions();
    initQualityGates();
    startJobProgressPolling();
});

// Job actions
function initJobActions() {
    const jobBtns = document.querySelectorAll('.job-btn');
    
    jobBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const action = this.textContent.trim();
            const jobRow = this.closest('.job-row');
            const jobName = jobRow?.querySelector('.job-name')?.textContent;
            const jobId = jobRow?.querySelector('.job-id')?.textContent;
            
            switch (action) {
                case 'Pause':
                    pauseJob(jobId);
                    break;
                case 'Logs':
                    showJobLogs(jobId);
                    break;
                case 'Retry':
                case 'Rerun':
                    retryJob(jobId);
                    break;
                case 'Cancel':
                    cancelJob(jobId);
                    break;
                case 'Edit':
                    editJob(jobId);
                    break;
            }
        });
    });
}

function pauseJob(jobId) {
    fetch(`/api/pipelines/jobs/${jobId}/pause`, { method: 'POST' })
        .then(r => r.json())
        .then(data => {
            showNotification(`Job ${jobId} paused`);
        });
}

function retryJob(jobId) {
    fetch(`/api/pipelines/jobs/${jobId}/retry`, { method: 'POST' })
        .then(r => r.json())
        .then(data => {
            showNotification(`Job ${jobId} retry queued`);
        });
}

function cancelJob(jobId) {
    if (confirm('Cancel this job?')) {
        fetch(`/api/pipelines/jobs/${jobId}/cancel`, { method: 'POST' })
            .then(r => r.json())
            .then(data => {
                showNotification(`Job ${jobId} cancelled`);
            });
    }
}

function showJobLogs(jobId) {
    window.open(`/app/pipelines/logs/${jobId}`, '_blank');
}

function editJob(jobId) {
    window.location.href = `/app/pipelines/edit/${jobId}`;
}

// Quality gates
function initQualityGates() {
    // Quality gate monitoring would go here
}

// Poll job progress
function startJobProgressPolling() {
    setInterval(() => {
        updateJobProgress();
    }, 3000);
}

function updateJobProgress() {
    const runningJobs = document.querySelectorAll('.status-badge.running');
    
    runningJobs.forEach(badge => {
        const jobRow = badge.closest('.job-row');
        const progressFill = jobRow?.querySelector('.job-progress-fill');
        const progressText = jobRow?.querySelector('.job-progress-text');
        
        if (progressFill) {
            const currentWidth = parseFloat(progressFill.style.width) || 0;
            const newWidth = Math.min(currentWidth + Math.random() * 2, 100);
            progressFill.style.width = newWidth + '%';
            
            if (progressText) {
                const match = progressText.textContent.match(/\(([^)]+)\)/);
                if (match) {
                    progressText.textContent = `${newWidth.toFixed(0)}% ${match[0]}`;
                }
            }
        }
    });
}

// Create new pipeline
function createPipeline(config) {
    return fetch('/api/pipelines', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
    }).then(r => r.json());
}

// Notification helper
function showNotification(message) {
    // Simple notification - could be replaced with toast system
    console.log('[Pipeline]', message);
}

// API
const DataPipelines = {
    getJobs: (filters = {}) => {
        const params = new URLSearchParams(filters);
        return fetch(`/api/pipelines/jobs?${params}`).then(r => r.json());
    },
    
    getJob: (jobId) => fetch(`/api/pipelines/jobs/${jobId}`).then(r => r.json()),
    
    create: (config) => fetch('/api/pipelines', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
    }).then(r => r.json()),
    
    update: (jobId, config) => fetch(`/api/pipelines/jobs/${jobId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
    }).then(r => r.json()),
    
    delete: (jobId) => fetch(`/api/pipelines/jobs/${jobId}`, { method: 'DELETE' }),
    
    getQualityGates: () => fetch('/api/pipelines/quality-gates').then(r => r.json()),
    
    getRetentionPolicies: () => fetch('/api/pipelines/retention').then(r => r.json())
};

window.DataPipelines = DataPipelines;
