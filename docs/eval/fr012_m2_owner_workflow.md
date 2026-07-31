# FR-012 M2 — Owner-Operable Assisted Submission Workflow

**Date:** 2026-07-31  
**Status:** Complete (M2) — historical milestone record. FR-012 closed out:
[fr012_submission_assistance.md](fr012_submission_assistance.md).
**Architecture:** Thin `cic submission` over frozen M1 `SubmissionOrchestrator`;
no new channels; no PipelineStatus; no FR-008 changes.  
**Preceding:** [M0](fr012_m0_submission_contracts.md),
[M1](fr012_m1_submission_orchestration.md)

---

## 1. Architectural decisions

| Decision | Choice | Why |
|----------|--------|-----|
| CLI surface | `check`, `run`, `record-manual`, `show`, `list` | Matches owner workflow; mirrors FR-010/011 thin adapters |
| Readiness | `SubmissionOrchestrator.check_readiness` | Gates stay in orchestrator; check never creates attempts |
| Approval flag | `--approve-submit` | Distinct from package / preparation `--approve` |
| Exit 0 | `submitted`, `manual_completed`, successful check/show/list | Fail-closed for MAR / failed / unknown / gates |
| Offline fake aid | `--fake-outcome` | Manual/CLI tests without network; not a product channel |
| No new policy | M1 duplicate / idempotency unchanged | M2 exposes capability; does not extend behaviour |

```
Owner
  → cic submission
  → SubmissionOrchestrator
  → SubmissionAdapter / AttemptStore
```

---

## 2. Implementation summary

| Command | Orchestrator call |
|---------|-------------------|
| `cic submission check` | `check_readiness` |
| `cic submission run` | `submit` |
| `cic submission record-manual` | `record_manual_completion` |
| `cic submission show` | `get_attempt` |
| `cic submission list` | `list_attempts` |

Headlines: Submission Ready / Completed / Manual Action Required / Outcome Unknown /
Duplicate Submission Blocked / Owner Approval Required / Attempt Recorded / …

---

## 3. Validation evidence

### CLI unit tests

`tests/unit/submission/test_cli.py` — check, run, show, list, record-manual,
approval required, duplicate blocked, manual-assisted, fake success, unknown outcome,
exit codes.

### Manual

```
python scripts/run_fr012_submission_manual.py cli --workspace data/_fr012_m2_manual
```

RESULT: PASS (offline).

### Full suite

```
python -m pytest -q
1145 passed in 25.33s
```

Baseline at M1 was 1136; M2 adds 9 focused CLI tests.

---

## 4. Documentation updated

| Document | Change |
|----------|--------|
| Functional specification | M2 complete; owner workflow commands |
| Domain model / testing / implementation notes | M2 coverage |
| Roadmap / changelog v1.71 | M2 status |
| AGENTS / README / repository guide | Current focus + CLI examples |

---

## 5. Technical debt

| Item | Classification | Notes |
|------|----------------|-------|
| `--fake-outcome` on CLI | accepted offline aid | Not a live channel; document as test-only |
| Force / unknown flags as long option names | accepted | Clarity over brevity |

---

## 6. Scope confirmation

| Constraint | Held |
|------------|------|
| No browser | Yes |
| No network | Yes |
| No PipelineStatus | Yes |
| No FR-008 modifications | Yes |
| No new submission channels | Yes |

---

## 7. Readiness for Close-out

**Ready.** Owner-operable assisted-manual submission is complete (M0–M2).
Close-out may freeze FR-012 and mark FR-013 next without further behaviour
changes, unless a concrete defect appears.

Validate first. Change second. Never silently submit.
