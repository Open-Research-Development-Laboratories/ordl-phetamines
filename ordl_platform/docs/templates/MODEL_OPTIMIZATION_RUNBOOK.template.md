# <Model Optimization Runbook>

## Intent
- improve model quality for <task>

## Inputs
- baseline model: `<model snapshot>`
- datasets:
  - training: `<path/id>`
  - validation: `<path/id>`
  - eval: `<path/id>`

## Constraints
- eval-before-promotion required
- schema contract must not break
- rollback criteria must be defined

## Tool Policy
- allowed APIs: `responses`, `evals`, `fine_tuning` (when approved)
- restricted operations: production promotion without eval pass

## Output Contract
- return:
  1. baseline metrics
  2. changed prompts/instructions
  3. eval deltas
  4. release decision

## Failure Handling
- if thresholds fail:
  - reject promotion
  - return failed criteria and remediation plan

## Acceptance Criteria
- [ ] eval suite executed
- [ ] metrics documented
- [ ] promotion decision logged

