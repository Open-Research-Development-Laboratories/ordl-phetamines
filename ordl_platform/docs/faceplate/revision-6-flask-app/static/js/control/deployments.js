/**
 * Deployments JavaScript
 * Handles deployment management, rollbacks, and canary controls
 */

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    initDeployments();
});

function initDeployments() {
    setupEventListeners();
}

function setupEventListeners() {
    // Environment selector
    document.querySelectorAll('.env-item').forEach(item => {
        item.addEventListener('click', function() {
            document.querySelectorAll('.env-item').forEach(i => i.classList.remove('active'));
            this.classList.add('active');
        });
    });
    
    // Canary slider
    const canarySlider = document.getElementById('canarySlider');
    if (canarySlider) {
        canarySlider.addEventListener('input', function() {
            document.querySelector('.canary-percentage').textContent = this.value + '%';
        });
    }
}

// Environment selection
function selectEnv(el, env) {
    document.querySelectorAll('.env-item').forEach(item => item.classList.remove('active'));
    el.classList.add('active');
    console.log('Selected environment:', env);
    loadDeployments(env);
}

function loadDeployments(env) {
    console.log('Loading deployments for:', env);
    // Load deployment data for selected environment
}

// Deployment card actions
function toggleDetails(header) {
    const details = header.nextElementSibling;
    if (details) {
        details.classList.toggle('open');
    }
}

function deployNow() {
    console.log('Deploy now');
    showModal('deployModal');
}

function viewLogs(deploymentId) {
    console.log('View logs for:', deploymentId);
    window.open(`/api/deployments/${deploymentId}/logs`, '_blank');
}

function pauseDeploy(deploymentId) {
    console.log('Pause deployment:', deploymentId);
    // Pause deployment
}

function promote(deploymentId) {
    console.log('Promote deployment:', deploymentId);
    if (confirm('Promote this deployment to the next environment?')) {
        // Promote deployment
    }
}

function retryDeploy(deploymentId) {
    console.log('Retry deployment:', deploymentId);
    if (confirm('Retry this failed deployment?')) {
        // Retry deployment
    }
}

// Rollback
function rollback(deploymentId) {
    console.log('Rollback deployment:', deploymentId);
    rollbackModal();
}

function rollbackModal() {
    const modal = document.getElementById('rollbackModal');
    if (modal) {
        modal.classList.add('active');
    }
}

function closeRollbackModal() {
    const modal = document.getElementById('rollbackModal');
    if (modal) {
        modal.classList.remove('active');
    }
}

function selectRollback(el) {
    document.querySelectorAll('.rollback-item').forEach(item => item.classList.remove('selected'));
    el.classList.add('selected');
}

function confirmRollback() {
    const selected = document.querySelector('.rollback-item.selected');
    if (selected) {
        console.log('Rollback to version');
        closeRollbackModal();
        // Perform rollback
    } else {
        alert('Please select a version to rollback to');
    }
}

function viewMetrics() {
    console.log('View metrics');
    window.location.href = '/app/reports';
}

// Modal helpers
function showModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('active');
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('active');
    }
}
