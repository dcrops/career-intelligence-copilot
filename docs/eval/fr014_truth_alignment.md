# FR-014 Truth Alignment — Post-M5 False-Positive Correction

**Status:** **ACCEPTED** (owner close-out 2026-08-20)  
**Date:** 2026-08-20  
**Kind:** Bounded FR-014 detector correction (not a new FR; freeze not reopened)  
**Validator version:** `fr014-truth-alignment-2`  
**Discovered by:** Document Positioning M5 official run
`m5_restart_after_m3_optional_relevance_2026-08-20`

This report is **not** a fresh end-to-end M5 rerun. The original benchmark
execution remains historically **FAIL** under the then-current validator.
Owner close-out recorded M5 COMPLETE from quality 4/4 plus Truth PASS on
unchanged CIC artefact replay through the corrected validator — see
[document_positioning_m5_acceptance.md](document_positioning_m5_acceptance.md).

---

## 1. Problem statement

The frozen M5 CIC artefacts contained five named FR-014 Truth-gate findings
(`llm`, `rag`, `awsbedrock`, `intesting` × 2). A subsequent read-only forensic
audit found **zero genuine unsupported candidate claims** among those five.
FR-014 was rejecting truthful wording because:

1. Capability identity was split between the M2 positioning catalogue and the
   FR-014 detector.
2. Explicit denial (`I do not claim…`) was classified as a positive Class A
   claim.
3. Multi-domain duration lists were truncated at the first comma
   (`10 years in testing` → `intesting`).

The correction is fail-closed detector hardening. It does not weaken Truth,
tune M3/M4 output, patch M5 artefacts, or rewrite the historical M5 result.

---

## 2. Historical M5 result (unchanged)

Quality: CIC preferred 4/4 (threshold ≥ 3/4).  
Truth: CIC pair failures = 3 (zero allowed).  
Formal result of the original execution: **M5 FAIL — Truth gate.**

| Job | Historical CIC CV | Historical CIC letter |
|-----|-------------------|-----------------------|
| E1 | PASS | FAIL — `llm` |
| E2 | REVIEW-REQUIRED — `intesting` | FAIL — `rag`, `awsbedrock` |
| E3 | PASS | PASS |
| E4 | REVIEW-REQUIRED — `intesting` | PASS |

Sources:
[document_positioning_m5_acceptance.md](document_positioning_m5_acceptance.md),
[document_positioning_m5_unblinded.md](document_positioning_m5_unblinded.md).

---

## 3. Forensic evidence

Engineering interpretation of the five named findings:

| Finding | Job | Classification |
|---------|-----|----------------|
| `llm` | E1 letter | False positive — canonical identity mismatch |
| `rag` | E2 letter | False positive — canonical identity mismatch |
| `awsbedrock` | E2 letter | False positive — negation classified as claim |
| `intesting` | E2 CV | False positive — duration-list truncation |
| `intesting` | E4 CV | False positive — duration-list truncation |

Genuine unsupported candidate claims among those five: **0**.

Secondary (not a named Truth-gate finding): E2 letter
`review_required` project/delivery span
`andmaintainedenterprisedatapipelinesusingawsservicespythonandsqlensuringreliableproductiondatasystems`.
The employer (nbn) is named in the **previous** sentence. This finding already
existed in frozen `E2_truth.json`. It was deferred from RC-1–RC-3 and is
corrected in § 12 by a bounded previous-sentence employment bind.

---

## 4. Root causes

**RC-1 — Canonical capability identity split.**  
M2 already treats `LLM` / `LLMs` / `LLM application development` as identity
`llm`, and `RAG` / `Retrieval-Augmented Generation` as identity `rag`. FR-014
matched catalogue display strings and tiny alias groups only, so a generated
`LLM` / `RAG` claim could fail against profile evidence that used the longer
canonical phrase.

**RC-2 — Negation classified as candidate claim.**  
`_CANDIDATE_CUES` matched `I do` inside `I do not claim`, so a truthful Bedrock
denial became Class A unsupported.

**RC-3 — Multi-domain duration list truncation.**  
`_YEARS` captured through the first comma, normalised `10 years in testing` to
`intesting`, and dropped the remaining career-chapter list. Authoritative
chronology supports the **overall** engineering span, not a 10-year testing
specialty.

---

## 5. Files changed

### Detector

- `src/career_intelligence/truth_validation/canonical_identity.py` **(new)**
- `src/career_intelligence/truth_validation/catalogue.py`
- `src/career_intelligence/truth_validation/detection.py`
- `src/career_intelligence/truth_validation/extended_claims.py`
- `src/career_intelligence/truth_validation/aliases.py`
- `src/career_intelligence/truth_validation/models.py`

### Tests

- `tests/unit/truth_validation/test_truth_alignment.py` **(new)**
- `tests/unit/truth_validation/test_career_positioning_duration.py`

### Documentation

- this report; [fr014_truth_alignment_learning.md](fr014_truth_alignment_learning.md)
- [08_implementation_notes.md](../08_implementation_notes.md)
- [07_testing_strategy.md](../07_testing_strategy.md)
- [04_functional_specification.md](../04_functional_specification.md)
- [11_changelog.md](../11_changelog.md) § 1.170
- [00_repository_guide.md](../00_repository_guide.md)
- [document_positioning_remediation.md](document_positioning_remediation.md)
- [document_positioning_m5_acceptance.md](document_positioning_m5_acceptance.md)
- [fr014_recruiter_document_truth_validation.md](fr014_recruiter_document_truth_validation.md)
- [fr014_m4_claim_validation.md](fr014_m4_claim_validation.md)
- [adr/006_recruiter_document_truth_validation.md](../adr/006_recruiter_document_truth_validation.md)
- [10_roadmap.md](../10_roadmap.md)
- [AGENTS.md](../../AGENTS.md)

**Unchanged:** M3/M4 composers, prompts, and local validators; M5 owner scores;
hidden A/B mapping; generated CIC/baseline documents; `cic package prepare`
wiring.

---

## 6. Architecture decision

Prefer one canonical identity authority:

```
FR-014  ──identity only──►  document_positioning.catalogue
                               (resolve_identity / aliases_for_identity)
TailoringPlan / PositioningPlan ──►  same catalogue
```

Adapter: `career_intelligence.truth_validation.canonical_identity`.

It imports **only** `resolve_identity` and `aliases_for_identity`. It does
**not** import `classify_requirement`, RELATED maps, or `may_claim_requested`.

**Identity ≠ permission.** AWS RELATED AWS Bedrock remains legitimate related
*planning* evidence. It does not authorise a candidate claim of AWS Bedrock
experience.

**Dependency direction:** Truth → positioning catalogue submodule. The
catalogue module does not import `truth_validation`. Imports go to
`document_positioning.catalogue`, not the package `__init__`, so there is no
circular-import cycle.

**Why not an FR-014-only LLM/RAG alias table:** that would recreate two
competing identity systems. M2 already models those aliases.

**Why M3/M4 did not change:** the false positives were validator defects, not
composer defects. The generated wording was truthful.

`VALIDATOR_VERSION` is now `fr014-truth-alignment-2`. Historical freeze
recorded `fr014-m4-deterministic-1`; that freeze is not reopened.

---

## 7. Implementation summary

1. Catalogue support matching uses `identity_match_keys()` (M2 aliases +
   existing FR-014 js/ts groups). RELATED identities are excluded.
2. Technology lexicon includes domain skills and M2 scan aliases for evidenced
   identities, longest-phrase occupancy first, so `LLM` does not steal
   `LLM application development`.
3. Scan-only well-known labels `AWS Bedrock` / `Bedrock` so those spans are
   detected. Detection is not authorisation.
4. Candidate cue `i do` is now `i do(?!\s+not)`. Per-span denial uses
   `_DENIAL_BEFORE_SPAN` in the local clause before the span; `, but` / `;`
   start a new clause so a later positive claim still fires.
5. Duration extraction extends comma-separated domain lists before
   classification, without swallowing `, I later…`. Two or more career-chapter
   markers resolve to `overall_engineering_experience`. Single-domain inflation
   still maps to the domain key and remains fail-closed.
6. Detected technology `object_key` is the shared canonical identity when one
   exists (`Bedrock` → `awsbedrock`).

---

## 8. Canonical identity behaviour

| Evidence | Claim | Result |
|----------|-------|--------|
| LLM application development | LLM | supported |
| LLM application development | LLMs | supported (`llms` is an explicit M2 alias) |
| Retrieval-Augmented Generation | RAG | supported |
| Retrieval-Augmented Generation | Retrieval-Augmented Generation | supported |
| Java | JavaScript | unsupported / blocking |
| AWS | AWS Bedrock experience | unsupported / blocking |

`large language models` was **not** added. M2 does not model that phrase.

---

## 9. Negation behaviour

| Sentence | Result |
|----------|--------|
| I have direct experience with AWS Bedrock. | Class A; blocking if no Bedrock evidence |
| I have worked extensively with AWS Bedrock. | Class A; blocking |
| I do not have direct experience with AWS Bedrock. | not a positive Bedrock claim |
| I do not claim direct experience with AWS Bedrock. | not a positive Bedrock claim |
| Although I have not used AWS Bedrock directly, I have AWS experience. | Bedrock not DIRECT; AWS independent |
| I do not claim direct Bedrock experience, but I have delivered production systems using Bedrock. | later positive claim still blocks |

Sentence-global “if `not` appears, ignore” was rejected.

---

## 10. Duration behaviour

The parser keeps the complete list, then classifies:

- `over 10 years in testing, automation, data engineering, and applied AI engineering`
  → `overall_engineering_experience` (supported when chronology supports the
  career floor)
- `10+ years across testing, automation, data engineering and applied AI engineering`
  → same (pre-existing `across` path retained)
- `over 10 years in AI engineering` / `10+ years of applied AI engineering` /
  `12 years of data engineering` → domain keys; **blocking** unless domain
  tenure is actually evidenced

There is no hardcoded `intesting` → overall mapping.

---

## 11. Header / target-role behaviour

A standalone employer target-role title containing AWS Bedrock / Agentic AI /
Chatbots is **not** Class A. Positive candidate prose claiming Bedrock after
that header still blocks. Target-role tailoring was not removed.

Employer-requirement language (`The role requires AWS Bedrock experience.`)
remains Class B and is not candidate evidence.

---

## 12. Secondary E2 previous-sentence employment bind

**Implemented** (`fr014-truth-alignment-2`). Same-sentence
`At nbn Australia, I developed…` already bound to employment evidence. The
frozen E2 letter names nbn in the immediately previous sentence, then restates
the pipeline highlight.

The binder now consults **only** that immediately previous sentence, and only
when it explicitly names **exactly one** known employer. Highlight-token
overlap against the Career Profile catalogue remains the evidence check. The
previous sentence is context, not evidence. Named-project binding in the
current sentence is unchanged and still takes precedence.

Not implemented: paragraph walk, two-sentence lookback, pronouns
(`this experience`, `the company`), or authorising arbitrary work because an
employer was named nearby. Invented delivery after an nbn sentence remains
unresolved / fail-closed. Two named employers in the previous sentence do
not auto-bind.

M3/M4 were not changed. The original M5 execution remains historically FAIL.
Owner close-out recorded M5 COMPLETE without a fresh end-to-end rerun.

---

## 13. Tests added

`tests/unit/truth_validation/test_truth_alignment.py` (13 tests):

- LLM / LLMs / LLM application development identity
- RAG ↔ Retrieval-Augmented Generation
- Java ≠ JavaScript; AWS ≠ AWS Bedrock; RELATED ≠ DIRECT
- positive Bedrock blocks; `do not have` / `do not claim` / mixed clause
- employer requirement is Class B
- target-role header is not a candidate claim
- multi-domain `in testing, …` overall support; AI-only inflation blocks

`test_career_positioning_duration.py`:
`test_years_in_multi_domain_list_resolves_to_overall_engineering`.

`tests/unit/truth_validation/test_previous_sentence_employment.py` (9 tests):
same-sentence nbn; previous-sentence truthful pipeline; exact frozen E2 pair;
invented GPU after nbn; no known employer; employer two sentences back;
named-project precedence; employer-requirement language; two employers in the
previous sentence fail closed.

Existing Truth / Document Positioning / CV / letter / package assertions were
not weakened.

---

## 14. Test results

| Command | Result |
|---------|--------|
| `python -m pytest tests/unit/truth_validation/test_previous_sentence_employment.py tests/unit/truth_validation/test_truth_alignment.py tests/unit/truth_validation/test_m4_claim_kinds.py -q` | **36 passed** |
| `python -m pytest tests/unit/truth_validation/ -q` | **87 passed** |
| `python -m pytest tests/unit/truth_validation tests/functional/test_fr014_m2_truth_validation.py tests/functional/test_fr014_m3_owner_workflow.py tests/functional/test_fr014_m4_claim_validation.py tests/unit/document_positioning -q` | **248 passed** |
| `python -m pytest tests/unit/document_positioning tests/unit/cv_generation tests/unit/cover_letter tests/unit/application_package tests/unit/truth_validation -q` | **436 passed** |

No unrelated failures were concealed. M3/M4 Document Positioning tests are
included in the positioning and broader unit runs.

---

## 15. Frozen artefact replay (validator only)

Replay used existing
`docs/eval/document_positioning_m5/hidden/generation_records/E{1-4}_cic.json`
plus the live Career Profile and job-analysis technology labels. Documents were
**not** regenerated. Hidden records were **not** overwritten.

| Job | CV Truth | Letter Truth | Notes |
|-----|----------|--------------|-------|
| E1 | PASS | PASS | Named `llm` false positive gone |
| E2 | PASS | PASS | Named `intesting` / `rag` / `awsbedrock` gone; previous-sentence nbn delivery now supported employment (`fr014-truth-alignment-2`) |
| E3 | PASS | PASS | Unchanged PASS |
| E4 | PASS | PASS | Named `intesting` false positive gone |

After `fr014-truth-alignment-1`, E2 letter was still REVIEW-REQUIRED on the
nbn delivery span. After this bind, E1–E4 CIC pairs are all external-use
allowed on the **existing** frozen artefacts. Hidden records were not
overwritten.

No unexpected **new blocking** or review-required findings.

This replay is **not** a fresh end-to-end M5 run. Owner close-out used it as
Truth acceptance evidence alongside the frozen 4/4 quality result. See
[document_positioning_m5_acceptance.md](document_positioning_m5_acceptance.md).

---

## 16. Regressions

None observed in the suites above. Redwolf TypeScript/Vue remains blocking.
Java ≠ JavaScript. AWS ≠ Bedrock DIRECT. Employer requirements remain
context-only.

---

## 17. Unresolved risks

- Shared identity coverage is limited to identities M2 already models.
  Unknown recruiter phrases still fail closed.
- Clause-scoped negation is pattern-based. Novel denial phrasing may still
  need corpus-justified extensions.
- Previous-sentence employment bind is one sentence only. A truthful restatement
  two sentences after the employer name remains unresolved by design.
- Replay against frozen artefacts is not a substitute for a new blind
  preference evaluation.

---

## 18. Definition of Done

- [x] RC-1 canonical identity mismatch corrected
- [x] FR-014 reuses shared canonical identity authority where architecturally safe
- [x] no duplicate ad-hoc FR-014 LLM/RAG alias system introduced
- [x] Java remains distinct from JavaScript
- [x] AWS remains distinct from direct AWS Bedrock experience
- [x] RELATED does not become DIRECT
- [x] RC-2 explicit negation corrected
- [x] positive unsupported Bedrock claim still blocks
- [x] mixed negation + positive claim still blocks
- [x] RC-3 complete multi-domain duration list is preserved
- [x] overall career duration is supported only from authoritative chronology
- [x] domain-specific duration inflation still blocks
- [x] target-role header does not create candidate experience
- [x] employer requirements never become candidate evidence
- [x] focused regression tests pass
- [x] full FR-014 suite passes
- [x] M0–M4 Document Positioning tests pass
- [x] relevant CV/letter/package regressions pass
- [x] frozen M5 CIC artefact replay completed without regeneration
- [x] historical M5 FAIL preserved
- [x] documentation updated
- [x] acceptance report written
- [x] learning note written
- [x] M5 NOT marked complete
- [x] M6 NOT started
- [x] no SEEK / Playwright / AAS
- [x] no application submitted
- [x] previous-sentence unique employer bind implemented (not paragraph walk)
- [x] invented delivery after named employer still rejected
- [x] owner close-out: M5 COMPLETE on quality 4/4 + unchanged-artefact Truth replay
- [x] historical original M5 execution FAIL preserved
- [x] no fresh end-to-end M5 rerun claimed

---

## 19. Owner close-out

**ACCEPTED.** Owner recorded Document Positioning M5 as **COMPLETE**
(2026-08-20):

- Quality: CIC preferred 4/4 on the frozen blind benchmark.
- Truth: all E1–E4 CIC CV and cover-letter pairs PASS when the **unchanged**
  frozen artefacts are replayed through `fr014-truth-alignment-2`.
- Historical original execution remains **FAIL** under the then-current
  validator.
- No fresh end-to-end benchmark rerun occurred.
- M6 not started.

Canonical record:
[document_positioning_m5_acceptance.md](document_positioning_m5_acceptance.md).
