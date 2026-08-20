# Document Positioning M1 — Engineering / Acceptance Report

**Status:** **Complete — pending owner review before M2**  
**Date:** 2026-08-20  
**Scope:** PositioningPlan contract + deterministic builder only.  
**Programme:** [document_positioning_remediation.md](document_positioning_remediation.md)

No production document-generation behaviour change. No CSK regeneration.
No SEEK / Playwright / AAS. PositioningPlan is **not** imported by
`cic package prepare`.

Owner review is required before M2.

---

## 1. What was built

Typed `PositioningPlan` and `build_positioning_plan(job, profile, assessment=None)`.

The plan answers: *what is the strongest truthful case for this job?*  
It does not write CV or cover-letter prose. It does not call an LLM.

Module: `career_intelligence.document_positioning`

| File | Role |
|------|------|
| `models.py` | Contract types |
| `catalogue.py` | M0 identities + alias scan helpers |
| `evidence.py` | CareerProfile refs only |
| `policies.py` | trajectory_mode + include_methodology |
| `builder.py` | Need extraction, classify, spine, forbidden claims |
| `render.py` | Owner-inspection Markdown |

Inspection artefact:
[document_positioning_m1_inspection.md](document_positioning_m1_inspection.md)
(regenerate with `python scripts/inspect_positioning_plans.py`).

---

## 2. Evidence sources

**Employer needs:** `JobAnalysis` technologies, then catalogue identities
mentioned in experience requirements / responsibilities. JD text never becomes
a candidate skill.

**Candidate evidence:** `CareerProfile` skills, skill evidence refs, matching
certifications, and (for catalogue identities) limited extra
experience/project refs. Unknown exact matches use the skill + its own refs
only, so a Python need does not dump every Python project.

**Ignored:** `OpportunityAssessment.summary.key_alignments` and all other
assessment free text. The builder accepts `assessment` so tests can prove it
is unused.

E2 structured freeze (posting was not edited):
`tests/fixtures/document_positioning/eval_jobs/02_csk_mixed_fit/job_analysis.json`.

---

## 3. Policies (deterministic, no scores)

### trajectory_mode

| Condition | Mode |
|-----------|------|
| `role_family == ai_adjacent` and profile has testing + DE + independent AI employment chapters | `full_chapters` |
| `data_engineering` or `software_engineering` and testing employment | `bridge` |
| otherwise (including `ai_engineering`) | `ai_lead` |

No numeric thresholds. Frozen eval jobs: E4 is `full_chapters`; E1–E3 are
`ai_lead`. `bridge` is covered by a synthetic software-engineering job.

### include_methodology

True when the profile has `engineering_methodology` **and** structured employer
text contains evaluation / orchestration / governance / reliability (or
`risk management` / `human in the loop`). Not a global omit. Not employer-named.

---

## 4. Known catalogue limits (not M1 defects)

v1 does not alias LLM → RAG. E1 therefore lists `LLM` as UNSUPPORTED even
though the profile has Retrieval-Augmented Generation. Expanding that relation
is M2 catalogue work, not a CSK patch.

Unknown JD labels (GPU, Copilot, Claude) cannot become RELATED dynamically.

---

## 5. Tests

- M0 catalogue + isolation tests preserved
- `tests/unit/document_positioning/test_positioning_plan.py` (A–S)
- `tests/unit/document_positioning/test_eval_jobs_m1.py` (E1–E4)

`python -m pytest tests/unit/document_positioning -q` → **41 passed**.

Related regressions (planner Azure/ADF, package production integration):
**18 passed**. Production modules still do not import `document_positioning`.

---

## 6. Definition of Done — M1

- [x] Typed PositioningPlan contract
- [x] Deterministic builder
- [x] No LLM
- [x] DIRECT / RELATED / UNSUPPORTED
- [x] Evidence provenance
- [x] Employer requirements cannot become candidate evidence
- [x] key_alignments cannot independently establish candidate truth
- [x] argument_spine deterministic
- [x] forbidden_claims deterministic
- [x] trajectory_mode deterministic
- [x] include_methodology deterministic
- [x] Four frozen jobs inspected
- [x] Synthetic specialist acceptance case
- [x] Unit tests pass
- [x] Existing relevant tests remain passing
- [x] Production package generation unchanged
- [x] Not wired into `cic package prepare`
- [x] No CV/cover-letter regeneration
- [x] No SEEK/AAS/Playwright
- [x] This report
- [x] Learning note
- [x] Documentation/changelog updated
- [ ] Owner review before M2
