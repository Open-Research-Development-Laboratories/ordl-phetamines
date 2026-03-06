/**
 * ORDL IDE - Panel Components
 * Agent Detail Panel (Individual View) and Fleet Overview Panel (Collective View)
 * 
 * Cream-on-charcoal monitoring station aesthetic
 * Live updating data simulation
 */

// ============================================================
// COLOR PALETTE - Cream on Charcoal
// ============================================================
const COLORS = {
  // Backgrounds
  bgPrimary: '#1a1a1a',
  bgSecondary: '#252525',
  bgTertiary: '#2d2d2d',
  bgPanel: '#222222',
  bgInput: '#1f1f1f',
  
  // Cream tones (foreground)
  cream: '#f5f0e6',
  creamDim: '#c9c4b8',
  creamMuted: '#9a9588',
  creamDark: '#6b675c',
  
  // Accents
  accentCyan: '#5fb3b3',
  accentAmber: '#d9a662',
  accentGreen: '#7cb37c',
  accentRed: '#c97a7a',
  accentPurple: '#b08cb0',
  
  // Status
  statusActive: '#7cb37c',
  statusPaused: '#d9a662',
  statusError: '#c97a7a',
  statusIdle: '#9a9588',
  
  // Borders
  border: '#3a3a3a',
  borderHighlight: '#4a4a4a',
};

// ============================================================
// MOCK DATA - Agent "alpha"
// ============================================================
const MOCK_AGENTS = {
  alpha: {
    id: 'alpha',
    name: 'alpha',
    status: 'active',
    type: 'coordinator',
    uptime: '14h 32m 18s',
    version: 'v2.4.1',
    
    // Code content (JavaScript agent logic)
    code: `/**
 * Agent Alpha - Coordinator Node
 * Handles task distribution and fleet orchestration
 */

class CoordinatorAgent extends BaseAgent {
  constructor(config) {
    super(config);
    this.workers = new Map();
    this.taskQueue = [];
    this.metrics = {
      tasksCompleted: 0,
      errors: 0,
      avgLatency: 0
    };
  }

  async onMessage(msg) {
    switch(msg.type) {
      case 'TASK_ASSIGN':
        await this.distributeTask(msg.payload);
        break;
      case 'WORKER_HEARTBEAT':
        this.updateWorkerStatus(msg.from, msg.data);
        break;
      case 'TOPOLOGY_UPDATE':
        this.rebalanceFleet(msg.topology);
        break;
    }
  }

  async distributeTask(task) {
    const worker = this.selectOptimalWorker();
    if (!worker) {
      this.queueTask(task);
      return;
    }
    
    try {
      await this.send(worker.id, {
        type: 'EXECUTE',
        task: task,
        deadline: Date.now() + task.timeout
      });
      this.metrics.tasksCompleted++;
    } catch (err) {
      this.metrics.errors++;
      this.handleDistributionError(err, task);
    }
  }

  selectOptimalWorker() {
    return Array.from(this.workers.values())
      .filter(w => w.load < 0.8 && w.status === 'active')
      .sort((a, b) => a.load - b.load)[0];
  }
}`,
    
    // Local state
    state: {
      variables: [
        { name: 'workers', type: 'Map', value: 'Map(4) {beta, gamma, delta, epsilon}', size: 4 },
        { name: 'taskQueue', type: 'Array', value: 'Array(12)', size: 12 },
        { name: 'metrics', type: 'Object', value: '{tasksCompleted: 15234, ...}', size: 4 },
        { name: 'lastRebalance', type: 'Date', value: '2026-03-06T11:23:45Z', size: null },
        { name: 'topologyVersion', type: 'number', value: '247', size: null },
        { name: 'pendingAcks', type: 'Set', value: 'Set(3)', size: 3 },
        { name: 'config', type: 'Object', value: '{heartbeatInterval: 5000, ...}', size: 8 },
        { name: 'circuitBreaker', type: 'Map', value: 'Map(2)', size: 2 },
      ],
      messageQueue: [
        { id: 'msg-8923', type: 'TASK_ASSIGN', from: 'orchestrator', priority: 'high', timestamp: Date.now() - 120 },
        { id: 'msg-8922', type: 'WORKER_HEARTBEAT', from: 'gamma', priority: 'normal', timestamp: Date.now() - 450 },
        { id: 'msg-8921', type: 'TOPOLOGY_UPDATE', from: 'discovery', priority: 'high', timestamp: Date.now() - 890 },
        { id: 'msg-8920', type: 'METRICS_REPORT', from: 'beta', priority: 'low', timestamp: Date.now() - 1200 },
        { id: 'msg-8919', type: 'TASK_COMPLETE', from: 'delta', priority: 'normal', timestamp: Date.now() - 1450 },
        { id: 'msg-8918', type: 'ERROR_REPORT', from: 'epsilon', priority: 'critical', timestamp: Date.now() - 2100 },
      ],
      currentTask: {
        id: 'task-5521',
        name: 'rebalanceFleet()',
        startedAt: Date.now() - 3500,
        progress: 67,
        description: 'Redistributing tasks after topology change',
      }
    },
    
    // Log entries
    logs: [
      { timestamp: Date.now() - 50, level: 'info', message: 'Task task-5520 completed by worker gamma (142ms)' },
      { timestamp: Date.now() - 120, level: 'debug', message: 'Received heartbeat from delta (load: 0.42, mem: 64%)' },
      { timestamp: Date.now() - 180, level: 'info', message: 'Distributing task-5521 to optimal worker' },
      { timestamp: Date.now() - 280, level: 'warn', message: 'Worker epsilon lagging behind (queue: 23, latency: 450ms)' },
      { timestamp: Date.now() - 450, level: 'info', message: 'Topology update received, triggering rebalance' },
      { timestamp: Date.now() - 520, level: 'debug', message: 'Metrics aggregation cycle complete' },
      { timestamp: Date.now() - 890, level: 'error', message: 'Connection timeout to node-zeta (attempt 2/3)' },
      { timestamp: Date.now() - 1200, level: 'info', message: 'New worker beta-2 registered (capacity: 100)' },
      { timestamp: Date.now() - 1450, level: 'debug', message: 'Garbage collection: freed 12MB, 4 orphaned tasks' },
      { timestamp: Date.now() - 2100, level: 'error', message: 'Task task-5518 failed: OutOfMemoryError in worker epsilon' },
      { timestamp: Date.now() - 2300, level: 'warn', message: 'Circuit breaker opened for downstream service catalog' },
      { timestamp: Date.now() - 2800, level: 'info', message: 'Health check: all critical services OK' },
      { timestamp: Date.now() - 3200, level: 'debug', message: 'Rate limiter: 847 req/s (capacity: 1000/s)' },
      { timestamp: Date.now() - 3500, level: 'info', message: 'Starting fleet rebalance (trigger: topology_change)' },
      { timestamp: Date.now() - 4100, level: 'warn', message: 'Memory pressure detected: heap 78%' },
      { timestamp: Date.now() - 4800, level: 'info', message: 'Worker gamma reported task completion' },
      { timestamp: Date.now() - 5200, level: 'debug', message: 'Message bus: 23.4k msg/s throughput' },
      { timestamp: Date.now() - 5600, level: 'info', message: 'Scheduled maintenance window in 4h 23m' },
      { timestamp: Date.now() - 6100, level: 'error', message: 'DNS resolution failed for backup-registry (retrying)' },
      { timestamp: Date.now() - 6800, level: 'debug', message: 'Checkpoint created: state-v247.json (2.3MB)' },
    ]
  },
  
  beta: {
    id: 'beta',
    name: 'beta',
    status: 'active',
    type: 'worker',
    uptime: '8h 15m 42s',
    version: 'v2.4.0',
    code: `class WorkerAgent extends BaseAgent {
  constructor(config) {
    super(config);
    this.currentTask = null;
    this.taskHistory = [];
  }
  
  async executeTask(task) {
    this.currentTask = task;
    // ... execution logic
  }
}`,
    state: {
      variables: [
        { name: 'currentTask', type: 'Task', value: 'Task{id:5521, ...}', size: null },
        { name: 'taskHistory', type: 'Array', value: 'Array(342)', size: 342 },
      ],
      messageQueue: [],
      currentTask: { id: 'task-5521', name: 'processBatch()', startedAt: Date.now() - 1200, progress: 34 }
    },
    logs: [
      { timestamp: Date.now() - 100, level: 'info', message: 'Executing batch job (records: 500)' },
      { timestamp: Date.now() - 500, level: 'debug', message: 'Database connection pool: 4/10 active' },
    ]
  },
  
  gamma: {
    id: 'gamma',
    name: 'gamma',
    status: 'active',
    type: 'worker',
    uptime: '12h 45m 11s',
    version: 'v2.4.1',
    code: `class WorkerAgent extends BaseAgent {
  // Worker node implementation
}`,
    state: {
      variables: [
        { name: 'queue', type: 'Array', value: 'Array(8)', size: 8 },
      ],
      messageQueue: [],
      currentTask: null
    },
    logs: [
      { timestamp: Date.now() - 200, level: 'info', message: 'Task completed successfully' },
    ]
  },
  
  delta: {
    id: 'delta',
    name: 'delta',
    status: 'paused',
    type: 'worker',
    uptime: '3h 22m 05s',
    version: 'v2.3.9',
    code: `class WorkerAgent extends BaseAgent {
  // Paused for maintenance
}`,
    state: {
      variables: [
        { name: 'maintenanceMode', type: 'boolean', value: 'true', size: null },
      ],
      messageQueue: [],
      currentTask: null
    },
    logs: [
      { timestamp: Date.now() - 5000, level: 'warn', message: 'Agent paused by operator' },
    ]
  },
  
  epsilon: {
    id: 'epsilon',
    name: 'epsilon',
    status: 'error',
    type: 'worker',
    uptime: '0h 45m 12s',
    version: 'v2.4.1',
    code: `class WorkerAgent extends BaseAgent {
  // Error state - OOM recovery
}`,
    state: {
      variables: [
        { name: 'errorCount', type: 'number', value: '3', size: null },
        { name: 'lastError', type: 'Error', value: 'OutOfMemoryError', size: null },
      ],
      messageQueue: [],
      currentTask: null
    },
    logs: [
      { timestamp: Date.now() - 2100, level: 'error', message: 'FATAL: OutOfMemoryError - heap exhausted' },
      { timestamp: Date.now() - 2150, level: 'error', message: 'Failed to allocate 64MB for buffer' },
    ]
  }
};

// ============================================================
// FLEET MOCK DATA
// ============================================================
const MOCK_FLEET = {
  activeAgents: 5,
  totalAgents: 5,
  messageThroughput: 23476,
  errorRate: 0.03,
  avgLatency: 142,
  
  topology: {
    nodes: [
      { id: 'alpha', type: 'coordinator', x: 400, y: 200, status: 'active' },
      { id: 'beta', type: 'worker', x: 250, y: 350, status: 'active' },
      { id: 'gamma', type: 'worker', x: 400, y: 400, status: 'active' },
      { id: 'delta', type: 'worker', x: 550, y: 350, status: 'paused' },
      { id: 'epsilon', type: 'worker', x: 400, y: 100, status: 'error' },
    ],
    connections: [
      { from: 'alpha', to: 'beta' },
      { from: 'alpha', to: 'gamma' },
      { from: 'alpha', to: 'delta' },
      { from: 'alpha', to: 'epsilon' },
      { from: 'beta', to: 'gamma' },
    ]
  },
  
  events: [
    { timestamp: Date.now() - 120, type: 'task', message: 'Task task-5520 completed (142ms)', severity: 'info' },
    { timestamp: Date.now() - 450, type: 'topology', message: 'Node delta state: active → paused', severity: 'warn' },
    { timestamp: Date.now() - 890, type: 'error', message: 'Node epsilon: OutOfMemoryError', severity: 'error' },
    { timestamp: Date.now() - 1200, type: 'agent', message: 'New agent beta-2 registered', severity: 'info' },
    { timestamp: Date.now() - 2300, type: 'system', message: 'Circuit breaker opened: catalog-service', severity: 'warn' },
    { timestamp: Date.now() - 3500, type: 'topology', message: 'Fleet rebalance initiated', severity: 'info' },
    { timestamp: Date.now() - 4100, type: 'system', message: 'Memory pressure warning: alpha (78%)', severity: 'warn' },
    { timestamp: Date.now() - 6100, type: 'error', message: 'DNS failure: backup-registry', severity: 'error' },
  ],
  
  // Ghost fleet (simulation/test data)
  ghostFleet: {
    activeAgents: 12,
    totalAgents: 15,
    messageThroughput: 89234,
    errorRate: 0.12,
    avgLatency: 340,
    
    topology: {
      nodes: [
        { id: 'sim-alpha', type: 'coordinator', x: 400, y: 200, status: 'active' },
        { id: 'sim-beta-1', type: 'worker', x: 200, y: 300, status: 'active' },
        { id: 'sim-beta-2', type: 'worker', x: 300, y: 350, status: 'active' },
        { id: 'sim-gamma-1', type: 'worker', x: 400, y: 400, status: 'active' },
        { id: 'sim-gamma-2', type: 'worker', x: 500, y: 350, status: 'active' },
        { id: 'sim-delta', type: 'worker', x: 600, y: 300, status: 'error' },
      ],
      connections: []
    },
    
    events: [
      { timestamp: Date.now() - 50, type: 'system', message: 'Simulation tick: 1000 agents spawned', severity: 'info' },
      { timestamp: Date.now() - 500, type: 'error', message: 'Simulated cascade failure in region-east', severity: 'error' },
    ]
  }
};

// ============================================================
// UTILITY FUNCTIONS
// ============================================================

function formatTime(ms) {
  const seconds = Math.floor(ms / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  
  if (hours > 0) return `${hours}h ${minutes % 60}m`;
  if (minutes > 0) return `${minutes}m ${seconds % 60}s`;
  return `${seconds}s`;
}

function formatBytes(bytes) {
  const units = ['B', 'KB', 'MB', 'GB'];
  let i = 0;
  while (bytes >= 1024 && i < units.length - 1) {
    bytes /= 1024;
    i++;
  }
  return `${bytes.toFixed(1)} ${units[i]}`;
}

function syntaxHighlight(code) {
  // Simple syntax highlighting for JavaScript
  return code
    .replace(/(\/\*[\s\S]*?\*\/)/g, '<span class="comment">$1</span>')
    .replace(/(\/\/.*$)/gm, '<span class="comment">$1</span>')
    .replace(/\b(class|const|let|var|function|return|async|await|if|else|switch|case|break|try|catch|new|this|super|extends|import|from|export|default)\b/g, '<span class="keyword">$1</span>')
    .replace(/\b(true|false|null|undefined)\b/g, '<span class="literal">$1</span>')
    .replace(/\b(\d+)\b/g, '<span class="number">$1</span>')
    .replace(/(['"`])(.*?)\1/g, '<span class="string">$1$2$1</span>')
    .replace(/\b([A-Z][a-zA-Z0-9]*)\b/g, '<span class="type">$1</span>')
    .replace(/\b([a-z][a-zA-Z0-9]*)(?=\()/g, '<span class="function">$1</span>');
}

// ============================================================
// STYLES
// ============================================================
const PANEL_STYLES = `
<style id="ordl-panels-styles">
  .ordl-panel {
    font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
    background: ${COLORS.bgPrimary};
    color: ${COLORS.cream};
    border: 1px solid ${COLORS.border};
    border-radius: 4px;
    overflow: hidden;
  }
  
  .ordl-panel-header {
    background: ${COLORS.bgSecondary};
    border-bottom: 1px solid ${COLORS.border};
    padding: 12px 16px;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  
  .ordl-panel-title {
    font-size: 14px;
    font-weight: 600;
    color: ${COLORS.cream};
    text-transform: uppercase;
    letter-spacing: 1px;
  }
  
  .ordl-panel-subtitle {
    font-size: 11px;
    color: ${COLORS.creamMuted};
    margin-left: 12px;
  }
  
  .ordl-badge {
    display: inline-flex;
    align-items: center;
    padding: 2px 8px;
    border-radius: 3px;
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
  
  .ordl-badge.active { background: rgba(124, 179, 124, 0.2); color: ${COLORS.statusActive}; }
  .ordl-badge.paused { background: rgba(217, 166, 98, 0.2); color: ${COLORS.statusPaused}; }
  .ordl-badge.error { background: rgba(201, 122, 122, 0.2); color: ${COLORS.statusError}; }
  .ordl-badge.idle { background: rgba(154, 149, 136, 0.2); color: ${COLORS.statusIdle}; }
  
  /* Agent Selector */
  .ordl-selector {
    background: ${COLORS.bgInput};
    border: 1px solid ${COLORS.border};
    color: ${COLORS.cream};
    padding: 8px 12px;
    font-family: inherit;
    font-size: 12px;
    border-radius: 3px;
    cursor: pointer;
    min-width: 180px;
  }
  
  .ordl-selector:hover {
    border-color: ${COLORS.borderHighlight};
  }
  
  .ordl-selector:focus {
    outline: none;
    border-color: ${COLORS.accentCyan};
  }
  
  .ordl-selector option {
    background: ${COLORS.bgSecondary};
    color: ${COLORS.cream};
  }
  
  /* Code Editor */
  .ordl-code-editor {
    background: ${COLORS.bgPanel};
    border: 1px solid ${COLORS.border};
    border-radius: 3px;
    overflow: auto;
    max-height: 400px;
  }
  
  .ordl-code-content {
    padding: 16px;
    font-size: 12px;
    line-height: 1.6;
    white-space: pre;
    tab-size: 2;
  }
  
  .ordl-code-content .comment { color: ${COLORS.creamDark}; font-style: italic; }
  .ordl-code-content .keyword { color: ${COLORS.accentPurple}; }
  .ordl-code-content .string { color: ${COLORS.accentGreen}; }
  .ordl-code-content .number { color: ${COLORS.accentAmber}; }
  .ordl-code-content .function { color: ${COLORS.accentCyan}; }
  .ordl-code-content .type { color: ${COLORS.accentAmber}; }
  .ordl-code-content .literal { color: ${COLORS.accentRed}; }
  
  .ordl-line-numbers {
    float: left;
    padding: 16px 12px 16px 16px;
    background: ${COLORS.bgSecondary};
    border-right: 1px solid ${COLORS.border};
    color: ${COLORS.creamDark};
    font-size: 12px;
    line-height: 1.6;
    text-align: right;
    user-select: none;
  }
  
  /* State Inspector */
  .ordl-inspector {
    background: ${COLORS.bgPanel};
    border: 1px solid ${COLORS.border};
    border-radius: 3px;
  }
  
  .ordl-inspector-section {
    border-bottom: 1px solid ${COLORS.border};
  }
  
  .ordl-inspector-section:last-child {
    border-bottom: none;
  }
  
  .ordl-inspector-header {
    padding: 10px 14px;
    background: ${COLORS.bgSecondary};
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: ${COLORS.creamDim};
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  
  .ordl-inspector-count {
    background: ${COLORS.bgTertiary};
    padding: 2px 6px;
    border-radius: 2px;
    font-size: 10px;
  }
  
  .ordl-inspector-content {
    padding: 8px 0;
    max-height: 200px;
    overflow-y: auto;
  }
  
  .ordl-var-row {
    display: flex;
    align-items: center;
    padding: 6px 14px;
    font-size: 12px;
    cursor: pointer;
    transition: background 0.15s;
  }
  
  .ordl-var-row:hover {
    background: ${COLORS.bgSecondary};
  }
  
  .ordl-var-name {
    color: ${COLORS.accentCyan};
    min-width: 140px;
    font-weight: 500;
  }
  
  .ordl-var-type {
    color: ${COLORS.accentPurple};
    min-width: 60px;
    font-size: 11px;
  }
  
  .ordl-var-value {
    color: ${COLORS.creamDim};
    flex: 1;
    font-family: inherit;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  
  .ordl-var-size {
    color: ${COLORS.creamDark};
    font-size: 10px;
    margin-left: 8px;
  }
  
  /* Message Queue */
  .ordl-msg-row {
    display: flex;
    align-items: center;
    padding: 8px 14px;
    font-size: 11px;
    border-bottom: 1px solid ${COLORS.border};
  }
  
  .ordl-msg-row:last-child {
    border-bottom: none;
  }
  
  .ordl-msg-priority {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    margin-right: 10px;
  }
  
  .ordl-msg-priority.critical { background: ${COLORS.accentRed}; box-shadow: 0 0 6px ${COLORS.accentRed}; }
  .ordl-msg-priority.high { background: ${COLORS.accentAmber}; }
  .ordl-msg-priority.normal { background: ${COLORS.accentCyan}; }
  .ordl-msg-priority.low { background: ${COLORS.creamDark}; }
  
  .ordl-msg-type {
    color: ${COLORS.accentPurple};
    min-width: 100px;
    font-weight: 500;
  }
  
  .ordl-msg-from {
    color: ${COLORS.accentCyan};
    min-width: 80px;
  }
  
  .ordl-msg-id {
    color: ${COLORS.creamDark};
    font-size: 10px;
  }
  
  .ordl-msg-time {
    color: ${COLORS.creamMuted};
    margin-left: auto;
    font-size: 10px;
  }
  
  /* Current Task */
  .ordl-task-panel {
    padding: 14px;
    background: ${COLORS.bgSecondary};
  }
  
  .ordl-task-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 10px;
  }
  
  .ordl-task-name {
    font-size: 12px;
    font-weight: 600;
    color: ${COLORS.cream};
  }
  
  .ordl-task-id {
    font-size: 10px;
    color: ${COLORS.creamDark};
    font-family: inherit;
  }
  
  .ordl-task-desc {
    font-size: 11px;
    color: ${COLORS.creamMuted};
    margin-bottom: 10px;
  }
  
  .ordl-progress-bar {
    height: 4px;
    background: ${COLORS.bgTertiary};
    border-radius: 2px;
    overflow: hidden;
  }
  
  .ordl-progress-fill {
    height: 100%;
    background: linear-gradient(90deg, ${COLORS.accentCyan}, ${COLORS.accentGreen});
    border-radius: 2px;
    transition: width 0.3s ease;
  }
  
  .ordl-progress-text {
    font-size: 10px;
    color: ${COLORS.creamDim};
    margin-top: 6px;
    text-align: right;
  }
  
  /* Log Stream */
  .ordl-log-stream {
    background: ${COLORS.bgPanel};
    border: 1px solid ${COLORS.border};
    border-radius: 3px;
    max-height: 300px;
    overflow-y: auto;
    font-size: 11px;
    line-height: 1.5;
  }
  
  .ordl-log-entry {
    padding: 4px 12px;
    border-bottom: 1px solid ${COLORS.border};
    display: flex;
    align-items: flex-start;
  }
  
  .ordl-log-entry:last-child {
    border-bottom: none;
  }
  
  .ordl-log-entry:hover {
    background: ${COLORS.bgSecondary};
  }
  
  .ordl-log-time {
    color: ${COLORS.creamDark};
    min-width: 70px;
    font-size: 10px;
  }
  
  .ordl-log-level {
    min-width: 50px;
    font-weight: 600;
    font-size: 10px;
    text-transform: uppercase;
  }
  
  .ordl-log-level.info { color: ${COLORS.accentCyan}; }
  .ordl-log-level.debug { color: ${COLORS.creamMuted}; }
  .ordl-log-level.warn { color: ${COLORS.accentAmber}; }
  .ordl-log-level.error { color: ${COLORS.accentRed}; }
  
  .ordl-log-message {
    color: ${COLORS.creamDim};
    flex: 1;
    word-break: break-word;
  }
  
  /* Controls */
  .ordl-controls {
    display: flex;
    gap: 8px;
    padding: 12px 16px;
    background: ${COLORS.bgSecondary};
    border-top: 1px solid ${COLORS.border};
  }
  
  .ordl-btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 8px 14px;
    font-family: inherit;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    border: 1px solid ${COLORS.border};
    border-radius: 3px;
    background: ${COLORS.bgInput};
    color: ${COLORS.creamDim};
    cursor: pointer;
    transition: all 0.15s;
  }
  
  .ordl-btn:hover {
    background: ${COLORS.bgTertiary};
    color: ${COLORS.cream};
    border-color: ${COLORS.borderHighlight};
  }
  
  .ordl-btn:active {
    transform: translateY(1px);
  }
  
  .ordl-btn.primary {
    background: ${COLORS.accentCyan};
    color: ${COLORS.bgPrimary};
    border-color: ${COLORS.accentCyan};
  }
  
  .ordl-btn.primary:hover {
    background: #6fc3c3;
  }
  
  .ordl-btn.danger {
    background: ${COLORS.accentRed};
    color: ${COLORS.bgPrimary};
    border-color: ${COLORS.accentRed};
  }
  
  .ordl-btn.danger:hover {
    background: #d98a8a;
  }
  
  .ordl-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  
  /* Fleet Metrics */
  .ordl-metrics-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    padding: 16px;
  }
  
  .ordl-metric-card {
    background: ${COLORS.bgPanel};
    border: 1px solid ${COLORS.border};
    border-radius: 3px;
    padding: 14px;
    text-align: center;
  }
  
  .ordl-metric-label {
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: ${COLORS.creamMuted};
    margin-bottom: 6px;
  }
  
  .ordl-metric-value {
    font-size: 24px;
    font-weight: 600;
    color: ${COLORS.cream};
    font-family: inherit;
  }
  
  .ordl-metric-unit {
    font-size: 12px;
    color: ${COLORS.creamDim};
    margin-left: 4px;
  }
  
  .ordl-metric-delta {
    font-size: 10px;
    margin-top: 4px;
  }
  
  .ordl-metric-delta.positive { color: ${COLORS.statusActive}; }
  .ordl-metric-delta.negative { color: ${COLORS.statusError}; }
  
  /* Topology Canvas */
  .ordl-topology {
    background: ${COLORS.bgPanel};
    border: 1px solid ${COLORS.border};
    border-radius: 3px;
    height: 300px;
    position: relative;
    overflow: hidden;
  }
  
  .ordl-topology-canvas {
    width: 100%;
    height: 100%;
  }
  
  /* Events List */
  .ordl-events {
    background: ${COLORS.bgPanel};
    border: 1px solid ${COLORS.border};
    border-radius: 3px;
    max-height: 250px;
    overflow-y: auto;
  }
  
  .ordl-event-row {
    display: flex;
    align-items: center;
    padding: 10px 14px;
    border-bottom: 1px solid ${COLORS.border};
    font-size: 12px;
  }
  
  .ordl-event-row:last-child {
    border-bottom: none;
  }
  
  .ordl-event-row:hover {
    background: ${COLORS.bgSecondary};
  }
  
  .ordl-event-indicator {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    margin-right: 12px;
  }
  
  .ordl-event-indicator.info { background: ${COLORS.accentCyan}; }
  .ordl-event-indicator.warn { background: ${COLORS.accentAmber}; }
  .ordl-event-indicator.error { background: ${COLORS.accentRed}; }
  
  .ordl-event-type {
    color: ${COLORS.accentPurple};
    min-width: 80px;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
  
  .ordl-event-message {
    color: ${COLORS.creamDim};
    flex: 1;
  }
  
  .ordl-event-time {
    color: ${COLORS.creamDark};
    font-size: 10px;
  }
  
  /* Ghost Fleet Toggle */
  .ordl-ghost-toggle {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 16px;
    background: ${COLORS.bgSecondary};
    border: 1px solid ${COLORS.border};
    border-radius: 3px;
  }
  
  .ordl-toggle-switch {
    position: relative;
    width: 44px;
    height: 22px;
    background: ${COLORS.bgTertiary};
    border-radius: 11px;
    cursor: pointer;
    transition: background 0.2s;
  }
  
  .ordl-toggle-switch.active {
    background: ${COLORS.accentPurple};
  }
  
  .ordl-toggle-thumb {
    position: absolute;
    top: 2px;
    left: 2px;
    width: 18px;
    height: 18px;
    background: ${COLORS.cream};
    border-radius: 50%;
    transition: transform 0.2s;
  }
  
  .ordl-toggle-switch.active .ordl-toggle-thumb {
    transform: translateX(22px);
  }
  
  .ordl-toggle-label {
    font-size: 12px;
    color: ${COLORS.creamDim};
  }
  
  .ordl-toggle-label strong {
    color: ${COLORS.cream};
  }
  
  /* Panel Layouts */
  .ordl-agent-panel {
    display: flex;
    flex-direction: column;
    height: 100%;
  }
  
  .ordl-agent-content {
    display: grid;
    grid-template-columns: 1fr 350px;
    gap: 16px;
    padding: 16px;
    flex: 1;
    overflow: auto;
  }
  
  .ordl-agent-left {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }
  
  .ordl-agent-right {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }
  
  .ordl-fleet-panel {
    display: flex;
    flex-direction: column;
    height: 100%;
  }
  
  .ordl-fleet-content {
    display: flex;
    flex-direction: column;
    gap: 16px;
    padding: 16px;
    flex: 1;
    overflow: auto;
  }
  
  .ordl-fleet-section {
    display: grid;
    grid-template-columns: 2fr 1fr;
    gap: 16px;
  }
  
  /* Scrollbars */
  .ordl-panel ::-webkit-scrollbar {
    width: 8px;
    height: 8px;
  }
  
  .ordl-panel ::-webkit-scrollbar-track {
    background: ${COLORS.bgSecondary};
  }
  
  .ordl-panel ::-webkit-scrollbar-thumb {
    background: ${COLORS.borderHighlight};
    border-radius: 4px;
  }
  
  .ordl-panel ::-webkit-scrollbar-thumb:hover {
    background: ${COLORS.creamDark};
  }
  
  /* Animations */
  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
  }
  
  .ordl-pulse {
    animation: pulse 2s ease-in-out infinite;
  }
  
  @keyframes live-indicator {
    0% { box-shadow: 0 0 0 0 rgba(124, 179, 124, 0.4); }
    70% { box-shadow: 0 0 0 8px rgba(124, 179, 124, 0); }
    100% { box-shadow: 0 0 0 0 rgba(124, 179, 124, 0); }
  }
  
  .ordl-live-indicator {
    width: 8px;
    height: 8px;
    background: ${COLORS.statusActive};
    border-radius: 50%;
    animation: live-indicator 2s infinite;
  }
</style>
`;

// ============================================================
// AGENT PANEL COMPONENT
// ============================================================

class AgentPanel {
  constructor(containerId, options = {}) {
    this.container = document.getElementById(containerId);
    this.currentAgent = options.agent || 'alpha';
    this.updateInterval = null;
    this.onControlAction = options.onControlAction || (() => {});
    
    this.init();
  }
  
  init() {
    this.injectStyles();
    this.render();
    this.startLiveUpdates();
  }
  
  injectStyles() {
    if (!document.getElementById('ordl-panels-styles')) {
      document.head.insertAdjacentHTML('beforeend', PANEL_STYLES);
    }
  }
  
  render() {
    const agent = MOCK_AGENTS[this.currentAgent];
    
    this.container.innerHTML = `
      <div class="ordl-panel ordl-agent-panel">
        <div class="ordl-panel-header">
          <div style="display: flex; align-items: center;">
            <span class="ordl-panel-title">Agent Inspector</span>
            <span class="ordl-panel-subtitle">
              <span class="ordl-live-indicator" style="display: inline-block; margin-right: 6px;"></span>
              LIVE
            </span>
          </div>
          <div style="display: flex; align-items: center; gap: 12px;">
            <select class="ordl-selector" id="agent-selector">
              ${Object.entries(MOCK_AGENTS).map(([id, a]) => `
                <option value="${id}" ${id === this.currentAgent ? 'selected' : ''}>
                  ${a.name} (${a.type})
                </option>
              `).join('')}
            </select>
            <span class="ordl-badge ${agent.status}">${agent.status}</span>
          </div>
        </div>
        
        <div class="ordl-agent-content">
          <div class="ordl-agent-left">
            ${this.renderCodeEditor(agent)}
            ${this.renderLogStream(agent)}
          </div>
          
          <div class="ordl-agent-right">
            ${this.renderStateInspector(agent)}
          </div>
        </div>
        
        <div class="ordl-controls">
          <button class="ordl-btn ${agent.status === 'active' ? 'primary' : ''}" data-action="pause">
            ${agent.status === 'active' ? '⏸ Pause' : '▶ Resume'}
          </button>
          <button class="ordl-btn" data-action="step">⏭ Step</button>
          <button class="ordl-btn danger" data-action="kill">⏹ Kill</button>
          <button class="ordl-btn" data-action="restart">🔄 Restart</button>
          <div style="margin-left: auto; display: flex; align-items: center; gap: 12px; font-size: 11px; color: ${COLORS.creamMuted};">
            <span>v${agent.version}</span>
            <span>uptime: ${agent.uptime}</span>
          </div>
        </div>
      </div>
    `;
    
    this.attachEventListeners();
  }
  
  renderCodeEditor(agent) {
    const lines = agent.code.split('\n');
    const lineNumbers = lines.map((_, i) => i + 1).join('\n');
    const highlightedCode = syntaxHighlight(agent.code);
    
    return `
      <div class="ordl-code-editor">
        <div style="display: flex;">
          <div class="ordl-line-numbers">${lineNumbers}</div>
          <div class="ordl-code-content">${highlightedCode}</div>
        </div>
      </div>
    `;
  }
  
  renderStateInspector(agent) {
    return `
      <div class="ordl-inspector">
        ${agent.state.currentTask ? `
          <div class="ordl-inspector-section">
            <div class="ordl-inspector-header">Current Task</div>
            <div class="ordl-task-panel">
              <div class="ordl-task-header">
                <span class="ordl-task-name">${agent.state.currentTask.name}</span>
                <span class="ordl-task-id">${agent.state.currentTask.id}</span>
              </div>
              <div class="ordl-task-desc">${agent.state.currentTask.description || 'No description'}</div>
              <div class="ordl-progress-bar">
                <div class="ordl-progress-fill" style="width: ${agent.state.currentTask.progress}%"></div>
              </div>
              <div class="ordl-progress-text">${agent.state.currentTask.progress}% complete</div>
            </div>
          </div>
        ` : `
          <div class="ordl-inspector-section">
            <div class="ordl-inspector-header">Current Task</div>
            <div class="ordl-task-panel">
              <div class="ordl-task-desc" style="text-align: center; margin: 0; padding: 20px; color: ${COLORS.creamDark};">
                No active task
              </div>
            </div>
          </div>
        `}
        
        <div class="ordl-inspector-section">
          <div class="ordl-inspector-header">
            <span>Local Variables</span>
            <span class="ordl-inspector-count">${agent.state.variables.length}</span>
          </div>
          <div class="ordl-inspector-content">
            ${agent.state.variables.map(v => `
              <div class="ordl-var-row">
                <span class="ordl-var-name">${v.name}</span>
                <span class="ordl-var-type">${v.type}</span>
                <span class="ordl-var-value">${v.value}</span>
                ${v.size !== null ? `<span class="ordl-var-size">[${v.size}]</span>` : ''}
              </div>
            `).join('')}
          </div>
        </div>
        
        <div class="ordl-inspector-section">
          <div class="ordl-inspector-header">
            <span>Message Queue</span>
            <span class="ordl-inspector-count">${agent.state.messageQueue.length}</span>
          </div>
          <div class="ordl-inspector-content">
            ${agent.state.messageQueue.length > 0 ? agent.state.messageQueue.map(m => `
              <div class="ordl-msg-row">
                <span class="ordl-msg-priority ${m.priority}"></span>
                <span class="ordl-msg-type">${m.type}</span>
                <span class="ordl-msg-from">${m.from}</span>
                <span class="ordl-msg-id">${m.id}</span>
                <span class="ordl-msg-time">-${formatTime(Date.now() - m.timestamp)}</span>
              </div>
            `).join('') : `
              <div style="padding: 20px; text-align: center; color: ${COLORS.creamDark}; font-size: 11px;">
                Queue empty
              </div>
            `}
          </div>
        </div>
      </div>
    `;
  }
  
  renderLogStream(agent) {
    return `
      <div>
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
          <span style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; color: ${COLORS.creamDim};">Log Stream</span>
          <span style="font-size: 10px; color: ${COLORS.creamDark};">${agent.logs.length} entries</span>
        </div>
        <div class="ordl-log-stream" id="log-stream">
          ${agent.logs.map(log => `
            <div class="ordl-log-entry">
              <span class="ordl-log-time">-${formatTime(Date.now() - log.timestamp)}</span>
              <span class="ordl-log-level ${log.level}">${log.level}</span>
              <span class="ordl-log-message">${log.message}</span>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }
  
  attachEventListeners() {
    // Agent selector
    const selector = this.container.querySelector('#agent-selector');
    if (selector) {
      selector.addEventListener('change', (e) => {
        this.currentAgent = e.target.value;
        this.render();
      });
    }
    
    // Control buttons
    this.container.querySelectorAll('[data-action]').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const action = e.currentTarget.dataset.action;
        this.handleControlAction(action);
      });
    });
  }
  
  handleControlAction(action) {
    const agent = MOCK_AGENTS[this.currentAgent];
    
    switch (action) {
      case 'pause':
        agent.status = agent.status === 'active' ? 'paused' : 'active';
        this.addLogEntry(agent, 'info', `Agent ${agent.status === 'active' ? 'resumed' : 'paused'} by operator`);
        break;
      case 'step':
        this.addLogEntry(agent, 'debug', 'Single step execution');
        break;
      case 'kill':
        agent.status = 'error';
        this.addLogEntry(agent, 'error', 'Agent terminated by operator');
        break;
      case 'restart':
        agent.status = 'active';
        agent.uptime = '0h 0m 0s';
        this.addLogEntry(agent, 'info', 'Agent restarted');
        break;
    }
    
    this.onControlAction(action, this.currentAgent);
    this.render();
  }
  
  addLogEntry(agent, level, message) {
    agent.logs.unshift({
      timestamp: Date.now(),
      level,
      message
    });
    if (agent.logs.length > 100) agent.logs.pop();
  }
  
  startLiveUpdates() {
    this.updateInterval = setInterval(() => {
      this.updateLiveData();
    }, 2000);
  }
  
  updateLiveData() {
    const agent = MOCK_AGENTS[this.currentAgent];
    
    // Update task progress
    if (agent.state.currentTask && agent.state.currentTask.progress < 100) {
      agent.state.currentTask.progress = Math.min(100, agent.state.currentTask.progress + Math.floor(Math.random() * 5));
    }
    
    // Add occasional log entries
    if (Math.random() > 0.7) {
      const messages = [
        { level: 'debug', msg: `Heartbeat acknowledged (${Math.floor(Math.random() * 100)}ms)` },
        { level: 'info', msg: `Task processed: batch-${Math.floor(Math.random() * 1000)}` },
        { level: 'debug', msg: `Memory usage: ${Math.floor(50 + Math.random() * 30)}%` },
        { level: 'info', msg: `Message received from worker-${['beta', 'gamma', 'delta'][Math.floor(Math.random() * 3)]}` },
      ];
      const randomMsg = messages[Math.floor(Math.random() * messages.length)];
      this.addLogEntry(agent, randomMsg.level, randomMsg.msg);
    }
    
    // Update uptime
    const parts = agent.uptime.match(/(\d+)h (\d+)m (\d+)s/);
    if (parts) {
      let [_, h, m, s] = parts.map(Number);
      s++;
      if (s >= 60) { s = 0; m++; }
      if (m >= 60) { m = 0; h++; }
      agent.uptime = `${h}h ${m}m ${s}s`;
    }
    
    this.render();
  }
  
  destroy() {
    if (this.updateInterval) {
      clearInterval(this.updateInterval);
    }
  }
}

// ============================================================
// FLEET PANEL COMPONENT
// ============================================================

class FleetPanel {
  constructor(containerId, options = {}) {
    this.container = document.getElementById(containerId);
    this.showGhostFleet = false;
    this.updateInterval = null;
    this.onToggleGhost = options.onToggleGhost || (() => {});
    
    this.init();
  }
  
  init() {
    this.injectStyles();
    this.render();
    this.startLiveUpdates();
  }
  
  injectStyles() {
    if (!document.getElementById('ordl-panels-styles')) {
      document.head.insertAdjacentHTML('beforeend', PANEL_STYLES);
    }
  }
  
  render() {
    const data = this.showGhostFleet ? MOCK_FLEET.ghostFleet : MOCK_FLEET;
    
    this.container.innerHTML = `
      <div class="ordl-panel ordl-fleet-panel">
        <div class="ordl-panel-header">
          <div style="display: flex; align-items: center;">
            <span class="ordl-panel-title">Fleet Overview</span>
            <span class="ordl-panel-subtitle">
              <span class="ordl-live-indicator" style="display: inline-block; margin-right: 6px;"></span>
              LIVE
            </span>
          </div>
          <div class="ordl-ghost-toggle">
            <span class="ordl-toggle-label">
              <strong>Ghost Fleet</strong> (Simulation)
            </span>
            <div class="ordl-toggle-switch ${this.showGhostFleet ? 'active' : ''}" id="ghost-toggle">
              <div class="ordl-toggle-thumb"></div>
            </div>
          </div>
        </div>
        
        <div class="ordl-fleet-content">
          ${this.renderMetrics(data)}
          
          <div class="ordl-fleet-section">
            ${this.renderTopology(data)}
            ${this.renderEvents(data)}
          </div>
        </div>
      </div>
    `;
    
    this.attachEventListeners();
    this.drawTopology(data);
  }
  
  renderMetrics(data) {
    const throughputUnit = this.showGhostFleet ? '' : '';
    const throughputLabel = this.showGhostFleet ? 'msg/s' : 'msg/s';
    
    return `
      <div class="ordl-metrics-grid">
        <div class="ordl-metric-card">
          <div class="ordl-metric-label">Active Agents</div>
          <div class="ordl-metric-value">
            ${data.activeAgents}
            <span class="ordl-metric-unit">/ ${data.totalAgents}</span>
          </div>
          <div class="ordl-metric-delta ${data.activeAgents >= data.totalAgents * 0.8 ? 'positive' : 'negative'}">
            ${Math.round((data.activeAgents / data.totalAgents) * 100)}% healthy
          </div>
        </div>
        
        <div class="ordl-metric-card">
          <div class="ordl-metric-label">Message Throughput</div>
          <div class="ordl-metric-value">
            ${data.messageThroughput.toLocaleString()}
            <span class="ordl-metric-unit">${throughputLabel}</span>
          </div>
          <div class="ordl-metric-delta ${Math.random() > 0.5 ? 'positive' : 'negative'}">
            ${Math.random() > 0.5 ? '+' : '-'}${Math.floor(Math.random() * 5)}%
          </div>
        </div>
        
        <div class="ordl-metric-card">
          <div class="ordl-metric-label">Error Rate</div>
          <div class="ordl-metric-value">
            ${(data.errorRate * 100).toFixed(2)}
            <span class="ordl-metric-unit">%</span>
          </div>
          <div class="ordl-metric-delta ${data.errorRate < 0.05 ? 'positive' : 'negative'}">
            ${data.errorRate < 0.05 ? 'acceptable' : 'elevated'}
          </div>
        </div>
        
        <div class="ordl-metric-card">
          <div class="ordl-metric-label">Avg Latency</div>
          <div class="ordl-metric-value">
            ${data.avgLatency}
            <span class="ordl-metric-unit">ms</span>
          </div>
          <div class="ordl-metric-delta ${data.avgLatency < 200 ? 'positive' : 'negative'}">
            p99: ${Math.floor(data.avgLatency * 1.5)}ms
          </div>
        </div>
      </div>
    `;
  }
  
  renderTopology(data) {
    return `
      <div>
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
          <span style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; color: ${COLORS.creamDim};">Topology</span>
          <span style="font-size: 10px; color: ${COLORS.creamDark};">${data.topology.nodes.length} nodes</span>
        </div>
        <div class="ordl-topology">
          <canvas class="ordl-topology-canvas" id="topology-canvas"></canvas>
        </div>
      </div>
    `;
  }
  
  renderEvents(data) {
    const events = this.showGhostFleet ? MOCK_FLEET.ghostFleet.events : MOCK_FLEET.events;
    
    return `
      <div>
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
          <span style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; color: ${COLORS.creamDim};">Recent Events</span>
          <span style="font-size: 10px; color: ${COLORS.creamDark};">${events.length} events</span>
        </div>
        <div class="ordl-events">
          ${events.map(e => `
            <div class="ordl-event-row">
              <span class="ordl-event-indicator ${e.severity}"></span>
              <span class="ordl-event-type">${e.type}</span>
              <span class="ordl-event-message">${e.message}</span>
              <span class="ordl-event-time">-${formatTime(Date.now() - e.timestamp)}</span>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }
  
  drawTopology(data) {
    const canvas = this.container.querySelector('#topology-canvas');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    const rect = canvas.parentElement.getBoundingClientRect();
    canvas.width = rect.width;
    canvas.height = rect.height;
    
    const { nodes, connections } = data.topology;
    
    // Clear canvas
    ctx.fillStyle = COLORS.bgPanel;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    // Scale positions to canvas size
    const scaleX = canvas.width / 800;
    const scaleY = canvas.height / 500;
    
    // Draw connections
    ctx.strokeStyle = COLORS.borderHighlight;
    ctx.lineWidth = 1;
    connections.forEach(conn => {
      const from = nodes.find(n => n.id === conn.from);
      const to = nodes.find(n => n.id === conn.to);
      if (from && to) {
        ctx.beginPath();
        ctx.moveTo(from.x * scaleX, from.y * scaleY);
        ctx.lineTo(to.x * scaleX, to.y * scaleY);
        ctx.stroke();
        
        // Draw animated packet
        const t = (Date.now() % 2000) / 2000;
        const px = from.x * scaleX + (to.x * scaleX - from.x * scaleX) * t;
        const py = from.y * scaleY + (to.y * scaleY - from.y * scaleY) * t;
        ctx.fillStyle = COLORS.accentCyan;
        ctx.beginPath();
        ctx.arc(px, py, 3, 0, Math.PI * 2);
        ctx.fill();
      }
    });
    
    // Draw nodes
    nodes.forEach(node => {
      const x = node.x * scaleX;
      const y = node.y * scaleY;
      
      // Node glow for active
      if (node.status === 'active') {
        const gradient = ctx.createRadialGradient(x, y, 10, x, y, 25);
        gradient.addColorStop(0, `${COLORS.statusActive}33`);
        gradient.addColorStop(1, 'transparent');
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(x, y, 25, 0, Math.PI * 2);
        ctx.fill();
      }
      
      // Node circle
      ctx.fillStyle = node.status === 'active' ? COLORS.statusActive : 
                      node.status === 'paused' ? COLORS.statusPaused : 
                      COLORS.statusError;
      ctx.beginPath();
      ctx.arc(x, y, 8, 0, Math.PI * 2);
      ctx.fill();
      
      // Node border
      ctx.strokeStyle = COLORS.cream;
      ctx.lineWidth = 2;
      ctx.stroke();
      
      // Node label
      ctx.fillStyle = COLORS.creamDim;
      ctx.font = '11px JetBrains Mono, Consolas, monospace';
      ctx.textAlign = 'center';
      ctx.fillText(node.id, x, y + 22);
      
      // Node type
      ctx.fillStyle = COLORS.creamDark;
      ctx.font = '9px JetBrains Mono, Consolas, monospace';
      ctx.fillText(node.type, x, y + 34);
    });
  }
  
  attachEventListeners() {
    const toggle = this.container.querySelector('#ghost-toggle');
    if (toggle) {
      toggle.addEventListener('click', () => {
        this.showGhostFleet = !this.showGhostFleet;
        this.onToggleGhost(this.showGhostFleet);
        this.render();
      });
    }
  }
  
  startLiveUpdates() {
    this.updateInterval = setInterval(() => {
      this.updateLiveData();
    }, 1000);
  }
  
  updateLiveData() {
    // Update metrics with small random variations
    const data = this.showGhostFleet ? MOCK_FLEET.ghostFleet : MOCK_FLEET;
    
    data.messageThroughput += Math.floor((Math.random() - 0.5) * 500);
    data.avgLatency += Math.floor((Math.random() - 0.5) * 10);
    data.avgLatency = Math.max(10, Math.min(500, data.avgLatency));
    
    // Occasionally add new events
    if (Math.random() > 0.9) {
      const eventTypes = ['task', 'topology', 'system', 'agent'];
      const severities = ['info', 'info', 'info', 'warn', 'error'];
      const messages = [
        'Task batch completed',
        'Agent heartbeat missed',
        'Topology rebalancing',
        'Memory threshold warning',
        'New connection established',
      ];
      
      const newEvent = {
        timestamp: Date.now(),
        type: eventTypes[Math.floor(Math.random() * eventTypes.length)],
        message: messages[Math.floor(Math.random() * messages.length)],
        severity: severities[Math.floor(Math.random() * severities.length)]
      };
      
      if (this.showGhostFleet) {
        MOCK_FLEET.ghostFleet.events.unshift(newEvent);
        if (MOCK_FLEET.ghostFleet.events.length > 20) MOCK_FLEET.ghostFleet.events.pop();
      } else {
        MOCK_FLEET.events.unshift(newEvent);
        if (MOCK_FLEET.events.length > 20) MOCK_FLEET.events.pop();
      }
    }
    
    this.render();
  }
  
  destroy() {
    if (this.updateInterval) {
      clearInterval(this.updateInterval);
    }
  }
}

// ============================================================
// EXPORTS
// ============================================================

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { AgentPanel, FleetPanel, COLORS, MOCK_AGENTS, MOCK_FLEET };
} else {
  window.ORDL = window.ORDL || {};
  window.ORDL.AgentPanel = AgentPanel;
  window.ORDL.FleetPanel = FleetPanel;
  window.ORDL.COLORS = COLORS;
  window.ORDL.MOCK_AGENTS = MOCK_AGENTS;
  window.ORDL.MOCK_FLEET = MOCK_FLEET;
}

// Auto-initialize demo if containers exist
document.addEventListener('DOMContentLoaded', () => {
  if (document.getElementById('agent-panel')) {
    new AgentPanel('agent-panel');
  }
  if (document.getElementById('fleet-panel')) {
    new FleetPanel('fleet-panel');
  }
});
