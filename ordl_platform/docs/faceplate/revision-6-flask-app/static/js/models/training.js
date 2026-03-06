/**
 * templates/models/training.js - Model Training JavaScript
 */

document.addEventListener('DOMContentLoaded', function() {
    initDatasetSelection();
    initHardwareSelection();
    initCostEstimator();
    initLaunchButton();
});

// Dataset selection
function initDatasetSelection() {
    const datasetItems = document.querySelectorAll('.dataset-item');
    const searchInput = document.getElementById('datasetSearch');
    
    datasetItems.forEach(item => {
        item.addEventListener('click', function(e) {
            if (e.target.type !== 'checkbox') {
                const checkbox = this.querySelector('.dataset-checkbox');
                checkbox.checked = !checkbox.checked;
            }
            this.classList.toggle('selected', this.querySelector('.dataset-checkbox').checked);
            updateCostEstimate();
        });
    });
    
    // Search filtering
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            const term = this.value.toLowerCase();
            datasetItems.forEach(item => {
                const name = item.querySelector('.dataset-name').textContent.toLowerCase();
                item.style.display = name.includes(term) ? 'flex' : 'none';
            });
        });
    }
}

// Hardware selection
function initHardwareSelection() {
    const hardwareOptions = document.querySelectorAll('.hardware-option');
    
    hardwareOptions.forEach(option => {
        option.addEventListener('click', function() {
            hardwareOptions.forEach(o => o.classList.remove('selected'));
            this.classList.add('selected');
            updateCostEstimate();
        });
    });
}

// Cost estimation
function initCostEstimator() {
    const inputs = document.querySelectorAll('.config-input');
    inputs.forEach(input => {
        input.addEventListener('change', updateCostEstimate);
    });
    updateCostEstimate();
}

function updateCostEstimate() {
    // Selected hardware price
    const selectedHardware = document.querySelector('.hardware-option.selected');
    const priceText = selectedHardware ? selectedHardware.querySelector('.hardware-price').textContent : '$32.50/hr';
    const hourlyRate = parseFloat(priceText.replace(/[$,/hr]/g, ''));
    
    // Selected datasets size
    const selectedDatasets = document.querySelectorAll('.dataset-item.selected').length;
    
    // Estimated hours (simplified calculation)
    const batchSize = parseInt(document.querySelector('input[value="512"]')?.value || 512);
    const maxSteps = parseInt(document.querySelector('input[value="100000"]')?.value || 100000);
    
    // Rough estimate: 1000 steps ≈ 0.5 hour on 8xA100
    const estimatedHours = (maxSteps / 1000) * 0.5 * (512 / batchSize);
    const totalCost = estimatedHours * hourlyRate;
    
    // Update display
    const hoursEl = document.getElementById('computeHours');
    const totalEl = document.getElementById('estimateTotal');
    
    if (hoursEl) hoursEl.textContent = `~${estimatedHours.toFixed(1)} hrs`;
    if (totalEl) totalEl.textContent = `$${totalCost.toFixed(0)}`;
}

// Launch button
function initLaunchButton() {
    const launchBtn = document.getElementById('launchBtn');
    if (launchBtn) {
        launchBtn.addEventListener('click', function() {
            if (confirm('Launch training job with current configuration?')) {
                launchTraining();
            }
        });
    }
}

function launchTraining() {
    const config = collectTrainingConfig();
    
    fetch('/api/models/training/jobs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
    })
    .then(r => r.json())
    .then(data => {
        alert(`Training job queued: ${data.job_id}`);
        window.location.href = `/app/models/workshop`;
    })
    .catch(err => {
        alert('Failed to launch training: ' + err.message);
    });
}

function collectTrainingConfig() {
    const datasets = [];
    document.querySelectorAll('.dataset-item.selected').forEach(item => {
        datasets.push(item.querySelector('.dataset-name').textContent);
    });
    
    const hardware = document.querySelector('.hardware-option.selected .hardware-name')?.textContent;
    
    return {
        model_name: 'Orchestrator-v2.1.1',
        datasets,
        hardware,
        batch_size: 512,
        learning_rate: 1e-4,
        warmup_steps: 1000,
        max_steps: 100000
    };
}

// API
const ModelTraining = {
    getDatasets: () => fetch('/api/datasets').then(r => r.json()),
    getHardware: () => fetch('/api/hardware').then(r => r.json()),
    estimateCost: (config) => fetch('/api/models/training/estimate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
    }).then(r => r.json()),
    launchJob: (config) => fetch('/api/models/training/jobs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
    }).then(r => r.json())
};

window.ModelTraining = ModelTraining;
