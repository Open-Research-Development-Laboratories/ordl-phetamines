# <Dispatch Name>

## Intent
- <objective>

## Inputs
- <absolute file paths>
- <api endpoints>

## Constraints
- one worker per file ownership at a time
- no mock data as source of truth
- endpoint usage must align to `/v1` contract

## Tool Policy
- use: <required tools>
- fallback: <fallback tools>

## Output Contract
- exact order:
  1. Summary
  2. Risks
  3. Action List
  4. Open Questions

## Failure Handling
- return blocked item with:
  - missing endpoint signature
  - required schema
  - temporary safe behavior

## Acceptance Criteria
- [ ] all assigned files updated
- [ ] no TODO stubs remain
- [ ] report posted with full body

