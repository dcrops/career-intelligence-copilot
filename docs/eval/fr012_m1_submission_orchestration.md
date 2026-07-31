# FR-012 M1 — Deterministic Submission Assistance

**Date:** 2026-07-31  
**Status:** Complete (M1) — historical milestone record. FR-012 closed out:
[fr012_submission_assistance.md](fr012_submission_assistance.md). Succeeded by
[M2 owner workflow](fr012_m2_owner_workflow.md).
**Architecture:** `SubmissionOrchestrator` + adapter contract + offline fake /
manual-assisted adapters; M0 contracts unchanged; FR-008 / PipelineStatus
untouched.  
**Preceding:** [FR-012 M0](fr012_m0_submission_contracts.md)

---

## 1. Architectural decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Orchestrator API | `submit`, `record_manual_completion`, `get_attempt`, `list_attempts` | Matches FR-011 style; separates adapter submit from owner attestation |
| Adapter contract | `SubmissionAdapter.execute(request) → SubmissionAdapterResult` | Minimal; adapters never persist or enforce policy |
| Offline adapters | `FakeSubmissionAdapter`, `ManualAssistedAdapter` | Deterministic tests; assisted-manual first; no network |
| Approval | Distinct `owner_approved_submit=True` | Not inferred from apply / package / FR-006/007 gates |
| Duplicate success | Block `(opportunity_id, channel)` success unless `force_new_attempt` + reason | Prevent accidental re-apply; auditable force |
| Open attempts | Reclaim `in_progress` / `manual_action_required`; no second adapter call | Idempotent reclaim |
| `outcome_unknown` | New attempt only with `acknowledge_prior_outcome_unknown=True` | Never auto-retry uncertainty |
| Prior `failed` | Allow new attempt | Documented retry after deterministic failure |
| Manual completion | New attempt or complete open assisted attempt; `result_code=manual_owner_completed` | Never pretends adapter submitted |
| Pipeline / FR-008 | Untouched | FR-013 owns lifecycle; FR-008 stays frozen |

```
OpportunityService
        │
        ▼
SubmissionOrchestrator
        ├── ApplicationPackageService.verify / get
        ├── SubmissionAdapter registry (fake | manual_assisted)
        └── SubmissionAttemptStore
```

---

## 2. Implementation summary

| Component | Role |
|-----------|------|
| `SubmissionOrchestrator` | Gates, sequencing, policy, outcome persistence |
| `SubmissionAdapter` protocol | Channel execute + structured result |
| `FakeSubmissionAdapter` | Fixture outcomes; call counting |
| `ManualAssistedAdapter` | Checklist → `manual_action_required` only |
| M0 store / transitions | Unchanged foundation |

Public surface: `career_intelligence.submission`.

---

## 3. Validation evidence

### Unit / functional

`tests/unit/submission/`, `tests/functional/test_fr012_submission.py`

| Check | Result |
|-------|--------|
| Gates (approval, apply, package, integrity, channel, destination) | Pass |
| Fake outcomes (submitted / failed / MAR / unknown) | Pass |
| Duplicate / force / reclaim / unknown ack / failed retry | Pass |
| Manual completion + closes open assisted | Pass |
| Adapters do not persist | Pass |
| Functional offline journey | Pass |

### Manual

```
python scripts/run_fr012_submission_manual.py --workspace data/_fr012_m1_manual
```

RESULT: PASS (offline).

### Full suite

```
python -m pytest -q
1136 passed in 25.81s
```

Baseline at M0 was 1113; M1 adds 23 focused orchestrator / functional tests.

---

## 4. Documentation updated

| Document | Change |
|----------|--------|
| Functional specification | FR-012 status M1 complete; milestone table |
| Domain model | Submission Attempt M1 behaviour |
| Testing strategy | M1 coverage |
| Implementation notes | M1 section |
| Roadmap | FR-012 M1 progress |
| Changelog | v1.70 |
| AGENTS / README / repository guide | Current focus M1 |

---

## 5. Technical debt

| Item | Classification | Notes |
|------|----------------|-------|
| Force / unknown ack encoded in evidence.message | accepted | Avoids M0 schema change; structured fields can wait for product evidence |
| Default destination always required for registered adapters | accepted | Matches assisted / fake needs; relax only with adapter evidence |
| No CLI | deliberate deferral | M2 |
| No resume of interrupted adapter mid-flight beyond reclaim | accepted | Open attempt reclaim is sufficient for M1 |

---

## 6. Scope confirmation

| Constraint | Held |
|------------|------|
| No CLI | Yes |
| No network | Yes |
| No browser automation | Yes |
| No PipelineStatus updates | Yes |
| No FR-008 changes | Yes |

---

## 7. Readiness for M2

**Ready.** Deterministic submission assistance is owner-callable via the public
orchestrator API. M2 may add a thin owner CLI / workflow interface without
reopening M1 policy unless a concrete defect appears.

Validate first. Change second. Never silently submit.
