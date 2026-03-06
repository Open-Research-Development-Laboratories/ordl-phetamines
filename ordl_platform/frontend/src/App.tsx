import { useEffect, useMemo, useState } from 'react'
import {
  type AuditEventOut,
  type DashboardBundle,
  type WorkerConnectivityOut,
  type WorkerOut,
  getHealth,
  loadDashboardBundle,
} from './api'
import './styles.css'

type ViewState = {
  health?: Record<string, unknown>
  bundle?: DashboardBundle
  error?: string
  loading: boolean
  loadedAt?: string
}

type MentalityState = {
  strictMode: boolean
  postbackLock: boolean
  retryBudget: number
  aggression: number
  maxParallel: number
  ghostOpacity: number
}

type TopologyNode = {
  id: string
  label: string
  role: string
  kind: 'hub' | 'worker'
  status: string
  connectivity: string
  throughput: number
  x: number
  y: number
}

type TopologyEdge = {
  id: string
  source: string
  target: string
  throughput: number
  latency: number
}

const TOPOLOGY_WIDTH = 980
const TOPOLOGY_HEIGHT = 420

const defaultMentality: MentalityState = {
  strictMode: true,
  postbackLock: true,
  retryBudget: 2,
  aggression: 35,
  maxParallel: 1,
  ghostOpacity: 45,
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value))
}

function safeNumber(value: unknown, fallback: number): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback
}

function colorFromStatus(status: string, connectivity: string): string {
  if (status === 'offline' || connectivity === 'down') return '#b2542e'
  if (status === 'degraded' || connectivity === 'degraded') return '#f0a54a'
  return '#f5f2e9'
}

function seeded(seed: string, offset: number): number {
  let hash = 2166136261
  for (let i = 0; i < seed.length; i += 1) {
    hash ^= seed.charCodeAt(i)
    hash += (hash << 1) + (hash << 4) + (hash << 7) + (hash << 8) + (hash << 24)
  }
  return (Math.abs(hash + offset * 131) % 1000) / 1000
}

function buildTopology(workers: WorkerOut[], connectivity: WorkerConnectivityOut[], jobRuns: DashboardBundle['jobRuns']): {
  nodes: TopologyNode[]
  edges: TopologyEdge[]
} {
  const connectivityByWorkerId = new Map(connectivity.map((item) => [item.worker_id, item]))
  const throughputByWorkerId = new Map<string, number>()

  for (const worker of workers) {
    throughputByWorkerId.set(worker.id, 0)
  }

  for (const run of jobRuns) {
    if (run.target_worker_id && throughputByWorkerId.has(run.target_worker_id)) {
      throughputByWorkerId.set(run.target_worker_id, (throughputByWorkerId.get(run.target_worker_id) ?? 0) + 1)
      continue
    }
    if (run.target_role) {
      const roleTargets = workers.filter((worker) => worker.role === run.target_role)
      if (roleTargets.length > 0) {
        for (const roleWorker of roleTargets) {
          throughputByWorkerId.set(roleWorker.id, (throughputByWorkerId.get(roleWorker.id) ?? 0) + 1)
        }
        continue
      }
    }
    for (const worker of workers) {
      throughputByWorkerId.set(worker.id, (throughputByWorkerId.get(worker.id) ?? 0) + 1)
    }
  }

  const nodes: TopologyNode[] = [
    {
      id: 'hub-control',
      label: 'hub-control',
      role: 'coordinator',
      kind: 'hub',
      status: 'online',
      connectivity: 'online',
      throughput: workers.reduce((acc, worker) => acc + (throughputByWorkerId.get(worker.id) ?? 0), 0),
      x: TOPOLOGY_WIDTH / 2,
      y: TOPOLOGY_HEIGHT / 2,
    },
  ]

  const radiusX = TOPOLOGY_WIDTH * 0.36
  const radiusY = TOPOLOGY_HEIGHT * 0.34

  workers.forEach((worker, index) => {
    const angle = (Math.PI * 2 * index) / Math.max(workers.length, 1)
    const jitterX = (seeded(worker.id, 3) - 0.5) * 52
    const jitterY = (seeded(worker.id, 7) - 0.5) * 38
    const conn = connectivityByWorkerId.get(worker.id)
    nodes.push({
      id: worker.id,
      label: worker.name,
      role: worker.role,
      kind: 'worker',
      status: worker.status,
      connectivity: conn?.connectivity_state ?? 'unknown',
      throughput: throughputByWorkerId.get(worker.id) ?? 0,
      x: TOPOLOGY_WIDTH / 2 + Math.cos(angle) * radiusX + jitterX,
      y: TOPOLOGY_HEIGHT / 2 + Math.sin(angle) * radiusY + jitterY,
    })
  })

  const edges: TopologyEdge[] = workers.map((worker) => {
    const conn = connectivityByWorkerId.get(worker.id)
    return {
      id: `edge-${worker.id}`,
      source: 'hub-control',
      target: worker.id,
      throughput: Math.max(1, throughputByWorkerId.get(worker.id) ?? 0),
      latency: conn?.gateway_rtt_ms ?? -1,
    }
  })

  return { nodes, edges }
}

function runLayout(nodes: TopologyNode[], edges: TopologyEdge[]): TopologyNode[] {
  const map = new Map(nodes.map((node) => [node.id, { ...node }]))
  const workerNodes = nodes.filter((node) => node.kind === 'worker')

  for (let step = 0; step < 72; step += 1) {
    for (let i = 0; i < workerNodes.length; i += 1) {
      for (let j = i + 1; j < workerNodes.length; j += 1) {
        const a = map.get(workerNodes[i].id)
        const b = map.get(workerNodes[j].id)
        if (!a || !b) continue
        const dx = a.x - b.x
        const dy = a.y - b.y
        const dist = Math.max(Math.sqrt(dx * dx + dy * dy), 1)
        const force = 1800 / (dist * dist)
        const ux = dx / dist
        const uy = dy / dist
        a.x += ux * force
        a.y += uy * force
        b.x -= ux * force
        b.y -= uy * force
      }
    }

    for (const edge of edges) {
      const source = map.get(edge.source)
      const target = map.get(edge.target)
      if (!source || !target) continue
      const dx = target.x - source.x
      const dy = target.y - source.y
      const dist = Math.max(Math.sqrt(dx * dx + dy * dy), 1)
      const desired = 210
      const stretch = (dist - desired) * 0.015
      const ux = dx / dist
      const uy = dy / dist
      target.x -= ux * stretch * 11
      target.y -= uy * stretch * 11
    }

    for (const worker of workerNodes) {
      const node = map.get(worker.id)
      if (!node) continue
      node.x = clamp(node.x, 80, TOPOLOGY_WIDTH - 80)
      node.y = clamp(node.y, 60, TOPOLOGY_HEIGHT - 60)
    }
  }

  return nodes.map((node) => map.get(node.id) ?? node)
}

function parseIso(value: string): number {
  const stamp = Date.parse(value)
  return Number.isNaN(stamp) ? 0 : stamp
}

function statusCount(workers: WorkerOut[]): Record<string, number> {
  return workers.reduce<Record<string, number>>((acc, worker) => {
    acc[worker.status] = (acc[worker.status] ?? 0) + 1
    return acc
  }, {})
}

function eventIsBranch(event: AuditEventOut): boolean {
  return event.severity !== 'info' || event.event_type.includes('failed') || event.event_type.includes('denied')
}

export default function App() {
  const [token, setToken] = useState('')
  const [projectId, setProjectId] = useState('')
  const [state, setState] = useState<ViewState>({ loading: false })
  const [selectedNodeId, setSelectedNodeId] = useState<string>('hub-control')
  const [timelineIndex, setTimelineIndex] = useState(0)
  const [mentality, setMentality] = useState<MentalityState>(defaultMentality)

  useEffect(() => {
    getHealth()
      .then((health) => setState((current) => ({ ...current, health })))
      .catch((error: Error) => setState((current) => ({ ...current, error: error.message })))
  }, [])

  useEffect(() => {
    const profile = state.bundle?.profiles?.[0]
    if (!profile) return
    setMentality((current) => ({
      ...current,
      strictMode: profile.quality_bar.toLowerCase() !== 'fast',
      postbackLock: profile.visible_body_required,
      retryBudget: profile.retry_max_attempts,
      maxParallel: profile.max_parallel,
    }))
  }, [state.bundle?.profiles])

  const hasToken = token.trim().length > 0

  const topology = useMemo(() => {
    const workers = state.bundle?.workers ?? []
    const connectivity = state.bundle?.connectivity ?? []
    const jobRuns = state.bundle?.jobRuns ?? []
    const seed = buildTopology(workers, connectivity, jobRuns)
    return {
      nodes: runLayout(seed.nodes, seed.edges),
      edges: seed.edges,
    }
  }, [state.bundle?.workers, state.bundle?.connectivity, state.bundle?.jobRuns])

  useEffect(() => {
    const workerNode = topology.nodes.find((node) => node.kind === 'worker')
    if (workerNode) {
      setSelectedNodeId((current) => (current === 'hub-control' ? workerNode.id : current))
    }
  }, [topology.nodes])

  const selectedNode = useMemo(() => topology.nodes.find((node) => node.id === selectedNodeId), [selectedNodeId, topology.nodes])

  const timelineEvents = useMemo(() => {
    const events = [...(state.bundle?.auditEvents ?? [])]
    events.sort((a, b) => parseIso(a.created_at) - parseIso(b.created_at))
    return events
  }, [state.bundle?.auditEvents])

  useEffect(() => {
    if (timelineEvents.length > 0) {
      setTimelineIndex(timelineEvents.length - 1)
    } else {
      setTimelineIndex(0)
    }
  }, [timelineEvents.length])

  const currentEvent = timelineEvents[timelineIndex] ?? null
  const branchPoints = useMemo(() => timelineEvents.filter(eventIsBranch), [timelineEvents])

  const causalChain = useMemo(() => {
    if (!currentEvent) return []
    const key = currentEvent.trace_id || currentEvent.run_id
    if (!key) return timelineEvents.slice(Math.max(timelineIndex - 4, 0), timelineIndex + 1)
    return timelineEvents.filter((event) => event.trace_id === key || event.run_id === key).slice(-5)
  }, [currentEvent, timelineEvents, timelineIndex])

  const workerStatusCounts = useMemo(() => statusCount(state.bundle?.workers ?? []), [state.bundle?.workers])

  const complianceScore = useMemo(() => {
    const workers = state.bundle?.workers ?? []
    if (workers.length === 0) return 0
    const online = workers.filter((worker) => worker.status === 'online').length
    const onlinePct = (online / workers.length) * 100
    const strictAdjustment = mentality.strictMode ? 1 : 0.87
    const retryAdjustment = clamp(1 - mentality.retryBudget * 0.025, 0.8, 1.05)
    return Math.round(clamp(onlinePct * strictAdjustment * retryAdjustment, 0, 100))
  }, [state.bundle?.workers, mentality.strictMode, mentality.retryBudget])

  const ghostDelta = useMemo(() => {
    const riskFactor = (50 - mentality.aggression) / 5
    const parallelImpact = mentality.maxParallel > 1 ? -2 * (mentality.maxParallel - 1) : 0
    const base = complianceScore + riskFactor + parallelImpact
    return Math.round(clamp(base, 0, 100))
  }, [complianceScore, mentality.aggression, mentality.maxParallel])

  const providerRows = useMemo(() => {
    const source = (state.bundle?.providers?.providers ?? {}) as Record<string, { auth_mode: string; required_secrets: string[] }>
    return Object.entries(source).map(([provider, meta]) => ({
      provider,
      authMode: meta.auth_mode,
      requiredSecrets: (meta.required_secrets ?? []).length,
    }))
  }, [state.bundle?.providers])

  async function loadDashboard() {
    if (!token.trim()) return
    setState((current) => ({ ...current, loading: true, error: undefined }))
    try {
      const bundle = await loadDashboardBundle(token.trim(), projectId.trim())
      setState((current) => ({
        ...current,
        bundle,
        loading: false,
        loadedAt: new Date().toISOString(),
        error: undefined,
      }))
    } catch (error) {
      setState((current) => ({ ...current, loading: false, error: (error as Error).message }))
    }
  }

  const projectLoaded = Boolean(state.bundle && projectId.trim())

  return (
    <div className="app-shell">
      <header className="control-header blueprint-card">
        <div>
          <p className="eyebrow">ORDL Fleet IDE</p>
          <h1>Monochrome Machinery Control Faceplate</h1>
          <p className="subtitle">Deterministic orchestration, governed collaboration, and fleet telemetry in one control surface.</p>
        </div>
        <div className="status-strip">
          <span className="status-pill">Gateway {state.health ? 'online' : 'checking'}</span>
          <span className="status-pill">Workers {(state.bundle?.workers ?? []).length}</span>
          <span className={`status-pill ${branchPoints.length > 0 ? 'warn' : 'ok'}`}>
            Branch points {branchPoints.length}
          </span>
        </div>
      </header>

      <section className="input-deck blueprint-card">
        <label>
          Bearer token
          <input
            type="password"
            value={token}
            onChange={(event) => setToken(event.target.value)}
            placeholder="Paste ORDL API bearer token"
          />
        </label>
        <label>
          Project ID
          <input
            value={projectId}
            onChange={(event) => setProjectId(event.target.value)}
            placeholder="Project scope UUID"
          />
        </label>
        <button type="button" className="command-button" disabled={!hasToken || state.loading} onClick={loadDashboard}>
          {state.loading ? 'Refreshing matrix...' : 'Load control plane'}
        </button>
        <div className="load-meta">
          <div>Last load: {state.loadedAt ? new Date(state.loadedAt).toLocaleString() : 'not loaded'}</div>
          <div>Project scope: {projectId.trim() || 'token scope only'}</div>
        </div>
      </section>

      {state.error ? <section className="error-banner">Error: {state.error}</section> : null}

      <main className="board-grid">
        <section className="blueprint-card topology-card">
          <h2>Swarm Topology</h2>
          <p className="panel-note">Node pulse maps to activity. Edge thickness maps to throughput. Click any worker to inspect individual state.</p>
          <svg viewBox={`0 0 ${TOPOLOGY_WIDTH} ${TOPOLOGY_HEIGHT}`} className="topology-canvas" role="img" aria-label="fleet topology map">
            {topology.edges.map((edge) => {
              const source = topology.nodes.find((node) => node.id === edge.source)
              const target = topology.nodes.find((node) => node.id === edge.target)
              if (!source || !target) return null
              const strokeWidth = clamp(edge.throughput * 0.8, 1.5, 10)
              return (
                <g key={edge.id}>
                  <line
                    x1={source.x}
                    y1={source.y}
                    x2={target.x}
                    y2={target.y}
                    className="edge"
                    style={{ strokeWidth }}
                  />
                  <text x={(source.x + target.x) / 2} y={(source.y + target.y) / 2 - 8} className="edge-label">
                    {edge.throughput}/m {edge.latency >= 0 ? `| ${edge.latency}ms` : ''}
                  </text>
                </g>
              )
            })}

            {topology.nodes.map((node) => {
              const isSelected = node.id === selectedNodeId
              const radius = node.kind === 'hub' ? 34 : clamp(16 + node.throughput * 2.2, 16, 30)
              return (
                <g key={node.id} className={`node ${node.kind} ${node.status === 'online' ? 'pulse' : ''}`} onClick={() => setSelectedNodeId(node.id)}>
                  <circle
                    cx={node.x}
                    cy={node.y}
                    r={radius}
                    fill="none"
                    stroke={colorFromStatus(node.status, node.connectivity)}
                    strokeWidth={isSelected ? 4 : 2}
                  />
                  <text x={node.x} y={node.y + 4} className="node-label">
                    {node.label}
                  </text>
                  <text x={node.x} y={node.y + radius + 16} className="node-role">
                    {node.role}
                  </text>
                </g>
              )
            })}

            {topology.nodes
              .filter((node) => node.kind === 'worker')
              .map((node) => (
                <g key={`ghost-${node.id}`} style={{ opacity: mentality.ghostOpacity / 100 }}>
                  <circle
                    cx={node.x + 18}
                    cy={node.y - 16}
                    r={14}
                    className="ghost-node"
                    strokeWidth={1.5}
                    fill="none"
                  />
                </g>
              ))}
          </svg>
        </section>

        <section className="blueprint-card temporal-card">
          <h2>Determinism Slider</h2>
          <p className="panel-note">Rewind through audited causality. Branch points indicate divergence or governance exceptions.</p>
          <input
            type="range"
            min={0}
            max={Math.max(timelineEvents.length - 1, 0)}
            value={timelineIndex}
            onChange={(event) => setTimelineIndex(Number(event.target.value))}
            disabled={timelineEvents.length === 0}
          />
          <div className="timeline-readout">
            {currentEvent ? (
              <>
                <div>
                  <strong>{currentEvent.event_type}</strong>
                  <span>{new Date(currentEvent.created_at).toLocaleString()}</span>
                </div>
                <div className="tiny-metadata">
                  <span>Trace: {currentEvent.trace_id || 'none'}</span>
                  <span>Run: {currentEvent.run_id || 'none'}</span>
                  <span>Severity: {currentEvent.severity}</span>
                </div>
              </>
            ) : (
              <div>No project audit events loaded yet. Set project scope and refresh.</div>
            )}
          </div>
          <div className="chain-grid">
            <div>
              <h3>Causal chain</h3>
              <ul>
                {causalChain.map((event) => (
                  <li key={event.id}>
                    <span>{event.event_type}</span>
                    <small>{new Date(event.created_at).toLocaleTimeString()}</small>
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <h3>Branch points</h3>
              <ul className="branch-list">
                {branchPoints.slice(-5).map((event) => (
                  <li key={`branch-${event.id}`}>
                    <span>{event.event_type}</span>
                    <small>{event.severity}</small>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </section>

        <section className="blueprint-card mentality-card">
          <h2>Mentality Panel</h2>
          <p className="panel-note">Policy behavior controls with immediate compliance projection across the active fleet.</p>
          <div className="switch-row">
            <button
              type="button"
              className={`toggle ${mentality.strictMode ? 'active' : ''}`}
              onClick={() => setMentality((current) => ({ ...current, strictMode: !current.strictMode }))}
            >
              Strict mode
            </button>
            <button
              type="button"
              className={`toggle ${mentality.postbackLock ? 'active' : ''}`}
              onClick={() => setMentality((current) => ({ ...current, postbackLock: !current.postbackLock }))}
            >
              Visible postback lock
            </button>
          </div>

          <label>
            Aggression dial
            <input
              type="range"
              min={0}
              max={100}
              value={mentality.aggression}
              onChange={(event) =>
                setMentality((current) => ({ ...current, aggression: safeNumber(Number(event.target.value), current.aggression) }))
              }
            />
          </label>

          <label>
            Retry budget
            <input
              type="range"
              min={0}
              max={10}
              value={mentality.retryBudget}
              onChange={(event) =>
                setMentality((current) => ({ ...current, retryBudget: safeNumber(Number(event.target.value), current.retryBudget) }))
              }
            />
          </label>

          <label>
            Max parallel routes
            <input
              type="range"
              min={1}
              max={12}
              value={mentality.maxParallel}
              onChange={(event) =>
                setMentality((current) => ({ ...current, maxParallel: safeNumber(Number(event.target.value), current.maxParallel) }))
              }
            />
          </label>

          <div className="meter-stack">
            <div>
              <div className="meter-label">
                <span>Projected compliance</span>
                <strong>{complianceScore}%</strong>
              </div>
              <div className="meter">
                <div style={{ width: `${complianceScore}%` }} />
              </div>
            </div>
            <div>
              <div className="meter-label">
                <span>Ghost fleet expectation</span>
                <strong>{ghostDelta}%</strong>
              </div>
              <div className="meter ghost">
                <div style={{ width: `${ghostDelta}%` }} />
              </div>
            </div>
          </div>
        </section>

        <section className="blueprint-card split-card">
          <h2>Individual vs Collective</h2>
          <div className="split-plane">
            <article>
              <h3>Individual</h3>
              {selectedNode ? (
                <div className="facts">
                  <div>
                    <span>Node</span>
                    <strong>{selectedNode.label}</strong>
                  </div>
                  <div>
                    <span>Role</span>
                    <strong>{selectedNode.role}</strong>
                  </div>
                  <div>
                    <span>Status</span>
                    <strong>{selectedNode.status}</strong>
                  </div>
                  <div>
                    <span>Connectivity</span>
                    <strong>{selectedNode.connectivity}</strong>
                  </div>
                  <div>
                    <span>Throughput</span>
                    <strong>{selectedNode.throughput}/m</strong>
                  </div>
                </div>
              ) : (
                <div>Select a node from topology.</div>
              )}
            </article>
            <article>
              <h3>Collective</h3>
              <div className="facts">
                <div>
                  <span>Workers online</span>
                  <strong>{workerStatusCounts.online ?? 0}</strong>
                </div>
                <div>
                  <span>Workers degraded</span>
                  <strong>{workerStatusCounts.degraded ?? 0}</strong>
                </div>
                <div>
                  <span>Workers offline</span>
                  <strong>{workerStatusCounts.offline ?? 0}</strong>
                </div>
                <div>
                  <span>Active job runs</span>
                  <strong>{(state.bundle?.jobRuns ?? []).length}</strong>
                </div>
                <div>
                  <span>Collab messages</span>
                  <strong>{(state.bundle?.messages ?? []).length}</strong>
                </div>
              </div>
            </article>
          </div>
        </section>

        <section className="blueprint-card ghost-card">
          <h2>Ghost Fleet Overlay</h2>
          <p className="panel-note">Shadow rollout model overlays production behavior before promotion.</p>
          <label>
            Ghost opacity
            <input
              type="range"
              min={0}
              max={100}
              value={mentality.ghostOpacity}
              onChange={(event) =>
                setMentality((current) => ({ ...current, ghostOpacity: safeNumber(Number(event.target.value), current.ghostOpacity) }))
              }
            />
          </label>
          <div className="facts ghost-stats">
            <div>
              <span>Production confidence</span>
              <strong>{complianceScore}%</strong>
            </div>
            <div>
              <span>Ghost confidence</span>
              <strong>{ghostDelta}%</strong>
            </div>
            <div>
              <span>Divergence</span>
              <strong>{Math.abs(complianceScore - ghostDelta)} pts</strong>
            </div>
            <div>
              <span>Promotion threshold</span>
              <strong>{ghostDelta >= complianceScore - 5 ? 'ready' : 'hold'}</strong>
            </div>
          </div>
        </section>

        <section className="blueprint-card provider-card">
          <h2>Provider Matrix</h2>
          <p className="panel-note">Configured provider adapters loaded from the control plane registry.</p>
          <div className="provider-table">
            <div className="provider-row provider-head">
              <span>Provider</span>
              <span>Auth mode</span>
              <span>Required secrets</span>
            </div>
            {providerRows.map((row) => (
              <div key={row.provider} className="provider-row">
                <span>{row.provider}</span>
                <span>{row.authMode}</span>
                <span>{row.requiredSecrets}</span>
              </div>
            ))}
          </div>
        </section>
      </main>

      {!projectLoaded ? (
        <footer className="info-footer">
          Project-scoped views activate when a valid project ID is provided. Token-scoped info and provider registry are already live.
        </footer>
      ) : null}
    </div>
  )
}
