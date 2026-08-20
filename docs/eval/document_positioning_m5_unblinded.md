# Document Positioning M5 — Unblinded owner-review report

**Status:** **M5 FAIL** under the frozen acceptance contract (historical
execution). Owner close-out later recorded **M5 COMPLETE** without rewriting
this FAIL — [document_positioning_m5_acceptance.md](document_positioning_m5_acceptance.md).  
**Date:** 2026-08-20  
**Official run:** `m5_restart_after_m3_optional_relevance_2026-08-20`  
**Protocol:** [document_positioning_m5_protocol.md](document_positioning_m5_protocol.md)

Owner scores were persisted in
`docs/eval/document_positioning_m5/owner_review/` **before** the mapping was
revealed. Unspecified rubric rows were left null and were not inferred.
Documents were not regenerated. M3/M4/M5 product behaviour was not changed.
M6 was not started.

---

## 1. Persist-before-unblind confirmation

| Check | Result |
|-------|--------|
| Owner declared scores made without inspecting `hidden/` | Yes |
| `owner_scores.json` + four scoring sheets written first | Yes (`persist_record.md`) |
| Job result field | `overall` (overall submit preference) |
| Unspecified rubric dimensions | left `null` |
| Mapping marked `revealed: true` only after persist | Yes |

Owner-supplied CV and cover-letter preferences were stored as notes, not as
invented 15-second-scan / positioning / evidence rows.

---

## 2. Revealed A/B mapping

| Job | Version A | Version B | Owner overall | System result |
|-----|-----------|-----------|---------------|---------------|
| E1 Allura | baseline | CIC | Version B | **CIC preferred** |
| E2 CSK | baseline | CIC | Version B | **CIC preferred** |
| E3 Maincode | CIC | baseline | Version A | **CIC preferred** |
| E4 Repurpose | CIC | baseline | Version A | **CIC preferred** |

Ties: none.

---

## 3. Quality result (preference only)

Do not mix this table with Truth.

| Outcome | Jobs |
|---------|------|
| CIC quality wins | E1, E2, E3, E4 |
| Baseline quality wins | none |
| Ties | none |

**CIC preferred or tied: 4/4.** Frozen quality threshold is ≥ 3/4. Quality
alone would pass.

Owner-supplied CV and letter preferences matched overall on every job.

---

## 4. FR-014 Truth result (external-use gate only)

Do not mix this table with preference.

A pair fails if either CV or letter is not allowed for external use
(`fail` **or** `review_required` blocks external use under ADR-006).

### CIC (four pairs)

| Job | CV | Letter | Pair | Truth failure |
|-----|----|--------|------|---------------|
| E1 | pass | fail — blocking `llm` | not allowed | **yes** |
| E2 | review_required — `intesting` | fail — blocking `rag`, `awsbedrock` | not allowed | **yes** |
| E3 | pass | pass | allowed | no |
| E4 | review_required — `intesting` | pass | not allowed | **yes** |

**CIC Truth failures: 3.** Frozen allowance: **0**.

### Baseline (four pairs)

| Job | CV | Letter | Pair | Truth failure |
|-----|----|--------|------|---------------|
| E1 | fail — blocking `education` | fail — blocking `llm`, `googlecloud` | not allowed | **yes** |
| E2 | fail — blocking `education` | fail — blocking `awsbedrock`, `rag`, certification span | not allowed | **yes** |
| E3 | fail — blocking `education` | fail — blocking `gpu`, `linux` | not allowed | **yes** |
| E4 | fail — blocking `education` | fail — blocking `aitools`, `copilot`, `claude` | not allowed | **yes** |

**Baseline Truth failures: 4.** Recorded honestly. Not repaired.

---

## 5. Formal M5 result

Frozen contract (protocol § 8): CIC passes M5 **if and only if**

1. CIC preferred or tied on ≥ 3 of 4 jobs, **and**
2. CIC Truth failures = 0.

`compute_release_result`:

> FAIL: CIC Truth failures = 3 (zero allowed). CIC preferred or tied on 4/4.

**Formal status: M5 FAIL.**

Forbidden reinterpretations (protocol § 8), all rejected here:

- 4/4 quality does not waive Truth
- a Truth failure is not “minor”
- E2 (CSK) success is not acceptance (and is not needed; quality already 4/4)

---

## 6. Failure classification

M5 failed on the **Truth gate**, not on preference.

| Dimension | Frozen bar | Observed | Gate |
|-----------|------------|----------|------|
| Quality | ≥ 3/4 CIC preferred or tied | 4/4 CIC preferred | pass |
| Truth | 0 CIC pair failures | 3 CIC pair failures | **fail** |
| Combined | both | | **FAIL** |

This is not a “CIC lost the writing contest” result. The owner would submit
CIC on every job. It is a “CIC documents are not FR-014-clean enough to
release” result.

---

## 7. Root-cause analysis (no product change)

### 7.1 Why CIC won preference

Across E1–E4 the owner preferred the version that kept the Master chassis:
fuller project overviews and engineering highlights, and (on E1/E2) correct
reverse-chronological experience.

The losing baseline versions:

- E1/E2: listed nbn (Mar 2020–Oct 2023) **before** Professional Development
  (Oct 2023–Nov 2025), which the owner read as the wrong career order.
- E1/E2/E3: thinned project bodies to one or two bullets.
- E1 letter: “extensive experience” with AWS and Azure Data Factory (owner:
  too strong; ADF is not recent).
- E3 letter: “strong computational skills” (owner: vague vs HPC/infrastructure
  evidence).

CIC already keeps Master project prose and Master experience order. Two
selected projects on E1 was acceptable; thinness was the baseline problem.

CIC quality notes that did **not** reverse submit preference:

- E1 CIC letter repeats skills/keywords.
- E2 CIC letter uses American “organizations”.
- E1 CIC letter’s ADF “familiarity” was the better honesty move.

### 7.2 Why CIC failed Truth

Local M3/M4 validation passed. FR-014 is a separate gate and still failed.

**E1 CIC letter — blocking `llm`.**  
The letter claims “LLM application development” (a CareerProfile skill) and
also “LLMs” as a capability. FR-014 Class A keyed `llm`. This is a
writer/token-alignment failure: authorised evidence exists under a longer
label, but the bounded letter still produced a Class A token the Truth
catalogue treated as unsupported/blocking.

**E2 and E4 CIC CVs — review_required `intesting`.**  
E2/E4 summaries say “over 10 years **in testing**”. E1 and E3 CIC summaries
keep Master-like “10+ years **across** testing” and those CVs **passed**.
The bounded CV writer’s paraphrase created a Class A object `intesting`.
ADR-006: review-required blocks external use. This is not an invented
employer or metric; it is a lexical change that the Truth gate will not
silently forgive.

**E2 CIC letter — blocking `rag` and `awsbedrock`.**  
The letter claims RAG directly (CSK pack treats RAG as DIRECT) and denies
Bedrock (“I do not claim direct experience with AWS Bedrock”). FR-014 still
raised blocking `rag` and `awsbedrock`. Two contributing surfaces:

1. Denial phrasing still contains the Bedrock token; FR-014 does not treat
   “I do not claim X” as authorised related-capability promotion.
2. The CIC E2 CV header overlays the **employer job title**
   (`Senior AI Engineer - AWS Bedrock | Agentic AI | Chatbots & Customer
   Support Auto`) onto the candidate document. That is a Master-adapt
   target-role overlay, not a new M3 invention, and it puts unsupported
   employer identities on the CV chrome.

**E3 CIC pair passed Truth.**  
Same composers, same profile, same gate. So CIC is capable of an
externally-usable pair when wording stays inside authorised labels
(“across testing”, no Bedrock token, no `llm` abbreviation collision).
The failures are job-specific writer/overlay collisions, not a total
inability to pass FR-014.

### 7.3 What this is not

- Not a validation bypass opportunity. Do not strip Truth findings to force
  a pass.
- Not a licence to regenerate E1/E2/E4 after seeing scores.
- Not proof that the baseline is safer. Baseline failed Truth on all four
  pairs (`education` on every baseline CV, plus letter overclaims).
- Not M6. Preference success does not wire `cic package prepare`.

---

## 8. Recommendations for owner decision

1. **Record M5 as FAIL.** Keep the frozen contract. Do not start M6.
2. **Do not treat 4/4 preference as a production-ready positioning path.**
   The documents the owner would submit still fail the recruiter-document
   Truth gate on three of four jobs.
3. **Do not patch M3/M4 in order to relabel this run as a pass.** Any later
   Truth-alignment work is a **new** authorised correction, after which the
   **entire** four-job benchmark would have to be re-run blind. Selective
   regeneration is forbidden.
4. If a follow-on is authorised, keep quality and Truth separate. Likely
   bounded investigation (not implemented here):
   - stop overlaying employer titles that contain unsupported identities
     (Bedrock, Chatbots) onto the CV header;
   - keep Master “across testing” rather than “in testing”;
   - emit FR-014-authorised capability labels (`LLM application development`,
     `Retrieval-Augmented Generation`) instead of colliding abbreviations;
   - do not put denied RELATED identities (Bedrock) into letter prose in a
     form FR-014 still scores as a candidate claim.
5. Optional quality notes for a later cycle, not this fail: Australian
   spelling; reduce letter keyword repetition. These would not have changed
   the frozen M5 result.

**Recommended status until owner says otherwise:**

M5 FAIL — Truth gate (3 CIC pair failures). Quality 4/4 CIC preferred.
Prepare remains unwired. M6 not started.

---

## Later note (not a rewrite of this unblinded FAIL)

A subsequent forensic audit and bounded FR-014 detector correction
([fr014_truth_alignment.md](fr014_truth_alignment.md)) treated the five named
CIC findings as validator false positives, then bound the E2 nbn delivery
span using the immediately previous sentence only. M3/M4 were **not** retuned.

Owner close-out (2026-08-20): **M5 COMPLETE**. Quality 4/4 from this frozen
blind review. Truth PASS on replay of the **unchanged** CIC artefacts through
the corrected validator. **This unblinded report’s historical FAIL is
unchanged.** No fresh end-to-end benchmark rerun occurred. M6 was not started.

