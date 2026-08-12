# FR-019 M1.1 — Reliability Hardening (Assess Retry + Failed-Run Recovery)

**Status:** **Implementation complete — proposed GO (owner review)**  
**Date:** 2026-08-11  
**Phase:** Horizon 1B — FR-019 Core Loop Operationalisation  
**Parent:** [fr019_core_loop_operationalisation.md](fr019_core_loop_operationalisation.md)  
**M0:** [fr019_m0_engineering_spike.md](fr019_m0_engineering_spike.md) (**GO**)  
**M1:** [fr019_m1_mailbox_intake.md](fr019_m1_mailbox_intake.md) (**CONDITIONAL GO** → lift after M1.1 acceptance)  
**Does not begin:** M2 `cic daily`, LinkedIn metadata fix, submission automation,
Recruiter Intelligence.

---

## 1. Executive summary

M1.1 closes the pre-M2 reliability debt found in live LinkedIn assess failures:

1. **Selective assess retry** — approved stochastic *generated assessment* validation
   codes participate in existing FR-008 `max_attempts=3` retries. Validators are
   unchanged. Unknown validation types remain **unrecoverable**.
2. **Targeted recovery** — `cic opportunity retry-run <workflow_run_id>` reopens a
   terminal failed analyse/assess checkpoint, reuses JobAnalysis, and continues the
   pipeline. Mailbox ledger is untouched.
3. **Failure UX** — discovery/mailbox FAILED items surface `workflow_run_id`, failed
   stage, and retry guidance when available.

**Live revalidation (2026-08-11):** all three previously failed LinkedIn workflows
were recovered via `retry-run` to `awaiting_owner` with Opportunity ids allocated;
ledger unchanged; JobAnalysis not re-run.

**Proposed verdicts (owner review):**

| Decision | Proposal |
|----------|----------|
| **M1.1** | **GO** |
| **FR-019 M1** | **GO** (lift CONDITIONAL GO) |
| **M2** | **Not started** — begin only on separate owner authorisation |

---

## 2. Gate A — Selective assessment retry

### Retryable ErrorDetail.type codes (only)

| Code | Meaning | Live class |
|------|---------|------------|
| `judgment_material_inconsistency` | strong judgment + material gap/conflict | MYOB |
| `evidence_ref_name_mismatch` | finding tech name ≠ JobAnalysis technologies[i] | HUB24 / Maincode |
| `evidence_ref_index_out_of_range` | generated item_index out of bounds | related flake |

### Remain unrecoverable

- `forbidden_embedded_input` (trust boundary)
- Any unknown / unclassified validation `type` (including generic `value_error`)
- Missing artefacts, provider refusals without transient markers, non-assess nodes

**Not** a blanket `assessment_schema_coercion` category.

### Implementation

- [`opportunity_assessment/errors.py`](../../src/career_intelligence/opportunity_assessment/errors.py) —
  `assessment_validation_is_retryable`
- Model validator emits `PydanticCustomError("judgment_material_inconsistency", …)`
- [`refs.py`](../../src/career_intelligence/opportunity_assessment/refs.py) stable codes
- [`AssessNode`](../../src/career_intelligence/orchestration/spike_nodes.py) uses typed
  helper; else `classify_exception`
- `max_attempts=3` unchanged

---

## 3. Gate B — Targeted failed-workflow recovery

| Piece | Detail |
|-------|--------|
| Runner | `ApplicationWorkflowRunner.retry_failed(run_id)` |
| CLI | `cic opportunity retry-run <workflow_run_id>` |
| Store | Existing `data/workflow_runs/` checkpoints only |
| Eligible | `status=failed` and failed node in `{analyse, assess}` with required artefacts |
| Ledger | **Not** read or written |

FAILED discovery outcomes now carry `workflow_run_id` on pre-persist runner
failures and print retry guidance.

---

## 4. Gate C — LinkedIn metadata (tracked debt — not fixed)

**Classification:** **NON-BLOCKING DEFECT** (real data-quality issue, not cosmetic).

| Fact | Detail |
|------|--------|
| Origin | LinkedIn plaintext card parser assumes Title/Company/Location; email title/company preferred over URL enrich; LinkedIn HTML often leaves company unset |
| Live example | HUB24 — company/title labels swapped or location used as company |
| Downstream risk | Wrong labels can reach JobPosting identity, JA prompts, review queue, CV target role, and cover-letter employer/role copy **when** assess succeeds |
| M1.1 action | Document only; **do not fix** |
| Before M2 | Accept residual risk or schedule separate polish; not a M1.1 blocker |

---

## 5. Testing evidence

| Suite | Result |
|-------|--------|
| Unit `test_m11_retryable_validation.py` | Pass |
| Functional `test_fr019_m11_reliability.py` | Pass (retry success, exhaust@3, forbidden no-retry, retry-failed, ledger isolation) |
| Full regression | **1600 passed** (2026-08-11) |

---

## 6. Live / manual validation

| Run | Failure class | Command | Result | Ledger |
|-----|---------------|---------|--------|--------|
| `wfr_01KZQEQ3ERS5K2PDK19JE50FA5` | judgment/material-gap | `cic opportunity retry-run …` | `awaiting_owner` → `opp_01KZQGRX1YT9GKYT80GM82FZ79` | unchanged |
| `wfr_01KZQEQR6HKW4PQZH6WVWSN2NV` | evidence name mismatch | same | `awaiting_owner` → `opp_01KZQGSRMW5SVW1261E8FDKYP4` | unchanged |
| `wfr_01KZQESEF3VMS27DHM88BNND08` | evidence name mismatch | same | `awaiting_owner` → `opp_01KZQGTC7ARJCHENBRGDHRN7ZH` | unchanged |

Upstream: `job_analysis preserved`; single `analyse` start in event history after
recovery. Fresh assess under full validation. Stochastic LLM happened to pass on
these retries; exhaust behaviour is proven in automated tests.

Automatic in-process selective retry (Gate A) is proven by functional tests with
typed `OpportunityAssessmentValidationError` injection (attempt 1 fail → retry →
success; and 3× fail → `retry_exhausted`).

---

## 7. Acceptance criteria

| # | Criterion | Status |
|---|-----------|--------|
| 1 | Selective retry codes only; unknown fail closed | **PASS** |
| 2 | Validators not weakened | **PASS** |
| 3 | `max_attempts=3` | **PASS** |
| 4 | `retry-run` uses existing checkpoints | **PASS** |
| 5 | No mailbox ledger mutation | **PASS** (tests + live) |
| 6 | FAILED UX surfaces run id / stage / retry hint | **PASS** |
| 7 | LinkedIn metadata documented as debt | **PASS** |
| 8 | Unit + functional + full regression | **PASS** (1600) |
| 9 | Live retry of both failure classes | **PASS** |
| 10 | M2 not started | **PASS** |

---

## 8. Learning takeaways

- Strict validation catching bad model output is a **feature**.
- Bounded retry is appropriate for **stochastic structured output**, not for
  trust-boundary or unknown defects.
- Checkpoint recovery avoids repeating successful acquire/analyse work.
- Email ledger success and child-workflow failure are **separate** concerns.
- Production AI needs validate + bounded retry + checkpoints + idempotency +
  human-visible recovery — not prompts alone.

---

## 9. Repository status

| Item | Status |
|------|--------|
| FR-019 M1.1 | **Proposed GO** (this report) |
| FR-019 M1 | Propose lift to **GO** after owner accepts M1.1 |
| M2–M6 | Not started |
| LinkedIn metadata polish | Tracked debt |
