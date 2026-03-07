# Revision 10 Fleet Dispatch Pack

Use these dispatches as-is for the next Revision 10 cleanup and integration pass.

Reporting recipients:
- Aaron Marshall Ferguson (Winsock)
- ORDL board review route

Postback requirement:
- Worker must post the full report body into chat.
- Header-only completion is invalid.

## worker-arch-desktop

```text
Objective:
Normalize Revision 10 architecture and migration documents so they match the current ORDL backend contract and repo topology exactly.

Inputs (exact filenames):
- C:\Users\Winsock\Documents\GitHub\ordl-phetamines\ordl_platform\docs\faceplate\revision-10\ORDL_API_ADAPTER_PLAN.md
- C:\Users\Winsock\Documents\GitHub\ordl-phetamines\ordl_platform\docs\faceplate\revision-10\ORDL_REV9_PRODUCTION_MIGRATION_SPEC.md
- C:\Users\Winsock\Documents\GitHub\ordl-phetamines\ordl_platform\docs\contracts\api-v1-contract.json
- C:\Users\Winsock\Documents\GitHub\ordl-phetamines\ordl_platform\docs\contracts\api-v1-routes.md

Constraints / Invariants:
- No legacy product naming or paths.
- ORDL backend /v1 contract is source of truth.
- Explicitly call out any document claim that cannot be proven from this repo.

Output format (strict order):
1) Summary
2) Risks
3) Action List
4) Open Questions
```

## worker-build-laptop

```text
Objective:
Convert the Revision 10 adapter plan into an implementation-ready Flask BFF change list against the current ORDL backend.

Inputs (exact filenames):
- C:\Users\Winsock\Documents\GitHub\ordl-phetamines\ordl_platform\docs\faceplate\revision-9-fixed-app\ordl_fixed\app\blueprints\api.py
- C:\Users\Winsock\Documents\GitHub\ordl-phetamines\ordl_platform\docs\faceplate\revision-10\ORDL_API_ADAPTER_PLAN.md
- C:\Users\Winsock\Documents\GitHub\ordl-phetamines\ordl_platform\docs\contracts\api-v1-contract.json

Constraints / Invariants:
- Flask remains the frontend BFF stack.
- Do not invent endpoints not present in /v1.
- Replace local in-memory and mock auth assumptions with real backend boundaries.

Output format (strict order):
1) Summary
2) Risks
3) Action List
4) Open Questions
```

## worker-batch-server

```text
Objective:
Regenerate a reliability validation report for Revision 10 using only reproducible commands and current tests from this workspace.

Inputs (exact filenames):
- C:\Users\Winsock\Documents\GitHub\ordl-phetamines\ordl_platform\docs\faceplate\revision-10\ordl_platform\RELIABILITY_VALIDATION_REPORT.md
- C:\Users\Winsock\Documents\GitHub\ordl-phetamines\ordl_platform\backend\tests\test_model_governance_policies.py
- C:\Users\Winsock\Documents\GitHub\ordl-phetamines\ordl_platform\backend\tests

Constraints / Invariants:
- Use only tests that exist in this repo right now.
- Every count must be reproducible from the listed commands.
- Remove unverifiable timestamps, actor identifiers, and fabricated suite names.

Output format (strict order):
1) Summary
2) Risks
3) Action List
4) Open Questions
```
