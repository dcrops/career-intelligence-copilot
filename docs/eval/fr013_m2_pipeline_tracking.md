# FR-013 M2 — Pipeline Tracking Service

**Date:** 2026-08-05  
**Status:** Complete (M2) — succeeded by
[M3 owner workflow](fr013_m3_owner_workflow.md).
**Architecture:** [ADR-005](../adr/005_application_pipeline_lifecycle.md)  
**Preceding:** [M1 contracts](fr013_m1_pipeline_contracts.md)  
**Next:** M3 owner CLI + FR-012/package evidence bridges (not started)

---

## 1. Architecture decision — coordinated persistence

Two stores must stay consistent without a cross-file DB transaction:

| Store | Role |
|-------|------|
| `data/pipeline_events/` | Append-only audit (immutable) |
| `data/opportunities/` | Stored current `PipelineStatus` / `OutcomeRecord` |

### Decision: **event-first dual write**

```
validate (fail closed, no writes)
  → append PipelineEvent
  → project onto Opportunity (if kind touches lifecycle fields)
```

| Concern | Policy |
|---------|--------|
| Validation before writes | `validate_event_contract` + `from_status == Opportunity.status` before append |
| Write ordering | **Event first**, Opportunity second |
| Partial failure | Event durable + Opportunity not updated → `PipelinePartialWriteError` |
| Idempotent retry | `apply_stored_event(event_id)` or owner op with existing `event_id` |
| Divergence detection | `detect_divergence` / `require_consistent` |
| Recovery | `reconcile` re-projects folded event history onto Opportunity |
| Event-only kinds | `note`, `evidence_added` — no Opportunity write |
| Terminal correction | `correct_status` → `correction` event + `allow_terminal_reopen` |
| FR-012 auto-advance | **Forbidden** (ADR-005) |

**Why not Opportunity-first?** A successful Opportunity write with a failed event
append would advance queryable status without audit — worse than an auditable
event waiting for projection retry.

---

## 2. Service API

`career_intelligence.pipeline.PipelineTrackingService`

| Method | Role |
|--------|------|
| `apply_event` | Validate → append (if new) → project |
| `apply_stored_event` | Idempotent recovery / re-project |
| `advance_status` / `record_submitted` | Owner status advances |
| `change_interview_stage` / `change_outcome` / `set_follow_up` | Field updates |
| `add_note` / `add_evidence` | Event-only audit |
| `correct_status` | Terminal reopen via correction event |
| `list_events` / `get_opportunity` | Reads |
| `detect_divergence` / `require_consistent` / `reconcile` | Consistency |

Supporting: `OpportunityService.apply_pipeline_projection` (same-status idempotent;
`allow_terminal_reopen` for corrections).

---

## 3. Implementation summary

| Component | Delivered |
|-----------|-----------|
| `pipeline/service.py` | `PipelineTrackingService` |
| `pipeline/projection.py` | Per-event + folded history projection |
| `opportunities/service.py` | `apply_pipeline_projection` |
| Errors | `PipelinePartialWriteError`, `PipelineConsistencyError`, `PipelineDivergenceError` |
| Tests | `tests/unit/pipeline/test_service.py`, `tests/functional/test_fr013_pipeline_tracking.py` |
| Manual | `scripts/run_fr013_pipeline_manual.py demo` |

**Not in M2:** CLI, FR-012 auto-bridge, reporting projections (M3/M4).

---

## 4. Failure semantics

| Scenario | Behaviour |
|----------|-----------|
| Illegal transition / missing evidence | Fail before any write |
| Stale `from_status` | `PipelineConsistencyError`; no write |
| Event append fails | No Opportunity change |
| Event ok, Opportunity save fails | `PipelinePartialWriteError(event_id=…)`; retry via `apply_stored_event` |
| Same `event_id`, different payload | `PipelineConsistencyError` |
| Same `event_id`, recovery | Skip append; re-project; idempotent |
| Divergent Opportunity vs events | `detect_divergence`; fix with `reconcile` |
| Mistaken terminal status | `correct_status` appends correction; never mutates prior events |

---

## 5. Tests

| Suite | Result |
|-------|--------|
| `tests/unit/pipeline/` | Pass (incl. M2 service coordination) |
| `tests/functional/test_fr013_pipeline_tracking.py` | Pass |
| Opportunity decision/outcome unit | Pass (no regression) |

Covered: validation-before-write, partial failure + retry, idempotent complete,
divergence + reconcile, terminal correction, status/outcome/interview consistency,
no auto-advance API, JSON persistence round-trip.

---

## 6. Manual validation

```bash
python scripts/run_fr013_pipeline_manual.py demo --workspace data/_fr013_m2_manual
```

**RESULT: PASS** — advance → submit → interview → injected partial failure →
`apply_stored_event` recovery → `divergent=False`.

---

## 7. Documentation updated

Functional spec, domain model, testing strategy, implementation notes, roadmap,
changelog, AGENTS/README, ADR-005 consequences, this eval.

---

## 8. Readiness for M3

**Ready.** Tracking service and dual-write semantics are frozen. M3 may add thin
CLI and optional “cite SubmissionAttempt” helpers without silent auto-advance.
