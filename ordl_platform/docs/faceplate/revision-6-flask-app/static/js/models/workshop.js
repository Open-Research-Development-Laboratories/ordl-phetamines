/**
 * templates/models/workshop.js - Model Workshop JavaScript
 */

// Initialize Model Workshop
document.addEventListener('DOMContentLoaded', function() {
    initLineNumbers();
    initModelSelection();
    initEditorTabs();
    startJobProgressSimulation();
});

// Line numbers for editor
function initLineNumbers() {
    const editor = document.getElementById('codeEditor');
    const lineNumbers = document.getElementById('lineNumbers');
    
    function updateLineNumbers() {
        const lines = editor.value.split('\n').length;
        lineNumbers.innerHTML = Array.from({length: lines}, (_, i) => i + 1).join('\n');
    }
    
    editor.addEventListener('input', updateLineNumbers);
    editor.addEventListener('scroll', () => {
        lineNumbers.scrollTop = editor.scrollTop;
    });
    
    updateLineNumbers();
}

// Model selection
function initModelSelection() {
    const modelItems = document.querySelectorAll('.model-item');
    
    modelItems.forEach(item => {
        item.addEventListener('click', function() {
            modelItems.forEach(i => i.classList.remove('selected'));
            this.classList.add('selected');
        });
    });
}

// Editor tabs
function initEditorTabs() {
    const tabs = document.querySelectorAll('.editor-tab');
    
    tabs.forEach(tab => {
        tab.addEventListener('click', function() {
            tabs.forEach(t => t.classList.remove('active'));
            this.classList.add('active');
        });
    });
}

// Simulate job progress updates
function startJobProgressSimulation() {
    const jobs = [
        { name: 'Orchestrator-v2.1.1-finetune', progress: 78, speed: 0.1 },
        { name: 'Classifier-A-v1.5.0-RLHF', progress: 34, speed: 0.05 }
    ];
    
    setInterval(() => {
        const progressBars = document.querySelectorAll('.progress-fill');
        progressBars.forEach((bar, index) => {
            if (jobs[index] && jobs[index].progress < 100) {
                jobs[index].progress += Math.random() * jobs[index].speed;
                if (jobs[index].progress > 100) jobs[index].progress = 100;
                bar.style.width = jobs[index].progress.toFixed(1) + '%';
                
                // Update percentage text
                const percentText = bar.parentElement.nextElementSibling;
                if (percentText) {
                    percentText.textContent = jobs[index].progress.toFixed(0) + '%';
                }
            }
        });
    }, 2000);
}

// API functions for integration
const ModelWorkshop = {
    // Load model into editor
    loadModel: function(modelId) {
        fetch(`/api/models/${modelId}`)
            .then(r => r.json())
            .then(data => {
                document.getElementById('codeEditor').value = data.code;
                initLineNumbers();
            });
    },
    
    // Validate current model
    validate: function() {
        const code = document.getElementById('codeEditor').value;
        return fetch('/api/models/validate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code })
        }).then(r => r.json());
    },
    
    // Deploy model
    deploy: function(modelId, channel) {
        return fetch('/api/models/deploy', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ model_id: modelId, channel })
        }).then(r => r.json());
    },
    
    // Queue fine-tune job
    queueJob: function(config) {
        return fetch('/api/models/jobs', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        }).then(r => r.json());
    }
};

// Expose for global access
window.ModelWorkshop = ModelWorkshop;
