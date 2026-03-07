# Revision 11 Fleet Dispatch Pack

Reporting recipients:
- Aaron Marshall Ferguson (Winsock)
- ORDL board review route

Postback requirement:
- Worker must post the full report body into chat.
- Header-only completion is invalid.

## worker-arch-desktop

```text
Objective:
Rewrite Revision 11 documentation so it matches the current ORDL repo truth and removes stale route-count and contract claims.

Inputs (exact filenames):
- ordl_platform\docs\faceplate\revision-11\ORDL_REV10_IMPLEMENTATION_CHANGE_LIST.md
- ordl_platform\docs\faceplate\revision-11\ORDL_REVISION_10_NORMALIZATION_REPORT.md
- ordl_platform\docs\contracts\api-v1-contract.json
- ordl_platform\docs\contracts\api-v1-routes.md

Constraints / Invariants:
- Use the current ORDL repo as source of truth.
- Do not cite `47 routes` unless you can prove it from current artifacts.
- Do not claim missing files that currently exist.

Output format (strict order):
1) Summary
2) Risks
3) Action List
4) Open Questions
```

## worker-build-laptop

```text
Objective:
Turn the Revision 11 Flask BFF change-list into a file-accurate implementation plan against the actual Flask bundle path in this repo.

Inputs (exact filenames):
- ordl_platform\docs\faceplate\revision-9-fixed-app\ordl_fixed\app\blueprints\api.py
- ordl_platform\docs\faceplate\revision-11\ORDL_REV10_IMPLEMENTATION_CHANGE_LIST.md
- ordl_platform\docs\contracts\api-v1-contract.json

Constraints / Invariants:
- Use the full repo path to the Flask BFF file.
- Do not reference non-existent tests or non-existent frontend files.
- Keep backend `/v1` as source of truth.

Output format (strict order):
1) Summary
2) Risks
3) Action List
4) Open Questions
```

## worker-batch-server

```text
Objective:
Replace the Revision 11 reliability report with a reproducible report based only on currently present backend tests and current local execution constraints.

Inputs (exact filenames):
- ordl_platform\docs\faceplate\revision-11\ordl_platform\docs\faceplate\revision-10\ordl_platform\RELIABILITY_VALIDATION_REPORT.md
- ordl_platform\backend\tests
- ordl_platform\docs\faceplate\revision-11\ORDL_REVISION_11_INTAKE_REVIEW.md

Constraints / Invariants:
- Use only tests that exist in the current repo.
- Do not cite `test_ordl_api.py`.
- Include any environment limitation that prevents clean rerun.

Output format (strict order):
1) Summary
2) Risks
3) Action List
4) Open Questions
```
