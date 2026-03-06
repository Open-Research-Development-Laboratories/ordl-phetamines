# AI Control IDE Spec

Status: Draft v0.1  
Owner: ORDL Platform

## 1) Product Goal

Build a complete GUI-first environment for configuring and operating AI systems at every scope:

- self
- team
- business unit
- full organization

The platform must support end-to-end control of models, providers, protocols, tools, skills, MCP servers, agent teams, orchestration jobs, and reporting chains.

## 2) Platform Pillars

1. Governance Studio
- Org, team, seat, clearance, and policy controls.
- Explicit ownership and reporting lines.

2. Model and Provider Studio
- Provider connections and credential metadata.
- Model registry with versioned configs and safety/runtime limits.
- Model capability profiles (latency, cost, quality, context, tool support).

3. Skill, Tool, and MCP Studio
- Visual + code editors for skills, tools, and MCP server definitions.
- Versioned artifacts with signing, validation, and rollout controls.
- Dependency graph and compatibility checks.

4. Agent Team Studio
- Build individual agents and multi-agent teams.
- Group-based routing policies and failover plans.
- Role templates and delegation contracts.

5. Job Orchestration Studio
- Configure templates, schedules, retries, and postback rules.
- Route by group or individual worker.
- Require designated recipients for every run.

6. Protocol and Standards Studio
- Registry of standards (MCP, ACP, internal contracts, provider schemas).
- Compatibility matrix and migration tooling.
- ORDL-native protocol authoring, versioning, and conformance execution.

7. Evaluation and Reliability Studio
- Benchmark suites, regression gates, policy tests, and scenario replay.
- Visibility checks for delivery/postback quality.

8. Model Forge Studio
- Pipelines for generative model adaptation and deterministic model creation.
- Dataset registry, training runs, evaluation gates, and reproducibility metadata.

## 3) Core Entities (v2 scope)

- `OrgUnit`, `Team`, `SeatAssignment`, `ReportingLine`
- `ProviderAdapter`, `ModelConfig`, `ModelVersion`, `ModelCapabilityProfile`
- `SkillPackage`, `ToolPackage`, `McpServerPackage`
- `AgentDefinition`, `WorkerIdentity`, `WorkerGroup`, `OrchestrationProfile`
- `JobTemplate`, `JobRun`, `DeliveryReceipt`, `EscalationEvent`
- `ProtocolStandard`, `ProtocolVersion`, `CompatibilityRecord`
- `Dataset`, `TrainingRun`, `EvalSuite`, `EvalRun`

## 4) Mandatory Runtime Invariants

1. No execution without owner + designated recipients.
2. No provider dispatch without policy token and auth check.
3. No completion without visible report body in chat/report channel.
4. No unsigned artifact promotion (skills/tools/MCP packages).
5. No model/profile rollout without compatibility check against selected protocols.

## 5) GUI Surface Map

- `Workspace`: project explorer, entity graph, policy status
- `Orchestration`: groups, profiles, templates, runs, delivery status
- `Models`: registry, configs, rollout ring control, provider mappings
- `Skills/Tools/MCP`: builders, validators, release channels
- `Protocols`: standards registry and compatibility matrix
- `Forge`: dataset/training/eval pipeline management
- `Audit`: immutable event trail and escalation history

## 6) API Surface Expansion (Planned)

- `/model-registry/*`
- `/provider-adapters/*`
- `/skills/*`, `/tools/*`, `/mcp-servers/*`
- `/agent-definitions/*`, `/worker-groups/*`, `/orchestration/profiles/*`
- `/jobs/templates/*`, `/jobs/runs/*`, `/jobs/delivery/*`
- `/protocols/standards/*`, `/protocols/compatibility/*`
- `/protocols/validate/*`, `/protocols/conformance/*`
- `/datasets/*`, `/training/runs/*`, `/eval/suites/*`, `/eval/runs/*`
- `/audit/events/*`, `/audit/verify/*`, `/audit/export/*`

## 7) Build Phases

Phase 1: Control Plane Hardening
- Worker groups, orchestration profiles, job templates/runs
- Reporting chain + visible postback enforcement
- Expanded audit and delivery receipts

Phase 2: Builder Studios
- Skill/tool/MCP package builder and signer
- Model registry + provider adapter manager
- Protocol standards registry

Phase 3: IDE Integration
- Unified workspace with visual editors and code-first views
- Scenario simulation and replay
- One-click environment export/import

Phase 4: Model Forge
- Dataset governance and training orchestration
- Deterministic and generative model pipelines
- Eval-driven release gates

## 8) Acceptance Criteria

- Admin can configure org/team/self scopes in GUI.
- Operator can create and run jobs against groups or individuals.
- Every run has owner, recipients, escalation route, and visible output delivery proof.
- Team can build and version skills/tools/MCP servers fully in platform.
- Platform can register and configure models from multiple providers with compatibility checks.
- Forge module can execute deterministic and generative model pipeline runs with auditable metadata.
- Protocol studio can produce machine-checkable standards with conformance evidence suitable for external adoption.
