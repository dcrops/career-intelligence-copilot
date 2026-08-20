# Document Positioning M5 — Engineering / Acceptance Report

**Status:** **M5 COMPLETE** (owner close-out 2026-08-20)  
**Date:** 2026-08-20  
**Official run:** `m5_restart_after_m3_optional_relevance_2026-08-20`  
**Protocol:** [document_positioning_m5_protocol.md](document_positioning_m5_protocol.md)  
**Unblinded report:** [document_positioning_m5_unblinded.md](document_positioning_m5_unblinded.md)  
**Programme:** [document_positioning_remediation.md](document_positioning_remediation.md)  
**FR-014 detector correction:** [fr014_truth_alignment.md](fr014_truth_alignment.md)

**Owner close-out:** Quality acceptance demonstrated **4/4** through the frozen
blind owner benchmark. Truth acceptance demonstrated by replaying the
**unchanged** frozen CIC artefacts through the subsequently corrected FR-014
validator (`fr014-truth-alignment-2`), with all E1–E4 CV and cover-letter
pairs **PASS**. The original benchmark execution remains historically recorded
as **FAIL** under the then-current validator. **No claim is made that a fresh
end-to-end benchmark rerun occurred.** M6 was not started. `cic package prepare`
was not rewired.

The first live attempt remains **INVALIDATED — PRE-BENCHMARK PRODUCT BLOCKER**
(`docs/eval/document_positioning_m5/invalidated_pre_benchmark_blocker/`).

---

## 1. Persist-before-unblind

Owner overall submit preferences were written to
`docs/eval/document_positioning_m5/owner_review/owner_scores.json` and the
four scoring sheets **before** `hidden/ab_mapping.json` was marked
`revealed: true`. Unspecified rubric rows remain null.

---

## 2. Quality (preference only)

Revealed mapping: E1/E2 Version B = CIC; E3/E4 Version A = CIC.

| Job | Owner overall | System |
|-----|---------------|--------|
| E1 | Version B | CIC preferred |
| E2 | Version B | CIC preferred |
| E3 | Version A | CIC preferred |
| E4 | Version A | CIC preferred |

CIC preferred or tied: **4/4**. Ties: none. Baseline quality wins: none.

---

## 3. FR-014 (separate from preference)

| Job | CIC pair | Baseline pair |
|-----|----------|----------------|
| E1 | FAIL (letter blocking `llm`) | FAIL (CV `education`; letter `llm`, `googlecloud`) |
| E2 | FAIL (CV review-required `intesting`; letter blocking `rag`, `awsbedrock`) | FAIL (CV `education`; letter `awsbedrock`, `rag`, cert span) |
| E3 | PASS | FAIL (CV `education`; letter `gpu`, `linux`) |
| E4 | FAIL (CV review-required `intesting`; letter pass) | FAIL (CV `education`; letter `aitools`, `copilot`, `claude`) |

CIC Truth failures: **3**. Baseline Truth failures: **4**. Zero CIC Truth
failures are allowed for release.

---

## 4. Formal result

`compute_release_result`:

> FAIL: CIC Truth failures = 3 (zero allowed). CIC preferred or tied on 4/4.

**Historical execution result (then-current validator):**

`compute_release_result`:

> FAIL: CIC Truth failures = 3 (zero allowed). CIC preferred or tied on 4/4.

That original execution remains **FAIL** under the validator that scored the
live generation. Quality passed the ≥ 3/4 bar. Truth did not, at that time.
4/4 preference does not waive the historical FAIL.

**Owner close-out (corrected validator, unchanged artefacts):** M5 COMPLETE.
See header. Not a fresh end-to-end rerun.

---

## 5. Definition of Done

- [x] Bounded M3 correction implemented and tested
- [x] First M5 live run invalidated
- [x] Entire E1–E4 set generated under frozen protocol
- [x] Blind owner artefacts generated
- [x] Owner overall scores persisted before unblind
- [x] Mapping revealed after persist
- [x] Release calculated against frozen contract
- [x] Failure classified; RCA only at unblind (no M3/M4 product change)
- [x] Prepare not wired; M6 not started
- [x] M5 complete (owner close-out: quality 4/4 frozen blind; Truth PASS on
      unchanged CIC artefacts through corrected FR-014; historical execution
      FAIL preserved; no fresh end-to-end rerun)
- [ ] M6 authorised by owner

**Final status: M5 COMPLETE** (owner close-out). Historical execution FAIL
preserved. Do not start M6 until owner authorises it.

---

## 6. Later FR-014 detector correction and owner close-out

A bounded Truth-validator correction followed the historical FAIL
([fr014_truth_alignment.md](fr014_truth_alignment.md)), including the
immediately previous-sentence employment bind for the E2 nbn delivery span.
Forensic audit of the five named CIC findings: 0 genuine unsupported candidate
claims.

Owner close-out (2026-08-20): **M5 COMPLETE**. Quality 4/4 from the frozen
blind benchmark. Truth PASS on replay of the **unchanged** frozen CIC
artefacts through `fr014-truth-alignment-2`. Historical execution remains FAIL
under the then-current validator. This is **not** a fresh end-to-end M5 rerun.
M6 was not started.
