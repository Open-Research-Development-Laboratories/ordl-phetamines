# Revision 13 Fleet Dispatch Pack

Use these as direct worker assignments.  
Reporting recipients for all tasks: Winsock + hub-control.

---

## 1) worker-arch-desktop

### Objective
Normalize Revision 13 documentation to current ORDL repo reality and remove stale assumptions.

### Inputs (exact filenames)
- `ordl_platform/docs/faceplate/revision-13/ORDL_REV11_IMPLEMENTATION_PLAN.md`
- `ordl_platform/docs/faceplate/revision-13/ORDL_REVISION_11_DOCUMENTATION.md`
- `ordl_platform/docs/faceplate/revision-13/RELIABILITY_VALIDATION_REPORT.md`
- `ordl_platform/docs/contracts/api-v1-contract.json`
- `ordl_platform/docs/contracts/api-v1-routes.md`

### Constraints / Invariants
- ORDL backend `/v1` is source of truth.
- No `openclaw` paths.
- No `47 routes` claim.
- No missing-file claims for existing artifacts.
- Keep output implementation-grade, not advisory fluff.

### Output format (strict order)
1. Summary
2. Risks
3. Action List
4. Open Questions

---

## 2) worker-build-laptop

### Objective
Implement the Flask BFF proxy migration against real ORDL `/v1` contracts in the Revision 9 app bundle.

### Inputs (exact filenames)
- `ordl_platform/docs/faceplate/revision-9-fixed-app/ordl_fixed/app/blueprints/api.py`
- `ordl_platform/docs/contracts/api-v1-contract.json`
- `ordl_platform/docs/contracts/api-v1-routes.md`
- `ordl_platform/docs/faceplate/revision-13/ORDL_REV11_IMPLEMENTATION_PLAN.md`

### Constraints / Invariants
- Keep Flask + vanilla JS stack.
- Remove in-memory mock data behavior from runtime paths.
- Use backend `/v1` contract, not static fake responses.
- Preserve authz/audit flow and fail closed on backend unavailability.
- Do not change unrelated files.

### Output format (strict order)
1. Summary
2. Risks
3. Action List
4. Open Questions

---

## 3) worker-batch-server

### Objective
Regenerate a truthful reliability validation report for current ORDL repo using only existing tests and reproducible command evidence.

### Inputs (exact filenames)
- `ordl_platform/backend/tests/`
- `ordl_platform/docs/faceplate/revision-13/RELIABILITY_VALIDATION_REPORT.md`
- `ordl_platform/scripts/release-gate.ps1`

### Constraints / Invariants
- No fabricated pass counts.
- No references to missing test files.
- Include exact command lines executed and observed counts.
- Include fail-closed checks and dependency outage behavior.

### Output format (strict order)
1. Summary
2. Risks
3. Action List
4. Open Questions

---

## 4) Optional parallel hardening job (any worker)

### Objective
Produce frontend-to-backend endpoint binding matrix for production UI wiring.

### Inputs (exact filenames)
- `ordl_platform/frontend/src/App.tsx`
- `ordl_platform/frontend/src/api.ts`
- `ordl_platform/docs/contracts/api-v1-routes.md`
- `ordl_platform/docs/faceplate/revision-13/ORDL_REVISION_11_DOCUMENTATION.md`

### Constraints / Invariants
- Only map to real `/v1` endpoints.
- Mark missing UI bindings explicitly.
- Prioritize governance, providers, workers, dispatch, approvals, and audit views.

### Output format (strict order)
1. Summary
2. Risks
3. Action List
4. Open Questions

