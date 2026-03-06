# ADR-0001: Clean-Room Boundary

## Status

Accepted

## Decision

Implement ORDL platform as a clean-room system that does not import or copy upstream ordlctl source code.

## Rules

1. Reuse only behavior-level observations and public standards/protocols.
2. Preserve independent naming, data model, and execution paths.
3. Keep compatibility bridges at interface level only.
4. No code-level dependency on upstream ordlctl internals.

## Consequences

- Longer initial implementation compared with direct forking.
- Higher IP clarity and independent roadmap control.
- Explicit migration adapter requirements for parity operations.
