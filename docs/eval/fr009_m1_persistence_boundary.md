# FR-009 M1 Acceptance Report — Pre-Review Opportunity Persistence & Derived Review Projection

**Milestone:** FR-009 M1 (of M0–M4 + close-out)  
**Status:** Complete — historical milestone record. FR-009 was closed on 2026-07-30
([FR-009 acceptance](fr009_opportunity_review_queue.md)).  
**Date:** 2026-07-30  
**Architecture:** [ADR-004](../adr/004_opportunity_review_boundary.md) (Accepted; implemented here)  
**Predecessor:** [FR-009 M0 acceptance](fr009_m0_domain_contracts.md)  
**Scope:** move Opportunity persistence before the owner-review interrupt with
exactly-one semantics; expose a minimal derived review projection. No owner queue
actions, duplicate detection, ranking calibration, UI, or pipeline tracking.

---

## 1. Implementation summary

Two changes, in priority order.

**Persistence boundary.** `persist` moved from the post-decision sequence into
`PRE_APPROVAL_SEQUENCE`, immediately after `strategy`. A successfully strategised job now
becomes a durable Opportunity with `decision=None` before the owner is asked anything.
`PersistOpportunityNode` no longer refuses to run unless the decision is `apply`, and
`OwnerReviewNode` asserts that `artefacts.opportunity_id` is set before it pauses, so the
interrupt cannot be reached without a durable record. After resume, all three
decisions — `apply`, `skip`, `defer` — run the same `record_decision` node against that
record. `APPLY_SIDE_EFFECT_SEQUENCE` was therefore renamed `POST_DECISION_SEQUENCE`
(containing `record_decision` only) and `apply_side_effects_complete` became
`post_decision_complete`; `SIDE_EFFECT_NODE_IDS` names the two nodes with externally
visible writes.

**Derived projection.** New package `career_intelligence.review_queue` provides
`ReviewQueueService`, a read-only query over `OpportunityService` with two scopes:
`list_awaiting_review` (no decision yet) and `list_active_opportunities` (still live,
including applied-for records). Eligibility is a pure function of persisted fields plus an
explicit reference date; ordering delegates unchanged to
`OpportunityComparisonService.compare_open`. Nothing about the queue is stored.

## 2. Workflow before and after

Before (FR-008):

```
Acquire → Validate → Analyse → Assess → Match → Strategy → Owner Review
  ├─ Apply → allocate id → Persist Opportunity → Record Decision → Complete
  ├─ Skip  → Complete   (no Opportunity)
  └─ Defer → Complete   (no Opportunity)
```

After (FR-009 M1):

```
Acquire → Validate → Analyse → Assess → Match → Strategy
  → allocate opportunity_id → checkpoint
  → Persist Opportunity (decision = None) → checkpoint
  → Owner Review  ← interrupt
  → resume with apply | skip | defer
  → Record Decision on the same opportunity_id → Complete
```

`describe_pre_approval_graph()` and `describe_post_decision_graph()` expose both halves
for inspection, and `completed_spike_nodes(state)` shows `persist` completing before
`owner_review`.

## 3. Idempotency proof

The mechanism is unchanged from FR-008 M2; only its position moved. Two independent
guards give exactly-one semantics:

1. **Pre-allocated identity.** `_run_loop` allocates `artefacts.opportunity_id`
   (`allocate_opportunity_id()`, a ULID) and checkpoints it *before* `persist` executes.
   `OpportunityService.create_from_strategy(opportunity_id=…)` returns the existing record
   when that id is already stored, so re-executing the node is a no-op rather than a
   second create. No id is ever allocated twice for one run, because allocation is
   conditional on `opportunity_id is None` and the checkpoint is written first.
2. **Completed-node routing.** `next_spike_node` skips nodes recorded in
   `completed_spike_nodes`, so a run resumed from a checkpoint that already passed
   `persist` never re-enters it at all.

`record_decision` is idempotent for a repeated identical decision and fails closed on a
conflicting one: `resume` refuses to change an accepted decision
(`Cannot change accepted owner decision`), and a completed run replayed with the same
decision returns the terminal state unchanged.

Evidence: `test_replayed_persist_node_reuses_the_existing_record`,
`test_repeating_the_same_decision_is_idempotent`,
`test_a_recorded_decision_is_not_silently_overwritten`,
`test_rerunning_the_workflow_after_a_lost_checkpoint_creates_no_duplicate`.

## 4. Crash-window outcomes

| Window | Situation | Observed behaviour | Test |
|--------|-----------|--------------------|------|
| A | Persist fails before owner review | Run pauses as resumable (`running`, error recorded, planned id retained); **no Opportunity, no approval request**; owner review never reached | `test_persist_failure_pauses_before_the_interrupt_and_creates_nothing` |
| B | Opportunity created, crash before checkpoint | Re-executing `persist` with the checkpointed planned id reclaims the same record; artefacts unchanged; one record | `test_replayed_persist_node_reuses_the_existing_record` |
| C | Checkpoint written, owner review interrupted | Reloaded run re-enters `owner_review` with the record already present and `decision=None`, visible as awaiting review | `test_crash_between_checkpoint_and_interrupt_resumes_into_owner_review` |
| D | Decision received, update fails | Run stays resumable and does **not** report completion; the decision remains accepted, so a retry re-applies the same decision | `test_decision_update_failure_prevents_false_completion` |
| E | Decision stored, crash before completion | Resume observes the stored decision, completes without rewriting it; still one record with one decision | `test_repeating_the_same_decision_is_idempotent`, `test_every_decision_updates_the_same_persisted_record` |

**Refinement to ADR-004 window A.** The ADR anticipated a "terminal/recoverable failure".
The implementation makes side-effect failures a *resumable pause* rather than a terminal
failure, matching how FR-008 M2 already treated `record_decision`, so a transient store
outage cannot discard completed FR-002–FR-005 analysis. The invariant the window
protects — no record, no approval request — is unchanged. Recorded in ADR-004
§ Implementation status.

## 5. Queue policy

| Rule | Behaviour |
|------|-----------|
| Scope `awaiting_review` | Eligible records with `decision is None` |
| Scope `active` | Eligible records regardless of `apply`; excludes `skip` |
| Exclusion: `archived` | `review.archived_at` set |
| Exclusion: `confirmed_duplicate` | `duplicate` relation present (owner-confirmed only; detection is M3) |
| Exclusion: `skipped` | `decision == "skip"` — record retained and auditable |
| Exclusion: `deferred` | `review.defer_until` later than the reference date; when no date is set, `decision == "defer"` |
| Exclusion: `closed` | Terminal `PipelineStatus` (`TERMINAL_STATUSES`, owned by FR-012) |
| Exclusion: `decided` | Awaiting scope only — a decision already exists |
| Ordering | `OpportunityComparisonService.compare_open`, unchanged at M1: pursuit posture → fit strength → application tier → `opportunity_id`. **Superseded by M4:** the tertiary key became `practical_value` |
| Explanation | Each item carries the M4 `reasons`; each exclusion carries its ordered reasons |
| Reference date | Explicit `reference_date` parameter; defaults to today (UTC) at the service edge, never read inside policy |
| Persistence | Nothing — eligibility, rank, and reasons are recomputed per query |

An undated defer is treated as manually deferred and holds until the owner reopens it,
because FR-008's owner-review boundary provides no defer date. `PipelineStatus` is never
written by FR-009: skipped and deferred records keep `assessed`.

## 6. Test evidence

**New unit tests — `tests/unit/orchestration/test_m1_pre_review_persistence.py` (11):**

| Test | Proves |
|------|--------|
| `test_opportunity_is_durable_before_the_owner_review_interrupt` | Reloadable record with `decision=None` exists at the pause |
| `test_checkpoint_carries_the_id_but_not_the_opportunity_record` | State contract: id + artefact references only |
| `test_persist_failure_pauses_before_the_interrupt_and_creates_nothing` | Window A |
| `test_replayed_persist_node_reuses_the_existing_record` | Window B; artefacts unchanged |
| `test_crash_between_checkpoint_and_interrupt_resumes_into_owner_review` | Window C |
| `test_every_decision_updates_the_same_persisted_record[apply\|skip\|defer]` | One record per decision path (3 cases) |
| `test_decision_update_failure_prevents_false_completion` | Window D |
| `test_a_recorded_decision_is_not_silently_overwritten` | Conflict fails closed |
| `test_repeating_the_same_decision_is_idempotent` | Window E |

**New unit tests — `tests/unit/review_queue/` (17):** eligibility for undecided, applied,
skipped, undated-defer, dated-defer, archived, confirmed-duplicate, and terminal-status
records; stable multi-reason ordering; policy purity; awaiting vs active scopes; M4
ordering preserved; stable id tie-break; reference-date behaviour; legacy records without
review keys; read-only guarantee; empty store.

**New functional tests — `tests/functional/test_fr009_review_queue.py` (5):** apply, skip,
and defer journeys end to end against real JSON/YAML stores in `tmp_path`; re-running
after a discarded checkpoint creates no duplicate; several analysed jobs queue in
deterministic order.

**Updated FR-008 tests (deliberate, per ADR-004):** `test_routing.py`,
`test_runner.py`, `test_m2_side_effects.py`, `test_fr008_workflow_execution.py`,
`test_fr008_job_acquisition.py`, `test_fr008_checkpoint_resume.py` — `persist` now
completes before `owner_review`, and "skip/defer create no Opportunity" became
"skip/defer retain the same record carrying that decision".

**Results:**

- Focused M1 suites — **33 passed**
- `tests/unit/opportunities` + `tests/unit/opportunity_comparison` +
  `tests/unit/orchestration` + `tests/unit/review_queue` + `tests/functional` —
  **347 passed**
- Full repository suite — **928 passed** (895 at M0 + 33 new; no regressions)
- Ruff on M1 files — **clean**; the seven pre-existing findings in touched
  orchestration/test files are unchanged from `HEAD` (two were incidentally resolved).
  Repository-wide lint debt (186 findings) was out of scope and left untouched.

## 7. Manual validation

`scripts/run_fr009_review_queue_manual.py demo --workspace data/_fr009_m1_manual
--offline-fixtures`, using three fixture postings (Data Engineer, AI Engineer, Applied AI
Engineer) in a scratch workspace, plus a read-only `queue` run against live
`data/opportunities/`.

| # | Check | Outcome |
|---|-------|---------|
| 1 | Three analysed jobs persisted before any owner decision (`decisions=[None, None, None]`) | **Pass** |
| 2 | Awaiting queue ordered deterministically with readable M4 reasons | **Pass** |
| 3 | Apply updated the existing record (`same_record=True`, `stored_decision=apply`) | **Pass** |
| 4 | Skip retained the record and removed it from both queues | **Pass** |
| 5 | Defer retained the record and removed it from the default queues | **Pass** |
| 6 | Replaying the completed apply run created no duplicate (`total_records=3`) | **Pass** |
| 7 | Ranking explanations understandable | **Minor issue** |
| 8 | Live store projects unchanged and unmigrated (16 records → 13 awaiting, 15 active, 1 skipped excluded; `index.yaml` byte-identical after querying) | **Pass** |

**Minor issue (7).** An applied record still shows the M4 reason "Recently assessed;
awaiting owner action" in the active queue. This is a **pre-existing M4 explanation text**
issue, not an M1 defect: `compare_open` composes reasons from `strategy_summary` and was
written when every persisted record was pre-decision. Classification: policy/wording
calibration, deferred to M4 where ranking explanations are reviewed. No code change made,
per "do not change ranking policy from a single validation example".

## 8. Backward compatibility

- **No migration and no live-data mutation.** The 16 existing records load and project
  unchanged; `data/opportunities/index.yaml` was byte-identical before and after the
  read-only queue run.
- **Old and new records coexist.** Records written under apply-only semantics (missing
  `review` / `duplicate` keys) read as "never reviewed, not a duplicate" and are ranked
  normally — covered by `test_records_written_before_review_metadata_still_project`.
- **Mixed stores tested:** apply-era records, `decision=None` records, new pre-review
  records, skipped, deferred (dated and undated), and archived records in one store.
- **Serialisation side effect unchanged from M0:** because `save()` rewrites the whole
  index, default review keys appear on existing rows the next time any record is written.
  Serialisation changes; meaning does not.
- **Public API impact is confined to orchestration.** Renamed exports
  (`POST_DECISION_SEQUENCE`, `post_decision_complete`, `describe_post_decision_graph`) are
  internal orchestration symbols; `career_intelligence.opportunities`,
  `career_intelligence.profile`, and the CLI are untouched. `career_intelligence.review_queue`
  is purely additive.

## 9. Deferred work

- Owner queue actions: pin / unpin, mark reviewed, defer until a date, archive / reopen (M2)
- Duplicate candidate detection and owner confirmation (M3)
- Ranking calibration, including the M4 explanation wording noted in §7 (M4)
- UI / CLI queue surfaces (not scheduled)
- Application pipeline tracking and `PipelineStatus` semantics (FR-012)
- Document packages and submission (FR-010, FR-011)

## 10. GO / NO-GO assessment

| Area | Result | Notes |
|------|--------|-------|
| Implementation | **PASS** | Persistence moved with the smallest viable routing change; all three decisions share one record |
| Idempotency | **PASS** | Pre-allocated id + completed-node routing; replay and re-run yield one record |
| Resume safety | **PASS** | Windows A–E covered; side-effect failures stay resumable; no false completion |
| Projection | **PASS** | Read-only derived queue with explicit exclusion reasons; nothing persisted |
| Testing | **PASS** | 33 new tests; 347 targeted; 928 full suite; no lint regressions |
| Manual validation | **PASS** | 7 of 8 Pass, 1 Minor issue (pre-existing M4 wording, deferred) |
| Documentation | **PASS** | Spec, domain model, notes, testing strategy, roadmap, changelog, ADR-004, this report |
| Backward compatibility | **PASS** | No migration, no live mutation, mixed stores tested |
| Architecture | **PASS** | One system of record; checkpoints remain recovery data; M4 sort key untouched |

### Recommendation

**GO for FR-009 M2** — owner queue actions (mark reviewed, pin, defer until, archive,
reopen) over the now-durable pre-review records, with reversibility and audit as M2's
primary risk.

M2 must not begin without explicit owner approval.

## 11. Verification commands

```
python -m pytest tests/unit/orchestration/test_m1_pre_review_persistence.py tests/unit/review_queue tests/functional/test_fr009_review_queue.py -q
python -m pytest tests/unit/opportunities tests/unit/opportunity_comparison tests/unit/orchestration tests/unit/review_queue tests/functional -q
python -m pytest -q
python -m ruff check src/career_intelligence/review_queue tests/unit/review_queue tests/unit/orchestration/test_m1_pre_review_persistence.py tests/functional/test_fr009_review_queue.py scripts/run_fr009_review_queue_manual.py
python scripts/run_fr009_review_queue_manual.py demo --workspace data/_fr009_m1_manual --offline-fixtures
python scripts/run_fr009_review_queue_manual.py queue --opportunities-dir data/opportunities
```
