const API_BASE = import.meta.env.VITE_ORDL_API_BASE || 'http://127.0.0.1:8891/v1'
const CONTROL_BASE = API_BASE.endsWith('/v1') ? API_BASE.slice(0, -3) : API_BASE

type RequestOptions = {
  token?: string
}

async function requestJson<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = {}
  if (options.token) {
    headers.Authorization = `Bearer ${options.token}`
  }
  const res = await fetch(`${API_BASE}${path}`, { headers })
  if (!res.ok) {
    const body = await res.text()
    const suffix = body ? `: ${body.slice(0, 200)}` : ''
    throw new Error(`request failed (${res.status}) ${path}${suffix}`)
  }
  return (await res.json()) as T
}

export type WorkerOut = {
  id: string
  project_id: string
  name: string
  role: string
  host: string
  device_id: string
  status: string
  capabilities: string[]
}

export type WorkerConnectivityOut = {
  worker_id: string
  worker_name: string
  role: string
  status: string
  connectivity_state: string
  last_seen_at: string | null
  last_keepalive_at: string | null
  last_probe_at: string | null
  last_gateway_url: string
  gateway_rtt_ms: number
  reconnect_required: boolean
  reconnect_targets: string[]
}

export type WorkerGroupOut = {
  id: string
  project_id: string
  name: string
  routing_strategy: string
  selection_mode: string
  target_role: string
  capability_tags: string[]
  worker_ids: string[]
  failover_group_id: string | null
}

export type OrchestrationProfileOut = {
  id: string
  project_id: string
  name: string
  routing_mode: string
  quality_bar: string
  max_parallel: number
  retry_max_attempts: number
  retry_backoff_seconds: number
  postback_required: boolean
  visible_body_required: boolean
  max_chunk_chars: number
  owner_principal_id: string
  report_to: string[]
  escalation_to: string[]
  visibility_mode: string
  status: string
}

export type JobRunOut = {
  id: string
  project_id: string
  template_id: string | null
  profile_id: string | null
  owner_principal_id: string
  report_to: string[]
  escalation_to: string[]
  visibility_mode: string
  routing_mode: string
  target_group_id: string | null
  target_worker_id: string | null
  target_role: string
  objective: string
  input_payload: Record<string, unknown>
  state: string
  attempt_count: number
  artifact_summary: Array<Record<string, unknown>>
  last_error: string
  state_reason: string
}

export type MessageOut = {
  id: string
  project_id: string
  author_user_id: string
  reviewer_user_id: string | null
  title: string
  body: string
  state: string
  revision: number
  parent_message_id: string | null
  review_notes: string
}

export type AuditEventOut = {
  id: string
  event_index: number
  event_type: string
  actor_id: string
  actor_role: string
  severity: string
  trace_id: string
  run_id: string
  session_id: string
  payload: Record<string, unknown>
  resource: Record<string, unknown>
  context: Record<string, unknown>
  created_at: string
}

export type DashboardBundle = {
  info: Record<string, unknown>
  providers: Record<string, unknown>
  workers: WorkerOut[]
  connectivity: WorkerConnectivityOut[]
  groups: WorkerGroupOut[]
  profiles: OrchestrationProfileOut[]
  jobRuns: JobRunOut[]
  messages: MessageOut[]
  auditEvents: AuditEventOut[]
}

export async function getHealth(): Promise<Record<string, unknown>> {
  const res = await fetch(`${CONTROL_BASE}/health`)
  if (!res.ok) {
    throw new Error('health request failed')
  }
  return (await res.json()) as Record<string, unknown>
}

export function getInfo(token: string): Promise<Record<string, unknown>> {
  return requestJson<Record<string, unknown>>('/info', { token })
}

export function getProviders(token: string): Promise<Record<string, unknown>> {
  return requestJson<Record<string, unknown>>('/providers', { token })
}

export function getWorkers(token: string, projectId: string): Promise<WorkerOut[]> {
  const qs = new URLSearchParams({ project_id: projectId }).toString()
  return requestJson<WorkerOut[]>(`/workers?${qs}`, { token })
}

export function getWorkerConnectivity(token: string, projectId: string): Promise<WorkerConnectivityOut[]> {
  const qs = new URLSearchParams({ project_id: projectId }).toString()
  return requestJson<WorkerConnectivityOut[]>(`/workers/connectivity?${qs}`, { token })
}

export function getWorkerGroups(token: string, projectId: string): Promise<WorkerGroupOut[]> {
  const qs = new URLSearchParams({ project_id: projectId }).toString()
  return requestJson<WorkerGroupOut[]>(`/worker-groups?${qs}`, { token })
}

export function getOrchestrationProfiles(token: string, projectId: string): Promise<OrchestrationProfileOut[]> {
  const qs = new URLSearchParams({ project_id: projectId }).toString()
  return requestJson<OrchestrationProfileOut[]>(`/orchestration/profiles?${qs}`, { token })
}

export function getJobRuns(token: string, projectId: string, limit = 120): Promise<JobRunOut[]> {
  const qs = new URLSearchParams({ project_id: projectId, limit: String(limit) }).toString()
  return requestJson<JobRunOut[]>(`/jobs/runs?${qs}`, { token })
}

export function getMessages(token: string, projectId: string): Promise<MessageOut[]> {
  const qs = new URLSearchParams({ project_id: projectId }).toString()
  return requestJson<MessageOut[]>(`/messages?${qs}`, { token })
}

export function getAuditEvents(token: string, projectId: string, limit = 240): Promise<AuditEventOut[]> {
  const qs = new URLSearchParams({ project_id: projectId, limit: String(limit) }).toString()
  return requestJson<AuditEventOut[]>(`/audit/events?${qs}`, { token })
}

export async function loadDashboardBundle(token: string, projectId: string): Promise<DashboardBundle> {
  const [info, providers] = await Promise.all([getInfo(token), getProviders(token)])

  if (!projectId.trim()) {
    return {
      info,
      providers,
      workers: [],
      connectivity: [],
      groups: [],
      profiles: [],
      jobRuns: [],
      messages: [],
      auditEvents: [],
    }
  }

  const [workers, connectivity, groups, profiles, jobRuns, messages, auditEvents] = await Promise.all([
    getWorkers(token, projectId),
    getWorkerConnectivity(token, projectId),
    getWorkerGroups(token, projectId),
    getOrchestrationProfiles(token, projectId),
    getJobRuns(token, projectId),
    getMessages(token, projectId),
    getAuditEvents(token, projectId),
  ])

  return {
    info,
    providers,
    workers,
    connectivity,
    groups,
    profiles,
    jobRuns,
    messages,
    auditEvents,
  }
}
