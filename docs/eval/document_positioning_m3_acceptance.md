# Document Positioning M3 — Engineering / Acceptance Report

**Status:** **Complete — owner approved 2026-08-20; bounded optional-relevance correction 2026-08-20**  
**Date:** 2026-08-20  
**Scope:** Evidence-bounded CV positioning composer + Master rewrite surface.  
**Programme:** [document_positioning_remediation.md](document_positioning_remediation.md)

`cic package prepare` still uses Master-adapt with the generic Master summary
and global `omit_methodology=True`. M6 owns wiring this composer into prepare.
No CSK regeneration. No SEEK / Playwright / AAS. No M5 A/B benchmark.

Owner approved 2026-08-20. M4 was authorised separately.

---

## 1. Production CV-path audit (verified)

```
cic package prepare
  ApplicationPackageService.prepare
        ├─ TailoringPlanService.plan          # M2 catalogue classification
        ├─ CvGenerationService.generate
        │     adapt_from_master=True
        │     rewrite_summary=False           # forced in prepare
        │     omit_methodology=True           # hardcoded in generate()
        │     adapt_master_cv_markdown(...)
        │     NO LLM, NO PositioningPlan
        └─ BoundedCoverLetterService.compose  # unchanged
              write drafts + manifest
```

FR-014 remains a **separate** gate (`cic truth validate-package`). Prepare
does not invoke it.

Master-adapt today:

| Section | Behaviour |
|---------|-----------|
| Header / target role / contact overlay | Rebuilt |
| Core Skills | Rebuilt from TailoringPlan |
| Featured AI Projects | Reordered/subset; **bodies copied from Master** |
| AI Engineering Methodology | Dropped (`omit_methodology=True`) |
| Professional Summary | Copied from Master |
| Selected Engineering Highlights | Copied from Master |
| Experience, Courses, Certifications | Copied from Master |

---

## 2. FR-006c audit

`CvGenerationService._resolve_summary` returns `master_baseline` whenever
`adapt_from_master=True`. Theme-aware composition and Phase C
`SummaryRewriter` never run on the package path.

Phase C on the non-adapt path **falls back to the profile summary** on
validation or provider failure. That silent fallback is the defect M0
rejected for positioning. M3 does **not** enable FR-006c. M3 reuses only
the *idea* of structured output + deterministic validators, with fail-closed
errors instead of fallback.

---

## 3. Architecture after M3

```
JobAnalysis + CareerProfile + Master Markdown + TailoringPlan
        ↓
build_positioning_plan          # deterministic (M1)
        ↓
build_cv_positioning_pack       # deterministic (M3)
        ↓
CvPositioningComposer           # fixture in tests; OpenAI implemented, unwired
        ↓
validate_positioning_output     # forbidden / unsupported / metrics / years
        ↓
adapt_master_cv_markdown        # optional rewrite-surface overrides
        ↓
validate_locked_master_sections
```

Public API: `BoundedCvPositioningService.compose(...)`.

Not called by `ApplicationPackageService.prepare`.

---

## 4. Evidence-pack contract

`CvPositioningPack` (`cv_pack.py`):

- Employer needs with DIRECT / RELATED / UNSUPPORTED (employer context)
- Argument spine, forbidden claims, trajectory, methodology flag
- Claimable DIRECT labels vs related **profile** labels vs unsupported labels
- Candidate evidence snippets from CareerProfile refs + Master summary
- Selected existing Master highlights (reordered, not invented)
- Selected project locked bodies + technologies

`OpportunityAssessment` is accepted and **ignored** (`assessment_ignored=True`).
JD excerpts sit only on `PackedNeed.employer_excerpt`.

---

## 5. Rewrite surface vs locked Master

**LLM may write:** Professional Summary; optional one-line project relevance
(`*Relevant to this role: …*` inserted above the locked project body).
Project relevance is **implemented**, not deferred.

**Deterministic:** highlight *selection/reorder* of existing Master bullets;
skills line from TailoringPlan; methodology include/exclude from
`PositioningPlan.include_methodology`.

**Locked:** experience headings/dates/bullets; project factual bodies;
courses; certifications; contact content (header target-role overlay is the
existing Master-adapt behaviour).

---

## 6. Failure policy

Fail closed.

| Failure | Result |
|---------|--------|
| Provider / unexpected composer exception | `CvPositioningProviderError` |
| Empty/malformed structured output | `CvPositioningValidationError` |
| Forbidden / unsupported / invented metric or years | `CvPositioningValidationError` |
| Unknown project claim in the Professional Summary | `CvPositioningValidationError` |
| Invalid **optional** project relevance line | Line discarded; remainder revalidated; success only if remainder passes |
| Locked section rewrite | `CvPositioningValidationError` |

There is **no** successful return that substitutes the Master summary.

---

## 7. FR-014 relationship

M3 validators are local composer guards. They are not Truth PASS.
FR-014 remains `cic truth validate-package` / `evaluate_package_truth`.
M5 still requires Truth PASS.

---

## 8. Production wiring status

| Surface | Live after M3? |
|---------|----------------|
| Catalogue in TailoringPlan planner | Yes (M2) |
| `BoundedCvPositioningService` | Implemented, callable, **not** in prepare |
| Master-adapt optional overrides | Yes, unused by prepare |
| Package CV summary | Still Master baseline |
| Package methodology | Still globally omitted |
| Cover letter | Unchanged |
| PositioningPlan import in prepare/CLI | No |

---

## 9. E1–E4 (fixture composer)

See [document_positioning_m3_inspection.md](document_positioning_m3_inspection.md).
Regenerate with `python scripts/inspect_m3_cv.py` (`PYTHONPATH=src`).

| Job | Result |
|-----|--------|
| E1 | AI-lead; Python/REST/LLM DIRECT; GCP/MLOps/DevOps unclaimed; methodology on; RAG + CIC packed |
| E2 | RAG DIRECT; AWS related; Bedrock/chatbot unclaimed; methodology on; RAG project packed |
| E3 | GPU/Linux/HPC unclaimed; methodology off; employment body unchanged; truthful AI projects still packed |
| E4 | `full_chapters`; Claude/GitHub Copilot unclaimed; methodology on |

Fixture prose is pack-faithful, not recruiter-literary. Project relevance lines
currently collapse to generic Python delivery. That is an inspection limitation,
not M5 acceptance.

---

## 10. Tests

`tests/unit/document_positioning/test_m3_cv_positioning.py` (A–X plus Bedrock
relevance) and `test_eval_jobs_m3.py`.

`python -m pytest tests/unit/document_positioning -q` → **98 passed**.

M0–M2 tests were not weakened. Planner/package regressions in this slice
stayed green (`test_master_adapt`, `test_deterministic_planner`,
`test_production_integration`).

---

## 11. Definition of Done

- [x] Current production CV generation path audited
- [x] Existing FR-006c behaviour audited
- [x] Positioning evidence-pack contract implemented
- [x] PositioningPlan controls CV argument
- [x] Bounded LLM composition implemented for approved surface
- [x] Professional Summary can be role-positioned
- [x] Highlight positioning/selection implemented within approved bounds
- [x] Project relevance line implemented (optional; fixture emits when overlap exists)
- [x] Methodology obeys per-job PositioningPlan policy on the positioning path
- [x] Locked Master employment content preserved
- [x] Locked Master project bodies preserved
- [x] Courses/certifications/contact preserved
- [x] DIRECT claims allowed
- [x] RELATED requested claims forbidden
- [x] UNSUPPORTED claims forbidden
- [x] Deterministic post-generation validation implemented
- [x] LLM/provider/validation failure is fail-closed
- [x] No silent generic-summary success fallback
- [x] FR-014 relationship accurately documented
- [x] E1–E4 offline inspection completed
- [x] Maincode checked specifically for over-positioning
- [x] CSK checked specifically for Bedrock/chatbot overclaim
- [x] Repurpose checked for trajectory positioning
- [x] Focused M3 tests pass
- [x] Existing relevant FR-006/planner/package regressions pass
- [x] M0–M2 semantic tests not weakened
- [x] No final M5 A/B benchmark run
- [x] No CSK live package regeneration
- [x] No SEEK / Playwright / AAS
- [x] M3 acceptance report written
- [x] M3 inspection report written
- [x] M3 learning note written
- [x] Documentation/changelog updated
- [x] Owner review required before M4
