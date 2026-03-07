# ORDL Revision 11 Intake Review

**Date:** 2026-03-07  
**Reviewer:** hub-control  
**Scope:** `revision-11` artifact validation against current ORDL workspace truth

---

## 1) SUMMARY

Revision 11 is directionally useful, but it is not yet an authoritative implementation pack.

What is usable:
- The Flask BFF change-list intent is still valid.
- The normalization report is attempting the right job.
- The reliability report captures the correct class of concerns: in-memory runtime state, Windows pytest friction, and deployment-readiness gaps.

What is not yet clean:
- Route counts are stale.
- Test suite references are stale.
- Some findings contradict the current repo.
- Revision 11 does not consistently inherit the Revision 10 normalization baseline.

Current ORDL workspace truth:
- Current backend contract export path count: `119`
- `api-v1-routes.md` exists at `ordl_platform/docs/contracts/api-v1-routes.md`
- Current backend test files do **not** include `test_ordl_api.py`
- The Flask BFF target file exists at:
  `ordl_platform/docs/faceplate/revision-9-fixed-app/ordl_fixed/app/blueprints/api.py`

---

## 2) FINDINGS

1. `ORDL_REV10_IMPLEMENTATION_CHANGE_LIST.md` still claims `47 routes` and a `full /v1 contract alignment (47 routes)`.
   - Current contract export is `119` paths, not `47`.
   - This makes the migration sizing and missing-route counts stale.

2. `ORDL_REVISION_10_NORMALIZATION_REPORT.md` claims `47 routes confirmed`.
   - That contradicts the current generated contract artifact in this repo.

3. `ORDL_REVISION_10_NORMALIZATION_REPORT.md` says `api-v1-routes.md` is missing.
   - It exists at `ordl_platform/docs/contracts/api-v1-routes.md`.

4. The Revision 11 reliability artifact still cites `test_ordl_api.py` and a `92/92` suite.
   - That test file does not exist in the current backend test tree.
   - The report should not be used as authoritative evidence for current repo state.

5. The Flask target path is not fully wrong, but it is underspecified.
   - `ordl_fixed/app/blueprints/api.py` exists only inside the Revision 9 fixed-app bundle, not as a root project path.
   - Any implementation handoff should use the full repo path.

6. `/v1/auth/check` remains unproven from the current repo state.
   - Revision 11 correctly raises this as a blocker question.
   - That part should stay open until backend confirms the intended auth boundary.

---

## 3) ACTION LIST

1. Treat Revision 11 as a worker draft, not a publishable source of truth.
2. Keep the Revision 10 normalized files as the current clean baseline.
3. Have `worker-arch-desktop` rewrite the Revision 11 docs against the current `119`-path contract.
4. Have `worker-build-laptop` convert the BFF change-list into file-accurate implementation steps against the actual Flask bundle path.
5. Have `worker-batch-server` regenerate the reliability report from existing test files only.
6. Reject any future report that cites:
   - `47 routes`
   - `test_ordl_api.py`
   - missing `api-v1-routes.md`
   unless the repo actually changes to make those statements true.

---

## 4) OPEN QUESTIONS

1. Do you want me to normalize Revision 11 in place, or keep it as a draft and maintain ORDL-authored overlay reviews like this one?
2. Should the Flask BFF implementation start now from the Revision 9 fixed-app bundle, or wait for the frontend team’s next faceplate pass?
3. Do you want the next fleet cycle to produce code patches, or documentation-only cleanup first?
