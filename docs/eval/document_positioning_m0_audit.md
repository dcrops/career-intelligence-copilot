# Document Positioning M0 — Engineering Audit

**Status:** **Complete — pending owner review**  
**Date:** 2026-08-20  
**Scope:** Architecture/audit only. No production document-generation behaviour
change. No CSK regeneration. No SEEK/Playwright/AAS.  
**Programme:** [document_positioning_remediation.md](document_positioning_remediation.md)

M0 is not PASS merely because tests pass. Owner review is required before M1.

---

## 1. What was inspected

- `ApplicationPackageService.prepare` and `cic package prepare`
- `CvGenerationService.generate` / `_resolve_summary` / `adapt_master_cv_markdown`
- `DeterministicTailoringPlanner._classify_against_profile`
- Cover-letter `select_projects_for_letter`, `build_cover_letter_evidence_pack`,
  `BoundedCoverLetterService.compose` / `validate_composed_paragraphs`
- FR-014 `TruthValidationService`, `evaluate_package_truth`,
  `cic truth validate-package`
- FR-006b golden suite docs and `manual_validation/jobs/` + `outputs/`
- CSK live artefacts under gitignored `data/opportunities/artifacts/`
- `AssessmentSummary.key_alignments`
- Existing Azure→ADF test in `tests/unit/test_document_quality_refinements.py`

---

## 2. Current production architecture (verified)

```
cic package prepare
  ApplicationPackageService.prepare   # src/career_intelligence/application_package/service.py
        │
        ├─ TailoringPlanService.plan  (deterministic; DeterministicTailoringPlanner)
        ├─ CvGenerationService.generate
        │     adapt_from_master=True, rewrite_summary=False   # forced ~lines 240–244
        │     omit_methodology=True hardcoded in generate()   # generation_service.py:155
        │     Master Markdown chassis + TailoringPlan project order + skills line
        │     NO LLM
        │
        └─ CoverLetterPlanService.plan  (deterministic)
              BoundedCoverLetterService.compose               # bounded_generation.py:105
                evidence pack (deterministic)
                one CoverLetterComposer call (OpenAI in production; fixture in pytest)
                validate_composed_paragraphs (forbidden phrases / invented metrics)
                NO Truth call inside compose (assess_truth is separate)
        │
        └─ write drafts + manifest + export PDFs
              owner_review_required=True
              never Submit
```

FR-014 is a **separate** gate: `cic truth validate-package` →
`evaluate_package_truth` (`src/career_intelligence/truth_validation/gates.py`).
The agent path may sequence prepare then truth. Prepare does not block on Truth.
Bounded `compose()` does not call `assess_truth()`.

**Authoritative facts:** CareerProfile (Class A evidence) and Master CV
employment/project prose. JobAnalysis is employer context. JD technologies are
not candidate skills. `AssessmentSummary.key_alignments` is unconstrained
free text and is **not** consumed by CV or cover-letter generation.

**Deterministic today:** TailoringPlan, Master-adapt, cover-letter plan, evidence
pack, Truth (when run), package fingerprints.

**LLM today:** cover-letter paragraph composition only (production). CV has no
LLM on the package path. FR-006c theme-aware summary is unused on that path.

### CV — how TailoringPlan influences the artefact

`adapt_master_cv_markdown`
([src/career_intelligence/cv_generation/master_adapt.py](../../src/career_intelligence/cv_generation/master_adapt.py)):

- Header target role from the posting title (`_adapt_header`)
- Rebuild Core Skills from `skills_to_promote` + limited additional (`_render_skills_section`)
- Reorder/subset Featured AI Projects from `plan.projects_to_emphasise` names
  (`_render_projects_section`); project bodies copied from Master
- Drop `## AI Engineering Methodology` when `omit_methodology=True`
  (production always True at `generation_service.py:155`)
- Copy remaining H2 sections verbatim from Master: Professional Summary,
  Selected Engineering Highlights, Experience, Courses, Certifications,
  Earlier Experience

`CvGenerationService._resolve_summary` (`generation_service.py:163–186`)
returns `master_baseline` whenever `adapt_from_master` is true.
`compose_theme_aware_summary` runs only in the non-adapt branch.
**FR-006c is bypassed on the production package path.**

Planner classification (`deterministic_planner.py`):

- `_direct_match` is exact or compatible token-subset (`:310`)
- `_related_match` is exact membership in `_RELATED_CAPABILITY_GROUPS` (`:94`, `:342`)
- Skills that do not support a candidate-backed JD technology land in
  `skills_not_emphasised` (`:807–819`)

### Cover letter

Plan → `build_cover_letter_evidence_pack` → one LLM call →
`validate_composed_paragraphs` → deterministic header/signature.

Experience packing always walks testing employment, then data-engineering
employment, then independent AI (`evidence_pack.py` `_select_experience` `:224`
and `_CHAPTER_ORDER` `:67`).

Project selection defaults to **two** projects unless a third scores at least
as high as the second and ≥ 6
(`project_selection.py` `:366–372`).

Opening quality is prompt/pack policy only
(`cover_letter_bounded_v2.md`; `evidence_pack.py` ~`:469`).
`bounded_generation._FORBIDDEN_PHRASES` (`:39`) does not include generic
“particularly relevant to my background”.

---

## 3. Root-cause verification

| Claim | Classification | Evidence |
|-------|----------------|----------|
| Master-adapt suppresses role positioning | **PROVEN** | `adapt_master_cv_markdown` copies remaining H2 sections; plan themes unused for summary/highlights/experience prose |
| FR-006c bypassed on Master-adapt path | **PROVEN** | `_resolve_summary` returns `master_baseline` when `adapt_from_master` (`generation_service.py:170`) |
| RAG acronym vs Retrieval-Augmented Generation mismatch | **PROVEN** | `_direct_match("RAG", "Retrieval-Augmented Generation")` fails token subset; LLM related group contains `"retrieval augmented generation"` but not `"rag"` (`deterministic_planner.py:94–107`) |
| AWS / Bedrock: no claim Bedrock, but AWS not promoted | **PROVEN** | No AWS/Bedrock related group. Bedrock is `unsupported`. AWS then sits in `skills_not_emphasised` (“does not support a candidate-backed JD technology”, `:807–819`) |
| Cover-letter two-project rule | **PROVEN** | Designed cap: `return selected[:2]` unless third score ≥ second and ≥ 6 (`project_selection.py:366–372`) |
| Mandatory testing → DE → AI packing | **PROVEN** | `_select_experience` always adds testing, DE, then independent AI (`evidence_pack.py:224–251`) |
| Opening-quality enforcement gap | **PROVEN** | Prompt/pack forbids generic relevance; `_FORBIDDEN_PHRASES` does not enforce it |
| `key_alignments` free-text integrity | **PROVEN** | `AssessmentSummary.key_alignments: list[str]` (`opportunity_assessment/models.py:202`). Local CSK `assessment.json` summary claimed “AWS Bedrock and Python” while `commercial_fit` gapped Bedrock. Live artifact is gitignored; not the tracked freeze |
| Global `omit_methodology=True` | **PROVEN** | Hardcoded in `CvGenerationService.generate` (`:155`) regardless of job needs |
| Truth runs inside `cic package prepare` | **REJECTED / PLAN NEEDS CORRECTION** | Prepare writes drafts. Truth is `cic truth validate-package` / `evaluate_package_truth`. `compose()` does not call `assess_truth()` |
| CSK pipeline JSON is a tracked freeze | **PARTIALLY PROVEN** | Live `data/opportunities/artifacts/opp_01M0E6GQ9XQH9DK9N5T0MS67N0/` is gitignored. Tracked freeze is `tests/fixtures/document_positioning/eval_jobs/02_csk_mixed_fit/` |

Plan correction (not a rejected product diagnosis): document generation does
**not** currently consume `key_alignments`. Still constrain it later so
PositioningPlan cannot inherit false alignments.

**Catalogue vs live planner:** v1 is not a drop-in for
`_RELATED_CAPABILITY_GROUPS`. The production Azure group also includes
Microsoft Fabric and other pipeline phrases. M2 must not shrink those live
relations when wiring the catalogue.

---

## 4. Catalogue v1 (implemented, unused in production)

`career_intelligence.document_positioning.classify_requirement`

See programme doc § 5. Tests:
`tests/unit/document_positioning/test_catalogue_v1.py` and
`tests/unit/document_positioning/test_m0_invariants.py` (17 passed, 2026-08-20).

---

## 5. M1 tests deferred (abstraction does not exist yet)

- PositioningPlan builder on a synthetic specialist job: AWS RELATED, Bedrock
  forbidden, RAG DIRECT, chatbot UNSUPPORTED
- Adoption-shaped job selects `trajectory_mode=full_chapters`
- Production planner still uses `_RELATED_CAPABILITY_GROUPS` until M2 — do not
  treat catalogue tests as proof the live CV planner is fixed

---

## 6. Risks / open questions for owner

1. Confirm E1 is Allura G1 rather than live Repurpose AI Engineer.
2. Confirm CSK tracked freeze (`job.txt`) is sufficient given gitignored live
   artifacts.
3. M3 fail-closed on LLM summary failure will block package prepare (same as
   today's letter). Confirm that is acceptable vs Master-summary fallback
   (rejected in the approved plan).
4. Catalogue identity `chatbot` groups several conversational phrases. If a
   future JD uses “conversational interfaces” for document Q&A, RELATED-to-RAG
   is **not** in v1 on purpose. Adding it requires a new explicit relation and
   M1 review — not a CSK patch.
5. Catalogue v1 is not a drop-in for `_RELATED_CAPABILITY_GROUPS` (Microsoft
   Fabric and other Azure-group members are not in v1). M2 must not shrink live
   planner relations.
6. `key_alignments` is unused by document generation today. M1 should still
   treat it as untrusted so PositioningPlan does not inherit false alignments.

---

## 7. Definition of Done — M0

- [x] Current production architecture verified against code
- [x] Approved assumptions checked against repository
- [x] Positioning terminology frozen
- [x] Capability catalogue v1 defined
- [x] DIRECT / RELATED / UNSUPPORTED explicit
- [x] Four-job evaluation set identified and frozen
- [x] M5 rubric and release threshold frozen
- [x] Semantic catalogue tests added
- [x] No CSK-specific production hacks
- [x] No production positioning implementation
- [x] No CV/cover-letter regeneration
- [x] No SEEK/AAS/Playwright
- [x] This audit report
- [x] Learning note
- [x] Documentation/changelog updated
- [ ] Owner review before M1
