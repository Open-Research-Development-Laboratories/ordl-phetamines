/**
 * Command Center JavaScript
 * Handles batch dispatch, targeted dispatch, and response streams
 */

let selectedTargets = new Set();
let currentTargetTab = 'nodes';
let selectedScope = 'parallel';

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    initCommandCenter();
});

function initCommandCenter() {
    setupEventListeners();
    updateTargetCount();
}

function setupEventListeners() {
    // Command input
    const commandInput = document.getElementById('commandInput');
    if (commandInput) {
        commandInput.addEventListener('input', updateDispatchButton);
    }
    
    // Rate slider
    const rateSlider = document.getElementById('rateSlider');
    if (rateSlider) {
        rateSlider.addEventListener('input', function() {
            updateRateValue(this.value);
        });
    }
}

// Target tab selection
function selectTargetTab(el, tab) {
    document.querySelectorAll('.target-tab').forEach(t => t.classList.remove('active'));
    el.classList.add('active');
    
    document.querySelectorAll('.target-panel').forEach(p => p.classList.remove('active'));
    document.getElementById(`panel-${tab}`).classList.add('active');
    
    currentTargetTab = tab;
}

// Target selection
function toggleTarget(el, targetId) {
    el.classList.toggle('selected');
    
    if (selectedTargets.has(targetId)) {
        selectedTargets.delete(targetId);
    } else {
        selectedTargets.add(targetId);
    }
    
    updateTargetCount();
}

function toggleChip(el) {
    el.classList.toggle('active');
    const targetId = el.textContent.trim();
    
    if (selectedTargets.has(targetId)) {
        selectedTargets.delete(targetId);
    } else {
        selectedTargets.add(targetId);
    }
    
    updateTargetCount();
}

function updateTargetCount() {
    const countEl = document.getElementById('selectedCount');
    if (countEl) {
        countEl.textContent = selectedTargets.size;
    }
    updateDispatchButton();
}

// Command presets
function setCommand(command) {
    const input = document.getElementById('commandInput');
    if (input) {
        input.value = command;
        updateDispatchButton();
    }
}

function updateRateValue(value) {
    const valueEl = document.getElementById('rateValue');
    if (valueEl) {
        valueEl.textContent = value + '/s';
    }
}

// Scope selection
function selectScope(el, scope) {
    document.querySelectorAll('.scope-option').forEach(o => o.classList.remove('active'));
    el.classList.add('active');
    selectedScope = scope;
}

// Dispatch button state
function updateDispatchButton() {
    const btn = document.getElementById('dispatchBtn');
    const command = document.getElementById('commandInput')?.value.trim();
    
    if (btn) {
        btn.disabled = selectedTargets.size === 0 || !command;
    }
}

// Dry run
function dryRun() {
    const command = document.getElementById('commandInput')?.value;
    if (!command) {
        alert('Please enter a command');
        return;
    }
    
    console.log('Dry run command:', command);
    console.log('Targets:', Array.from(selectedTargets));
    
    addStreamEntry({
        timestamp: new Date().toISOString().split('T')[1].split('.')[0],
        target: 'DRY RUN',
        message: `Command "${command}" would affect ${selectedTargets.size} targets`,
        type: 'info'
    });
}

// Dispatch command
function dispatchCommand() {
    const command = document.getElementById('commandInput')?.value;
    if (!command) {
        alert('Please enter a command');
        return;
    }
    
    if (selectedTargets.size === 0) {
        alert('Please select at least one target');
        return;
    }
    
    console.log('Dispatching command:', command);
    console.log('Targets:', Array.from(selectedTargets));
    console.log('Scope:', selectedScope);
    
    // Show batch summary
    const summary = document.getElementById('batchSummary');
    if (summary) {
        summary.style.display = 'block';
    }
    
    // Simulate dispatch
    Array.from(selectedTargets).forEach((target, index) => {
        setTimeout(() => {
            addStreamEntry({
                timestamp: new Date().toISOString().split('T')[1].split('.')[0],
                target: target,
                message: `Executing "${command}"...`,
                type: 'info'
            });
            
            setTimeout(() => {
                addStreamEntry({
                    timestamp: new Date().toISOString().split('T')[1].split('.')[0],
                    target: target,
                    message: 'Command completed successfully',
                    type: 'success'
                });
            }, 1000 + Math.random() * 2000);
        }, index * 100);
    });
}

// Response stream
function addStreamEntry(entry) {
    const stream = document.getElementById('responseStream');
    if (!stream) return;
    
    const typeClass = entry.type === 'success' ? 'stream-success' : 
                      entry.type === 'error' ? 'stream-error' :
                      entry.type === 'warning' ? 'stream-warning' : '';
    
    const html = `
        <div class="stream-entry">
            <div class="stream-timestamp">${entry.timestamp}</div>
            <div>
                <span class="stream-target">${entry.target}</span>
                ${typeClass ? `<span class="${typeClass}">${entry.type.toUpperCase()}</span>` : ''}
            </div>
            <div class="stream-message">${entry.message}</div>
        </div>
    `;
    
    stream.insertAdjacentHTML('beforeend', html);
    stream.scrollTop = stream.scrollHeight;
}

// Stream controls
function clearStream() {
    const stream = document.getElementById('responseStream');
    if (stream) {
        stream.innerHTML = '';
    }
}

function exportStream() {
    const stream = document.getElementById('responseStream');
    if (!stream) return;
    
    const text = stream.innerText;
    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = `command-stream-${new Date().toISOString().split('T')[0]}.txt`;
    a.click();
    
    URL.revokeObjectURL(url);
}

function pauseStream() {
    console.log('Pause stream');
    // Pause/resume stream logic
}

// Help modal
function showCommandHelp() {
    console.log('Show command help');
    // Open help modal with command documentation
}
