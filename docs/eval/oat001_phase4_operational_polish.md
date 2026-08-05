# OAT-001 Phase 4 — Operational Polish

**Status:** Complete  
**Date:** 2026-08-05  
**Prerequisite:** [Phase 3 BOPA evaluation](oat001_phase3_bopa_evaluation.md) (Ready with minor improvements)  
**Scope:** Owner presentation / stop-reason mapping only  
**Does not:** redesign FR-015, weaken ToolPolicy, change allow-list, modify truth or pipeline behaviour, begin FR-016

---

## 1. Executive summary

Phase 4 closes the three OAT-001 Phase 3 defects and three presentation enhancements.
Architecture, ToolPolicy, and service gates are unchanged. Material-benefit refusals now
stop as `material_benefit_required` (`awaiting_owner`) with clear `--override-material-benefit`
guidance. Failed runs no longer suggest resume. `cic agent show` reports pipeline stage
(informational), owner-facing truth blockers, and an initial-inspection summary.

**Recommendation:** **Operationally Ready**

---

## 2. Defects resolved

| ID | Resolution |
|----|------------|
| D1 | Adapter material-benefit refusals map to `material_benefit_required` via `error_mapping.stop_reason_for_adapter_error` (not `unexpected_failure`) |
| D2 | `owner_action_required(..., status=)` always states legal next step: `failed` → new run; `awaiting_owner` → resume |
| D3 | Owner action for `material_benefit_required` explicitly names `--override-material-benefit`; CLI help updated |

---

## 3. Enhancements implemented

| ID | Resolution |
|----|------------|
| E1 | Readiness snapshot carries `pipeline_status`; show prints pipeline note (e.g. interviewing → preparation usually unnecessary). No pipeline authority. |
| E2 | Truth blockers section on show from owner-facing labels (unsupported certification/technology, missing evidence, …) |
| E3 | **Initial inspection** block on every report summarises observed readiness before step listing |

---

## 4. Documentation updated

- `README.md` — `cic agent` owner commands + status rules
- `docs/00_repository_guide.md` — OAT Phase 4 pointer
- `docs/08_implementation_notes.md` — Phase 4 polish notes
- `docs/eval/fr015_m3_owner_cli.md` — owner workflow / show / stop statuses
- This report

---

## 5. Tests added

`tests/unit/agent/test_oat001_phase4_presentation.py` — material-benefit mapping, override
guidance, failed vs awaiting_owner text, pipeline messaging, truth blockers, show sections.

Regression: FR-015 unit + functional agent suites green (71 tests in targeted run).

---

## 6. Manual validation results

See evidence under `data/_oat001_phase4_polish/` (generated during Phase 4 close-out).

| Check | Opportunity | Result |
|-------|-------------|--------|
| Material-benefit stop | Carlton (Bronze apply) | `material_benefit_required` / `awaiting_owner`; override in owner action |
| Override guidance | same show output | `--override-material-benefit` present |
| Resume guidance | failed unsupported (Officeworks) vs awaiting material-benefit | failed → new run; awaiting → resume |
| Pipeline messaging | Bluefin interviewing | pipeline note: usually unnecessary |
| Truth blockers | Redwolf (existing fail truth) | Unsupported certification label on show |
| Show output | all above | Initial inspection + readiness + owner action |

---

## 7. Remaining operational observations

- Live Silver/Bronze apply Opportunities still need an explicit material-benefit override to prepare (by design of FR-006/007).
- Generated Markdown may still fail truth (e.g. unsupported certifications) — fail-closed; owner edits remain mandatory.
- Pipeline messaging is advisory only; BOPA may still propose prepare when decision=`apply` and package absent (ToolPolicy unchanged).

---

## 8. Recommendation

**Operationally Ready**
