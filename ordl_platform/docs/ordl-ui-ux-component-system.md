# ORDL UI and UX Component System

This file defines the design system and interaction model for the ORDL platform.

It is implementation-level guidance for frontend engineering and design consistency.

## 1) Visual system principles

- Monochrome Machinery theme:
  - deep charcoal surfaces
  - warm cream typography
  - amber for caution and branch-state emphasis
- Prioritize information density with clarity.
- Preserve readability under heavy operational data.

## 2) Core layout primitives

- `ShellLayout`
  - top bar, side nav, command palette trigger, status strip
- `WorkspaceLayout`
  - split panels with resizable boundaries
- `DockLayout`
  - attachable panels for logs, diagnostics, traces, chat
- `TimelineLayout`
  - event ruler, scrubber, and branch overlays

## 3) Navigation components

- `GlobalSidebar`
  - section icons, role-aware visibility
- `SectionTabs`
  - route-level mode switches
- `BreadcrumbTrail`
  - hierarchy context (tenant/org/team/project)
- `QuickActionBar`
  - context-sensitive action buttons

## 4) Data display components

- `MetricTile`
  - value, delta, threshold status
- `HealthBadge`
  - healthy, degraded, failed, unknown
- `RiskPill`
  - low, medium, high, critical
- `ResourceTable`
  - sortable, filterable, bulk actions
- `EventTimeline`
  - chronological events with branch markers
- `TopologyCanvas`
  - node graph with live edge throughput

## 5) Fleet-specific components

- `NodeCard`
  - role, state, heartbeat freshness, reconnect score
- `GatewayCard`
  - active sessions, failover group, maintenance state
- `ProbeResultPanel`
  - latest probe and historical probe trends
- `ReconnectPolicyEditor`
  - sticky gateway toggle, fallback order, jitter profile
- `UpdateWaveBoard`
  - canary and staged rollout statuses

## 6) Model lifecycle components

- `ModelRegistryGrid`
  - model family and versions
- `TrainingRunBoard`
  - queued, running, completed, failed runs
- `EvalScorePanel`
  - quality, safety, regression metrics
- `InferenceEndpointCard`
  - p95 latency, throughput, error rate
- `LineageGraph`
  - dataset, train run, eval run, deploy lineage

## 7) IDE and authoring components

- `MonacoEditorFrame`
  - syntax highlighting, diagnostics, minimap toggle
- `DirectiveLintPanel`
  - directive schema and policy lint findings
- `PolicySimulationPanel`
  - scenario inputs and decision outputs
- `DiffReviewPane`
  - side-by-side revisions with inline comments
- `SuggestionQueue`
  - AI suggestions with accept/reject actions

## 8) Collaboration components

- `ThreadInbox`
  - assigned and unassigned review threads
- `WorkflowStateStepper`
  - draft/review/approved/dispatched state
- `ReviewDecisionPanel`
  - decision + rationale controls
- `ApprovalSlaTimer`
  - deadline and escalation indicator
- `DeliveryStatusPanel`
  - dispatch destination state and retry counters

## 9) Security and compliance components

- `ControlMatrixView`
  - control status and evidence linkage
- `AuditChainStatus`
  - verification state and chain length
- `EvidenceExportWizard`
  - scoped export builder
- `IdentityProviderPanel`
  - OIDC/SAML settings and health
- `SecretsHealthPanel`
  - rotation due, stale secret alerts

## 10) Interaction states

Every interactive component must support:

- idle
- loading
- success
- error
- empty
- stale-data warning
- unauthorized
- disabled by policy

## 11) Motion and transitions

- Use short, purposeful transitions only.
- Avoid decorative animation in high-load views.
- Use deterministic timeline animation for replay tools.
- Preserve state when moving between neighboring routes.

## 12) Accessibility and usability requirements

- Keyboard-first navigation for all critical actions.
- Focus order and focus traps in modal workflows.
- Minimum contrast targets across all themes.
- Screen reader labels on all controls and statuses.
- Reduced-motion mode support.

## 13) Performance requirements for UI

- Initial app shell render under target budget.
- Progressive data hydration for heavy dashboards.
- Virtualized tables for large result sets.
- Streaming updates with bounded render frequency.

## 14) Role-aware UI rules

- hide inaccessible controls by default
- show explicit policy reason when action unavailable
- provide read-only fallback panels for audit roles

## 15) Component quality bars

- Every component must have:
  - unit tests
  - accessibility checks
  - visual regression coverage for critical states
- No component may ship without loading and error states.
