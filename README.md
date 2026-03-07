# ordl-phetamines

Public working repository for the ORDL platform effort.

This repository contains a clean-room platform program focused on:

- governed multi-model development workflows
- fleet and node orchestration
- policy-gated dispatch and approvals
- enterprise and regulated-environment operations
- public-facing product and architecture documentation

## What is here

- [`ordl_platform/`](ordl_platform)  
  Clean-room platform module with backend, frontend shell, infrastructure, scripts, contracts, and launch planning artifacts.
- [`fleet_api/`](fleet_api)  
  Internal fleet-control module for worker orchestration, policy checks, and handoff workflows.
- [`policy/`](policy)  
  Policy and control artifacts used by the platform program.
- [`specs/`](specs) and [`tests/`](tests)  
  Supporting specifications and validation material.

## Public document map

Start here if you are reviewing the project:

- [`ordl_platform/docs/ordl-blueprint-pack/README.md`](ordl_platform/docs/ordl-blueprint-pack/README.md)
- [`ordl_platform/docs/ordl-blueprint-pack/ordl-ultimate-platform-blueprint.md`](ordl_platform/docs/ordl-blueprint-pack/ordl-ultimate-platform-blueprint.md)
- [`ordl_platform/README.md`](ordl_platform/README.md)
- [`ordl_platform/docs/contracts/api-v1-routes.md`](ordl_platform/docs/contracts/api-v1-routes.md)
- [`ordl_platform/docs/deployment-first-pipeline.md`](ordl_platform/docs/deployment-first-pipeline.md)

## Current implementation shape

- Backend: FastAPI + SQLAlchemy
- Frontend shell: React + TypeScript
- Runtime: Podman Compose
- Security model: RBAC + ABAC, signed policy tokens, signed extension registration
- Governance model: tenant, organization, team, project, seat, clearance, compartment

## Repository posture

- This repository is public-facing.
- Live secrets, private environment files, internal runtime logs, and local memory files are intentionally excluded from source control.
- Operational examples are being normalized toward documentation-safe placeholder values.

## Development status

The ORDL platform is under active build-out. The repository already contains:

- backend route contracts
- governance and policy primitives
- fleet reliability and update planning
- model and orchestration lifecycle planning
- launch-readiness and validation blueprint material

## License

See [`LICENSE`](LICENSE).
