/**
 * ORDL IDE - Mentality Panel (Fleet Controls)
 * 
 * A cockpit-style interface with physical control aesthetics
 * for managing fleet policies and agent behavior.
 * 
 * Design language: Analog synth + aircraft cockpit + industrial panels
 */

const MentalityPanel = {
    // State object for all fleet controls
    state: {
        consensusThreshold: 66,
        timeoutDuration: 30000,
        retryPolicy: {
            enabled: true,
            maxRetries: 3,
            exponentialBackoff: true
        },
        circuitBreaker: {
            enabled: true,
            failureThreshold: 5,
            recoveryTimeout: 60000
        },
        loggingLevel: 'info' // debug, info, warn, error
    },

    // Initialize the panel
    init(containerId) {
        const container = document.getElementById(containerId);
        if (!container) {
            console.error(`Container #${containerId} not found`);
            return;
        }
        container.innerHTML = this.render();
        this.attachEventListeners(container);
        this.updateAllDisplays();
    },

    // Generate the HTML structure
    render() {
        return `
<style>
/* ============================================
   MENTALITY PANEL - Fleet Controls
   Aircraft Cockpit + Analog Synth Aesthetic
   ============================================ */

.mentality-panel {
    --cream: #F5F0E6;
    --cream-dim: #C9C4B8;
    --charcoal: #1A1A1A;
    --charcoal-light: #252525;
    --charcoal-dark: #0F0F0F;
    --accent: #E8A838;
    --accent-glow: rgba(232, 168, 56, 0.4);
    --success: #5A9B5A;
    --danger: #B85450;
    --warning: #D4A03C;
    
    background: linear-gradient(135deg, var(--charcoal) 0%, var(--charcoal-dark) 100%);
    border-radius: 8px;
    padding: 24px;
    color: var(--cream);
    font-family: 'SF Mono', 'Monaco', 'Inconsolata', monospace;
    box-shadow: 
        inset 0 1px 0 rgba(255,255,255,0.05),
        0 20px 40px rgba(0,0,0,0.6),
        0 0 0 1px rgba(255,255,255,0.03);
    position: relative;
    overflow: hidden;
}

.mentality-panel::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 2px;
    background: linear-gradient(90deg, transparent, var(--accent), transparent);
    opacity: 0.6;
}

/* Panel Header */
.mentality-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 24px;
    padding-bottom: 16px;
    border-bottom: 1px solid rgba(245, 240, 230, 0.1);
}

.mentality-title {
    font-size: 14px;
    font-weight: 600;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: var(--accent);
    display: flex;
    align-items: center;
    gap: 8px;
}

.mentality-title::before {
    content: '◆';
    font-size: 10px;
}

.mentality-status {
    font-size: 10px;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--cream-dim);
    display: flex;
    align-items: center;
    gap: 6px;
}

.status-indicator {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--success);
    box-shadow: 0 0 8px var(--success);
    animation: pulse-status 2s ease-in-out infinite;
}

@keyframes pulse-status {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}

/* Controls Grid */
.mentality-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 24px;
    margin-bottom: 24px;
}

/* Control Section */
.control-section {
    background: linear-gradient(145deg, var(--charcoal-light) 0%, var(--charcoal) 100%);
    border-radius: 6px;
    padding: 16px;
    box-shadow: 
        inset 0 1px 0 rgba(255,255,255,0.03),
        0 4px 8px rgba(0,0,0,0.3),
        inset 0 -2px 4px rgba(0,0,0,0.3);
    position: relative;
}

.control-section::after {
    content: '';
    position: absolute;
    top: 2px;
    left: 2px;
    right: 2px;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.08), transparent);
}

.control-label {
    font-size: 9px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--cream-dim);
    margin-bottom: 12px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.control-value {
    color: var(--accent);
    font-weight: 600;
}

/* ============================================
   SLIDER CONTROL (Linear fader style)
   ============================================ */

.slider-container {
    position: relative;
    padding: 8px 0;
}

.slider-track {
    height: 8px;
    background: linear-gradient(180deg, var(--charcoal-dark) 0%, var(--charcoal-light) 100%);
    border-radius: 4px;
    box-shadow: 
        inset 0 2px 4px rgba(0,0,0,0.5),
        0 1px 0 rgba(255,255,255,0.05);
    position: relative;
    cursor: pointer;
}

.slider-fill {
    height: 100%;
    background: linear-gradient(180deg, var(--accent) 0%, #C48A2A 100%);
    border-radius: 4px;
    box-shadow: 
        inset 0 1px 0 rgba(255,255,255,0.3),
        0 0 12px var(--accent-glow);
    transition: width 0.1s ease;
}

.slider-thumb {
    position: absolute;
    top: 50%;
    width: 20px;
    height: 32px;
    background: linear-gradient(180deg, 
        #3A3A3A 0%, 
        var(--charcoal-light) 20%,
        var(--charcoal-light) 80%,
        #151515 100%
    );
    border-radius: 3px;
    transform: translate(-50%, -50%);
    box-shadow: 
        0 2px 6px rgba(0,0,0,0.5),
        inset 0 1px 0 rgba(255,255,255,0.1),
        inset 0 -1px 0 rgba(0,0,0,0.3);
    cursor: grab;
    z-index: 2;
}

.slider-thumb::before {
    content: '';
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 2px;
    height: 16px;
    background: var(--accent);
    border-radius: 1px;
}

.slider-thumb:active {
    cursor: grabbing;
}

.slider-ticks {
    display: flex;
    justify-content: space-between;
    margin-top: 8px;
    padding: 0 10px;
}

.slider-tick {
    width: 1px;
    height: 6px;
    background: var(--cream-dim);
    opacity: 0.4;
}

.slider-tick.major {
    height: 10px;
    opacity: 0.7;
}

.slider-labels {
    display: flex;
    justify-content: space-between;
    margin-top: 4px;
    font-size: 8px;
    color: var(--cream-dim);
    opacity: 0.6;
}

/* ============================================
   DIAL CONTROL (Rotary knob)
   ============================================ */

.dial-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
}

.dial {
    width: 80px;
    height: 80px;
    position: relative;
}

.dial-bg {
    position: absolute;
    inset: 0;
    border-radius: 50%;
    background: conic-gradient(
        from 225deg,
        var(--charcoal-dark) 0deg,
        var(--charcoal-light) 90deg,
        var(--charcoal-dark) 180deg
    );
    box-shadow: 
        0 4px 12px rgba(0,0,0,0.4),
        inset 0 2px 4px rgba(255,255,255,0.05),
        inset 0 -4px 8px rgba(0,0,0,0.4);
}

.dial-indicator {
    position: absolute;
    inset: 4px;
    border-radius: 50%;
    background: linear-gradient(145deg, var(--charcoal) 0%, var(--charcoal-dark) 100%);
}

.dial-value-ring {
    position: absolute;
    inset: 8px;
    border-radius: 50%;
}

.dial-value-ring svg {
    transform: rotate(-225deg);
}

.dial-value-ring circle {
    fill: none;
    stroke-width: 3;
}

.dial-value-ring .track {
    stroke: var(--charcoal-dark);
}

.dial-value-ring .fill {
    stroke: var(--accent);
    stroke-linecap: round;
    filter: drop-shadow(0 0 4px var(--accent-glow));
    transition: stroke-dasharray 0.1s ease;
}

.dial-knob {
    position: absolute;
    inset: 16px;
    border-radius: 50%;
    background: linear-gradient(145deg, 
        #3A3A3A 0%, 
        var(--charcoal-light) 40%,
        var(--charcoal-light) 60%,
        #151515 100%
    );
    box-shadow: 
        0 2px 8px rgba(0,0,0,0.5),
        inset 0 1px 0 rgba(255,255,255,0.1);
    cursor: grab;
}

.dial-knob::before {
    content: '';
    position: absolute;
    top: 6px;
    left: 50%;
    transform: translateX(-50%);
    width: 4px;
    height: 12px;
    background: var(--accent);
    border-radius: 2px;
    box-shadow: 0 0 6px var(--accent-glow);
}

.dial-knob:active {
    cursor: grabbing;
}

.dial-value {
    font-size: 11px;
    font-weight: 600;
    color: var(--accent);
    letter-spacing: 0.05em;
}

.dial-ticks {
    position: absolute;
    inset: 0;
    pointer-events: none;
}

.dial-tick {
    position: absolute;
    width: 2px;
    height: 8px;
    background: var(--cream-dim);
    left: 50%;
    top: 2px;
    transform-origin: center 38px;
    opacity: 0.4;
}

.dial-tick.major {
    height: 12px;
    width: 3px;
    background: var(--cream);
    opacity: 0.6;
}

/* ============================================
   TOGGLE SWITCH (Aircraft style)
   ============================================ */

.toggle-container {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 0;
}

.toggle-label {
    font-size: 10px;
    letter-spacing: 0.08em;
    color: var(--cream-dim);
}

.toggle-switch {
    position: relative;
    width: 52px;
    height: 28px;
    background: linear-gradient(180deg, var(--charcoal-dark) 0%, var(--charcoal) 100%);
    border-radius: 14px;
    box-shadow: 
        inset 0 2px 6px rgba(0,0,0,0.5),
        0 1px 0 rgba(255,255,255,0.05);
    cursor: pointer;
    transition: all 0.2s ease;
}

.toggle-switch::before {
    content: '';
    position: absolute;
    top: 3px;
    left: 3px;
    width: 22px;
    height: 22px;
    background: linear-gradient(180deg, 
        #4A4A4A 0%, 
        var(--charcoal-light) 30%,
        var(--charcoal-light) 70%,
        #1A1A1A 100%
    );
    border-radius: 50%;
    box-shadow: 
        0 2px 6px rgba(0,0,0,0.4),
        inset 0 1px 0 rgba(255,255,255,0.2);
    transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.toggle-switch.active {
    background: linear-gradient(180deg, var(--success) 0%, #3A6B3A 100%);
    box-shadow: 
        inset 0 2px 6px rgba(0,0,0,0.3),
        0 0 12px rgba(90, 155, 90, 0.3);
}

.toggle-switch.active::before {
    transform: translateX(24px);
    background: linear-gradient(180deg, 
        #6A6A6A 0%, 
        #4A4A4A 30%,
        #4A4A4A 70%,
        #2A2A2A 100%
    );
}

.toggle-switch.danger.active {
    background: linear-gradient(180deg, var(--danger) 0%, #7A302C 100%);
    box-shadow: 
        inset 0 2px 6px rgba(0,0,0,0.3),
        0 0 12px rgba(184, 84, 80, 0.3);
}

.toggle-indicator {
    position: absolute;
    top: 50%;
    transform: translateY(-50%);
    font-size: 7px;
    font-weight: 700;
    letter-spacing: 0.1em;
    transition: opacity 0.2s ease;
}

.toggle-indicator.on {
    left: 8px;
    color: rgba(255,255,255,0.8);
    opacity: 0;
}

.toggle-indicator.off {
    right: 6px;
    color: var(--cream-dim);
    opacity: 0.5;
}

.toggle-switch.active .toggle-indicator.on {
    opacity: 1;
}

.toggle-switch.active .toggle-indicator.off {
    opacity: 0;
}

/* ============================================
   LOGGING LEVEL SELECTOR (Circular dial)
   ============================================ */

.logging-selector {
    position: relative;
    width: 120px;
    height: 120px;
    margin: 0 auto;
}

.logging-dial {
    position: absolute;
    inset: 0;
    border-radius: 50%;
    background: linear-gradient(145deg, var(--charcoal) 0%, var(--charcoal-dark) 100%);
    box-shadow: 
        0 4px 16px rgba(0,0,0,0.4),
        inset 0 2px 4px rgba(255,255,255,0.05);
}

.logging-option {
    position: absolute;
    width: 28px;
    height: 28px;
    border-radius: 50%;
    background: linear-gradient(145deg, var(--charcoal-light) 0%, var(--charcoal) 100%);
    border: 1px solid rgba(245, 240, 230, 0.1);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 8px;
    font-weight: 600;
    letter-spacing: 0.05em;
    color: var(--cream-dim);
    cursor: pointer;
    transition: all 0.2s ease;
    box-shadow: 
        0 2px 6px rgba(0,0,0,0.3),
        inset 0 1px 0 rgba(255,255,255,0.05);
}

.logging-option:hover {
    background: linear-gradient(145deg, #3A3A3A 0%, var(--charcoal-light) 100%);
    color: var(--cream);
}

.logging-option.active {
    background: linear-gradient(145deg, var(--accent) 0%, #C48A2A 100%);
    color: var(--charcoal-dark);
    box-shadow: 
        0 0 16px var(--accent-glow),
        inset 0 1px 0 rgba(255,255,255,0.3);
    border-color: var(--accent);
}

.logging-option[data-level="debug"] { top: 10px; left: 50%; transform: translateX(-50%); }
.logging-option[data-level="info"] { top: 50%; right: 10px; transform: translateY(-50%); }
.logging-option[data-level="warn"] { bottom: 10px; left: 50%; transform: translateX(-50%); }
.logging-option[data-level="error"] { top: 50%; left: 10px; transform: translateY(-50%); }

.logging-center {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 48px;
    height: 48px;
    border-radius: 50%;
    background: linear-gradient(145deg, 
        #3A3A3A 0%, 
        var(--charcoal-light) 40%,
        var(--charcoal-light) 60%,
        #151515 100%
    );
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.1em;
    color: var(--accent);
    box-shadow: 
        0 2px 8px rgba(0,0,0,0.5),
        inset 0 1px 0 rgba(255,255,255,0.1);
}

/* ============================================
   APPLY BUTTON (Large, prominent)
   ============================================ */

.apply-section {
    display: flex;
    justify-content: center;
    padding-top: 16px;
    border-top: 1px solid rgba(245, 240, 230, 0.1);
}

.apply-button {
    position: relative;
    padding: 16px 48px;
    background: linear-gradient(180deg, 
        var(--charcoal-light) 0%,
        var(--charcoal) 50%,
        var(--charcoal-dark) 100%
    );
    border: 1px solid rgba(232, 168, 56, 0.3);
    border-radius: 4px;
    color: var(--accent);
    font-family: inherit;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    cursor: pointer;
    box-shadow: 
        0 4px 12px rgba(0,0,0,0.4),
        inset 0 1px 0 rgba(255,255,255,0.08),
        0 0 0 1px rgba(0,0,0,0.3);
    transition: all 0.15s ease;
}

.apply-button::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--accent), transparent);
    opacity: 0.5;
}

.apply-button:hover {
    background: linear-gradient(180deg, 
        #3A3A3A 0%,
        var(--charcoal-light) 50%,
        var(--charcoal) 100%
    );
    border-color: var(--accent);
    box-shadow: 
        0 6px 20px rgba(0,0,0,0.5),
        inset 0 1px 0 rgba(255,255,255,0.1),
        0 0 20px var(--accent-glow);
    transform: translateY(-1px);
}

.apply-button:active {
    transform: translateY(1px);
    box-shadow: 
        0 2px 6px rgba(0,0,0,0.4),
        inset 0 2px 4px rgba(0,0,0,0.3);
}

.apply-button.committing {
    pointer-events: none;
    opacity: 0.8;
}

.apply-button.committing::after {
    content: '...';
    animation: dots 1.5s steps(4, end) infinite;
}

@keyframes dots {
    0%, 20% { content: ''; }
    40% { content: '.'; }
    60% { content: '..'; }
    80%, 100% { content: '...'; }
}

.apply-status {
    position: absolute;
    bottom: -24px;
    left: 50%;
    transform: translateX(-50%);
    font-size: 9px;
    letter-spacing: 0.1em;
    color: var(--success);
    white-space: nowrap;
    opacity: 0;
    transition: opacity 0.3s ease;
}

.apply-status.visible {
    opacity: 1;
}

/* ============================================
   SECTION GROUPS
   ============================================ */

.control-row {
    display: flex;
    gap: 12px;
}

.control-row .control-section {
    flex: 1;
}

.sub-control {
    margin-top: 12px;
    padding-top: 12px;
    border-top: 1px solid rgba(245, 240, 230, 0.05);
}

.sub-label {
    font-size: 8px;
    color: var(--cream-dim);
    margin-bottom: 8px;
    letter-spacing: 0.05em;
}

/* Mini dial for sub-controls */
.mini-dial-container {
    display: flex;
    align-items: center;
    gap: 12px;
}

.mini-dial {
    width: 48px;
    height: 48px;
    position: relative;
    flex-shrink: 0;
}

.mini-dial .dial-bg {
    background: conic-gradient(
        from 225deg,
        var(--charcoal-dark) 0deg,
        var(--charcoal-light) 90deg,
        var(--charcoal-dark) 180deg
    );
}

.mini-dial .dial-indicator {
    inset: 2px;
}

.mini-dial .dial-value-ring {
    inset: 4px;
}

.mini-dial .dial-knob {
    inset: 8px;
}

.mini-dial .dial-knob::before {
    width: 3px;
    height: 8px;
    top: 3px;
}

.mini-value {
    font-size: 10px;
    color: var(--accent);
    font-weight: 600;
}

/* Screws for industrial look */
.screw {
    position: absolute;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: radial-gradient(circle at 30% 30%, #4A4A4A, #1A1A1A);
    box-shadow: inset 0 1px 2px rgba(0,0,0,0.5);
}

.screw::before {
    content: '';
    position: absolute;
    top: 50%;
    left: 50%;
    width: 60%;
    height: 2px;
    background: #151515;
    transform: translate(-50%, -50%) rotate(45deg);
}

.screw::after {
    content: '';
    position: absolute;
    top: 50%;
    left: 50%;
    width: 60%;
    height: 2px;
    background: #151515;
    transform: translate(-50%, -50%) rotate(-45deg);
}

.screw.tl { top: 6px; left: 6px; }
.screw.tr { top: 6px; right: 6px; }
.screw.bl { bottom: 6px; left: 6px; }
.screw.br { bottom: 6px; right: 6px; }
</style>

<div class="mentality-panel">
    <!-- Header -->
    <div class="mentality-header">
        <div class="mentality-title">Mentality Control</div>
        <div class="mentality-status">
            <span class="status-indicator"></span>
            Fleet Online
        </div>
    </div>

    <!-- Main Controls Grid -->
    <div class="mentality-grid">
        <!-- Consensus Threshold -->
        <div class="control-section">
            <div class="screw tl"></div>
            <div class="screw tr"></div>
            <div class="screw bl"></div>
            <div class="screw br"></div>
            <div class="control-label">
                Consensus Threshold
                <span class="control-value" id="consensus-value">66%</span>
            </div>
            <div class="slider-container" id="consensus-slider">
                <div class="slider-track">
                    <div class="slider-fill" id="consensus-fill" style="width: 66%"></div>
                    <div class="slider-thumb" id="consensus-thumb" style="left: 66%"></div>
                </div>
                <div class="slider-ticks">
                    <div class="slider-tick"></div>
                    <div class="slider-tick"></div>
                    <div class="slider-tick major"></div>
                    <div class="slider-tick"></div>
                    <div class="slider-tick"></div>
                    <div class="slider-tick major"></div>
                    <div class="slider-tick"></div>
                    <div class="slider-tick"></div>
                    <div class="slider-tick major"></div>
                </div>
                <div class="slider-labels">
                    <span>0</span>
                    <span>50</span>
                    <span>100</span>
                </div>
            </div>
        </div>

        <!-- Timeout Duration -->
        <div class="control-section">
            <div class="screw tl"></div>
            <div class="screw tr"></div>
            <div class="screw bl"></div>
            <div class="screw br"></div>
            <div class="control-label">
                Timeout Duration
                <span class="control-value" id="timeout-value">30s</span>
            </div>
            <div class="dial-container">
                <div class="dial" id="timeout-dial">
                    <div class="dial-bg"></div>
                    <div class="dial-indicator">
                        <svg class="dial-value-ring" viewBox="0 0 64 64">
                            <circle class="track" cx="32" cy="32" r="28" stroke-dasharray="88 264" />
                            <circle class="fill" id="timeout-ring" cx="32" cy="32" r="28" 
                                stroke-dasharray="66 264" stroke-dashoffset="0" />
                        </svg>
                    </div>
                    <div class="dial-knob" id="timeout-knob" style="transform: rotate(0deg)"></div>
                    <div class="dial-ticks" id="timeout-ticks"></div>
                </div>
                <div class="dial-value" id="timeout-display">30000ms</div>
            </div>
        </div>

        <!-- Logging Level -->
        <div class="control-section">
            <div class="screw tl"></div>
            <div class="screw tr"></div>
            <div class="screw bl"></div>
            <div class="screw br"></div>
            <div class="control-label">
                Logging Level
                <span class="control-value" id="logging-value">INFO</span>
            </div>
            <div class="logging-selector">
                <div class="logging-dial"></div>
                <div class="logging-option" data-level="debug">DBG</div>
                <div class="logging-option active" data-level="info">INF</div>
                <div class="logging-option" data-level="warn">WRN</div>
                <div class="logging-option" data-level="error">ERR</div>
                <div class="logging-center">LOG</div>
            </div>
        </div>
    </div>

    <!-- Toggle Controls Row -->
    <div class="control-row">
        <!-- Retry Policy -->
        <div class="control-section">
            <div class="screw tl"></div>
            <div class="screw tr"></div>
            <div class="control-label">Retry Policy</div>
            <div class="toggle-container">
                <span class="toggle-label">Enable Retries</span>
                <div class="toggle-switch active" id="retry-toggle" data-state="true">
                    <span class="toggle-indicator on">ON</span>
                    <span class="toggle-indicator off">OFF</span>
                </div>
            </div>
            <div class="sub-control" id="retry-controls">
                <div class="sub-label">Max Retries</div>
                <div class="mini-dial-container">
                    <div class="mini-dial" id="maxretries-dial">
                        <div class="dial-bg"></div>
                        <div class="dial-indicator">
                            <svg class="dial-value-ring" viewBox="0 0 40 40">
                                <circle class="fill" id="maxretries-ring" cx="20" cy="20" r="16" 
                                    stroke-dasharray="38 100" stroke-dashoffset="0" />
                            </svg>
                        </div>
                        <div class="dial-knob" id="maxretries-knob" style="transform: rotate(0deg)"></div>
                    </div>
                    <span class="mini-value" id="maxretries-value">3</span>
                </div>
            </div>
        </div>

        <!-- Circuit Breaker -->
        <div class="control-section">
            <div class="screw tl"></div>
            <div class="screw tr"></div>
            <div class="control-label">Circuit Breaker</div>
            <div class="toggle-container">
                <span class="toggle-label">Enable CB</span>
                <div class="toggle-switch danger active" id="cb-toggle" data-state="true">
                    <span class="toggle-indicator on">ON</span>
                    <span class="toggle-indicator off">OFF</span>
                </div>
            </div>
            <div class="sub-control" id="cb-controls">
                <div class="sub-label">Failure Threshold</div>
                <div class="mini-dial-container">
                    <div class="mini-dial" id="cb-threshold-dial">
                        <div class="dial-bg"></div>
                        <div class="dial-indicator">
                            <svg class="dial-value-ring" viewBox="0 0 40 40">
                                <circle class="fill" id="cb-threshold-ring" cx="20" cy="20" r="16" 
                                    stroke-dasharray="32 100" stroke-dashoffset="0" />
                            </svg>
                        </div>
                        <div class="dial-knob" id="cb-threshold-knob" style="transform: rotate(0deg)"></div>
                    </div>
                    <span class="mini-value" id="cb-threshold-value">5</span>
                </div>
            </div>
        </div>

        <!-- Backoff Strategy -->
        <div class="control-section">
            <div class="screw tl"></div>
            <div class="screw tr"></div>
            <div class="control-label">Backoff Strategy</div>
            <div class="toggle-container">
                <span class="toggle-label">Exponential</span>
                <div class="toggle-switch active" id="backoff-toggle" data-state="true">
                    <span class="toggle-indicator on">ON</span>
                    <span class="toggle-indicator off">OFF</span>
                </div>
            </div>
            <div class="sub-control">
                <div class="sub-label">Recovery Timeout</div>
                <div class="mini-dial-container">
                    <div class="mini-dial" id="recovery-dial">
                        <div class="dial-bg"></div>
                        <div class="dial-indicator">
                            <svg class="dial-value-ring" viewBox="0 0 40 40">
                                <circle class="fill" id="recovery-ring" cx="20" cy="20" r="16" 
                                    stroke-dasharray="40 100" stroke-dashoffset="0" />
                            </svg>
                        </div>
                        <div class="dial-knob" id="recovery-knob" style="transform: rotate(0deg)"></div>
                    </div>
                    <span class="mini-value" id="recovery-value">60s</span>
                </div>
            </div>
        </div>
    </div>

    <!-- Apply Button -->
    <div class="apply-section">
        <button class="apply-button" id="apply-btn">
            Commit to Fleet
            <span class="apply-status" id="apply-status">✓ Changes Applied</span>
        </button>
    </div>
</div>
        `;
    },

    // Attach event listeners to all controls
    attachEventListeners(container) {
        // Consensus Slider
        this.initSlider(container, 'consensus-slider', 'consensus', 0, 100, this.state.consensusThreshold, (val) => {
            this.state.consensusThreshold = val;
            container.querySelector('#consensus-value').textContent = val + '%';
        });

        // Timeout Dial
        this.initDial(container, 'timeout-dial', 'timeout', 5000, 120000, this.state.timeoutDuration, (val) => {
            this.state.timeoutDuration = val;
            container.querySelector('#timeout-value').textContent = (val / 1000).toFixed(0) + 's';
            container.querySelector('#timeout-display').textContent = val + 'ms';
        });

        // Logging Level Selector
        container.querySelectorAll('.logging-option').forEach(opt => {
            opt.addEventListener('click', () => {
                container.querySelectorAll('.logging-option').forEach(o => o.classList.remove('active'));
                opt.classList.add('active');
                this.state.loggingLevel = opt.dataset.level;
                container.querySelector('#logging-value').textContent = opt.dataset.level.toUpperCase();
            });
        });

        // Retry Toggle
        this.initToggle(container, 'retry-toggle', (state) => {
            this.state.retryPolicy.enabled = state;
            const controls = container.querySelector('#retry-controls');
            controls.style.opacity = state ? '1' : '0.4';
            controls.style.pointerEvents = state ? 'auto' : 'none';
        });

        // Circuit Breaker Toggle
        this.initToggle(container, 'cb-toggle', (state) => {
            this.state.circuitBreaker.enabled = state;
            const controls = container.querySelector('#cb-controls');
            controls.style.opacity = state ? '1' : '0.4';
            controls.style.pointerEvents = state ? 'auto' : 'none';
        });

        // Backoff Toggle
        this.initToggle(container, 'backoff-toggle', (state) => {
            this.state.retryPolicy.exponentialBackoff = state;
        });

        // Max Retries Mini Dial
        this.initDial(container, 'maxretries-dial', 'maxretries', 0, 10, this.state.retryPolicy.maxRetries, (val) => {
            this.state.retryPolicy.maxRetries = val;
            container.querySelector('#maxretries-value').textContent = val;
        }, true);

        // CB Threshold Mini Dial
        this.initDial(container, 'cb-threshold-dial', 'cb-threshold', 1, 20, this.state.circuitBreaker.failureThreshold, (val) => {
            this.state.circuitBreaker.failureThreshold = val;
            container.querySelector('#cb-threshold-value').textContent = val;
        }, true);

        // Recovery Timeout Mini Dial
        this.initDial(container, 'recovery-dial', 'recovery', 10000, 300000, this.state.circuitBreaker.recoveryTimeout, (val) => {
            this.state.circuitBreaker.recoveryTimeout = val;
            container.querySelector('#recovery-value').textContent = (val / 1000).toFixed(0) + 's';
        }, true);

        // Apply Button
        const applyBtn = container.querySelector('#apply-btn');
        const applyStatus = container.querySelector('#apply-status');
        
        applyBtn.addEventListener('click', async () => {
            applyBtn.classList.add('committing');
            applyBtn.textContent = 'Committing';
            
            // Simulate API call
            await this.commitToFleet();
            
            applyBtn.classList.remove('committing');
            applyBtn.innerHTML = 'Commit to Fleet<span class="apply-status" id="apply-status">✓ Changes Applied</span>';
            applyStatus.classList.add('visible');
            
            setTimeout(() => {
                applyStatus.classList.remove('visible');
            }, 3000);
        });

        // Generate dial ticks
        this.generateDialTicks(container);
    },

    // Generate tick marks for dials
    generateDialTicks(container) {
        const dial = container.querySelector('#timeout-dial .dial-ticks');
        if (!dial) return;
        
        for (let i = 0; i <= 8; i++) {
            const tick = document.createElement('div');
            tick.className = i % 2 === 0 ? 'dial-tick major' : 'dial-tick';
            tick.style.transform = `translateX(-50%) rotate(${i * 30 - 120}deg)`;
            dial.appendChild(tick);
        }
    },

    // Initialize a slider control
    initSlider(container, id, name, min, max, value, callback) {
        const slider = container.querySelector(`#${id}`);
        const fill = container.querySelector(`#${name}-fill`);
        const thumb = container.querySelector(`#${name}-thumb`);
        let isDragging = false;

        const update = (clientX) => {
            const rect = slider.querySelector('.slider-track').getBoundingClientRect();
            const pct = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
            const val = Math.round(min + pct * (max - min));
            
            fill.style.width = (pct * 100) + '%';
            thumb.style.left = (pct * 100) + '%';
            callback(val);
        };

        slider.addEventListener('mousedown', (e) => {
            isDragging = true;
            update(e.clientX);
        });

        document.addEventListener('mousemove', (e) => {
            if (isDragging) update(e.clientX);
        });

        document.addEventListener('mouseup', () => {
            isDragging = false;
        });

        // Touch support
        slider.addEventListener('touchstart', (e) => {
            isDragging = true;
            update(e.touches[0].clientX);
        });

        document.addEventListener('touchmove', (e) => {
            if (isDragging) update(e.touches[0].clientX);
        });

        document.addEventListener('touchend', () => {
            isDragging = false;
        });
    },

    // Initialize a dial control
    initDial(container, id, name, min, max, value, callback, isMini = false) {
        const dial = container.querySelector(`#${id}`);
        const knob = container.querySelector(`#${name}-knob`);
        const ring = container.querySelector(`#${name}-ring`);
        let isDragging = false;

        const circumference = isMini ? 100 : 264;
        const maxDash = isMini ? 100 : 264;

        const update = (clientX, clientY) => {
            const rect = dial.getBoundingClientRect();
            const centerX = rect.left + rect.width / 2;
            const centerY = rect.top + rect.height / 2;
            
            let angle = Math.atan2(clientY - centerY, clientX - centerX) * 180 / Math.PI;
            angle = (angle + 90 + 360) % 360;
            
            // Clamp to valid range (roughly 225deg arc)
            if (angle > 135 && angle < 225) {
                angle = angle < 180 ? 135 : 225;
            } else if (angle >= 225) {
                angle = angle - 360;
            }
            
            const minAngle = -135;
            const maxAngle = 135;
            const normalized = Math.max(0, Math.min(1, (angle - minAngle) / (maxAngle - minAngle)));
            
            const val = Math.round(min + normalized * (max - min));
            
            knob.style.transform = `rotate(${angle}deg)`;
            const dashArray = normalized * maxDash;
            ring.setAttribute('stroke-dasharray', `${dashArray} ${circumference}`);
            
            callback(val);
        };

        knob.addEventListener('mousedown', (e) => {
            isDragging = true;
            e.preventDefault();
        });

        document.addEventListener('mousemove', (e) => {
            if (isDragging) update(e.clientX, e.clientY);
        });

        document.addEventListener('mouseup', () => {
            isDragging = false;
        });

        // Touch support
        knob.addEventListener('touchstart', (e) => {
            isDragging = true;
        });

        document.addEventListener('touchmove', (e) => {
            if (isDragging) update(e.touches[0].clientX, e.touches[0].clientY);
        });

        document.addEventListener('touchend', () => {
            isDragging = false;
        });
    },

    // Initialize a toggle switch
    initToggle(container, id, callback) {
        const toggle = container.querySelector(`#${id}`);
        
        toggle.addEventListener('click', () => {
            const newState = !toggle.classList.contains('active');
            toggle.classList.toggle('active');
            toggle.dataset.state = newState;
            callback(newState);
        });
    },

    // Update all displays to match initial state
    updateAllDisplays() {
        // This would sync UI with state if re-initializing
    },

    // Commit changes to fleet (simulated - replace with actual API)
    async commitToFleet() {
        return new Promise(resolve => {
            // Simulate network delay
            setTimeout(() => {
                console.log('Fleet configuration updated:', this.state);
                // Here you would actually call your fleet management API
                // fetch('/api/fleet/config', { method: 'POST', body: JSON.stringify(this.state) })
                resolve();
            }, 800);
        });
    },

    // Get current state
    getState() {
        return { ...this.state };
    },

    // Set state programmatically
    setState(newState) {
        this.state = { ...this.state, ...newState };
        // Would need to re-render or update UI elements here
    }
};

// Export for different module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MentalityPanel;
} else if (typeof window !== 'undefined') {
    window.MentalityPanel = MentalityPanel;
}

// Auto-initialize if DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    const autoContainer = document.getElementById('mentality-panel');
    if (autoContainer) {
        MentalityPanel.init('mentality-panel');
    }
});
