# OpenAI Model Lifecycle Standard v1 (ORDL)

This document defines ORDL's standard operating lifecycle for model use, optimization, and tuning.

## Lifecycle

1. Define task objective and measurable success criteria.
2. Select baseline model and API mode.
3. Build eval set before optimization changes.
4. Optimize prompts/instructions against evals.
5. Fine-tune only when prompt optimization plateaus.
6. Re-run evals and compare to baseline before promotion.
7. Promote via staged rollout and monitor regressions.

## API Defaults

- Primary API: `Responses API`.
- Structured output: JSON schema when parser-dependent.
- Reasoning effort: explicit and task-appropriate.
- Model choice: pinned snapshot in production.

## Evaluation Requirements

- Every production task must have:
  - baseline eval score
  - target threshold
  - regression threshold
  - rollback criteria
- Changes to prompt, schema, toolset, or model require eval rerun.

## Optimization Loop

1. Capture failure cases from production and test data.
2. Update instructions and examples.
3. Run eval suite.
4. Compare precision, recall, latency, and cost.
5. Approve only if thresholds pass.

## Fine-Tuning Policy

Fine-tune only when one or more is true:

- stable task with repetitive patterns
- prompt-only improvements no longer meet target
- output consistency cannot be achieved with schema + prompting

Fine-tuning prerequisites:

- versioned training and validation datasets
- documented data provenance
- explicit safety filters in data prep
- eval suite covering task and refusal/safety behavior

## Release Gating

Promotion requires:

- pass on quality eval threshold
- no critical safety regression
- no contract/schema break
- approved rollback path

## Observability

Track:

- quality scores by run
- latency percentiles
- token cost by request class
- tool-call success rate
- fallback rate and refusal rate

## Security Baseline

- enforce least privilege for tools/connectors
- redact sensitive user data before logging
- use signed policy tokens for outbound high-risk actions
- fail closed on policy validation errors

