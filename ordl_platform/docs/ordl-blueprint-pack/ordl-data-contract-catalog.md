# ORDL Data Contract Catalog

This file defines the core data objects, required fields, and key relationships for the ORDL platform.

It is the schema-level reference for backend models, API DTOs, database migrations, and data governance.

## 1) Modeling rules

- All top-level objects must be tenant-scoped unless explicitly global.
- Every mutable object must include:
  - `created_at`
  - `updated_at`
  - `created_by`
  - `updated_by`
- Every security-sensitive action must emit an `AuditEvent`.
- IDs use UUIDv7 or ULID where supported.

## 2) Identity and governance objects

### 2.1 Tenant

- `tenant_id`
- `name`
- `slug`
- `status`
- `compliance_profile`
- `data_residency_policy_id`
- `billing_account_id`

### 2.2 Organization

- `org_id`
- `tenant_id`
- `name`
- `entity_type` (solo, team, business, organization, enterprise)
- `jurisdiction`
- `owner_user_id`
- `board_policy_id`

### 2.3 Team

- `team_id`
- `org_id`
- `name`
- `purpose`
- `default_clearance_tier`

### 2.4 Project

- `project_id`
- `org_id`
- `team_id`
- `name`
- `code`
- `status`
- `risk_level`
- `environment_profile`

### 2.5 SeatAssignment

- `seat_id`
- `project_id`
- `user_id`
- `role`
- `rank`
- `position`
- `group_name`
- `clearance_tier`
- `compartment_tags`
- `seat_status`

### 2.6 AuthorizationDecision

- `decision_id`
- `tenant_id`
- `project_id`
- `user_id`
- `action`
- `resource_type`
- `resource_id`
- `decision` (allow, deny, hold)
- `reason_codes`
- `policy_version`
- `evaluated_at`

### 2.7 PolicyToken

- `policy_token_id`
- `tenant_id`
- `project_id`
- `decision_id`
- `request_hash`
- `destination_scope`
- `issued_at`
- `expires_at`
- `nonce`
- `signature`

## 3) Fleet and runtime objects

### 3.1 Gateway

- `gateway_id`
- `tenant_id`
- `region`
- `zone`
- `host`
- `status`
- `priority`
- `maintenance_mode`
- `last_heartbeat_at`

### 3.2 Node

- `node_id`
- `tenant_id`
- `gateway_id`
- `hostname`
- `ip`
- `platform`
- `node_role`
- `lifecycle_state`
- `last_known_gateway_id`
- `connectivity_score`

### 3.3 NodeCapability

- `capability_id`
- `node_id`
- `cpu_cores`
- `memory_gb`
- `gpu_count`
- `gpu_model`
- `disk_gb`
- `network_class`
- `supported_runtimes`

### 3.4 NodeHeartbeat

- `heartbeat_id`
- `node_id`
- `gateway_id`
- `sequence`
- `status`
- `latency_ms`
- `queue_depth`
- `received_at`

### 3.5 NodeProbe

- `probe_id`
- `node_id`
- `probe_type`
- `result`
- `details`
- `started_at`
- `finished_at`

### 3.6 FleetJob

- `job_id`
- `tenant_id`
- `project_id`
- `job_type`
- `target_scope`
- `status`
- `requested_by`
- `started_at`
- `finished_at`
- `result_summary`

### 3.7 ReconnectPolicy

- `policy_id`
- `tenant_id`
- `project_id`
- `sticky_last_gateway`
- `max_retries_per_gateway`
- `retry_backoff_profile`
- `gateway_fallback_order`
- `probe_interval_seconds`

## 4) Model lifecycle objects

### 4.1 ModelArtifact

- `artifact_id`
- `tenant_id`
- `project_id`
- `model_name`
- `artifact_type` (base, finetune, quantized, distilled)
- `format`
- `storage_uri`
- `digest_sha256`
- `signature`
- `status`

### 4.2 ModelVersion

- `model_version_id`
- `artifact_id`
- `version`
- `parent_version_id`
- `release_channel`
- `compatibility_tags`
- `is_deprecated`

### 4.3 Dataset

- `dataset_id`
- `tenant_id`
- `project_id`
- `name`
- `version`
- `sensitivity_class`
- `residency_zone`
- `retention_policy_id`
- `lineage_ref`

### 4.4 TrainingRun

- `training_run_id`
- `project_id`
- `model_version_id`
- `dataset_id`
- `compute_profile`
- `hyperparameters`
- `status`
- `metrics_summary`
- `checkpoint_refs`

### 4.5 EvaluationRun

- `evaluation_run_id`
- `project_id`
- `model_version_id`
- `suite_name`
- `status`
- `quality_score`
- `safety_score`
- `regression_score`
- `report_uri`

### 4.6 InferenceEndpoint

- `endpoint_id`
- `project_id`
- `model_version_id`
- `routing_policy`
- `autoscale_profile`
- `status`
- `latency_p95_ms`
- `throughput_rps`
- `error_rate`

## 5) Agent and dispatch objects

### 5.1 AgentTemplate

- `agent_template_id`
- `tenant_id`
- `project_id`
- `name`
- `role_class`
- `directive_pack_id`
- `default_tools`
- `default_provider_policy`

### 5.2 AgentRuntime

- `agent_runtime_id`
- `agent_template_id`
- `node_id`
- `runtime_state`
- `memory_profile`
- `token_budget`
- `tool_scope`

### 5.3 DispatchRequest

- `dispatch_request_id`
- `project_id`
- `requester_user_id`
- `dispatch_mode` (group, role, individual)
- `target_ids`
- `objective`
- `constraints`
- `policy_token_id`
- `status`

### 5.4 DispatchResult

- `dispatch_result_id`
- `dispatch_request_id`
- `worker_id`
- `summary`
- `risks`
- `actions`
- `open_questions`
- `posted_to_chat`
- `created_at`

### 5.5 WorkerReport

- `worker_report_id`
- `project_id`
- `worker_id`
- `report_type`
- `content_uri`
- `checksum`
- `status`

## 6) Collaboration and review objects

### 6.1 CollabMessage

- `message_id`
- `project_id`
- `thread_id`
- `author_user_id`
- `state` (draft, review, approved, dispatched, superseded)
- `title`
- `body`
- `current_revision_id`

### 6.2 MessageRevision

- `revision_id`
- `message_id`
- `revision_number`
- `editor_user_id`
- `body`
- `diff_from_previous`
- `created_at`

### 6.3 ReviewTask

- `review_task_id`
- `project_id`
- `message_id`
- `assigned_reviewer_id`
- `status`
- `sla_due_at`
- `decision`
- `rationale`

### 6.4 ApprovalDecision

- `approval_id`
- `project_id`
- `message_id`
- `approver_user_id`
- `decision`
- `rationale`
- `decision_at`

### 6.5 DeliveryRecord

- `delivery_id`
- `project_id`
- `message_id`
- `destination_type`
- `destination_id`
- `delivery_status`
- `retry_count`
- `last_error`

## 7) Security and compliance objects

### 7.1 AuditEvent

- `audit_event_id`
- `tenant_id`
- `project_id` (nullable for tenant/global events)
- `event_type`
- `actor_snapshot`
- `resource_snapshot`
- `payload`
- `trace_id`
- `run_id`
- `session_id`
- `severity`
- `event_index`
- `hash_prev`
- `hash_curr`
- `created_at`

### 7.2 ControlEvidence

- `evidence_id`
- `tenant_id`
- `project_id`
- `control_id`
- `evidence_type`
- `evidence_uri`
- `generated_at`
- `valid_until`
- `verification_status`

### 7.3 ConformanceRun

- `conformance_run_id`
- `tenant_id`
- `project_id`
- `standard_code`
- `standard_version`
- `suite_name`
- `result`
- `findings`
- `evidence_refs`

### 7.4 Incident

- `incident_id`
- `tenant_id`
- `project_id`
- `severity`
- `status`
- `summary`
- `opened_at`
- `resolved_at`
- `owner_user_id`
- `postmortem_uri`

## 8) Billing and commercial objects

### 8.1 Plan

- `plan_id`
- `name`
- `seat_limit`
- `feature_entitlements`
- `usage_pricing`

### 8.2 Subscription

- `subscription_id`
- `tenant_id`
- `plan_id`
- `status`
- `start_date`
- `renewal_date`

### 8.3 UsageRecord

- `usage_record_id`
- `tenant_id`
- `project_id`
- `provider_id`
- `resource_type`
- `quantity`
- `cost_amount`
- `timestamp`

### 8.4 CostCenter

- `cost_center_id`
- `tenant_id`
- `name`
- `owner_user_id`
- `budget_limit`

## 9) Relationship highlights

- One `Tenant` has many `Organizations`.
- One `Organization` has many `Teams`.
- One `Team` has many `Projects`.
- One `Project` has many `SeatAssignments`.
- One `Project` has many `Nodes`, `Gateways`, and `AgentRuntimes`.
- One `DispatchRequest` has many `DispatchResults`.
- One `CollabMessage` has many `MessageRevisions` and `ReviewTasks`.
- One `AuditEvent` links to actor/resource context and chain hashes.

## 10) Data protection requirements

- Encrypt all sensitive fields at rest.
- Store secret material only via secret backend references.
- Apply row-level security where feasible for tenant/project boundaries.
- Include retention policy hooks on all large artifacts and logs.
- Guarantee export and purge workflows with auditable proof records.

## 11) Migration and compatibility rules

- Additive schema changes must be backward compatible for one release window.
- Breaking changes require:
  - versioned API endpoint
  - migration script
  - rollback script
  - compatibility test coverage.
