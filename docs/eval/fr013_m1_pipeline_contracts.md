# FR-013 M1 — Application Pipeline Tracking Contracts

**Date:** 2026-08-05  
**Status:** Complete (M1) — contracts frozen. Succeeded by
[M2 tracking service](fr013_m2_pipeline_tracking.md).
**Architecture:** [ADR-005](../adr/005_application_pipeline_lifecycle.md) (Accepted)  
**Preceding:** [M0 engineering spike](fr013_m0_engineering_spike.md) (Accepted)

---

## 1. Architectural decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Aggregate / current SoT | **Opportunity** (`status` / `outcome` stored) | ADR-002/004; ranking already consumes status |
| Audit trail | Append-only **`PipelineEvent`** (`ple_<ULID>`) | Immutable history; corrections = new events |
| Package name | `career_intelligence.pipeline` | Lifecycle tracking distinct from submission |
| Status vocabulary | Existing coarse `PipelineStatus` + `InterviewStage` | Owner: no mega-enum |
| SubmissionAttempt → status | **Never automatic** | ADR-005 invariant; cite attempt as evidence only |
| Persistence | `data/pipeline_events/{opportunity_id}/` | Beside Opportunity; not SoT; not checkpoints |
| Opportunity writes | **Deferred to M2** | M1 = contracts + event store only |
| Tracking service / CLI | **Deferred to M2 / M3** | Same pattern as FR-012 M0 → M1 → M2 |

```
Owner (future service)
  → PipelineEventStore.append (M1)
       validates kind / transitions / evidence
       never writes Opportunity.status
```

---

## 2. Implementation summary

| API | Role |
|-----|------|
| `PipelineEvent` / `PipelineEvidence` / `PackageEvidenceRef` | Typed contracts |
| `validate_pipeline_status_change` | Forward allow-list or `correction=True` reopen |
| `validate_event_contract` | Fail-closed evidence rules by kind |
| `InMemoryPipelineEventStore` / `JsonDirectoryPipelineEventStore` | Append-only create / load / list |
| `new_pipeline_event_id` | `ple_<ULID>` |

Public surface: `career_intelligence.pipeline`.

Event kinds: `status_transition`, `interview_stage_change`, `outcome_change`,
`evidence_added`, `follow_up_set`, `correction`, `note`.

Actors: `owner` or `agent:<id>` (future FR-015; no agent behaviour in M1).

M1 does **not** implement `PipelineTrackingService`, Opportunity status dual-write,
CLI, FR-012 bridge behaviour, or reporting projections.

---

## 3. Validation results

### Unit

`tests/unit/pipeline/` — models, transitions/evidence, append-only store
(memory + JSON).

| Check | Result |
|-------|--------|
| Schema / id pattern | Pass |
| Package opportunity mismatch rejected | Pass |
| Allowed / illegal forward transitions | Pass |
| Correction may leave terminal | Pass |
| `submitted` requires substantive evidence | Pass |
| Correction requires note | Pass |
| `supersedes_event_id` only on correction | Pass |
| Append / load / list / filter / order | Pass |
| Duplicate append refused | Pass |
| No save/update/delete API | Pass |
| Attempt citation does not imply Opportunity write | Pass (store has no Opportunity API) |

### Full suite

`tests/unit/pipeline/` — **55 passed**. Opportunity + pipeline unit suites green
together (170 passed including opportunities). Broader suite depends on local
WeasyPrint install for package/PDF paths unrelated to M1.

---

## 4. Documentation updated

| Document | Change |
|----------|--------|
| ADR-005 | Accepted — hybrid lifecycle + SubmissionAttempt invariant |
| Functional specification | FR-013 M0 accepted; M1 contracts |
| Domain model | Pipeline Event entity |
| Testing strategy | FR-013 M1 coverage |
| Implementation notes | FR-013 M1 notes |
| Roadmap / changelog | FR-013 M1 progress |
| AGENTS / README | Current focus = FR-013 M1 complete; M2 next |
| ADR README | ADR-005 linked |
| M0 spike | Marked Accepted |

---

## 5. Technical debt

| Item | Classification | Notes |
|------|----------------|-------|
| Duplicate ULID helper vs submission / preparation | accepted for M1 | Avoids cross-package coupling |
| Forward allow-list delegated to `opportunities.transitions` | intentional | Single forward table until M2 unifies writers |
| Opportunity `update_outcome` still mutable without events | deliberate deferral | M2 service owns dual-write |
| No tracking service / CLI | deliberate deferral | M2 / M3 |

---

## 6. Recommendations for M2

| Recommendation | Classification |
|----------------|----------------|
| Implement `PipelineTrackingService` (append event + update Opportunity status/outcome) | M2 scope |
| Enforce ADR-005: no auto-advance from SubmissionAttempt success | M2 invariant tests |
| Owner operations: record submitted / advance / outcome / note / correction | M2 scope |
| Thin CLI | M3 (capability first) |

Validate first. Change second.

---

## 7. Readiness for M2

**Ready.** Contracts, transitions, evidence rules, ADR-005, and append-only
persistence are frozen as the M1 foundation. M2 may introduce the tracking service
and Opportunity dual-write without reopening M1 schemas unless a concrete defect
appears.
