from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class TokenRequest(BaseModel):
    tenant_name: str
    email: str
    display_name: str = ""
    roles: list[str] = Field(default_factory=lambda: ["engineer"])
    clearance_tier: str = "internal"
    compartments: list[str] = Field(default_factory=list)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    tenant_id: str


class TenantCreate(BaseModel):
    name: str
    tenant_type: str = "organization"


class TenantOut(BaseModel):
    id: str
    name: str
    tenant_type: str


class OrgCreate(BaseModel):
    tenant_id: str
    name: str


class OrgOut(BaseModel):
    id: str
    tenant_id: str
    name: str
    owner_user_id: str
    board_scope_mode: str


class TeamCreate(BaseModel):
    org_id: str
    name: str


class TeamOut(BaseModel):
    id: str
    org_id: str
    name: str


class ProjectCreate(BaseModel):
    team_id: str
    code: str
    name: str
    ingress_mode: str = "zero_trust"
    visibility_mode: str = "scoped"


class ProjectOut(BaseModel):
    id: str
    team_id: str
    code: str
    name: str
    ingress_mode: str
    visibility_mode: str


class SeatCreate(BaseModel):
    project_id: str
    user_id: str
    role: str
    rank: str = "member"
    position: str = ""
    group_name: str = ""
    clearance_tier: str = "internal"
    compartments: list[str] = Field(default_factory=list)
    status: str = "active"


class SeatOut(BaseModel):
    id: str
    project_id: str
    user_id: str
    role: str
    rank: str
    position: str
    group_name: str
    clearance_tier: str
    compartments: list[str]
    status: str


class ClearanceEvaluateRequest(BaseModel):
    action: str
    required_clearance: str = "internal"
    required_compartments: list[str] = Field(default_factory=list)
    high_risk: bool = False


class AuthorizationDecisionOut(BaseModel):
    decision: str
    reason_codes: list[str]


class MessageCreate(BaseModel):
    project_id: str
    title: str
    body: str
    reviewer_user_id: str | None = None
    parent_message_id: str | None = None


class MessageUpdate(BaseModel):
    title: str | None = None
    body: str | None = None
    review_notes: str | None = None


class MessageTransition(BaseModel):
    target_state: str
    review_notes: str = ""


class MessageOut(BaseModel):
    id: str
    project_id: str
    author_user_id: str
    reviewer_user_id: str | None
    title: str
    body: str
    state: str
    revision: int
    parent_message_id: str | None
    review_notes: str


class ApprovalCreate(BaseModel):
    project_id: str
    message_id: str
    decision: str = "approved"
    rationale: str = ""


class ApprovalOut(BaseModel):
    id: str
    project_id: str
    message_id: str
    reviewer_user_id: str
    decision: str
    rationale: str


class DispatchCreate(BaseModel):
    project_id: str
    message_id: str | None = None
    target_scope: Literal["group", "worker", "project", "team", "org"] = "group"
    target_value: str = "all"
    provider: str = "openai_codex"
    model: str
    payload: dict[str, Any] = Field(default_factory=dict)


class DispatchOut(BaseModel):
    id: str
    project_id: str
    message_id: str | None
    target_scope: str
    target_value: str
    provider: str
    model: str
    request_hash: str
    state: str


class DispatchExecuteRequest(BaseModel):
    force: bool = False


class DispatchExecutionOut(BaseModel):
    id: str
    dispatch_request_id: str
    started_by_user_id: str
    status: str
    provider_reference: str
    output_text: str
    error_text: str
    started_at: str | None
    completed_at: str | None


class DispatchEventOut(BaseModel):
    id: str
    execution_id: str
    dispatch_request_id: str
    sequence: int
    event_type: str
    event_payload: dict[str, Any]
    created_at: str | None


class DispatchResultOut(BaseModel):
    id: str
    dispatch_request_id: str
    worker_id: str
    status: str
    provider_reference: str
    output: str
    error: str


class PolicyDecideRequest(BaseModel):
    project_id: str
    action: str
    resource_type: str
    resource_id: str
    payload: dict = Field(default_factory=dict)
    required_clearance: str = "internal"
    required_compartments: list[str] = Field(default_factory=list)
    high_risk: bool = False
    destination_scope: str = "project"


class PolicyDecideResponse(BaseModel):
    decision: str
    reason_codes: list[str]
    request_hash: str
    policy_token: str | None = None


class PolicyValidateRequest(BaseModel):
    token: str
    request_hash: str
    destination_scope: str


class ProviderCredentialUpsert(BaseModel):
    tenant_id: str
    provider: str
    auth_mode: Literal["managed_secret", "oauth_supported"]
    configured: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExtensionCreate(BaseModel):
    tenant_id: str
    name: str
    version: str
    scopes: list[str] = Field(default_factory=list)
    signature: str


class ExtensionOut(BaseModel):
    id: str
    tenant_id: str
    name: str
    version: str
    scopes: list[str]
    status: str


class WorkerRegister(BaseModel):
    project_id: str
    name: str
    role: str
    host: str = ""
    device_id: str
    capabilities: list[str] = Field(default_factory=list)


class WorkerOut(BaseModel):
    id: str
    project_id: str
    name: str
    role: str
    host: str
    device_id: str
    status: str
    capabilities: list[str]


class WorkerActionRequest(BaseModel):
    action: str
    notes: str = ""


class WorkerActionOut(BaseModel):
    id: str
    worker_id: str
    action: str
    status: str
    notes: str
    created_at: str | None


class WorkerActionAckRequest(BaseModel):
    status: Literal["in_progress", "completed", "failed", "deferred"] = "completed"
    result: dict[str, Any] = Field(default_factory=dict)
    error: str = ""
    notes: str = ""


class WorkerHeartbeatRequest(BaseModel):
    gateway_url: str
    gateway_candidates: list[str] = Field(default_factory=list)
    gateway_rtt_ms: int = Field(default=-1, ge=-1)
    keepalive_interval_seconds: int = Field(default=30, ge=5, le=300)
    keepalive_miss_threshold: int = Field(default=3, ge=1, le=20)
    connectivity_state: Literal["online", "degraded", "down"] = "online"


class WorkerProbeRequest(BaseModel):
    reachable: bool
    gateway_url: str = ""
    gateway_rtt_ms: int = Field(default=-1, ge=-1)
    reason: str = ""


class WorkerConnectivityOut(BaseModel):
    worker_id: str
    worker_name: str
    role: str
    status: str
    connectivity_state: str
    last_seen_at: str | None
    last_keepalive_at: str | None
    last_probe_at: str | None
    last_gateway_url: str
    gateway_rtt_ms: int
    reconnect_required: bool
    reconnect_targets: list[str]


class WorkerMonitorConfigUpsert(BaseModel):
    project_id: str
    enabled: bool = True
    loop_interval_seconds: int = Field(default=30, ge=5, le=3600)
    stale_after_seconds: int = Field(default=90, ge=10, le=86400)
    queue_throttle_seconds: int = Field(default=120, ge=0, le=86400)
    probe_action_enabled: bool = True
    reconnect_action_enabled: bool = True


class WorkerMonitorConfigOut(BaseModel):
    id: str
    project_id: str
    enabled: bool
    loop_interval_seconds: int
    stale_after_seconds: int
    queue_throttle_seconds: int
    probe_action_enabled: bool
    reconnect_action_enabled: bool
    last_run_at: str | None
    last_result: dict[str, Any]
    created_by_user_id: str


class WorkerMonitorRunRequest(BaseModel):
    project_id: str
    force: bool = False


class WorkerUpdateCampaignCreate(BaseModel):
    project_id: str
    name: str
    bundle_id: str | None = None
    target_selector: dict[str, Any] = Field(default_factory=dict)
    desired_version: str
    rollout_strategy: Literal["canary", "rolling", "blue_green", "all_at_once"] = "rolling"
    preflight_required: bool = True
    backup_required: bool = True
    canary_batch_size: int = Field(default=1, ge=1, le=100)
    max_allowed_failures: int = Field(default=0, ge=0, le=1000)
    auto_rollback_on_halt: bool = True


class WorkerUpdateCampaignStart(BaseModel):
    worker_ids: list[str] = Field(default_factory=list)
    policy_token: str


class WorkerUpdateCampaignRollback(BaseModel):
    reason: str = ""


class WorkerUpdateCampaignOut(BaseModel):
    id: str
    project_id: str
    name: str
    bundle_id: str | None
    target_selector: dict[str, Any]
    desired_version: str
    rollout_strategy: str
    preflight_required: bool
    backup_required: bool
    canary_batch_size: int
    max_allowed_failures: int
    auto_rollback_on_halt: bool
    halt_reason: str
    state: str
    created_by_user_id: str
    started_at: str | None
    completed_at: str | None
    rolled_back_at: str | None


class WorkerUpdateExecutionOut(BaseModel):
    id: str
    campaign_id: str
    worker_id: str
    state: str
    preflight_ok: bool
    backup_ref: str
    applied_version: str
    failure_reason: str
    rollback_state: str
    started_at: str | None
    completed_at: str | None


class WorkerUpdateBundleCreate(BaseModel):
    project_id: str
    name: str
    version: str
    digest: str
    signature: str
    signer: str = ""
    artifact_uri: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkerUpdateBundleOut(BaseModel):
    id: str
    project_id: str
    name: str
    version: str
    digest: str
    signature: str
    signer: str
    artifact_uri: str
    metadata: dict[str, Any]
    status: str
    created_by_user_id: str


class WorkerDiscoveryScanCreate(BaseModel):
    project_id: str
    network_scope: str = "local"
    candidate_hosts: list[str] = Field(default_factory=list)
    auto_enroll: bool = False
    notes: str = ""


class WorkerDiscoveryScanOut(BaseModel):
    id: str
    project_id: str
    initiated_by_user_id: str
    network_scope: str
    status: str
    findings: list[dict[str, Any]]
    notes: str
    started_at: str | None
    completed_at: str | None


class WorkerGroupCreate(BaseModel):
    project_id: str
    name: str
    routing_strategy: Literal["round_robin", "least_loaded", "priority", "sticky"] = "round_robin"
    selection_mode: Literal["explicit", "role", "capability"] = "explicit"
    target_role: str = ""
    capability_tags: list[str] = Field(default_factory=list)
    worker_ids: list[str] = Field(default_factory=list)
    failover_group_id: str | None = None


class WorkerGroupOut(BaseModel):
    id: str
    project_id: str
    name: str
    routing_strategy: str
    selection_mode: str
    target_role: str
    capability_tags: list[str]
    worker_ids: list[str]
    failover_group_id: str | None


class OrchestrationProfileCreate(BaseModel):
    project_id: str
    name: str
    routing_mode: Literal["individual", "group", "hybrid"] = "group"
    target_group_id: str | None = None
    failover_group_id: str | None = None
    quality_bar: str = "standard"
    max_parallel: int = Field(default=1, ge=1, le=50)
    retry_max_attempts: int = Field(default=0, ge=0, le=10)
    retry_backoff_seconds: int = Field(default=30, ge=0, le=3600)
    postback_required: bool = True
    visible_body_required: bool = True
    max_chunk_chars: int = Field(default=1800, ge=100, le=8000)
    owner_principal_id: str
    report_to: list[str] = Field(default_factory=list)
    escalation_to: list[str] = Field(default_factory=list)
    visibility_mode: Literal["private", "team", "board", "public-internal"] = "team"
    status: str = "active"


class OrchestrationProfileOut(BaseModel):
    id: str
    project_id: str
    name: str
    routing_mode: str
    target_group_id: str | None
    failover_group_id: str | None
    quality_bar: str
    max_parallel: int
    retry_max_attempts: int
    retry_backoff_seconds: int
    postback_required: bool
    visible_body_required: bool
    max_chunk_chars: int
    owner_principal_id: str
    report_to: list[str]
    escalation_to: list[str]
    visibility_mode: str
    status: str


class JobTemplateCreate(BaseModel):
    project_id: str
    name: str
    version: str = "v1"
    objective: str = ""
    required_inputs: list[str] = Field(default_factory=list)
    constraints: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    default_profile_id: str | None = None
    report_to: list[str] = Field(default_factory=list)
    escalation_to: list[str] = Field(default_factory=list)
    visibility_mode: Literal["private", "team", "board", "public-internal"] = "team"
    status: str = "active"


class JobTemplateOut(BaseModel):
    id: str
    project_id: str
    name: str
    version: str
    objective: str
    required_inputs: list[str]
    constraints: dict[str, Any]
    output_schema: dict[str, Any]
    default_profile_id: str | None
    report_to: list[str]
    escalation_to: list[str]
    visibility_mode: str
    status: str


class JobRunCreate(BaseModel):
    project_id: str
    template_id: str | None = None
    profile_id: str | None = None
    owner_principal_id: str
    report_to: list[str] = Field(default_factory=list)
    escalation_to: list[str] = Field(default_factory=list)
    visibility_mode: Literal["private", "team", "board", "public-internal"] = "team"
    routing_mode: Literal["individual", "group", "hybrid"] = "group"
    target_group_id: str | None = None
    target_worker_id: str | None = None
    target_role: str = ""
    objective: str = ""
    input_payload: dict[str, Any] = Field(default_factory=dict)


class JobRunStateTransition(BaseModel):
    target_state: Literal[
        "queued",
        "dispatching",
        "running",
        "postback_pending",
        "delivered",
        "closed",
        "retrying",
        "failed",
        "failed_visibility",
        "escalated",
    ]
    state_reason: str = ""


class JobRunOut(BaseModel):
    id: str
    project_id: str
    template_id: str | None
    profile_id: str | None
    owner_principal_id: str
    report_to: list[str]
    escalation_to: list[str]
    visibility_mode: str
    routing_mode: str
    target_group_id: str | None
    target_worker_id: str | None
    target_role: str
    objective: str
    input_payload: dict[str, Any]
    state: str
    attempt_count: int
    artifact_summary: list[dict[str, Any]]
    last_error: str
    state_reason: str


class JobDeliveryCreate(BaseModel):
    recipient: str
    channel: str = "ordlctl_chat"
    status: Literal["delivered", "failed", "queued"] = "delivered"
    detail: dict[str, Any] = Field(default_factory=dict)


class JobDeliveryOut(BaseModel):
    id: str
    job_run_id: str
    project_id: str
    recipient: str
    channel: str
    status: str
    detail: dict[str, Any]
    delivered_at: str | None


class ProgramCreate(BaseModel):
    org_id: str
    team_id: str | None = None
    code: str
    name: str
    status: str = "active"
    summary: str = ""


class ProgramOut(BaseModel):
    id: str
    org_id: str
    team_id: str | None
    code: str
    name: str
    status: str
    summary: str
    owner_user_id: str


class ProgramMilestoneCreate(BaseModel):
    title: str
    target_at: datetime | None = None
    status: str = "planned"
    owner_user_id: str | None = None
    notes: str = ""


class ProgramMilestoneOut(BaseModel):
    id: str
    program_id: str
    title: str
    target_at: str | None
    status: str
    owner_user_id: str | None
    notes: str


class ProgramRiskCreate(BaseModel):
    title: str
    severity: Literal["low", "medium", "high", "critical"] = "medium"
    probability: Literal["low", "medium", "high"] = "medium"
    impact: Literal["low", "medium", "high"] = "medium"
    status: str = "open"
    owner_user_id: str | None = None
    mitigation: str = ""


class ProgramRiskOut(BaseModel):
    id: str
    program_id: str
    title: str
    severity: str
    probability: str
    impact: str
    status: str
    owner_user_id: str | None
    mitigation: str


class ChangeRequestCreate(BaseModel):
    title: str
    description: str = ""
    priority: Literal["low", "medium", "high", "critical"] = "medium"
    reviewer_user_id: str | None = None


class ChangeRequestDecision(BaseModel):
    status: Literal["approved", "rejected", "needs_rework"]
    decision_notes: str = ""


class ChangeRequestOut(BaseModel):
    id: str
    project_id: str
    requested_by_user_id: str
    reviewer_user_id: str | None
    title: str
    description: str
    priority: str
    status: str
    decision_notes: str


class ProtocolStandardCreate(BaseModel):
    code: str
    name: str
    domain: str = "general"
    steward: str = ""
    home_url: str = ""
    status: Literal["adopted", "draft", "deprecated"] = "adopted"
    adoption_tier: Literal["core", "recommended", "experimental"] = "recommended"
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    source_urls: list[str] = Field(default_factory=list)


class ProtocolStandardOut(BaseModel):
    id: str
    tenant_id: str
    code: str
    name: str
    domain: str
    steward: str
    home_url: str
    status: str
    adoption_tier: str
    description: str
    tags: list[str]
    source_urls: list[str]
    latest_version: str | None


class ProtocolStandardVersionCreate(BaseModel):
    version: str
    lifecycle_status: Literal["adopted", "draft", "deprecated"] = "adopted"
    specification_url: str = ""
    schema_uri: str = ""
    required_by_default: bool = False
    change_notes: str = ""
    compatibility: dict[str, Any] = Field(default_factory=dict)


class ProtocolStandardVersionOut(BaseModel):
    id: str
    standard_id: str
    version: str
    lifecycle_status: str
    specification_url: str
    schema_uri: str
    required_by_default: bool
    change_notes: str
    compatibility: dict[str, Any]
    released_at: str | None
    deprecated_at: str | None


class ProtocolCompatibilityItemOut(BaseModel):
    standard_id: str
    code: str
    name: str
    adoption_tier: str
    latest_version: str | None
    required: bool
    conformance_status: str
    last_run_id: str | None
    compatible: bool
    reasons: list[str]


class ProtocolCompatibilityOut(BaseModel):
    project_id: str
    compatible: bool
    items: list[ProtocolCompatibilityItemOut]


class ProtocolValidateRequirement(BaseModel):
    standard_code: str
    minimum_version: str | None = None
    required_tier: Literal["core", "recommended", "experimental"] | None = None


class ProtocolValidateRequest(BaseModel):
    project_id: str
    requirements: list[ProtocolValidateRequirement] = Field(default_factory=list)


class ProtocolValidateItemOut(BaseModel):
    standard_code: str
    minimum_version: str | None
    evaluated_version: str | None
    result: Literal["pass", "fail"]
    reasons: list[str]


class ProtocolValidateOut(BaseModel):
    project_id: str
    ok: bool
    items: list[ProtocolValidateItemOut]


class ProtocolConformanceRunCreate(BaseModel):
    project_id: str
    standard_id: str | None = None
    standard_code: str | None = None
    standard_version_id: str | None = None
    standard_version: str | None = None
    suite_name: str = "default"
    target_scope: str = "project"
    status: Literal["pass", "warn", "fail"] = "pass"
    score: int = Field(default=100, ge=0, le=100)
    findings: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    run_metadata: dict[str, Any] = Field(default_factory=dict)


class ProtocolConformanceRunOut(BaseModel):
    id: str
    project_id: str
    standard_id: str
    standard_version_id: str | None
    suite_name: str
    target_scope: str
    status: str
    score: int
    findings: list[str]
    evidence_refs: list[str]
    run_metadata: dict[str, Any]
    created_at: str


class ProtocolBootstrapRequest(BaseModel):
    overwrite_existing: bool = False
    include_versions: bool = True


class ProtocolBootstrapOut(BaseModel):
    created_standards: list[str]
    existing_standards: list[str]
    created_versions: list[str]


class DigestionRunRequest(BaseModel):
    project_id: str
    repo_root: str
    chunk_size: int = Field(default=200, ge=1, le=2000)
