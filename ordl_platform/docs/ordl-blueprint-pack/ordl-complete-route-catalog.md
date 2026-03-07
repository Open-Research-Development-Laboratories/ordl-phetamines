# ORDL Complete Route Catalog

This file defines the full route map and expected behavior for the ORDL Faceplate and ORDL Control Platform.

Use this as the implementation contract for frontend routes, backend API dependencies, and permission controls.

## 1) Route contract format

Each route definition includes:

- Route path
- Required roles
- Required clearance
- Data reads
- Data writes
- Primary actions
- Failure states

## 2) Public faceplate routes

### 2.1 Landing

- Route: `/`
- Required roles: none
- Required clearance: none
- Data reads:
  - Product highlights
  - Capability banners
  - Status summary badge
- Data writes: none
- Primary actions:
  - Start trial
  - Request demo
  - Open docs
- Failure states:
  - Static fallback shell
  - degraded banner if status feed unavailable

### 2.2 Product docs

- Route: `/docs`
- Required roles: none
- Required clearance: none
- Data reads:
  - Public docs index
  - Versioned release notes
  - API quickstarts
- Data writes: none
- Primary actions:
  - Filter docs
  - Copy code snippets
  - Open API reference

### 2.3 Trust center

- Route: `/trust`
- Required roles: none
- Required clearance: none
- Data reads:
  - Security controls overview
  - Compliance claims with evidence links
  - Incident disclosure summary
- Data writes: none
- Primary actions:
  - Download trust package
  - Request security questionnaire

### 2.4 Service status

- Route: `/status`
- Required roles: none
- Required clearance: none
- Data reads:
  - Service uptime
  - Incident timelines
  - component health by region
- Data writes: none
- Primary actions:
  - Subscribe to status alerts

### 2.5 Authentication

- Route: `/login`
- Required roles: none
- Required clearance: none
- Data reads:
  - Enabled identity providers
  - SSO metadata
- Data writes:
  - Session creation
- Primary actions:
  - Login with SSO
  - Login with local account where allowed
  - Start passwordless challenge

## 3) Control platform core routes

### 3.1 Command center

- Route: `/app/command-center`
- Required roles:
  - officer
  - board_member
  - operator
- Required clearance: internal+
- Data reads:
  - Fleet health aggregate
  - Active release and incident summary
  - Open policy holds
  - top risk findings
- Data writes:
  - Incident escalation
  - release freeze toggle
- Primary actions:
  - Escalate incident
  - open war room
  - freeze/resume deployments
- Failure states:
  - stale-data banner
  - event stream reconnect mode

### 3.2 Real-time topology

- Route: `/app/topology/live`
- Required roles:
  - architect
  - operator
  - officer
- Required clearance: internal+
- Data reads:
  - Nodes, gateways, links
  - Link throughput and RTT
  - Queue and message rates
- Data writes:
  - route overrides
  - node isolation command
- Primary actions:
  - inspect node
  - inspect channel
  - isolate/reroute

### 3.3 Temporal replay

- Route: `/app/topology/timeline`
- Required roles:
  - architect
  - operator
  - auditor
- Required clearance: restricted+
- Data reads:
  - Event timeline
  - state snapshots
  - branch markers
- Data writes:
  - scenario checkpoint creation
- Primary actions:
  - scrub timeline
  - open causal chain
  - save replay scenario

## 4) Fleet and mesh routes

### 4.1 Fleet overview

- Route: `/app/fleet/overview`
- Required roles:
  - operator
  - officer
  - architect
- Required clearance: internal+
- Data reads:
  - Node counts by state
  - gateway state
  - reconnect health
  - update wave progress
- Data writes: none
- Primary actions:
  - drill-down into node classes

### 4.2 Nodes

- Route: `/app/fleet/nodes`
- Required roles:
  - operator
  - engineer
  - architect
- Required clearance: internal+
- Data reads:
  - node inventory
  - node capabilities
  - heartbeat/probe history
- Data writes:
  - quarantine
  - decommission
  - role reassignment
- Primary actions:
  - approve candidate
  - run probe
  - trigger reconnect

### 4.3 Discovery

- Route: `/app/fleet/discovery`
- Required roles:
  - operator
  - officer
- Required clearance: restricted+
- Data reads:
  - scan jobs
  - discovered candidates
  - suitability scoring
- Data writes:
  - candidate approval/deny
  - bootstrap enqueue
- Primary actions:
  - run subnet scan
  - evaluate candidate
  - assign onboarding profile

### 4.4 Gateways

- Route: `/app/fleet/gateways`
- Required roles:
  - operator
  - architect
- Required clearance: restricted+
- Data reads:
  - gateway regions
  - active sessions
  - failover groups
- Data writes:
  - maintenance mode
  - failover group edit
- Primary actions:
  - drain gateway
  - force failover

### 4.5 Upgrades

- Route: `/app/fleet/upgrades`
- Required roles:
  - operator
  - officer
- Required clearance: controlled+
- Data reads:
  - available versions
  - rollout history
  - rollback readiness
- Data writes:
  - create rollout plan
  - execute wave
  - rollback run
- Primary actions:
  - canary rollout
  - promote wave
  - abort rollout

## 5) Model engineering routes

### 5.1 Model catalog

- Route: `/app/models/catalog`
- Required roles:
  - engineer
  - architect
  - officer
- Required clearance: internal+
- Data reads:
  - model registry entries
  - versions and health
  - provider compatibility
- Data writes:
  - tag updates
  - deprecate/pin
- Primary actions:
  - open model details
  - compare versions

### 5.2 Create model

- Route: `/app/models/create`
- Required roles:
  - engineer
  - architect
- Required clearance: restricted+
- Data reads:
  - base model options
  - template presets
- Data writes:
  - model draft configuration
  - new model request
- Primary actions:
  - define architecture
  - select data and objective
  - queue creation workflow

### 5.3 Training

- Route: `/app/models/train`
- Required roles:
  - engineer
  - operator
- Required clearance: restricted+
- Data reads:
  - train jobs
  - cluster capacity
  - dataset lineage
- Data writes:
  - training run config
  - pause/resume/cancel run
- Primary actions:
  - launch run
  - tune hyperparameters
  - inspect run artifacts

### 5.4 Evaluation

- Route: `/app/models/evaluate`
- Required roles:
  - engineer
  - architect
  - auditor
- Required clearance: restricted+
- Data reads:
  - quality benchmark results
  - safety and red-team outcomes
  - regression comparisons
- Data writes:
  - evaluation sign-off
  - gate override request
- Primary actions:
  - evaluate candidate
  - compare baseline vs candidate
  - issue promotion recommendation

### 5.5 Inference

- Route: `/app/models/inference`
- Required roles:
  - operator
  - engineer
- Required clearance: internal+
- Data reads:
  - endpoint status
  - latency/throughput/cost curves
- Data writes:
  - scaling controls
  - routing policy
- Primary actions:
  - set autoscale bounds
  - route traffic

## 6) IDE and authoring routes

### 6.1 Workspace editor

- Route: `/app/ide/workspace`
- Required roles:
  - engineer
  - architect
- Required clearance: internal+
- Data reads:
  - repository tree
  - open file content
  - diagnostics stream
- Data writes:
  - file edits
  - commits/patches
- Primary actions:
  - edit code
  - run static checks
  - request AI suggestions

### 6.2 Directive studio

- Route: `/app/ide/directive-studio`
- Required roles:
  - architect
  - officer
- Required clearance: restricted+
- Data reads:
  - directive packs
  - version history
  - lint findings
- Data writes:
  - directive edits
  - policy simulation runs
  - pack publish
- Primary actions:
  - edit directive schema
  - validate and publish

### 6.3 Policy studio

- Route: `/app/ide/policy-studio`
- Required roles:
  - architect
  - security_officer
- Required clearance: controlled+
- Data reads:
  - policy bundles
  - decision traces
- Data writes:
  - policy edits
  - simulation cases
  - release candidate policy
- Primary actions:
  - modify rules
  - run decision simulation
  - publish policy version

## 7) Collaboration routes

### 7.1 Inbox

- Route: `/app/collab/inbox`
- Required roles:
  - engineer
  - architect
  - officer
- Required clearance: internal+
- Data reads:
  - assigned review tasks
  - worker reports
  - pending approvals
- Data writes:
  - claim/unclaim task
  - status updates

### 7.2 Message workflow

- Route: `/app/collab/messages`
- Required roles:
  - engineer
  - architect
  - operator
- Required clearance: internal+
- Data reads:
  - message threads
  - revision history
- Data writes:
  - create draft
  - submit for review
  - rework and resubmit
  - dispatch approved output

### 7.3 Approval board

- Route: `/app/collab/approvals`
- Required roles:
  - officer
  - board_member
  - architect
- Required clearance: restricted+
- Data reads:
  - approval queues
  - SLA timers
  - decision history
- Data writes:
  - approve/reject/rework
  - escalate

## 8) Pipeline and deployment routes

### 8.1 Pipeline designer

- Route: `/app/pipelines/designer`
- Required roles:
  - engineer
  - operator
- Required clearance: restricted+
- Data reads:
  - pipeline templates
  - available stages/gates
- Data writes:
  - pipeline definitions
  - trigger conditions

### 8.2 Pipeline runs

- Route: `/app/pipelines/runs`
- Required roles:
  - engineer
  - operator
  - officer
- Required clearance: restricted+
- Data reads:
  - run statuses
  - logs and artifacts
- Data writes:
  - rerun
  - cancel
  - gate override request

### 8.3 Deploy room

- Route: `/app/deployments/room`
- Required roles:
  - operator
  - officer
- Required clearance: controlled+
- Data reads:
  - environment status
  - canary metrics
  - rollback state
- Data writes:
  - promote
  - pause
  - rollback

## 9) Security and compliance routes

### 9.1 Security overview

- Route: `/app/security/overview`
- Required roles:
  - security_officer
  - officer
  - auditor
- Required clearance: restricted+
- Data reads:
  - vulnerability totals
  - active threats
  - control drift

### 9.2 Identity and access

- Route: `/app/security/identity`
- Required roles:
  - security_officer
  - admin
- Required clearance: controlled+
- Data reads:
  - IdP settings
  - auth events
- Data writes:
  - SSO config changes
  - key rotation actions

### 9.3 Compliance controls

- Route: `/app/compliance/controls`
- Required roles:
  - auditor
  - officer
  - security_officer
- Required clearance: restricted+
- Data reads:
  - control mappings
  - evidence status
- Data writes:
  - control attestation records

### 9.4 Audit and evidence

- Route: `/app/compliance/audit`
- Required roles:
  - auditor
  - security_officer
- Required clearance: controlled+
- Data reads:
  - audit events
  - chain verification output
- Data writes:
  - evidence export requests

## 10) Administration routes

### 10.1 User and seat admin

- Route: `/app/admin/users`
- Required roles:
  - admin
  - officer
- Required clearance: controlled+
- Data reads:
  - users
  - seats
  - role assignments
- Data writes:
  - create/suspend/revoke users
  - assign/reassign seats

### 10.2 Role and clearance admin

- Route: `/app/admin/roles`
- Required roles:
  - admin
  - security_officer
- Required clearance: controlled+
- Data reads:
  - role templates
  - clearance templates
- Data writes:
  - role changes
  - compartment policy edits

### 10.3 Provider and extension admin

- Route: `/app/admin/providers`
- Required roles:
  - admin
  - officer
- Required clearance: controlled+
- Data reads:
  - provider status
  - secret health
  - extension catalog
- Data writes:
  - provider enable/disable
  - extension allow/revoke

### 10.4 System admin

- Route: `/app/admin/system`
- Required roles:
  - platform_admin
  - officer
- Required clearance: controlled+
- Data reads:
  - global config
  - feature flags
  - maintenance windows
- Data writes:
  - global toggles
  - maintenance operations

## 11) Reports routes

### 11.1 Executive report

- Route: `/app/reports/executive`
- Required roles:
  - officer
  - board_member
- Required clearance: restricted+
- Data reads:
  - release and risk summary
  - cost and reliability trend lines

### 11.2 Engineering report

- Route: `/app/reports/engineering`
- Required roles:
  - engineer
  - architect
  - officer
- Required clearance: internal+
- Data reads:
  - throughput
  - quality
  - regression

### 11.3 Fleet report

- Route: `/app/reports/fleet`
- Required roles:
  - operator
  - architect
  - officer
- Required clearance: internal+
- Data reads:
  - node health
  - reconnect stats
  - capacity and saturation

### 11.4 Cost report

- Route: `/app/reports/cost`
- Required roles:
  - officer
  - finance_admin
- Required clearance: restricted+
- Data reads:
  - usage by tenant/team/project/provider
  - cost allocation and trends

## 12) Route implementation quality bars

- Every route must implement:
  - permission checks
  - loading state
  - empty state
  - error state
  - audit write for state-changing actions
- No route may ship with static placeholder controls in production.
