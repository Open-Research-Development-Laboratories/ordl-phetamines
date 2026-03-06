# ORDL Revision-1 Expansion Prompt Pack (Flask + Vanilla)

This pack is for generating additional UI pages that must stay aligned to revision-1 style.

Reference sources:

- `ordl_platform/docs/faceplate/overall-look-and-feel.txt`
- `ordl_platform/docs/faceplate/how-to-generate-this-style.txt`
- `ordl_platform/docs/faceplate/revision-1/ordl-ide-prototype/*`

## Non-Negotiables

1. Stack: Flask + Jinja templates + vanilla JS + vanilla CSS only.
2. No React, no Tailwind, no UI frameworks.
3. Keep revision-1 visual language:
- Deep charcoal backgrounds (`#0a0a0a`, `#111111`)
- Warm cream text (`#f5f2e9` family)
- Amber accents only for active/alert/action (`#f59e0b` family)
4. Typography:
- Data/code: IBM Plex Mono
- UI/headings: Space Grotesk (or Helvetica fallback)
5. Interaction style:
- Industrial, mechanical, cockpit-like
- Subtle phosphor glow on focus/active
- No flashy gradients, no playful animation noise
6. Accessibility:
- Keyboard-first interactions
- Visible focus state
- ARIA labels on controls and command surfaces
7. Responsive:
- Desktop-first, must degrade cleanly to tablet/mobile

## Global Layout Contract

Every app page must follow this shell:

- Topbar: identity, scope selector, command entry, profile menu
- Left nav: sectioned navigation with clear active state
- Main canvas: primary workflow
- Context rail (right): details, state, approvals, audit info

## Flask Template Contract

Use this file shape for every page group:

- `templates/layouts/app_base.html`
- `templates/<domain>/<page>.html`
- `static/css/tokens.css`
- `static/css/layout.css`
- `static/css/<domain>/<page>.css`
- `static/js/<domain>/<page>.js`

## Prompt Template (use this for each page)

"Build `<ROUTE_NAME>` for ORDL Platform using Flask + Jinja + vanilla CSS/JS. Enforce revision-1 style from `overall-look-and-feel.txt` and `revision-1/ordl-ide-prototype`. Keep monochrome machinery look, amber only for action/alert. Include: shell layout, page-specific panels, realistic data placeholders (not lorem), keyboard interactions, ARIA labels, and mobile adaptation. Output:

1) Jinja template
2) page CSS
3) page JS
4) Flask route stub
5) integration notes into top nav and sidebar."

## Priority Page Prompts

### A) Faceplate/Public

1. `/` Home (enterprise + government trust)
- Hero, trust strip, architecture summary, capability pillars, proof metrics, CTA ladder.
2. `/pricing`
- Tier matrix, policy/compliance add-ons, enterprise procurement section.
3. `/docs`
- Quickstart cards, SDK/API start paths, versioning controls, search entry.
4. `/trust`
- Security posture, control mapping, disclosure flow, data residency statements.
5. `/status`
- Service status cards, incident timeline, dependency status, subscribe widget.
6. `/login` and `/signup`
- Auth forms, SSO options, security notices, OTP/MFA pathways.
7. `/changelog`
- Release notes with severity badges, migration notes, rollback notes.
8. `/contact`
- Sales/security/support routing with SLA expectations.

### B) Control Plane

9. `/app/dashboard`
- Global fleet summary, active incidents, deploy health, approval queue.
10. `/app/topology`
- Live node graph, edge throughput, role overlays, filter by org/project.
11. `/app/fleet/operations`
- Node status table, reconnect controls, drain/cordon actions, update status.
12. `/app/deployments`
- Release pipeline, staged rollout, canary controls, rollback actions.
13. `/app/command-center`
- Batch dispatch, targeted dispatch, response streams, rate/scope controls.
14. `/app/messages/rework`
- Draft -> review -> approved -> dispatched -> superseded lifecycle board.

### C) Governance + Security

15. `/app/orgs`
- Organization profile, board roster, policy defaults, region policy.
16. `/app/teams`
- Team assignment, operating scope, escalation trees.
17. `/app/projects`
- Project metadata, seat map, default clearance/compartments.
18. `/app/seats`
- Seat assignment CRUD, role/rank/position/group, lifecycle state.
19. `/app/clearance`
- Tier + compartment editor, need-to-know matrix, conflict visualization.
20. `/app/policy`
- Policy token decisions, rule simulation, hold/deny reason explorer.
21. `/app/providers`
- Model provider config, auth status, failover priority, health probes.
22. `/app/extensions`
- Plugin/skill/MCP registry, signature verification state, revocation controls.
23. `/app/audit`
- Immutable audit stream, filters, export jobs, evidence packages.

### D) Model Engineering

24. `/app/models/workshop`
- Model inventory, fine-tune jobs, artifact lineage, release channels.
25. `/app/models/training`
- Dataset selection, run configs, hardware targets, cost/time estimator.
26. `/app/models/inference`
- Prompt test harness, latency/quality dashboard, regression compare.
27. `/app/data/pipelines`
- Ingest/clean/label jobs, quality gates, retention policies.

### E) Platform Reliability

28. `/app/nodes/discovery`
- Scan planner, candidate hosts, fit score, proposed role assignment.
29. `/app/nodes/autoupdate`
- Update rings, maintenance windows, no-regression checks, rollback safety.
30. `/app/health`
- Gateway/node keepalive monitors, reconnect diagnostics, SLO view.
31. `/app/incidents`
- Incident board, triage workflows, timeline, postmortem links.

## Prompt Add-On (ask for this on every generated page)

"Also produce a tiny Flask route example and a registration snippet for sidebar + breadcrumb + command palette so the page is immediately pluggable into the app shell."

## Definition of Done for each page

1. Visual parity with revision-1 tone and palette.
2. Works in Flask template context with no framework build tools.
3. Includes keyboard and accessibility states.
4. Has real data regions wired for backend integration placeholders.
5. Includes route + nav integration notes.
