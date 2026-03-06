# Protocol and Standards Program

Status: Draft v0.1

## Objective

Define, version, validate, and publish ORDL-native protocols where existing standards are missing, ambiguous, or insufficient for deterministic enterprise orchestration.

## Scope

- orchestration contracts
- tool call contracts
- skill packaging contracts
- MCP server contracts
- delivery/postback contracts
- audit evidence contracts
- compatibility profiles for provider-specific behavior

## Core Principles

1. Explicit over implicit: every requirement is machine-checkable.
2. Deterministic compliance: pass/fail validation, no fuzzy interpretation.
3. Version-first governance: every standard has semantic version, changelog, and deprecation window.
4. Adapter isolation: provider quirks are mapped in adapters, not leaked into core contracts.
5. Backward-safe migration: protocol transitions require compatibility matrices and rollout rings.

## Governance Workflow

1. Propose
- RFC with problem statement, requirements, constraints, and test vectors.

2. Draft
- Formal schema, examples, negative cases, and conformance tests.

3. Review
- Technical review board + security review + implementation owner review.

4. Pilot
- Canary deployment with telemetry and failure analysis.

5. Adopt
- Mark as supported in protocol registry.

6. Enforce
- Gate runtime operations by protocol conformance checks.

## Required Artifacts Per Standard

- protocol id and version (`ordl.<domain>.<name>:vX.Y.Z`)
- normative schema (`json-schema` or equivalent)
- mandatory and optional fields
- success and failure examples
- conformance test suite
- migration notes from previous versions
- ambiguity log (known interpretation risks and resolutions)

## Conformance Levels

- `L0`: draft only, not enforceable
- `L1`: advisory, telemetry only
- `L2`: enforceable for new workloads
- `L3`: mandatory for all workloads in scoped environments

## Registry API Targets

- `POST /protocols/standards`
- `GET /protocols/standards`
- `POST /protocols/standards/{id}/versions`
- `GET /protocols/compatibility`
- `POST /protocols/validate`
- `POST /protocols/conformance/runs`

## R&D Outcome Target

ORDL publishes protocol artifacts that can be adopted by external teams and provider ecosystems because they are:

- clear
- testable
- versioned
- demonstrably reliable under real orchestration load
