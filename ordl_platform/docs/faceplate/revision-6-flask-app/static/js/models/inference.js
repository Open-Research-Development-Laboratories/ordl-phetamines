/**
 * templates/models/inference.js - Model Inference JavaScript
 */

document.addEventListener('DOMContentLoaded', function() {
    initInferenceHarness();
    initMetricsChart();
    startMetricsPolling();
});

// Inference harness
function initInferenceHarness() {
    const runBtn = document.getElementById('runInferenceBtn');
    const promptInput = document.getElementById('promptInput');
    
    if (runBtn) {
        runBtn.addEventListener('click', runInference);
    }
    
    if (promptInput) {
        promptInput.addEventListener('keydown', function(e) {
            if (e.ctrlKey && e.key === 'Enter') {
                runInference();
            }
        });
    }
}

async function runInference() {
    const prompt = document.getElementById('promptInput').value;
    const responseContent = document.getElementById('responseContent');
    const runBtn = document.getElementById('runInferenceBtn');
    
    if (!prompt.trim()) {
        alert('Please enter a prompt');
        return;
    }
    
    // Show loading
    runBtn.disabled = true;
    runBtn.textContent = '⏳ Running...';
    responseContent.textContent = 'Generating response...';
    
    const startTime = performance.now();
    
    try {
        const response = await fetch('/api/models/inference', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                model: document.querySelector('.model-selector select')?.value,
                prompt,
                temperature: parseFloat(document.querySelector('input[value="0.7"]')?.value || 0.7),
                max_tokens: parseInt(document.querySelector('input[value="512"]')?.value || 512)
            })
        });
        
        const data = await response.json();
        const endTime = performance.now();
        const latency = (endTime - startTime).toFixed(0);
        
        // Update response
        responseContent.textContent = data.text || data.response || 'No response';
        
        // Update metrics
        document.getElementById('latencyValue').textContent = `${latency}ms`;
        document.getElementById('tokensValue').textContent = data.tokens || data.token_count || '~';
        document.getElementById('tpsValue').textContent = data.tps || `${((data.tokens || 100) / (latency / 1000)).toFixed(1)}`;
        document.getElementById('costValue').textContent = data.cost || `$${((data.tokens || 100) * 0.00002).toFixed(4)}`;
        
    } catch (error) {
        responseContent.textContent = `Error: ${error.message}`;
    } finally {
        runBtn.disabled = false;
        runBtn.textContent = '▶ Run Inference';
    }
}

// Metrics chart
function initMetricsChart() {
    // Chart would be initialized here with a library like Chart.js
    // For now, using static SVG
}

// Poll metrics
function startMetricsPolling() {
    // Simulate live metrics updates
    setInterval(() => {
        const metrics = {
            avgLatency: 140 + Math.random() * 20,
            p99Latency: 380 + Math.random() * 40,
            throughput: 1800 + Math.random() * 200
        };
        
        updateMetricsDisplay(metrics);
    }, 5000);
}

function updateMetricsDisplay(metrics) {
    const avgEl = document.getElementById('avgLatency');
    const p99El = document.getElementById('p99Latency');
    const tputEl = document.getElementById('throughput');
    
    if (avgEl) avgEl.textContent = Math.round(metrics.avgLatency);
    if (p99El) p99El.textContent = Math.round(metrics.p99Latency);
    if (tputEl) tputEl.textContent = Math.round(metrics.throughput).toLocaleString();
}

// Regression comparison
function loadRegressionComparison(baseline, current) {
    return fetch(`/api/models/compare?baseline=${baseline}&current=${current}`)
        .then(r => r.json())
        .then(data => {
            updateComparisonTable(data);
        });
}

function updateComparisonTable(data) {
    // Update table with comparison data
    const tbody = document.querySelector('.compare-table tbody');
    if (!tbody) return;
    
    tbody.innerHTML = data.metrics.map(m => `
        <tr>
            <td class="metric-name">${m.name}</td>
            <td class="baseline">${m.baseline}</td>
            <td class="current">${m.current}</td>
            <td class="change ${m.change > 0 ? 'positive' : m.change < 0 ? 'negative' : 'neutral'}">
                ${m.change > 0 ? '+' : ''}${m.change.toFixed(1)}% ${m.change >= 0 ? '✓' : '⚠'}
            </td>
        </tr>
    `).join('');
}

// Batch testing
async function runBatchTest(prompts) {
    const results = [];
    
    for (const prompt of prompts) {
        const startTime = performance.now();
        const response = await fetch('/api/models/inference', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt })
        });
        const endTime = performance.now();
        const data = await response.json();
        
        results.push({
            prompt,
            response: data.text,
            latency: endTime - startTime,
            tokens: data.tokens
        });
    }
    
    return results;
}

// API
const ModelInference = {
    run: (config) => fetch('/api/models/inference', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
    }).then(r => r.json()),
    
    getMetrics: (model) => fetch(`/api/models/${model}/metrics`).then(r => r.json()),
    
    compare: (baseline, current) => fetch(`/api/models/compare?baseline=${baseline}&current=${current}`)
        .then(r => r.json()),
    
    getHistory: () => fetch('/api/models/inference/history').then(r => r.json())
};

window.ModelInference = ModelInference;
