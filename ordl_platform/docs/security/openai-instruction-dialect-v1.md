# OpenAI Instruction Dialect v1 (ORDL)

This is the canonical markdown instruction language for ORDL prompts, system files, worker dispatches, and runbooks.

## Goal

Define a deterministic, machine-readable instruction shape aligned to OpenAI prompt guidance and Responses API workflows.

## Dialect Rules

1. Every instruction document must be explicit, testable, and conflict-free.
2. Use imperative language for required behavior (`must`, `must not`, `only`).
3. Separate intent from constraints from output contract.
4. Never hide requirements in prose. Put requirements in labeled sections.
5. When output structure matters, define a strict JSON schema or exact section order.
6. If a task calls tools, define tool policy in the same file.

## Required Section Contract

All operational instruction files must include these sections in order:

1. `## Intent`
2. `## Inputs`
3. `## Constraints`
4. `## Tool Policy`
5. `## Output Contract`
6. `## Failure Handling`
7. `## Acceptance Criteria`

## Language Conventions

- Use short sentences.
- One requirement per bullet.
- Use backticks for paths, commands, endpoints, fields, and status values.
- Use absolute paths when referring to local files.
- For output sections, define exact order and do not allow substitutions.

## Prompt/Model Conventions

For OpenAI API requests:

- Put high-level behavior in `instructions`.
- Put task-specific data in `input`.
- Use schema-constrained output when machine parsing is required.
- Pin model snapshots for production stability.
- Couple prompt updates with eval runs before rollout.

## Worker Dispatch Conventions

Dispatch files must include:

- objective
- exact file inputs
- immutable constraints/invariants
- output sections in strict order
- escalation target for blocked items

Recommended output order:

1. Summary
2. Risks
3. Action List
4. Open Questions

## Example Skeleton

```md
# <Task Name>

## Intent
- <what must be accomplished>

## Inputs
- <absolute file paths>

## Constraints
- must ...
- must not ...

## Tool Policy
- use ...
- do not use ...

## Output Contract
- return sections in this order:
  1. Summary
  2. Risks
  3. Action List
  4. Open Questions

## Failure Handling
- if blocked by missing endpoint:
  - return exact missing endpoint signature
  - return fallback behavior

## Acceptance Criteria
- [ ] all required files changed
- [ ] tests pass
- [ ] no TODO stubs remain
```

