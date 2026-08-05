# OAT-001 Phase 3 — Live Bounded Agent Evaluation (BOPA)

**Status:** Complete (evaluation only)  
**Date:** 2026-08-05  
**Scope:** Operational acceptance of FR-015 BOPA against the reconciled live Opportunity corpus  
**Does not include:** FR-015 redesign, ToolPolicy changes, FR-016, automatic enhancement fixes  

**Evidence:** `data/_oat001_phase3_bopa/`  
**Harness:** `scripts/_oat001_phase3_bopa_eval.py`

---

## 1. Executive summary

BOPA is **safe** on the live corpus: ToolPolicy admits only allow-listed actions, preparation and truth run through existing services, pipeline status never mutated, and fail-closed truth correctly blocked external readiness.

BOPA is **not yet frictionless** for daily owner use. On representative `apply` Opportunities without packages, the default `cic agent run … --approve` path stopped as `unexpected_failure` because FR-006/007 material-benefit refused Silver/Bronze preparation. After an explicit `--override-material-benefit` and installing the declared WeasyPrint dependency, Redwolf progressed correctly: prepare → truth validate → `truth_validation_blocked`, with resume inspecting first and **not** repeating preparation or truth.

**Overall recommendation:** **Ready with minor improvements**

> **Update (OAT-001 Phase 4):** Presentation defects D1–D3 and enhancements E1–E3
> are addressed in [oat001_phase4_operational_polish.md](oat001_phase4_operational_polish.md).
> Post-polish verdict: **Operationally Ready**.

---

## 2. Scenarios tested

| ID | Opportunity | Why selected | Primary command |
|----|-------------|--------------|-----------------|
| S1 | `opp_01KZ8CEJANPX26DWEKQNF7BWH9` Redwolf + Rosch / AI Engineer | Fresh assessed, `apply`, Silver | `cic agent run … --approve` |
| S1b | same | Owner remediation after material-benefit refusal | `… --approve --override-material-benefit` (WeasyPrint missing) |
| S1c | same | Full coordination after WeasyPrint install | `… --approve --override-material-benefit` |
| S1d | same | Re-run after package+truth exist | `… --approve --override-material-benefit` |
| S2 | `opp_01KY8X66C3NSYXJ4E2RNTMMKM5` Officeworks | Submitted pipeline | `--approve` |
| S3 | `opp_01KY8RFAH81M9V30ZVH9TM09T5` Bluefin | Interviewing pipeline, `apply` | `--approve` |
| S4 | `opp_01KY8WYE6RM54EYV8QT0YXHCQP` Jirotech | Gold tier | `--approve` |
| S5 | `opp_01KZ8CCQZTVNN2JKF91P1FANT2` Carlton | Bronze + `apply`, fresh assessed | `--approve` |

Corpus note: no live Opportunity is both **Gold** and **`decision=apply`**. Jirotech is Gold with `consider_cv_tailoring` but `decision=None`.

---

## 3. Behaviour observed

### S1 Redwolf (fresh assessed, apply) — default `--approve`

| Field | Value |
|-------|--------|
| Readiness | `missing_package` |
| Proposed | `run_preparation` |
| ToolPolicy | **allow** |
| Executed | no (adapter error) |
| Artefacts | FR-002–005 present; package absent |
| Stop | `unexpected_failure` / `failed` |
| Owner action | generic “inspect history… resume or re-run” |
| Duration | ~2.0 s |
| Cause | Material-benefit gate: Silver + no `consider_cv_tailoring` |

### S1c Redwolf — `--approve --override-material-benefit` (WeasyPrint present)

| Field | Value |
|-------|--------|
| Steps | prepare → validate_truth → stop |
| Policy | allow on all three |
| Executed | preparation `apr_01KZ8DTFXQCW1BYQ27T9TY824Y`; truth reports `trp_01KZ8DTJ9X…`, `trp_01KZ8DTJAK…` |
| Package | present (CV+CL under `career-documents/…/generated/`) |
| Truth | **fail** (blocking unsupported claim: “AWS Certified Developer”) |
| Stop | `truth_validation_blocked` / `awaiting_owner` |
| Duration | ~3.9 s |
| Owner action | Edit Markdown → `cic truth validate-package` → `cic agent resume` — clear |

### S1d Redwolf re-run (package already present, truth fail)

| Field | Value |
|-------|--------|
| Readiness | `truth_blocked` |
| Proposed | `stop` immediately |
| No prep | **confirmed** |
| No truth re-run | **confirmed** |
| Duration | ~1.8 s |

### S2 Officeworks (submitted)

| Field | Value |
|-------|--------|
| Readiness | `unsupported_or_contradictory` (`decision=None`) |
| Proposed | `stop` |
| Policy | allow |
| Stop | `unsupported_state` / `failed` |
| Duration | ~1.4 s |
| Note | Pipeline remains `submitted`; BOPA does not mention pipeline |

### S3 Bluefin (interviewing, apply)

| Field | Value |
|-------|--------|
| Readiness | `missing_package` (pipeline interviewing **not** considered) |
| Proposed | `run_preparation` |
| Policy | **allow** |
| Stop | `unexpected_failure` (same material-benefit refusal as S1) |
| Duration | ~1.7 s |
| Pipeline after | still `interviewing` / recruiter — **unchanged** |

### S4 Jirotech (Gold)

| Field | Value |
|-------|--------|
| Readiness | `unsupported_or_contradictory` (`decision=None`) |
| Stop | `unsupported_state` |
| Duration | ~1.4 s |

### S5 Carlton (Bronze, apply)

| Field | Value |
|-------|--------|
| Same pattern as S1 | material-benefit → `unexpected_failure` |
| Duration | ~1.5 s |
| Pipeline | `assessed` unchanged |

---

## 4. Owner usability assessment

**What works well**

- Report layout (readiness → steps → policy → result → stop → owner action) is scannable.
- Explicit note that agent status ≠ pipeline status builds trust.
- `--approve` refusal without the flag is clear.
- On truth block (S1c), next steps are concrete and trustworthy.

**Confusing / awkward**

1. **`unexpected_failure` for expected gates** (material-benefit, missing WeasyPrint). Owner action does not say “re-run with `--override-material-benefit`” even though the step result does.
2. **Owner action says “resume or re-run”** after `failed`, but **`cic agent resume` refuses `failed`**.
3. **Submitted / interviewing** Opportunities get either `unsupported_state` (no decision) or an attempt to prepare (apply + missing package) with no pipeline context in the report.
4. **Gold scenario** looks “unsupported” because there is no apply decision — correct for BOPA goal, easy to misread as “Gold broken”.
5. **CLI exit code 1** on `failed` / `unsupported_state` is fine for scripts, but owners may treat any non-zero as a crash rather than a deliberate stop.
6. Initial run does not show an explicit `inspect_readiness` step (resume does). Observation still happens; audit is complete via `snapshot_observed`.

**Missing information**

- Pipeline status on the readiness block.
- Blocking truth finding summary on `show` (must open TruthReports).
- Count/identity of package paths on success beyond preparation run id.

---

## 5. Safety verification

| Check | Result |
|-------|--------|
| ToolPolicy sole admission | Pass — deny path not hit; only allow-listed actions proposed |
| No submit / no pipeline advance | Pass — stated on every report; verified via `pipeline show` |
| No FR-008 invoke | Pass |
| No truth waiver | Pass — fail-closed block on unsupported certification claim |
| Closed allow-list | Pass — no broaden during OAT |
| Deterministic proposer default | Pass |

---

## 6. Pipeline verification

Before/after `pipeline show` for every scenario (including S1c resume and S1d):

| Opportunity | Before | After | Mutation |
|-------------|--------|-------|----------|
| Redwolf | assessed / apply | assessed / apply | None |
| Officeworks | submitted | submitted | None |
| Bluefin | interviewing / recruiter | interviewing / recruiter | None |
| Jirotech | (assessed, no decision) | unchanged | None |
| Carlton | assessed / apply | assessed / apply | None |

No interview-stage or submission changes observed.

---

## 7. Truth verification

| Case | Observation |
|------|-------------|
| Truth missing after prep | BOPA runs `validate_truth_package` once |
| Truth fail | Stops `truth_validation_blocked`; does not waive |
| Resume while still fail | Inspect → stop; **does not** re-validate |
| New run while still fail | Immediate stop; **does not** re-validate |
| Truth already pass | Not exercised live (no pass package in selected set); unit/M3 coverage remains the regression proof |

Blocking finding (S1c): unsupported Class A certification claim “AWS Certified Developer” on CV Markdown — correct FR-014 behaviour, not a BOPA defect.

---

## 8. Package verification

| Check | Result |
|-------|--------|
| Unnecessary regeneration on resume | Pass — no second prep |
| Unnecessary regeneration on new run with package present | Pass — stop on truth_blocked only |
| Package integrity | Pass — readiness reports `present` with CV+CL; artefacts under `career-documents/cv|cover-letters/generated/` |
| Duplicate package dirs | Pass — single `data/application_packages/opp_01KZ8CE…/` |
| Failed prep attempts | Left failed `apr_*` records only; no partial package for S1/S3/S5 |

---

## 9. Resume verification

| Run | Resume behaviour |
|-----|------------------|
| S2/S3/S4/S5/S1 failed | **Refuse:** `cannot resume agent run in status 'failed'` |
| S1c awaiting_owner | **Pass:** `inspect_readiness` first; no prep; no truth re-run; same stop reason |
| Completed work not repeated | **Pass** on S1c resume and S1d re-run |

---

## 10. Defects

| ID | Finding | Evidence |
|----|---------|----------|
| D1 | Expected service refusals (material-benefit gate; missing WeasyPrint) are classified as `unexpected_failure` / `failed`, not an owner-actionable awaiting state | S1, S1b, S3, S5 |
| D2 | Owner action for `unexpected_failure` says “resume or re-run”, but resume is illegal for `failed` | All failed runs |
| D3 | Step result text already names `--override-material-benefit`, but owner-action mapping does not surface that command | S1 vs presentation.py |

These are presentation / error-mapping defects in the BOPA owner surface. They do **not** weaken ToolPolicy or truth.

---

## 11. Enhancements

| ID | Finding |
|----|---------|
| E1 | Include pipeline status (and optionally refuse prepare when already `submitted` / `interviewing`) in readiness / stop messaging |
| E2 | Dedicated stop reason for material-benefit refusal with owner action pointing at `--override-material-benefit` |
| E3 | On `truth_validation_blocked`, summarise top blocking findings in `cic agent show` |
| E4 | Emit explicit `inspect_readiness` as step 0 on initial `run` for parity with resume |
| E5 | Softer exit semantics or banner for deliberate `unsupported_state` stops vs infrastructure failure |

---

## 12. Documentation improvements

| ID | Finding |
|----|---------|
| Doc1 | Owner runbook: Silver/Bronze without `consider_cv_tailoring` require `--override-material-benefit` for preparation |
| Doc2 | Owner runbook: WeasyPrint is required for live PDF package generation on this machine |
| Doc3 | Clarify that BOPA only coordinates `decision=apply`; tier alone (Gold/Bronze) is insufficient |
| Doc4 | Clarify `failed` → new `cic agent run`; `awaiting_owner` → `cic agent resume` |
| Doc5 | Note agent status vs pipeline status with examples (Officeworks / Bluefin) |

---

## 13. Historical repository findings

| ID | Finding |
|----|---------|
| H1 | Officeworks is pipeline-`submitted` but Opportunity `decision` is `None` — BOPA therefore treats it as unsupported rather than “already past prepare” |
| H2 | No reconciled Opportunity is Gold **and** `apply` (Jirotech is Gold with CV-tailoring signal but undecided) |
| H3 | Live environment lacked installed WeasyPrint despite `pyproject.toml` dependency — blocked S1b until install |
| H4 | Generated Redwolf CV contained an unsupported AWS certification claim → truth correctly failed (profile/generation corpus issue, not agent policy) |

---

## 14. Overall recommendation

### Ready with minor improvements

**Keep using BOPA now for:**

- Diagnosing readiness on `apply` Opportunities
- Coordinating prepare + truth after explicit material-benefit override when needed
- Trustworthy stops when truth blocks
- Safe operation with zero pipeline mutation

**Before treating as frictionless daily default:**

- Fix D1–D3 (error → owner action mapping; resume guidance)
- Document Doc1–Doc4 in an owner runbook
- Optionally land E1–E3

Do **not** weaken ToolPolicy, broaden the allow-list, redesign FR-015, or start FR-016 based on this trial.

---

## Appendix — artefact index

```
data/_oat001_phase3_bopa/
  summary.json                 # S2–S5 (+ S1) harness summary
  S1_fresh_assessed/
  S1b_fresh_override/          # override; WeasyPrint missing
  S1c_fresh_override_weasy/    # successful prepare+truth block+resume
  S1d_rerun_after_package/     # no duplicate prep/truth
  S2_submitted/
  S3_interviewing/
  S4_gold/
  S5_bronze_apply/
```
