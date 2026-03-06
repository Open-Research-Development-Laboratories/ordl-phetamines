from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def uuid_str() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    tenant_type: Mapped[str] = mapped_column(String(32), default="organization")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), index=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(200), default="")
    roles_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Org(Base):
    __tablename__ = "orgs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    owner_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    board_scope_mode: Mapped[str] = mapped_column(String(32), default="scoped")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("orgs.id"), index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (UniqueConstraint("team_id", "code", name="uq_project_team_code"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    team_id: Mapped[str] = mapped_column(String(36), ForeignKey("teams.id"), index=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    ingress_mode: Mapped[str] = mapped_column(String(32), default="zero_trust")
    visibility_mode: Mapped[str] = mapped_column(String(32), default="scoped")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SeatAssignment(Base):
    __tablename__ = "seat_assignments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    role: Mapped[str] = mapped_column(String(64), nullable=False)
    rank: Mapped[str] = mapped_column(String(64), default="member")
    position: Mapped[str] = mapped_column(String(128), default="")
    group_name: Mapped[str] = mapped_column(String(128), default="")
    clearance_tier: Mapped[str] = mapped_column(String(32), default="internal")
    compartments_json: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(String(32), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class WorkerInstance(Base):
    __tablename__ = "worker_instances"
    __table_args__ = (UniqueConstraint("project_id", "device_id", name="uq_worker_project_device"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str] = mapped_column(String(64), nullable=False)
    host: Mapped[str] = mapped_column(String(200), default="")
    device_id: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="online")
    capabilities_json: Mapped[str] = mapped_column(Text, default="[]")
    connectivity_state: Mapped[str] = mapped_column(String(32), default="unknown")
    last_gateway_url: Mapped[str] = mapped_column(String(512), default="")
    gateway_candidates_json: Mapped[str] = mapped_column(Text, default="[]")
    gateway_rtt_ms: Mapped[int] = mapped_column(Integer, default=-1)
    keepalive_interval_seconds: Mapped[int] = mapped_column(Integer, default=30)
    keepalive_miss_threshold: Mapped[int] = mapped_column(Integer, default=3)
    last_keepalive_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_probe_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class WorkerAction(Base):
    __tablename__ = "worker_actions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    worker_id: Mapped[str] = mapped_column(String(36), ForeignKey("worker_instances.id"), index=True)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    requested_by_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(32), default="queued")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class WorkerUpdateBundle(Base):
    __tablename__ = "worker_update_bundles"
    __table_args__ = (UniqueConstraint("project_id", "name", "version", name="uq_worker_update_bundle_project_name_version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    digest: Mapped[str] = mapped_column(String(128), nullable=False)
    signature: Mapped[str] = mapped_column(String(256), nullable=False)
    signer: Mapped[str] = mapped_column(String(200), default="")
    artifact_uri: Mapped[str] = mapped_column(String(1024), default="")
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(32), default="active")
    created_by_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class WorkerUpdateCampaign(Base):
    __tablename__ = "worker_update_campaigns"
    __table_args__ = (UniqueConstraint("project_id", "name", name="uq_worker_update_campaign_project_name"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    bundle_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("worker_update_bundles.id"), nullable=True, index=True)
    target_selector_json: Mapped[str] = mapped_column(Text, default="{}")
    desired_version: Mapped[str] = mapped_column(String(64), nullable=False)
    rollout_strategy: Mapped[str] = mapped_column(String(32), default="rolling")
    preflight_required: Mapped[int] = mapped_column(Integer, default=1)
    backup_required: Mapped[int] = mapped_column(Integer, default=1)
    canary_batch_size: Mapped[int] = mapped_column(Integer, default=1)
    max_allowed_failures: Mapped[int] = mapped_column(Integer, default=0)
    auto_rollback_on_halt: Mapped[int] = mapped_column(Integer, default=1)
    halt_reason: Mapped[str] = mapped_column(Text, default="")
    state: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    created_by_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rolled_back_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class WorkerUpdateExecution(Base):
    __tablename__ = "worker_update_executions"
    __table_args__ = (UniqueConstraint("campaign_id", "worker_id", name="uq_worker_update_exec_campaign_worker"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    campaign_id: Mapped[str] = mapped_column(String(36), ForeignKey("worker_update_campaigns.id"), index=True)
    worker_id: Mapped[str] = mapped_column(String(36), ForeignKey("worker_instances.id"), index=True)
    state: Mapped[str] = mapped_column(String(32), default="queued")
    preflight_ok: Mapped[int] = mapped_column(Integer, default=0)
    backup_ref: Mapped[str] = mapped_column(String(255), default="")
    applied_version: Mapped[str] = mapped_column(String(64), default="")
    failure_reason: Mapped[str] = mapped_column(Text, default="")
    rollback_state: Mapped[str] = mapped_column(String(32), default="not_requested")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class WorkerDiscoveryScan(Base):
    __tablename__ = "worker_discovery_scans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), index=True)
    initiated_by_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    network_scope: Mapped[str] = mapped_column(String(255), default="local")
    status: Mapped[str] = mapped_column(String(32), default="completed")
    findings_json: Mapped[str] = mapped_column(Text, default="[]")
    notes: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class WorkerConnectivityMonitor(Base):
    __tablename__ = "worker_connectivity_monitors"
    __table_args__ = (UniqueConstraint("project_id", name="uq_worker_monitor_project"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), index=True)
    enabled: Mapped[int] = mapped_column(Integer, default=1)
    loop_interval_seconds: Mapped[int] = mapped_column(Integer, default=30)
    stale_after_seconds: Mapped[int] = mapped_column(Integer, default=90)
    queue_throttle_seconds: Mapped[int] = mapped_column(Integer, default=120)
    probe_action_enabled: Mapped[int] = mapped_column(Integer, default=1)
    reconnect_action_enabled: Mapped[int] = mapped_column(Integer, default=1)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_result_json: Mapped[str] = mapped_column(Text, default="{}")
    created_by_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class WorkerGroup(Base):
    __tablename__ = "worker_groups"
    __table_args__ = (UniqueConstraint("project_id", "name", name="uq_worker_group_project_name"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    routing_strategy: Mapped[str] = mapped_column(String(32), default="round_robin")
    selection_mode: Mapped[str] = mapped_column(String(32), default="explicit")
    target_role: Mapped[str] = mapped_column(String(64), default="")
    capability_tags_json: Mapped[str] = mapped_column(Text, default="[]")
    worker_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    failover_group_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("worker_groups.id"), nullable=True)
    created_by_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class OrchestrationProfile(Base):
    __tablename__ = "orchestration_profiles"
    __table_args__ = (UniqueConstraint("project_id", "name", name="uq_orchestration_profile_project_name"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    routing_mode: Mapped[str] = mapped_column(String(32), default="group")
    target_group_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("worker_groups.id"), nullable=True)
    failover_group_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("worker_groups.id"), nullable=True)
    quality_bar: Mapped[str] = mapped_column(String(32), default="standard")
    max_parallel: Mapped[int] = mapped_column(Integer, default=1)
    retry_max_attempts: Mapped[int] = mapped_column(Integer, default=0)
    retry_backoff_seconds: Mapped[int] = mapped_column(Integer, default=30)
    postback_required: Mapped[int] = mapped_column(Integer, default=1)
    visible_body_required: Mapped[int] = mapped_column(Integer, default=1)
    max_chunk_chars: Mapped[int] = mapped_column(Integer, default=1800)
    owner_principal_id: Mapped[str] = mapped_column(String(128), nullable=False)
    report_to_json: Mapped[str] = mapped_column(Text, default="[]")
    escalation_to_json: Mapped[str] = mapped_column(Text, default="[]")
    visibility_mode: Mapped[str] = mapped_column(String(32), default="team")
    status: Mapped[str] = mapped_column(String(32), default="active")
    created_by_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class JobTemplate(Base):
    __tablename__ = "job_templates"
    __table_args__ = (UniqueConstraint("project_id", "name", "version", name="uq_job_template_project_name_version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    version: Mapped[str] = mapped_column(String(64), default="v1")
    objective: Mapped[str] = mapped_column(Text, default="")
    required_inputs_json: Mapped[str] = mapped_column(Text, default="[]")
    constraints_json: Mapped[str] = mapped_column(Text, default="{}")
    output_schema_json: Mapped[str] = mapped_column(Text, default="{}")
    default_profile_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("orchestration_profiles.id"), nullable=True)
    report_to_json: Mapped[str] = mapped_column(Text, default="[]")
    escalation_to_json: Mapped[str] = mapped_column(Text, default="[]")
    visibility_mode: Mapped[str] = mapped_column(String(32), default="team")
    status: Mapped[str] = mapped_column(String(32), default="active")
    created_by_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class JobRun(Base):
    __tablename__ = "job_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), index=True)
    template_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("job_templates.id"), nullable=True, index=True)
    profile_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("orchestration_profiles.id"), nullable=True, index=True)
    owner_principal_id: Mapped[str] = mapped_column(String(128), nullable=False)
    report_to_json: Mapped[str] = mapped_column(Text, default="[]")
    escalation_to_json: Mapped[str] = mapped_column(Text, default="[]")
    visibility_mode: Mapped[str] = mapped_column(String(32), default="team")
    routing_mode: Mapped[str] = mapped_column(String(32), default="group")
    target_group_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("worker_groups.id"), nullable=True)
    target_worker_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("worker_instances.id"), nullable=True)
    target_role: Mapped[str] = mapped_column(String(64), default="")
    objective: Mapped[str] = mapped_column(Text, default="")
    input_payload_json: Mapped[str] = mapped_column(Text, default="{}")
    state: Mapped[str] = mapped_column(String(32), default="created", index=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    artifact_summary_json: Mapped[str] = mapped_column(Text, default="[]")
    last_error: Mapped[str] = mapped_column(Text, default="")
    state_reason: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class JobDeliveryReceipt(Base):
    __tablename__ = "job_delivery_receipts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    job_run_id: Mapped[str] = mapped_column(String(36), ForeignKey("job_runs.id"), index=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), index=True)
    recipient: Mapped[str] = mapped_column(String(255), nullable=False)
    channel: Mapped[str] = mapped_column(String(64), default="ordlctl_chat")
    status: Mapped[str] = mapped_column(String(32), default="delivered")
    detail_json: Mapped[str] = mapped_column(Text, default="{}")
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CollabMessage(Base):
    __tablename__ = "collab_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), index=True)
    author_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    reviewer_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    body: Mapped[str] = mapped_column(Text, default="")
    state: Mapped[str] = mapped_column(String(32), default="draft")
    revision: Mapped[int] = mapped_column(Integer, default=1)
    parent_message_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("collab_messages.id"), nullable=True)
    review_notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Approval(Base):
    __tablename__ = "approvals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), index=True)
    message_id: Mapped[str] = mapped_column(String(36), ForeignKey("collab_messages.id"), index=True)
    reviewer_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    decision: Mapped[str] = mapped_column(String(32), default="approved")
    rationale: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class DispatchRequest(Base):
    __tablename__ = "dispatch_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), index=True)
    requested_by_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    message_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("collab_messages.id"), nullable=True)
    target_scope: Mapped[str] = mapped_column(String(32), default="group")
    target_value: Mapped[str] = mapped_column(String(255), default="all")
    provider: Mapped[str] = mapped_column(String(32), default="openai_codex")
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    request_hash: Mapped[str] = mapped_column(String(64), index=True)
    state: Mapped[str] = mapped_column(String(32), default="queued")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class DispatchResult(Base):
    __tablename__ = "dispatch_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    dispatch_request_id: Mapped[str] = mapped_column(String(36), ForeignKey("dispatch_requests.id"), index=True)
    worker_id: Mapped[str] = mapped_column(String(36), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="accepted")
    provider_reference: Mapped[str] = mapped_column(String(255), default="")
    output: Mapped[str] = mapped_column(Text, default="")
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PolicyDecision(Base):
    __tablename__ = "policy_decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(64), nullable=False)
    decision: Mapped[str] = mapped_column(String(16), nullable=False)
    reason_codes_json: Mapped[str] = mapped_column(Text, default="[]")
    request_hash: Mapped[str] = mapped_column(String(64), index=True)
    token_nonce: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Extension(Base):
    __tablename__ = "extensions"
    __table_args__ = (UniqueConstraint("tenant_id", "name", "version", name="uq_extension_version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    signature: Mapped[str] = mapped_column(String(256), nullable=False)
    scopes_json: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(String(32), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ProviderCredential(Base):
    __tablename__ = "provider_credentials"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), index=True)
    provider: Mapped[str] = mapped_column(String(64), index=True)
    auth_mode: Mapped[str] = mapped_column(String(64), default="managed_secret")
    configured: Mapped[str] = mapped_column(String(8), default="false")
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ProtocolStandard(Base):
    __tablename__ = "protocol_standards"
    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_protocol_standard_tenant_code"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), index=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    domain: Mapped[str] = mapped_column(String(64), default="general")
    steward: Mapped[str] = mapped_column(String(200), default="")
    home_url: Mapped[str] = mapped_column(String(512), default="")
    status: Mapped[str] = mapped_column(String(32), default="adopted")
    adoption_tier: Mapped[str] = mapped_column(String(32), default="recommended")
    description: Mapped[str] = mapped_column(Text, default="")
    tags_json: Mapped[str] = mapped_column(Text, default="[]")
    source_urls_json: Mapped[str] = mapped_column(Text, default="[]")
    created_by_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ProtocolStandardVersion(Base):
    __tablename__ = "protocol_standard_versions"
    __table_args__ = (UniqueConstraint("standard_id", "version", name="uq_protocol_standard_version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    standard_id: Mapped[str] = mapped_column(String(36), ForeignKey("protocol_standards.id"), index=True)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    lifecycle_status: Mapped[str] = mapped_column(String(32), default="adopted")
    specification_url: Mapped[str] = mapped_column(String(512), default="")
    schema_uri: Mapped[str] = mapped_column(String(512), default="")
    required_by_default: Mapped[int] = mapped_column(Integer, default=0)
    change_notes: Mapped[str] = mapped_column(Text, default="")
    compatibility_json: Mapped[str] = mapped_column(Text, default="{}")
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deprecated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ProtocolConformanceRun(Base):
    __tablename__ = "protocol_conformance_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), index=True)
    standard_id: Mapped[str] = mapped_column(String(36), ForeignKey("protocol_standards.id"), index=True)
    standard_version_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("protocol_standard_versions.id"), nullable=True, index=True
    )
    suite_name: Mapped[str] = mapped_column(String(200), default="default")
    target_scope: Mapped[str] = mapped_column(String(64), default="project")
    status: Mapped[str] = mapped_column(String(16), default="pass")
    score: Mapped[int] = mapped_column(Integer, default=100)
    findings_json: Mapped[str] = mapped_column(Text, default="[]")
    evidence_refs_json: Mapped[str] = mapped_column(Text, default="[]")
    run_metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    executed_by_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), index=True)
    project_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("projects.id"), index=True, nullable=True
    )
    event_index: Mapped[int] = mapped_column(Integer, default=0, index=True)
    event_type: Mapped[str] = mapped_column(String(128), index=True)
    actor_type: Mapped[str] = mapped_column(String(32), default="", index=True)
    actor_id: Mapped[str] = mapped_column(String(128), default="", index=True)
    actor_role: Mapped[str] = mapped_column(String(128), default="")
    actor_rank: Mapped[str] = mapped_column(String(64), default="")
    actor_position: Mapped[str] = mapped_column(String(128), default="")
    source: Mapped[str] = mapped_column(String(64), default="api", index=True)
    classification: Mapped[str] = mapped_column(String(32), default="operational", index=True)
    severity: Mapped[str] = mapped_column(String(16), default="info")
    trace_id: Mapped[str] = mapped_column(String(64), default="", index=True)
    run_id: Mapped[str] = mapped_column(String(64), default="", index=True)
    session_id: Mapped[str] = mapped_column(String(64), default="", index=True)
    actor_json: Mapped[str] = mapped_column(Text, default="{}")
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    resource_json: Mapped[str] = mapped_column(Text, default="{}")
    context_json: Mapped[str] = mapped_column(Text, default="{}")
    prev_hash: Mapped[str] = mapped_column(String(64), default="")
    event_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    hash_version: Mapped[str] = mapped_column(String(16), default="v2")
    hash_timestamp: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CodeDigestRun(Base):
    __tablename__ = "code_digest_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), index=True)
    repo_root: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="running")
    total_files: Mapped[int] = mapped_column(Integer, default=0)
    total_lines: Mapped[int] = mapped_column(Integer, default=0)
    reviewed_lines: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CodeDigestFile(Base):
    __tablename__ = "code_digest_files"
    __table_args__ = (UniqueConstraint("run_id", "file_path", name="uq_digest_file_run_path"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("code_digest_runs.id"), index=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), index=True)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    total_lines: Mapped[int] = mapped_column(Integer, default=0)
    reviewed_lines: Mapped[int] = mapped_column(Integer, default=0)
    last_chunk_hash: Mapped[str] = mapped_column(String(64), default="")


class CodeDigestChunk(Base):
    __tablename__ = "code_digest_chunks"
    __table_args__ = (UniqueConstraint("file_id", "chunk_index", name="uq_digest_chunk_file_idx"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    file_id: Mapped[str] = mapped_column(String(36), ForeignKey("code_digest_files.id"), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    start_line: Mapped[int] = mapped_column(Integer, nullable=False)
    end_line: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class Program(Base):
    __tablename__ = "programs"
    __table_args__ = (UniqueConstraint("org_id", "code", name="uq_program_org_code"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("orgs.id"), index=True)
    team_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("teams.id"), nullable=True, index=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active")
    summary: Mapped[str] = mapped_column(Text, default="")
    owner_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ProgramMilestone(Base):
    __tablename__ = "program_milestones"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    program_id: Mapped[str] = mapped_column(String(36), ForeignKey("programs.id"), index=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    target_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="planned")
    owner_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ProgramRisk(Base):
    __tablename__ = "program_risks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    program_id: Mapped[str] = mapped_column(String(36), ForeignKey("programs.id"), index=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), default="medium")
    probability: Mapped[str] = mapped_column(String(16), default="medium")
    impact: Mapped[str] = mapped_column(String(16), default="medium")
    status: Mapped[str] = mapped_column(String(32), default="open")
    owner_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    mitigation: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ChangeRequest(Base):
    __tablename__ = "change_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), index=True)
    requested_by_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    reviewer_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    priority: Mapped[str] = mapped_column(String(16), default="medium")
    status: Mapped[str] = mapped_column(String(32), default="submitted")
    decision_notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
