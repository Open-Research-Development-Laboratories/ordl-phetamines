/**
 * Temporal Debugger (Determinism Slider) for ORDL IDE
 * A timeline-based debugger for visualizing and controlling deterministic replay
 */

// ============================================================================
// MOCK TIMELINE DATA - Simulates agent activations and message events
// ============================================================================

const MOCK_TIMELINE_DATA = {
    totalTicks: 1000,
    currentTick: 0,
    events: [
        // Agent activation events
        { tick: 10, type: 'agent_activation', agentId: 'agent-alpha', data: { role: 'coordinator', priority: 'high' } },
        { tick: 25, type: 'agent_activation', agentId: 'agent-beta', data: { role: 'worker', priority: 'normal' } },
        { tick: 45, type: 'agent_activation', agentId: 'agent-gamma', data: { role: 'worker', priority: 'normal' } },
        { tick: 120, type: 'agent_activation', agentId: 'agent-delta', data: { role: 'observer', priority: 'low' } },
        { tick: 200, type: 'agent_activation', agentId: 'agent-epsilon', data: { role: 'specialist', priority: 'high' } },
        { tick: 350, type: 'agent_activation', agentId: 'agent-zeta', data: { role: 'worker', priority: 'normal' } },
        { tick: 500, type: 'agent_activation', agentId: 'agent-eta', data: { role: 'coordinator', priority: 'high' } },
        { tick: 650, type: 'agent_activation', agentId: 'agent-theta', data: { role: 'worker', priority: 'normal' } },
        { tick: 800, type: 'agent_activation', agentId: 'agent-iota', data: { role: 'observer', priority: 'low' } },
        { tick: 950, type: 'agent_activation', agentId: 'agent-kappa', data: { role: 'worker', priority: 'normal' } },
        
        // Message events
        { tick: 30, type: 'message', from: 'agent-alpha', to: 'agent-beta', data: { content: 'init_task', size: 256 } },
        { tick: 50, type: 'message', from: 'agent-beta', to: 'agent-gamma', data: { content: 'delegate_work', size: 128 } },
        { tick: 85, type: 'message', from: 'agent-gamma', to: 'agent-alpha', data: { content: 'status_update', size: 64 } },
        { tick: 150, type: 'message', from: 'agent-alpha', to: 'agent-delta', data: { content: 'subscribe_request', size: 32 } },
        { tick: 220, type: 'message', from: 'agent-epsilon', to: 'agent-beta', data: { content: 'specialized_data', size: 512 } },
        { tick: 280, type: 'message', from: 'agent-beta', to: 'agent-epsilon', data: { content: 'ack', size: 16 } },
        { tick: 380, type: 'message', from: 'agent-zeta', to: 'agent-alpha', data: { content: 'task_complete', size: 128 } },
        { tick: 420, type: 'message', from: 'agent-alpha', to: 'agent-gamma', data: { content: 'new_assignment', size: 256 } },
        { tick: 520, type: 'message', from: 'agent-eta', to: 'agent-zeta', data: { content: 'coordination_sync', size: 64 } },
        { tick: 580, type: 'message', from: 'agent-zeta', to: 'agent-eta', data: { content: 'sync_ack', size: 16 } },
        { tick: 680, type: 'message', from: 'agent-theta', to: 'agent-gamma', data: { content: 'data_request', size: 48 } },
        { tick: 720, type: 'message', from: 'agent-gamma', to: 'agent-theta', data: { content: 'data_response', size: 1024 } },
        { tick: 850, type: 'message', from: 'agent-iota', to: 'agent-delta', data: { content: 'observation_log', size: 2048 } },
        { tick: 920, type: 'message', from: 'agent-alpha', to: 'agent-kappa', data: { content: 'final_task', size: 512 } },
        
        // State change events
        { tick: 100, type: 'state_change', data: { key: 'system_mode', oldValue: 'init', newValue: 'active' } },
        { tick: 300, type: 'state_change', data: { key: 'load_balancer', oldValue: 'round_robin', newValue: 'weighted' } },
        { tick: 600, type: 'state_change', data: { key: 'system_mode', oldValue: 'active', newValue: 'scaling' } },
        { tick: 900, type: 'state_change', data: { key: 'system_mode', oldValue: 'scaling', newValue: 'stable' } },
    ],
    
    // Branch points where execution could diverge
    branchPoints: [
        { tick: 150, description: 'Decision: Enable caching', alternatePath: 'no-cache-branch' },
        { tick: 400, description: 'Decision: Scale up workers', alternatePath: 'no-scale-branch' },
        { tick: 750, description: 'Decision: Failover to backup', alternatePath: 'primary-only-branch' },
    ],
    
    // Breakpoints set by user
    breakpoints: new Set(),
    
    // Saved scenarios
    savedScenarios: [],
    
    // Fleet state at key moments (sparse snapshots)
    snapshots: {
        0: { agents: [], activeConnections: 0, queueDepth: 0 },
        100: { agents: ['agent-alpha', 'agent-beta', 'agent-gamma'], activeConnections: 3, queueDepth: 12 },
        250: { agents: ['agent-alpha', 'agent-beta', 'agent-gamma', 'agent-delta', 'agent-epsilon'], activeConnections: 8, queueDepth: 24 },
        500: { agents: ['agent-alpha', 'agent-beta', 'agent-gamma', 'agent-delta', 'agent-epsilon', 'agent-zeta', 'agent-eta'], activeConnections: 12, queueDepth: 8 },
        750: { agents: ['agent-alpha', 'agent-beta', 'agent-gamma', 'agent-delta', 'agent-epsilon', 'agent-zeta', 'agent-eta', 'agent-theta'], activeConnections: 15, queueDepth: 3 },
        1000: { agents: ['agent-alpha', 'agent-beta', 'agent-gamma', 'agent-delta', 'agent-epsilon', 'agent-zeta', 'agent-eta', 'agent-theta', 'agent-iota', 'agent-kappa'], activeConnections: 18, queueDepth: 0 },
    }
};

// ============================================================================
// TEMPORAL DEBUGGER CLASS
// ============================================================================

class TemporalDebugger {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            throw new Error(`Container with id "${containerId}" not found`);
        }
        
        // Configuration
        this.options = {
            width: options.width || 800,
            timelineHeight: options.timelineHeight || 60,
            tickInterval: options.tickInterval || 50,
            majorTickInterval: options.majorTickInterval || 100,
            autoPlayInterval: options.autoPlayInterval || 100,
            ...options
        };
        
        // State
        this.data = MOCK_TIMELINE_DATA;
        this.isPlaying = false;
        this.playInterval = null;
        this.isDragging = false;
        this.dragStartX = 0;
        this.dragStartTick = 0;
        
        // UI Elements cache
        this.elements = {};
        
        // Initialize
        this.init();
    }
    
    // ============================================================================
    // INITIALIZATION
    // ============================================================================
    
    init() {
        this.createStyles();
        this.createDOM();
        this.attachEventListeners();
        this.render();
        this.updateStatePanel();
    }
    
    createStyles() {
        const styleId = 'temporal-debugger-styles';
        if (document.getElementById(styleId)) return;
        
        const styles = `
            .temporal-debugger {
                font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Fira Code', monospace;
                background: #1a1a1a;
                border-radius: 8px;
                overflow: hidden;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
                color: #e8e0d0;
            }
            
            .temporal-debugger * {
                box-sizing: border-box;
            }
            
            /* Header */
            .td-header {
                background: linear-gradient(180deg, #252525 0%, #1e1e1e 100%);
                padding: 12px 16px;
                border-bottom: 1px solid #333;
                display: flex;
                align-items: center;
                justify-content: space-between;
            }
            
            .td-title {
                font-size: 14px;
                font-weight: 600;
                color: #f5f0e6;
                display: flex;
                align-items: center;
                gap: 8px;
            }
            
            .td-title-icon {
                width: 16px;
                height: 16px;
                background: linear-gradient(135deg, #d4a853 0%, #b8934a 100%);
                border-radius: 3px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 10px;
            }
            
            .td-tick-display {
                font-size: 12px;
                color: #a09080;
                background: #151515;
                padding: 4px 12px;
                border-radius: 4px;
                border: 1px solid #333;
            }
            
            .td-tick-display span {
                color: #d4a853;
                font-weight: 600;
            }
            
            /* Timeline Container */
            .td-timeline-container {
                position: relative;
                padding: 20px 16px;
                background: 
                    linear-gradient(rgba(212, 168, 83, 0.03) 1px, transparent 1px),
                    linear-gradient(90deg, rgba(212, 168, 83, 0.03) 1px, transparent 1px),
                    #1e1e1e;
                background-size: 20px 20px;
            }
            
            /* Timeline Track */
            .td-timeline-track {
                position: relative;
                height: 40px;
                background: linear-gradient(180deg, #f5f0e6 0%, #e8e0d0 100%);
                border-radius: 3px;
                box-shadow: 
                    inset 0 1px 3px rgba(0,0,0,0.3),
                    0 1px 0 rgba(255,255,255,0.05);
                overflow: visible;
            }
            
            /* Tick Marks */
            .td-tick-marks {
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                pointer-events: none;
            }
            
            .td-tick {
                position: absolute;
                top: 0;
                bottom: 0;
                width: 1px;
                background: rgba(0,0,0,0.15);
            }
            
            .td-tick.major {
                width: 2px;
                background: rgba(0,0,0,0.3);
            }
            
            .td-tick-label {
                position: absolute;
                top: 44px;
                font-size: 9px;
                color: #807060;
                transform: translateX(-50%);
            }
            
            /* Event Markers */
            .td-event-marker {
                position: absolute;
                top: 8px;
                width: 3px;
                height: 24px;
                border-radius: 1px;
                transform: translateX(-50%);
                cursor: pointer;
                transition: all 0.15s ease;
                z-index: 5;
            }
            
            .td-event-marker:hover {
                transform: translateX(-50%) scaleY(1.2);
            }
            
            .td-event-marker.agent_activation {
                background: linear-gradient(180deg, #4a9eff 0%, #2d7dd4 100%);
                box-shadow: 0 0 4px rgba(74, 158, 255, 0.4);
            }
            
            .td-event-marker.message {
                background: linear-gradient(180deg, #5dd45d 0%, #3cb83c 100%);
                box-shadow: 0 0 4px rgba(93, 212, 93, 0.4);
            }
            
            .td-event-marker.state_change {
                background: linear-gradient(180deg, #d4a853 0%, #b8934a 100%);
                box-shadow: 0 0 4px rgba(212, 168, 83, 0.4);
            }
            
            /* Branch Points (Diamonds) */
            .td-branch-point {
                position: absolute;
                top: 50%;
                width: 14px;
                height: 14px;
                background: linear-gradient(135deg, #e07070 0%, #c05050 100%);
                transform: translate(-50%, -50%) rotate(45deg);
                cursor: pointer;
                z-index: 10;
                box-shadow: 
                    0 0 0 2px rgba(224, 112, 112, 0.3),
                    0 2px 4px rgba(0,0,0,0.3);
                transition: all 0.15s ease;
            }
            
            .td-branch-point:hover {
                transform: translate(-50%, -50%) rotate(45deg) scale(1.15);
                box-shadow: 
                    0 0 0 3px rgba(224, 112, 112, 0.5),
                    0 3px 6px rgba(0,0,0,0.4);
            }
            
            .td-branch-point::after {
                content: '';
                position: absolute;
                top: 50%;
                left: 50%;
                width: 4px;
                height: 4px;
                background: #f5f0e6;
                transform: translate(-50%, -50%);
                border-radius: 50%;
            }
            
            /* Breakpoint Indicators */
            .td-breakpoint {
                position: absolute;
                top: -8px;
                width: 0;
                height: 0;
                border-left: 6px solid transparent;
                border-right: 6px solid transparent;
                border-top: 10px solid #e05050;
                transform: translateX(-50%);
                cursor: pointer;
                z-index: 15;
                filter: drop-shadow(0 2px 2px rgba(0,0,0,0.3));
            }
            
            .td-breakpoint:hover {
                border-top-color: #ff6060;
            }
            
            /* Playhead */
            .td-playhead {
                position: absolute;
                top: -10px;
                bottom: -10px;
                width: 3px;
                background: linear-gradient(180deg, #d4a853 0%, #b8934a 100%);
                transform: translateX(-50%);
                cursor: grab;
                z-index: 20;
                box-shadow: 
                    0 0 15px rgba(212, 168, 83, 0.6),
                    0 0 30px rgba(212, 168, 83, 0.3),
                    0 2px 4px rgba(0,0,0,0.3);
            }
            
            .td-playhead:active {
                cursor: grabbing;
            }
            
            /* Tape Machine Style Playhead Top */
            .td-playhead::before {
                content: '';
                position: absolute;
                top: -8px;
                left: 50%;
                transform: translateX(-50%);
                width: 24px;
                height: 14px;
                background: linear-gradient(180deg, #3a3a3a 0%, #2a2a2a 100%);
                border-radius: 3px;
                box-shadow: 
                    0 2px 4px rgba(0,0,0,0.4),
                    inset 0 1px 0 rgba(255,255,255,0.1);
                border: 1px solid #1a1a1a;
            }
            
            /* Playhead Amber Glow Line */
            .td-playhead::after {
                content: '';
                position: absolute;
                top: -10px;
                bottom: -10px;
                left: 50%;
                transform: translateX(-50%);
                width: 1px;
                background: linear-gradient(180deg, 
                    transparent 0%,
                    rgba(212, 168, 83, 0.8) 20%,
                    rgba(212, 168, 83, 0.8) 80%,
                    transparent 100%
                );
            }
            
            /* Controls */
            .td-controls {
                display: flex;
                align-items: center;
                gap: 12px;
                padding: 12px 16px;
                background: #1e1e1e;
                border-top: 1px solid #333;
                border-bottom: 1px solid #333;
            }
            
            .td-btn {
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 6px;
                padding: 8px 14px;
                font-size: 12px;
                font-weight: 500;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                transition: all 0.15s ease;
                font-family: inherit;
            }
            
            .td-btn-primary {
                background: linear-gradient(180deg, #d4a853 0%, #b8934a 100%);
                color: #1a1a1a;
                box-shadow: 0 2px 4px rgba(0,0,0,0.3);
            }
            
            .td-btn-primary:hover {
                background: linear-gradient(180deg, #e0b860 0%, #c4a050 100%);
                transform: translateY(-1px);
                box-shadow: 0 3px 6px rgba(0,0,0,0.4);
            }
            
            .td-btn-primary:active {
                transform: translateY(0);
                box-shadow: 0 1px 2px rgba(0,0,0,0.3);
            }
            
            .td-btn-secondary {
                background: #2a2a2a;
                color: #d0c8b8;
                border: 1px solid #404040;
            }
            
            .td-btn-secondary:hover {
                background: #333;
                border-color: #505050;
            }
            
            .td-btn-secondary:disabled {
                opacity: 0.4;
                cursor: not-allowed;
            }
            
            .td-btn-icon {
                width: 14px;
                height: 14px;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            
            .td-step-controls {
                display: flex;
                gap: 4px;
            }
            
            .td-btn-step {
                width: 32px;
                padding: 8px;
            }
            
            .td-divider {
                width: 1px;
                height: 24px;
                background: #404040;
                margin: 0 4px;
            }
            
            /* State Panel */
            .td-state-panel {
                background: #151515;
                padding: 16px;
            }
            
            .td-panel-header {
                font-size: 11px;
                text-transform: uppercase;
                letter-spacing: 1px;
                color: #807060;
                margin-bottom: 12px;
                display: flex;
                align-items: center;
                gap: 8px;
            }
            
            .td-panel-header::before {
                content: '';
                width: 8px;
                height: 8px;
                background: #d4a853;
                border-radius: 2px;
            }
            
            .td-state-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 16px;
            }
            
            .td-state-card {
                background: #1e1e1e;
                border: 1px solid #2a2a2a;
                border-radius: 6px;
                padding: 12px;
            }
            
            .td-state-card-title {
                font-size: 11px;
                color: #a09080;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                margin-bottom: 8px;
            }
            
            .td-agent-list {
                display: flex;
                flex-wrap: wrap;
                gap: 6px;
            }
            
            .td-agent-badge {
                display: inline-flex;
                align-items: center;
                gap: 4px;
                padding: 4px 8px;
                background: #2a2a2a;
                border-radius: 3px;
                font-size: 11px;
                color: #c8c0b0;
                border: 1px solid #363636;
            }
            
            .td-agent-badge::before {
                content: '';
                width: 6px;
                height: 6px;
                background: #4a9eff;
                border-radius: 50%;
            }
            
            .td-agent-badge.active::before {
                background: #5dd45d;
                box-shadow: 0 0 4px #5dd45d;
            }
            
            .td-metric {
                display: flex;
                align-items: baseline;
                gap: 8px;
            }
            
            .td-metric-value {
                font-size: 24px;
                font-weight: 600;
                color: #f5f0e6;
            }
            
            .td-metric-label {
                font-size: 11px;
                color: #807060;
            }
            
            /* Message Flow */
            .td-message-list {
                max-height: 150px;
                overflow-y: auto;
            }
            
            .td-message-item {
                display: flex;
                align-items: center;
                gap: 8px;
                padding: 6px 0;
                border-bottom: 1px solid #2a2a2a;
                font-size: 11px;
            }
            
            .td-message-item:last-child {
                border-bottom: none;
            }
            
            .td-message-direction {
                color: #a09080;
                font-size: 10px;
            }
            
            .td-message-from {
                color: #4a9eff;
            }
            
            .td-message-to {
                color: #5dd45d;
            }
            
            .td-message-content {
                color: #d0c8b8;
                font-family: inherit;
                background: #252525;
                padding: 2px 6px;
                border-radius: 3px;
            }
            
            /* Legend */
            .td-legend {
                display: flex;
                gap: 16px;
                padding: 10px 16px;
                background: #1a1a1a;
                font-size: 10px;
                color: #807060;
                border-top: 1px solid #2a2a2a;
            }
            
            .td-legend-item {
                display: flex;
                align-items: center;
                gap: 6px;
            }
            
            .td-legend-marker {
                width: 8px;
                height: 12px;
                border-radius: 1px;
            }
            
            .td-legend-marker.agent { background: #4a9eff; }
            .td-legend-marker.message { background: #5dd45d; }
            .td-legend-marker.state { background: #d4a853; }
            .td-legend-marker.branch { 
                width: 8px;
                height: 8px;
                background: #e07070;
                transform: rotate(45deg);
            }
            
            /* Tooltip */
            .td-tooltip {
                position: absolute;
                background: rgba(30, 30, 30, 0.95);
                border: 1px solid #404040;
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 11px;
                color: #d0c8b8;
                pointer-events: none;
                z-index: 100;
                box-shadow: 0 4px 12px rgba(0,0,0,0.4);
                max-width: 250px;
            }
            
            .td-tooltip-title {
                font-weight: 600;
                color: #f5f0e6;
                margin-bottom: 4px;
            }
            
            .td-tooltip-row {
                display: flex;
                gap: 8px;
                margin-top: 2px;
            }
            
            .td-tooltip-label {
                color: #807060;
            }
            
            /* Scrollbar */
            .td-message-list::-webkit-scrollbar {
                width: 6px;
            }
            
            .td-message-list::-webkit-scrollbar-track {
                background: #1a1a1a;
            }
            
            .td-message-list::-webkit-scrollbar-thumb {
                background: #404040;
                border-radius: 3px;
            }
            
            .td-message-list::-webkit-scrollbar-thumb:hover {
                background: #505050;
            }
        `;
        
        const styleSheet = document.createElement('style');
        styleSheet.id = styleId;
        styleSheet.textContent = styles;
        document.head.appendChild(styleSheet);
    }
    
    createDOM() {
        this.container.className = 'temporal-debugger';
        this.container.innerHTML = `
            <div class="td-header">
                <div class="td-title">
                    <div class="td-title-icon">◈</div>
                    Temporal Debugger
                </div>
                <div class="td-tick-display">
                    Tick: <span id="td-current-tick">0</span> / ${this.data.totalTicks}
                </div>
            </div>
            
            <div class="td-timeline-container">
                <div class="td-timeline-track" id="td-track">
                    <div class="td-tick-marks" id="td-ticks"></div>
                    <div class="td-event-markers" id="td-events"></div>
                    <div class="td-branch-points" id="td-branches"></div>
                    <div class="td-breakpoints" id="td-breakpoints"></div>
                    <div class="td-playhead" id="td-playhead" style="left: 0%"></div>
                </div>
            </div>
            
            <div class="td-controls">
                <button class="td-btn td-btn-primary" id="td-play-btn">
                    <span class="td-btn-icon">▶</span>
                    <span id="td-play-text">Play</span>
                </button>
                
                <div class="td-step-controls">
                    <button class="td-btn td-btn-secondary td-btn-step" id="td-step-back" title="Step Back">
                        ◀
                    </button>
                    <button class="td-btn td-btn-secondary td-btn-step" id="td-step-forward" title="Step Forward">
                        ▶
                    </button>
                </div>
                
                <div class="td-divider"></div>
                
                <button class="td-btn td-btn-secondary" id="td-set-breakpoint">
                    <span class="td-btn-icon">◢</span>
                    Set Breakpoint
                </button>
                
                <button class="td-btn td-btn-secondary" id="td-save-scenario">
                    <span class="td-btn-icon">💾</span>
                    Save Scenario
                </button>
            </div>
            
            <div class="td-state-panel">
                <div class="td-panel-header">State Inspection</div>
                <div class="td-state-grid">
                    <div class="td-state-card">
                        <div class="td-state-card-title">Active Agents</div>
                        <div class="td-agent-list" id="td-agent-list">
                            <span class="td-agent-badge">None</span>
                        </div>
                    </div>
                    
                    <div class="td-state-card">
                        <div class="td-state-card-title">Fleet Metrics</div>
                        <div class="td-metric">
                            <span class="td-metric-value" id="td-connections">0</span>
                            <span class="td-metric-label">connections</span>
                        </div>
                        <div class="td-metric" style="margin-top: 8px;">
                            <span class="td-metric-value" id="td-queue">0</span>
                            <span class="td-metric-label">queue depth</span>
                        </div>
                    </div>
                    
                    <div class="td-state-card" style="grid-column: span 2;">
                        <div class="td-state-card-title">Message Flow at Tick <span id="td-msg-tick">0</span></div>
                        <div class="td-message-list" id="td-message-list">
                            <div style="color: #605040; font-size: 11px; font-style: italic;">
                                No messages at this tick
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="td-legend">
                <div class="td-legend-item">
                    <div class="td-legend-marker agent"></div>
                    Agent Activation
                </div>
                <div class="td-legend-item">
                    <div class="td-legend-marker message"></div>
                    Message
                </div>
                <div class="td-legend-item">
                    <div class="td-legend-marker state"></div>
                    State Change
                </div>
                <div class="td-legend-item">
                    <div class="td-legend-marker branch"></div>
                    Branch Point
                </div>
            </div>
        `;
        
        // Cache elements
        this.elements = {
            container: this.container,
            track: this.container.querySelector('#td-track'),
            playhead: this.container.querySelector('#td-playhead'),
            tickDisplay: this.container.querySelector('#td-current-tick'),
            tickContainer: this.container.querySelector('#td-ticks'),
            eventContainer: this.container.querySelector('#td-events'),
            branchContainer: this.container.querySelector('#td-branches'),
            breakpointContainer: this.container.querySelector('#td-breakpoints'),
            playBtn: this.container.querySelector('#td-play-btn'),
            playText: this.container.querySelector('#td-play-text'),
            stepBack: this.container.querySelector('#td-step-back'),
            stepForward: this.container.querySelector('#td-step-forward'),
            setBreakpoint: this.container.querySelector('#td-set-breakpoint'),
            saveScenario: this.container.querySelector('#td-save-scenario'),
            agentList: this.container.querySelector('#td-agent-list'),
            connections: this.container.querySelector('#td-connections'),
            queue: this.container.querySelector('#td-queue'),
            messageTick: this.container.querySelector('#td-msg-tick'),
            messageList: this.container.querySelector('#td-message-list'),
        };
    }
    
    // ============================================================================
    // EVENT LISTENERS
    // ============================================================================
    
    attachEventListeners() {
        // Play/Pause
        this.elements.playBtn.addEventListener('click', () => this.togglePlay());
        
        // Step controls
        this.elements.stepBack.addEventListener('click', () => this.step(-1));
        this.elements.stepForward.addEventListener('click', () => this.step(1));
        
        // Breakpoint
        this.elements.setBreakpoint.addEventListener('click', () => this.toggleBreakpointAtCurrent());
        
        // Save scenario
        this.elements.saveScenario.addEventListener('click', () => this.saveScenario());
        
        // Playhead drag
        this.elements.playhead.addEventListener('mousedown', (e) => this.startDrag(e));
        document.addEventListener('mousemove', (e) => this.onDrag(e));
        document.addEventListener('mouseup', () => this.endDrag());
        
        // Track click
        this.elements.track.addEventListener('click', (e) => {
            if (e.target === this.elements.track || e.target.closest('.td-tick-marks')) {
                this.seekToClick(e);
            }
        });
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (!this.container.contains(document.activeElement)) return;
            
            switch(e.code) {
                case 'Space':
                    e.preventDefault();
                    this.togglePlay();
                    break;
                case 'ArrowLeft':
                    e.preventDefault();
                    this.step(-1);
                    break;
                case 'ArrowRight':
                    e.preventDefault();
                    this.step(1);
                    break;
            }
        });
    }
    
    // ============================================================================
    // RENDERING
    // ============================================================================
    
    render() {
        this.renderTicks();
        this.renderEvents();
        this.renderBranchPoints();
        this.renderBreakpoints();
        this.updatePlayhead();
    }
    
    renderTicks() {
        const trackWidth = this.elements.track.offsetWidth;
        const tickSpacing = trackWidth / (this.data.totalTicks / this.options.tickInterval);
        let html = '';
        
        for (let tick = 0; tick <= this.data.totalTicks; tick += this.options.tickInterval) {
            const left = (tick / this.data.totalTicks) * 100;
            const isMajor = tick % this.options.majorTickInterval === 0;
            
            html += `<div class="td-tick ${isMajor ? 'major' : ''}" style="left: ${left}%"></div>`;
            
            if (isMajor) {
                html += `<div class="td-tick-label" style="left: ${left}%">${tick}</div>`;
            }
        }
        
        this.elements.tickContainer.innerHTML = html;
    }
    
    renderEvents() {
        let html = '';
        
        this.data.events.forEach(event => {
            const left = (event.tick / this.data.totalTicks) * 100;
            html += `
                <div class="td-event-marker ${event.type}" 
                     style="left: ${left}%"
                     data-tick="${event.tick}"
                     data-type="${event.type}"
                     title="${event.type} at tick ${event.tick}">
                </div>
            `;
        });
        
        this.elements.eventContainer.innerHTML = html;
    }
    
    renderBranchPoints() {
        let html = '';
        
        this.data.branchPoints.forEach((branch, index) => {
            const left = (branch.tick / this.data.totalTicks) * 100;
            html += `
                <div class="td-branch-point" 
                     style="left: ${left}%"
                     data-tick="${branch.tick}"
                     data-index="${index}"
                     title="${branch.description}">
                </div>
            `;
        });
        
        this.elements.branchContainer.innerHTML = html;
    }
    
    renderBreakpoints() {
        let html = '';
        
        this.data.breakpoints.forEach(tick => {
            const left = (tick / this.data.totalTicks) * 100;
            html += `
                <div class="td-breakpoint" 
                     style="left: ${left}%"
                     data-tick="${tick}"
                     title="Breakpoint at tick ${tick}">
                </div>
            `;
        });
        
        this.elements.breakpointContainer.innerHTML = html;
    }
    
    updatePlayhead() {
        const left = (this.data.currentTick / this.data.totalTicks) * 100;
        this.elements.playhead.style.left = `${left}%`;
        this.elements.tickDisplay.textContent = this.data.currentTick;
        this.elements.messageTick.textContent = this.data.currentTick;
    }
    
    // ============================================================================
    // STATE PANEL
    // ============================================================================
    
    updateStatePanel() {
        // Get nearest snapshot
        const snapshot = this.getNearestSnapshot(this.data.currentTick);
        
        // Update agent list
        if (snapshot && snapshot.agents.length > 0) {
            this.elements.agentList.innerHTML = snapshot.agents.map(agent => 
                `<span class="td-agent-badge active">${agent}</span>`
            ).join('');
        } else {
            this.elements.agentList.innerHTML = '<span class="td-agent-badge">No active agents</span>';
        }
        
        // Update metrics
        this.elements.connections.textContent = snapshot ? snapshot.activeConnections : 0;
        this.elements.queue.textContent = snapshot ? snapshot.queueDepth : 0;
        
        // Update message flow
        const messages = this.getMessagesAtTick(this.data.currentTick);
        if (messages.length > 0) {
            this.elements.messageList.innerHTML = messages.map(msg => `
                <div class="td-message-item">
                    <span class="td-message-from">${msg.from}</span>
                    <span class="td-message-direction">→</span>
                    <span class="td-message-to">${msg.to}</span>
                    <code class="td-message-content">${msg.data.content}</code>
                    <span style="color: #605040; margin-left: auto;">${msg.data.size}b</span>
                </div>
            `).join('');
        } else {
            this.elements.messageList.innerHTML = `
                <div style="color: #605040; font-size: 11px; font-style: italic; padding: 20px 0;">
                    No messages at this tick
                </div>
            `;
        }
    }
    
    getNearestSnapshot(tick) {
        const snapshotTicks = Object.keys(this.data.snapshots).map(Number).sort((a, b) => a - b);
        let nearest = null;
        
        for (const snapshotTick of snapshotTicks) {
            if (snapshotTick <= tick) {
                nearest = this.data.snapshots[snapshotTick];
            } else {
                break;
            }
        }
        
        return nearest;
    }
    
    getMessagesAtTick(tick) {
        return this.data.events.filter(e => 
            e.type === 'message' && e.tick === tick
        );
    }
    
    // ============================================================================
    // CONTROLS
    // ============================================================================
    
    togglePlay() {
        this.isPlaying = !this.isPlaying;
        
        if (this.isPlaying) {
            this.elements.playText.textContent = 'Pause';
            this.elements.playBtn.querySelector('.td-btn-icon').textContent = '⏸';
            this.startPlayback();
        } else {
            this.elements.playText.textContent = 'Play';
            this.elements.playBtn.querySelector('.td-btn-icon').textContent = '▶';
            this.stopPlayback();
        }
    }
    
    startPlayback() {
        this.playInterval = setInterval(() => {
            if (this.data.currentTick >= this.data.totalTicks) {
                this.togglePlay();
                return;
            }
            
            // Check for breakpoint
            if (this.data.breakpoints.has(this.data.currentTick)) {
                this.togglePlay();
                this.showNotification(`Paused at breakpoint (tick ${this.data.currentTick})`);
                return;
            }
            
            this.step(1);
        }, this.options.autoPlayInterval);
    }
    
    stopPlayback() {
        if (this.playInterval) {
            clearInterval(this.playInterval);
            this.playInterval = null;
        }
    }
    
    step(direction) {
        const newTick = this.data.currentTick + direction;
        if (newTick >= 0 && newTick <= this.data.totalTicks) {
            this.seekTo(newTick);
        }
    }
    
    seekTo(tick) {
        this.data.currentTick = Math.max(0, Math.min(this.data.totalTicks, tick));
        this.updatePlayhead();
        this.updateStatePanel();
        
        // Highlight events at this tick
        this.highlightEventsAtTick(this.data.currentTick);
    }
    
    seekToClick(e) {
        const rect = this.elements.track.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const percentage = x / rect.width;
        const tick = Math.round(percentage * this.data.totalTicks);
        this.seekTo(tick);
    }
    
    highlightEventsAtTick(tick) {
        // Remove previous highlights
        this.elements.eventContainer.querySelectorAll('.td-event-marker').forEach(el => {
            el.style.opacity = el.dataset.tick == tick ? '1' : '0.5';
            if (el.dataset.tick == tick) {
                el.style.transform = 'translateX(-50%) scaleY(1.3)';
            } else {
                el.style.transform = 'translateX(-50%) scaleY(1)';
            }
        });
    }
    
    // ============================================================================
    // DRAGGING
    // ============================================================================
    
    startDrag(e) {
        this.isDragging = true;
        this.dragStartX = e.clientX;
        this.dragStartTick = this.data.currentTick;
        this.stopPlayback();
        if (this.isPlaying) {
            this.togglePlay();
        }
    }
    
    onDrag(e) {
        if (!this.isDragging) return;
        
        const rect = this.elements.track.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const percentage = x / rect.width;
        const tick = Math.round(percentage * this.data.totalTicks);
        
        this.seekTo(tick);
    }
    
    endDrag() {
        this.isDragging = false;
    }
    
    // ============================================================================
    // BREAKPOINTS & SCENARIOS
    // ============================================================================
    
    toggleBreakpointAtCurrent() {
        const tick = this.data.currentTick;
        
        if (this.data.breakpoints.has(tick)) {
            this.data.breakpoints.delete(tick);
            this.showNotification(`Breakpoint removed at tick ${tick}`);
        } else {
            this.data.breakpoints.add(tick);
            this.showNotification(`Breakpoint set at tick ${tick}`);
        }
        
        this.renderBreakpoints();
    }
    
    saveScenario() {
        const scenario = {
            tick: this.data.currentTick,
            timestamp: Date.now(),
            snapshot: this.getNearestSnapshot(this.data.currentTick),
            activeAgents: this.getNearestSnapshot(this.data.currentTick)?.agents || [],
        };
        
        this.data.savedScenarios.push(scenario);
        this.showNotification(`Scenario saved at tick ${this.data.currentTick}`);
        
        // In a real implementation, this would serialize to disk
        console.log('Saved scenario:', scenario);
    }
    
    showNotification(message) {
        // Simple notification - could be enhanced
        console.log(`[Temporal Debugger] ${message}`);
    }
    
    // ============================================================================
    // UTILITY
    // ============================================================================
    
    destroy() {
        this.stopPlayback();
        const style = document.getElementById('temporal-debugger-styles');
        if (style) style.remove();
        this.container.innerHTML = '';
    }
    
    // Get current state for external consumers
    getState() {
        return {
            currentTick: this.data.currentTick,
            isPlaying: this.isPlaying,
            breakpoints: Array.from(this.data.breakpoints),
            savedScenarios: this.data.savedScenarios,
            currentSnapshot: this.getNearestSnapshot(this.data.currentTick),
        };
    }
}

// ============================================================================
// EXPORT
// ============================================================================

// ES Module export
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { TemporalDebugger, MOCK_TIMELINE_DATA };
}

// Browser global
if (typeof window !== 'undefined') {
    window.TemporalDebugger = TemporalDebugger;
    window.MOCK_TIMELINE_DATA = MOCK_TIMELINE_DATA;
}

// ============================================================================
// AUTO-INITIALIZE (for standalone testing)
// ============================================================================

if (typeof document !== 'undefined') {
    document.addEventListener('DOMContentLoaded', () => {
        // Check if there's a container with id 'temporal-debugger'
        const container = document.getElementById('temporal-debugger');
        if (container) {
            window.debugger = new TemporalDebugger('temporal-debugger');
            console.log('Temporal Debugger initialized. Access via window.debugger');
        }
    });
}
