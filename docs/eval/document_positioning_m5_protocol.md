# Document Positioning M5 — Frozen Evaluation Protocol

**Status:** Frozen before comparative judgement. Official run:
`m5_restart_after_m3_optional_relevance_2026-08-20`.  
The first live attempt is **INVALIDATED — PRE-BENCHMARK PRODUCT BLOCKER**.  
**Date:** 2026-08-20  
**Programme:** [document_positioning_remediation.md](document_positioning_remediation.md)

This document is the executable M5 contract. Owner overall scores exist.
Mapping is revealed. Formal result is FAIL on the Truth gate
([document_positioning_m5_unblinded.md](document_positioning_m5_unblinded.md)).
The threshold, jobs, and Truth rule were not changed after seeing results.

---

## 1. What M5 asks

M0–M4 built a positioning architecture. M5 asks whether it produces better
application documents than a strong evidence-constrained LLM using the same
candidate and employer facts.

A CIC loss is a valid result. Do not manipulate the experiment to make CIC
win.

---

## 2. Protocol verification against the M0 freeze

M0 § 7 froze:

| Item | Frozen value | M5 verification |
|------|----------------|-----------------|
| Jobs | E1 Allura, E2 CSK, E3 Maincode, E4 Repurpose Adoption | Unchanged. Tracked fixtures only. |
| Evidence | One pack per job from CareerProfile + Master facts + that job | One `FactualEvidenceBundle` per job, hashed |
| A | CIC after remediation | M3 CV + M4 letter composers, unwired from prepare |
| B | Strong LLM using the same pack and forbidden claims | Independent positioning from the same factual bundle |
| Truth | Both sides FR-014 PASS | `TruthValidationService` + external-use gate |
| Rubric | 15s scan, positioning, evidence, transfer, gaps, specificity, clarity, concision, submit preference | Owner scores `preferred` / `tied` / weaker as Version A/B/Tie |
| Release | CIC preferred or tied on ≥ 3/4 and zero CIC Truth failures | `compute_release_result`; CSK-only is not acceptance |
| Blind | Shuffled A/B | Per-job randomised mapping in `hidden/` |

### Facts vs policy (clarification of M0 “exactly that pack”)

M0 said B uses “exactly that pack”. The M5 execution prompt requires B to
remain a genuinely strong baseline and **not** be told CIC’s selection
decisions (for example “select RAG + nbn AWS because CIC selected them”).

M5 therefore splits the pack:

| Shared with A and B | CIC-only (A) |
|---------------------|--------------|
| CareerProfile candidate facts | `argument_spine` |
| Master CV factual sections | `selected_highlights` / `selected_projects` |
| Frozen advertisement + JobAnalysis employer fields | `selected_sources` / letter opening-body-closing facts |
| DIRECT / RELATED / UNSUPPORTED classifications | `trajectory_mode` as a writer instruction |
| Forbidden claims and truth rules | `include_methodology` as a writer instruction |

Both systems see the same truthful evidence. CIC applies deterministic
selection internally. B independently chooses what to emphasise.

This is not a change to the release threshold, jobs, or Truth gate.

If this split is rejected, the entire comparison set must be invalidated and
re-run. Do not mix the two interpretations.

---

## 3. Frozen jobs (do not substitute)

| ID | Role | Tracked freeze |
|----|------|----------------|
| E1 | Allura AI Engineer | `manual_validation/jobs/001_strong_ai_engineer.txt`, `manual_validation/outputs/001_strong_ai_engineer.json` |
| E2 | CSK specialist | `tests/fixtures/document_positioning/eval_jobs/02_csk_mixed_fit/` (`opp_01M0E6GQ9XQH9DK9N5T0MS67N0`) |
| E3 | Maincode AI Infrastructure | `manual_validation/jobs/012_maincode_ai_infrastructure_engineer.txt`, `manual_validation/outputs/012_maincode_ai_infrastructure_engineer.json` |
| E4 | Repurpose AI Adoption Specialist | `manual_validation/jobs/008_repurpose_it_ai_adoption_specialist.txt`, `manual_validation/outputs/008_repurpose_it_ai_adoption_specialist.json` |

Shared candidate authority: `data/career_profile.yaml` and
`career-documents/cv/master_ai_engineer_cv.md`.

Do not use gitignored live CSK artefacts. Do not edit advertisements.

Module: `career_intelligence.document_positioning.benchmark.jobs.FROZEN_EVAL_JOBS`.

---

## 4. Generation protocol (frozen before judgement)

Identifier: `document_positioning_m5_v1`.  
Official comparison run: `m5_restart_after_m3_optional_relevance_2026-08-20`.

The first live generation attempt is **INVALIDATED — PRE-BENCHMARK PRODUCT
BLOCKER**. Preserve it only under
`docs/eval/document_positioning_m5/invalidated_pre_benchmark_blocker/`.
Do not reuse its documents, retries, or quality observations.

After that invalidation, M3 received a bounded optional-relevance correction
(prompt + drop invalid optional lines + revalidate remainder). Product
behaviour was then frozen again. This restart uses the same jobs, evidence
rules, models, retry policy, rubric, and ≥ 3/4 + zero CIC Truth-failure
threshold. No further product tuning is allowed once this restart begins.

| Side | Composer | Model | Temperature |
|------|----------|-------|-------------|
| A CIC CV | `OpenAICvPositioningComposer` via `BoundedCvPositioningService` | `gpt-4o-mini` (composer default) | 0.2 |
| A CIC letter | `OpenAICoverLetterPositioningComposer` via `BoundedCoverLetterPositioningService` | `gpt-4o-mini` (composer default) | 0.2 |
| B baseline | `OpenAIBaselineComposer` | `gpt-4o` | 0.2 |

Baseline prompt: `src/career_intelligence/document_positioning/prompts/baseline_positioning_v1.md`.

Retry policy (symmetric; defined before comparative judgement):

- Maximum **2** retries after the first attempt
- Retry only provider / structured-output / local-validation failure
- **Never** retry to improve comparative quality
- **Never** regenerate one side because the other looks stronger

CIC local validators still fail closed. They are not FR-014 PASS.

Offline fixture composers exist only to test the harness. They are **not**
the quality candidate.

---

## 5. FR-014

Every A and B document pair is evaluated with
`TruthValidationService.validate_markdown` and
`evaluate_report_for_external_use`.

Job-analysis technology names are passed only as `context_technology_labels`
(scan lexicon). They never authorise Class A capability.

Local M3/M4 validation is recorded separately and is not the Truth result.

Zero CIC Truth failures are allowed for release. A baseline Truth failure is
recorded honestly and is not silently repaired.

---

## 6. Blind comparison

For each job, Version A and Version B are a random permutation of CIC and
baseline. Owner-facing files must not contain generator identity.

Hidden mapping: `docs/eval/document_positioning_m5/hidden/ab_mapping.json`.

**Do not open that file until scoring is complete.**

---

## 7. Rubric

For each job the owner marks each row as Version A preferred, Version B
preferred, or Tie:

1. 15-second scan
2. Role positioning
3. Evidence selection
4. Transfer argument
5. Honest gaps
6. Specificity
7. Clarity
8. Concision
9. Overall submit preference

The **overall submit preference** is the job result. Do not derive it from a
weighted sum of the other rows.

15-second scan notes are owner judgement, not an LLM judge.

---

## 8. Release threshold (frozen)

CIC passes M5 if and only if:

1. CIC is preferred **or** tied on **≥ 3 of 4** jobs, **and**
2. CIC Truth failures = 0.

Interpretations that are forbidden after seeing results:

- 2/4 is not “basically passed”
- A Truth failure is not “minor”
- CSK-only success is not acceptance

---

## 9. Control notes (do not change scoring because of them)

- **E1 Allura** — stronger direct AI fit; GCP/MLOps/DevOps must not become claims.
- **E2 CSK** — transfer (AWS related to Bedrock, RAG direct, no chatbot claim). Necessary but not sufficient.
- **E3 Maincode** — stretch control. Persuasive restraint is allowed. Do not punish honesty because the other version sounds more confident.
- **E4 Repurpose Adoption** — trajectory may be the argument. Do not reward a boring chronology by default, and do not reward stuffing two AI projects if they miss the job.

Truth is mandatory. Truth alone is not sufficient. A pretty hallucination still fails.

---

## 10. After owner scores

Reveal the mapping. Compute `compute_release_result`. Then:

- If pass: recommend READY FOR M6. Do not start M6 until owner approval.
- If fail: failure analysis only. Do not implement fixes in the same step.

Unblinded result (2026-08-20): original execution **FAIL** on the Truth gate.
Quality 4/4 CIC preferred. Owner close-out later recorded M5 COMPLETE without
a fresh end-to-end rerun — see
[document_positioning_m5_acceptance.md](document_positioning_m5_acceptance.md).

---

## 11. Out of scope

- Wiring M3/M4 into `cic package prepare`
- Tuning M3/M4/prompts after seeing outputs
- Changing E1–E4, the rubric, or the threshold
- Regenerating the CSK live package
- SEEK / Playwright / AAS
- Submitting any application
- Gamma presentation
